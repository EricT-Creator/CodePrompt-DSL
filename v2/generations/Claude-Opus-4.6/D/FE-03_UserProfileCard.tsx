import React, { useState } from "react";

const userData = {
  avatar: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200&h=200&fit=crop",
  name: "林小溪",
  bio: "热爱记录生活的设计师，相信好的界面源于对用户的尊重。平日喜欢阅读和慢跑。",
};

export default function UserProfileCard() {
  const [followed, setFollowed] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <div className="w-full max-w-xs bg-white rounded-2xl shadow p-6 text-center">
        <img
          src={userData.avatar}
          alt={userData.name}
          className="w-24 h-24 rounded-full mx-auto object-cover border-4 border-slate-100"
        />
        <h1 className="mt-3 text-lg font-bold text-slate-800">{userData.name}</h1>
        <p className="mt-2 text-sm text-slate-500 leading-relaxed">{userData.bio}</p>

        <button
          type="button"
          onClick={() => setFollowed((p) => !p)}
          className={`mt-5 w-full py-2.5 rounded-lg text-sm font-semibold transition ${
            followed
              ? "bg-slate-200 text-slate-700 hover:bg-slate-300"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}
        >
          {followed ? "已关注" : "关注"}
        </button>
      </div>
    </div>
  );
}
