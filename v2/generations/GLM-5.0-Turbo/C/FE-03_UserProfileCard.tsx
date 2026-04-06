import React, { useState } from "react";

export default function UserProfileCard() {
  const [followed, setFollowed] = useState(false);

  return (
    <div className="flex min-h-screen items-center justify-center bg-stone-100 p-4">
      <div className="w-full max-w-xs rounded-xl bg-white p-5 shadow-md">
        <div className="flex items-center gap-4">
          <img
            src="https://api.dicebear.com/7.x/avataaars/svg?seed=carol"
            alt="avatar"
            className="h-14 w-14 rounded-full bg-stone-200"
          />
          <div className="flex-1">
            <h2 className="text-base font-semibold text-stone-800">Carol Wu</h2>
            <p className="mt-0.5 text-xs text-stone-500">DevOps engineer & cloud nerd</p>
          </div>
        </div>
        <button
          onClick={() => setFollowed(!followed)}
          className={`mt-4 w-full rounded-md py-1.5 text-sm font-medium transition ${
            followed ? "bg-stone-100 text-stone-600" : "bg-stone-800 text-white hover:bg-stone-700"
          }`}
        >
          {followed ? "已关注" : "关注"}
        </button>
      </div>
    </div>
  );
}
