import React, { useState } from "react";

export default function UserProfileCard() {
  const [isFollowed, setIsFollowed] = useState(false);

  const profile = {
    username: "Bob Park",
    description: "UI/UX designer. Love creating beautiful interfaces.",
    picture: "https://api.dicebear.com/7.x/avataaars/svg?seed=bob",
  };

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-md w-full max-w-sm p-6 flex flex-col items-center">
        <img src={profile.picture} alt={profile.username} className="w-20 h-20 rounded-full bg-slate-200 mb-3" />
        <h1 className="text-xl font-bold text-slate-900">{profile.username}</h1>
        <p className="text-sm text-slate-500 mt-1 text-center">{profile.description}</p>
        <button
          onClick={() => setIsFollowed(!isFollowed)}
          className={`mt-4 px-6 py-2 rounded-lg text-sm font-medium transition ${
            isFollowed
              ? "bg-slate-100 text-slate-600 border border-slate-300 hover:bg-slate-200"
              : "bg-indigo-500 text-white hover:bg-indigo-600"
          }`}
        >
          {isFollowed ? "Unfollow" : "Follow"}
        </button>
      </div>
    </div>
  );
}
