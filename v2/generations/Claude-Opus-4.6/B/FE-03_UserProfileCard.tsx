import React, { useState } from "react";

interface UserData {
  avatarUrl: string;
  username: string;
  bio: string;
}

const user: UserData = {
  avatarUrl: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop",
  username: "Sofia Chen",
  bio: "Product designer passionate about accessible interfaces. Sketches ideas before pushing pixels.",
};

export default function UserProfileCard() {
  const [isFollowing, setIsFollowing] = useState(false);

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-md p-6 text-center">
        <img
          src={user.avatarUrl}
          alt={user.username}
          className="w-24 h-24 rounded-full mx-auto object-cover ring-2 ring-indigo-100"
        />
        <h1 className="mt-4 text-lg font-bold text-slate-900">{user.username}</h1>
        <p className="mt-2 text-sm text-slate-500 leading-relaxed">{user.bio}</p>

        <button
          type="button"
          onClick={() => setIsFollowing((prev) => !prev)}
          className={`mt-6 px-6 py-2 rounded-md text-sm font-medium transition ${
            isFollowing
              ? "bg-slate-200 text-slate-700 hover:bg-slate-300"
              : "bg-indigo-600 text-white hover:bg-indigo-700"
          }`}
        >
          {isFollowing ? "Following" : "Follow"}
        </button>
      </div>
    </div>
  );
}
