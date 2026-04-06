import React, { useState } from "react";

type UserProfile = {
  avatar: string;
  name: string;
  bio: string;
};

const mockUser: UserProfile = {
  avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=300&q=80",
  name: "Lena Hart",
  bio: "Designs structured AI workflows and writes careful evaluation plans.",
};

export default function UserProfileCard() {
  const [isFollowing, setIsFollowing] = useState(false);

  return (
    <div className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto w-full max-w-sm rounded-3xl bg-white p-6 shadow-xl">
        <div className="flex flex-col items-center text-center">
          <img
            src={mockUser.avatar}
            alt={mockUser.name}
            className="h-24 w-24 rounded-full object-cover ring-4 ring-sky-100"
          />
          <h1 className="mt-4 text-2xl font-bold text-slate-900">{mockUser.name}</h1>
          <p className="mt-3 text-sm leading-6 text-slate-500">{mockUser.bio}</p>
          <button
            type="button"
            onClick={() => setIsFollowing((previous) => !previous)}
            className={`mt-6 rounded-2xl px-5 py-3 text-sm font-semibold transition ${
              isFollowing
                ? "bg-slate-900 text-white hover:bg-slate-700"
                : "bg-sky-600 text-white hover:bg-sky-700"
            }`}
          >
            {isFollowing ? "Following" : "Follow"}
          </button>
        </div>
      </div>
    </div>
  );
}
