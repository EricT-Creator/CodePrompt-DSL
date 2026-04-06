import React, { useState } from "react";

export default function UserProfileCard() {
  const [following, setFollowing] = useState(false);
  const user = {
    name: "Alice Chen",
    bio: "Full-stack developer passionate about open source and coffee.",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=alice",
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg w-full max-w-xs overflow-hidden">
        <img src={user.avatar} alt="Avatar" className="w-full h-32 object-cover bg-gray-200" />
        <div className="p-5 text-center">
          <h2 className="text-lg font-bold text-gray-800">{user.name}</h2>
          <p className="text-sm text-gray-500 mt-1">{user.bio}</p>
          <button
            onClick={() => setFollowing(!following)}
            className={`mt-4 w-full py-2 rounded-lg text-sm font-semibold transition-colors ${
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
