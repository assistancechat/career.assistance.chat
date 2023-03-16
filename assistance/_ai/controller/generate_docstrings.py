# Copyright (C) 2023 Assistance.Chat contributors

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import json
import shutil
import textwrap

import aiofiles

from assistance._config import DEFAULT_OPENAI_MODEL
from assistance._embeddings import get_closest_functions
from assistance._keys import get_openai_api_key
from assistance._logging import log_info
from assistance._openai import get_completion_only
from assistance._paths import AI_REGISTRY_DIR

from .indexer import hash_for_docstring

OPEN_AI_API_KEY = get_openai_api_key()

MODEL_KWARGS = {
    "engine": DEFAULT_OPENAI_MODEL,
    "max_tokens": 2048,
    "temperature": 0,
}


DOCSTRING_INSTRUCTIONS = textwrap.dedent(
    """
        When you write a docstring it is to be in the numpydoc format.

        When writing a docstring do not include examples or notes.
        Keep the function referred to by the docstring as simple as
        possible, but no simpler.
    """
).strip()


INITIAL_PROMPT = (
    textwrap.dedent(
        """\
        # Writing a docstring for a function to fulfil a task

        ## Instructions

        {DOCSTRING_INSTRUCTIONS}

        ## Your task

        {task}

        ## Example response

        Calls a large language model (LLM) with the given prompt and
        returns the generated response.

        Parameters
        ----------
        prompt : str
            The input prompt to be used when calling the LLM.

        Returns
        -------
        str
            The generated response from the LLM

        ## Your response
"""
    )
    .strip()
    .replace("{DOCSTRING_INSTRUCTIONS}", DOCSTRING_INSTRUCTIONS)
)


PROMPT = (
    textwrap.dedent(
        r"""\
        # Writing a list of child docstrings for a parent docstring

        ## Instructions

        You are a single component of an AI cluster.

        You are aiming to create a list of child docstrings in order to
        help the cluster of AI agents write a library of functions that
        achieves the original task.

        DO NOT create docstrings for the original task itself, other
        AI agents will be doing that. Instead, only create docstrings
        for functions that will be explicitly helpful in the creation
        of your given parent docstring.

        {DOCSTRING_INSTRUCTIONS}

        ## Your parent docstring

        {docstring}

        ## The original task

        {task}

        ## Required JSON format

        [
            "<1st docstring>",
            "<2nd docstring>",
            ...
            "<nth docstring>"
        ]

        ## First example response

        [
            "Calls a large language model (LLM) with the given prompt and\nreturns the generated response.\n\nParameters\n----------\nprompt : str\n    The input prompt to be used when calling the LLM.\n\nReturns\n-------\nstr\n    The generated response from the LLM based on the input prompt.",
            "Returns the current date and time in ISO format.\n\nReturns\n-------\nstr\n    The current date and time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS).",
            "Uses a large language model (LLM) to generate a summary of the\ninput text based on the given instruction.\n\nParameters\n----------\ntext : str\n    The input text to be summarized by the LLM.\ninstruction : str\n    The instruction to guide the LLM in generating a focused summary\n    of the input text.\n\nReturns\n-------\nstr\n    The focused summary of the input text generated by the LLM based on\n    the provided instruction."
        ]


        ## Second example response

        []

        ## Third example response

        [
            "Extracts all email addresses from the input text using a regular expression pattern.\n\nParameters\n----------\ntext : str\n    The input text to extract email addresses from.\n\nReturns\n-------\nlist[str]\n    The list of email addresses extracted from the input text."
        ]

        ## Your JSON response (ONLY respond with JSON, nothing else)
    """
    )
    .strip()
    .replace("{DOCSTRING_INSTRUCTIONS}", DOCSTRING_INSTRUCTIONS)
)

SIMILAR_PROMPT = textwrap.dedent(
    """\
        # Docstring comparison

        ## Instructions

        You are comparing a base docstring to a series of similar
        docstrings. It is your goal to determine which of the docstrings
        is most similar to the base docstring.

        You are then to determine if the function produced by the most
        similar docstring is the same as the function produced by the
        base docstring.

        ## Base docstring

        {base_docstring}

        ## Similar docstrings

        {similar_docstrings}

        ## Required JSON format

        {{
            "think step by step": "<step by step reasoning>",
            "most similar": <index of most similar docstring>,
            "same function": <true or false>,
            "explanation": "<explanation>"
        }}

        ## Your JSON response (ONLY respond with JSON, nothing else)
"""
).strip()


Tree = dict[str, list["Tree"]]


async def generate_docstrings_tree(scope: str, task: str, max_depth: int):
    root_docstring = await get_completion_only(
        scope=scope,
        prompt=INITIAL_PROMPT.format(task=task),
        api_key=OPEN_AI_API_KEY,
        **MODEL_KWARGS,
    )

    root_docstring_hash = None

    tree = None
    for i in range(max_depth):
        root_docstring_hash = await _generate_docstrings(
            scope,
            task,
            docstring=root_docstring,
            already_traversing=set(),
            max_depth=i,
            parent=None,
        )
        # previous_tree = tree
        # tree = await _dependency_walk(root_docstring_hash, max_depth=max_depth - 1)

        # if tree == previous_tree:
        #     break

    assert root_docstring_hash is not None
    # assert tree is not None

    return tree


async def _dependency_walk(
    docstring_hash: str,
    max_depth: int,
    current_depth=0,
) -> Tree:
    dependencies_registry_path = _get_dependencies_registry_dir(docstring_hash)

    async with aiofiles.open(dependencies_registry_path, "r") as f:
        dependencies: list[str] = json.loads(await f.read())

    coroutines = [
        _dependency_walk(dependency, max_depth, current_depth + 1)
        for dependency in dependencies
    ]

    try:
        sub_trees = await asyncio.gather(*coroutines)
    except FileNotFoundError as e:
        raise ValueError(
            f"While processing {docstring_hash} a dependency was not found"
        ) from e

    tree = {docstring_hash: sub_trees}

    return tree


def _get_docstring_registry_path(docstring_hash: str):
    docstring_registry_path = AI_REGISTRY_DIR.joinpath(
        "docstrings", f"{docstring_hash}.txt"
    )

    return docstring_registry_path


def _get_dependencies_registry_dir(docstring_hash: str):
    dir = AI_REGISTRY_DIR.joinpath("dependencies", docstring_hash)
    dir.mkdir(exist_ok=True)

    return dir


def _get_dependents_registry_dir(docstring_hash: str):
    dir = AI_REGISTRY_DIR.joinpath("dependents", docstring_hash)
    dir.mkdir(exist_ok=True)

    return dir


async def _generate_docstrings(
    scope: str,
    task: str,
    already_traversing: set[str],
    docstring: str,
    max_depth: int,
    parent: str | None,
    current_depth=0,
) -> str | None:
    docstring_hash = hash_for_docstring(docstring)
    if docstring_hash in already_traversing:
        return docstring_hash

    already_traversing.add(docstring_hash)
    # log_info(scope, already_traversing)

    if current_depth >= max_depth:
        return docstring_hash

    docstring_registry_path = _get_docstring_registry_path(docstring_hash)
    dependents_registry_dir = _get_dependents_registry_dir(docstring_hash)
    dependencies_registry_dir = _get_dependencies_registry_dir(docstring_hash)

    similar_docstrings_to_check_against = await get_closest_functions(
        openai_api_key=OPEN_AI_API_KEY, docstring=docstring
    )

    try:
        similar_docstrings_to_check_against.remove(docstring)
    except ValueError:
        pass

    if len(similar_docstrings_to_check_against) != 0:
        similar_docstrings_with_indices = [
            f"[{i}]\n{item}"
            for i, item in enumerate(similar_docstrings_to_check_against)
        ]
        similar_docstrings_text = "\n\n---\n\n".join(similar_docstrings_with_indices)
        is_it_the_same_data = await _run_with_error_loop(
            scope=scope,
            prompt=SIMILAR_PROMPT.format(
                base_docstring=docstring, similar_docstrings=similar_docstrings_text
            ),
            api_key=OPEN_AI_API_KEY,
            model_kwargs=MODEL_KWARGS,
        )

        # Sometimes the LLM puts in a non-empty string like "unknown"
        if is_it_the_same_data["same function"] is True:
            index_of_most_similar = is_it_the_same_data["most similar"]
            similar_docstring = similar_docstrings_to_check_against[
                index_of_most_similar
            ]

            similar_docstring_hash = hash_for_docstring(similar_docstring)

            if similar_docstring_hash == parent:
                docstring_registry_path.unlink()
                shutil.rmtree(dependencies_registry_dir)
                shutil.rmtree(dependencies_registry_dir)
                for path in dependents_registry_dir.glob("*"):
                    dependent = path.stem
                    dependent_dependency_dir = _get_dependencies_registry_dir(dependent)

                    old_dependency_path = dependent_dependency_dir / docstring_hash
                    old_dependency_path.unlink()

                    return None

            similar_function_docstring_path = _get_docstring_registry_path(
                similar_docstring_hash
            )

            # Don't use aio, want this to run sequentially
            if similar_function_docstring_path.exists():
                docstring_registry_path.unlink()
                shutil.rmtree(dependencies_registry_dir)
                for path in dependents_registry_dir.glob("*"):
                    dependent = path.stem
                    dependent_dependency_dir = _get_dependencies_registry_dir(dependent)

                    old_dependency_path = dependent_dependency_dir / docstring_hash
                    new_dependency_path = (
                        dependent_dependency_dir / similar_docstring_hash
                    )
                    old_dependency_path.rename(new_dependency_path)

                return await _generate_docstrings(
                    scope,
                    task=task,
                    docstring=similar_docstring,
                    max_depth=max_depth,
                    current_depth=current_depth,
                    already_traversing=already_traversing,
                    parent=parent,
                )

    async with aiofiles.open(docstring_registry_path, "w") as f:
        file_contents = docstring + "\n"
        await f.write(file_contents)

    if parent is not None:
        (dependents_registry_dir / parent).touch()

    log_info(scope, f"Generating child docstrings for {docstring_hash[0:8]}")
    child_docstrings = await _run_with_error_loop(
        scope=scope,
        prompt=PROMPT.format(task=task, docstring=docstring),
        api_key=OPEN_AI_API_KEY,
        model_kwargs=MODEL_KWARGS,
    )

    coroutines = []
    for child_docstring in child_docstrings:
        coroutines.append(
            _generate_docstrings(
                scope,
                task=task,
                docstring=child_docstring,
                max_depth=max_depth,
                current_depth=current_depth + 1,
                already_traversing=already_traversing,
                parent=docstring_hash,
            )
        )

    child_docstring_hashes = await asyncio.gather(*coroutines)

    for child_hash in child_docstring_hashes:
        (dependencies_registry_dir / child_hash).touch()

    return docstring_hash


ERROR_MESSAGE_TEMPLATE = textwrap.dedent(
    """
        # Error Message

        You previously attempted the prompt below, however, when
        attempting to run `json.loads(response)` on the response you
        previously provided the following error was raised:

        {error}

        The response you previously provided was:

        {response}
    """
).strip()


async def _run_with_error_loop(scope, prompt, api_key, model_kwargs, prepend=""):
    error_message = ""

    while True:
        response = await get_completion_only(
            scope=scope,
            prompt=error_message + prompt,
            api_key=api_key,
            **model_kwargs,
        )

        response = prepend + response

        log_info(scope, response)

        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            error_message = (
                ERROR_MESSAGE_TEMPLATE.format(error=repr(e), response=response) + "\n\n"
            )
            continue

        return data
