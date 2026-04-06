import React, { useState } from "react";

const mockUser = {
  avatar: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200&h=200&fit=crop",
  name: "Alex Rivera",
  bio: "Full-stack developer who enjoys building delightful interfaces and experimenting with AI-assisted code generation workflows.",
};

export default function UserProfileCard() {
  const [following, setFollowing] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-xs bg-white rounded-2xl shadow-lg overflow-hidden">
        <div className="h-20 bg-gradient-to-r from-blue-500 to-purple-500" />
        <div className="px-6 pb-6 -mt-10 text-center">
          <img
            src={mockUser.avatar}
            alt={mockUser.name}
            className="w-20 h-20 rounded-full border-4 border-white mx-auto object-cover shadow"
          />
          <h2 className="mt-3 text-lg font-bold text-gray-900">{mockUser.name}</h2>
          <p className="mt-2 text-sm text-gray-500 leading-relaxed">
            {mockUser.bio}
          </p>
          <button
            type="button"
            onClick={() => setFollowing((prev) => !prev)}
            className={`mt-5 w-full py-2 rounded-lg text-sm font-semibold transition ${
              following
                ? "bg-gray-200 text-gray-700 hover:bg-gray-300"
                : "bg-blue-600 text-white hover:bg-blue-700"
            }`}
          >
            {following ? "Following" : "Follow"}
          </button>
        </div>
      </div>
    </div>
  );
}
