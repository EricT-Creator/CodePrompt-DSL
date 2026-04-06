import React, { useState } from "react";

type Profile = {
  avatar: string;
  username: string;
  summary: string;
};

const mockProfile: Profile = {
  avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=300&q=80",
  username: "Noah Lee",
  summary: "Builds internal tools, keeps data tidy, and enjoys clean interface details.",
};

export default function UserProfileCard() {
  const [followed, setFollowed] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-b from-violet-50 to-white px-4 py-10">
      <div className="mx-auto w-full max-w-sm overflow-hidden rounded-3xl border border-violet-100 bg-white shadow-lg shadow-violet-100/70">
        <div className="h-24 bg-gradient-to-r from-violet-500 to-fuchsia-500" />
        <div className="-mt-12 px-6 pb-6">
          <img
            src={mockProfile.avatar}
            alt={mockProfile.username}
            className="h-24 w-24 rounded-full border-4 border-white object-cover shadow-md"
          />
          <div className="mt-4">
            <div className="text-sm font-semibold uppercase tracking-[0.18em] text-violet-500">Creator profile</div>
            <h1 className="mt-2 text-2xl font-bold text-slate-900">{mockProfile.username}</h1>
            <p className="mt-3 text-sm leading-6 text-slate-500">{mockProfile.summary}</p>
          </div>
          <button
            type="button"
            onClick={() => setFollowed((previous) => !previous)}
            className={`mt-6 w-full rounded-2xl px-4 py-3 text-sm font-semibold transition ${
              followed
                ? "bg-slate-900 text-white hover:bg-slate-700"
                : "bg-violet-600 text-white hover:bg-violet-700"
            }`}
          >
            {followed ? "Following" : "Follow"}
          </button>
        </div>
      </div>
    </div>
  );
}
