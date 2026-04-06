import React, { useState } from "react";

export default function UserProfileCard() {
  const [isFollowed, setIsFollowed] = useState(false);

  const userInfo = {
    displayName: "林小明",
    introduction: "全栈工程师，热爱开源与技术写作。",
    profileImg: "https://api.dicebear.com/7.x/avataaars/svg?seed=linxm",
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-teal-50 to-white flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-xs overflow-hidden">
        <div className="h-24 bg-gradient-to-r from-teal-400 to-emerald-400" />
        <div className="px-5 pb-5 -mt-10 text-center">
          <img
            src={userInfo.profileImg}
            alt="头像"
            className="w-16 h-16 rounded-full border-4 border-white bg-gray-200 mx-auto"
          />
          <h2 className="mt-2 text-lg font-bold text-gray-800">{userInfo.displayName}</h2>
          <p className="text-sm text-gray-500 mt-1">{userInfo.introduction}</p>
          <button
            onClick={() => setIsFollowed(!isFollowed)}
            className={`mt-4 w-full py-2 rounded-xl text-sm font-semibold transition-colors ${
              isFollowed
                ? "bg-gray-100 text-gray-600 border border-gray-200"
                : "bg-teal-500 text-white hover:bg-teal-600"
            }`}
          >
            {isFollowed ? "已关注" : "关注"}
          </button>
        </div>
      </div>
    </div>
  );
}
