import { ArrowDownCircleIcon } from "@heroicons/react/24/solid";

import StartChatWithQuestionButton from "@/components/atoms/StartChatWithQuestionButton";

const DATA = {
  blurb1: "It's time to align your faith with your future",
  blurb2:
    "The courses at Alphacrucis are designed to provide you with an unique Christian experience. ",
  blurb3:
    "We offer a range of courses that will help you to grow in your faith and develop your skills.",
  video: {
    link: "https://www.youtube.com/embed/wds7y_0rix4?",
    title: "Thank you",
  },
  LearnButton: {
    text: "Alphacrucis counselling at a glance",
    link: "https://www.ac.edu.au/healthbrochure",
  },
  ChatButton1: {
    text: "Do I qualify for FEE-HELP?",
    link: "#Chat",
  },
  ChatButton2: {
    text: "What's the best course for me?",
    link: "#Chat",
  },
};

export default function MoreInfo() {
  return (
    <div className="relative bg-white">
      <div className="mx-auto max-w-full lg:grid lg:grid-cols-12 lg:gap-x-8 lg:px-8">
        <div className="px-6 pt-10 pb-24 sm:pb-32 lg:col-span-5 lg:px-0 lg:pb-56 ">
          <div className="mx-auto space-y-12 max-w-2xl lg:mx-0">
            <h1 className="pt-4 mt-10 text-5xl capitalize tracking-normal leading-none border-orange-400 border-t-4 border-orange-500">
              {DATA.blurb1}
            </h1>
            <h3 className="text-xl w-4/5 tracking-wide leading-tight font-light text-gray-800">
              The courses at Alphacrucis are designed to provide you with an
              unique Christian worldview. A range of courses that will help you
              grow your faith and develop your skills for the kingdom.
            </h3>
            <StartChatWithQuestionButton
              question={DATA.ChatButton1.text}
              buttonClassName="inline-flex h-max w-max space-x-2 animate-pulse relative h-4/6 w-4/6 place-self-center place-content-evenly self-end items-center rounded-md border border-transparent shadow-sm hover:bg-white focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 lg:justify-self-center lg:h-1/2"
              bubbleClassName="w-10 h-10 self-center text-orange-600"
              textClassName="self-center leading-none text-black text-sm uppercase"
            />
            <div className="h-11">
              <button
                type="button"
                href={DATA.LearnButton.link}
                className="inline-flex items-center rounded-md border uppercase border-transparent bg-orange-400 px-4 py-2 text-base font-medium text-white shadow-sm hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              >
                <ArrowDownCircleIcon
                  className="-ml-1 mr-3 h-8 w-8"
                  aria-hidden="true"
                />
                {DATA.LearnButton.text}{" "}
              </button>
            </div>
          </div>
        </div>

        <div className="relative lg:col-span-7 xl:inset-0">
          <iframe
            className="w-full h-screen p-4 bg-gray-50 object-cover lg:p-6"
            src={DATA.video.link}
            title={DATA.video.title}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
          />
        </div>
      </div>
    </div>
  );
}