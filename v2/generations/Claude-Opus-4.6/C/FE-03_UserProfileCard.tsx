import React, { useState } from "react";

const profile = {
  avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop",
  name: "Marcus Obi",
  bio: "Data engineer by day, open-source contributor by night. Likes clean pipelines and strong coffee.",
};

export default function UserProfileCard() {
  const [followed, setFollowed] = useState(false);

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
      <div className="w-full max-w-xs rounded-2xl bg-white shadow-lg p-6 flex flex-col items-center">
        <img
          src={profile.avatar}
          alt={profile.name}
          className="w-20 h-20 rounded-full object-cover ring-4 ring-emerald-50"
        />
        <h2 className="mt-4 text-lg font-bold text-gray-900">{profile.name}</h2>
        <p className="mt-2 text-center text-sm text-gray-500 leading-relaxed">
          {profile.bio}
        </p>
        <button
          type="button"
          onClick={() => setFollowed((v) => !v)}
          className={`mt-5 w-full py-2.5 rounded-xl text-sm font-semibold transition ${
            followed
              ? "bg-gray-100 text-gray-700 hover:bg-gray-200"
              : "bg-emerald-600 text-white hover:bg-emerald-700"
          }`}
        >
          {followed ? "Following" : "Follow"}
        </button>
      </div>
    </div>
  );
}
