import React, { useState } from "react";

const user = {
  avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=300&q=80",
  name: "Iris Song",
  intro: "Likes careful experiments, concise documentation, and interfaces that explain themselves.",
};

export default function UserProfileCard() {
  const [followed, setFollowed] = useState(false);

  return (
    <div className="min-h-screen bg-rose-50 px-4 py-12">
      <div className="mx-auto w-full max-w-sm rounded-[28px] bg-white p-6 shadow-lg shadow-rose-100/70">
        <div className="text-center">
          <img
            src={user.avatar}
            alt={user.name}
            className="mx-auto h-24 w-24 rounded-full object-cover ring-4 ring-rose-100"
          />
          <h1 className="mt-4 text-2xl font-bold text-slate-900">{user.name}</h1>
          <p className="mt-3 text-sm leading-6 text-slate-500">{user.intro}</p>
          <button
            type="button"
            onClick={() => setFollowed((previous) => !previous)}
            className={`mt-6 rounded-2xl px-5 py-3 text-sm font-semibold transition ${
              followed ? "bg-slate-900 text-white hover:bg-slate-700" : "bg-rose-500 text-white hover:bg-rose-600"
            }`}
          >
            {followed ? "Following" : "Follow"}
          </button>
        </div>
      </div>
    </div>
  );
}
