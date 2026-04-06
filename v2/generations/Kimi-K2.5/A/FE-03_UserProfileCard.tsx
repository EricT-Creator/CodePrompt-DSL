import React, { useState } from 'react';

export default function UserProfileCard() {
  const [isFollowing, setIsFollowing] = useState(false);

  const user = {
    name: 'Alex Johnson',
    handle: '@alexj',
    bio: 'Full-stack developer passionate about React and TypeScript. Building things that matter.',
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Alex',
    followers: 1234,
    following: 567
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="h-24 bg-gradient-to-r from-blue-500 to-purple-600"></div>
        <div className="px-6 pb-6">
          <div className="relative -top-12 mb-[-32px]">
            <img
              src={user.avatar}
              alt={user.name}
              className="w-24 h-24 rounded-full border-4 border-white bg-white shadow-md"
            />
          </div>
          <div className="mt-14">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-xl font-bold text-gray-900">{user.name}</h2>
                <p className="text-gray-500 text-sm">{user.handle}</p>
              </div>
              <button
                onClick={() => setIsFollowing(!isFollowing)}
                className={`px-4 py-2 rounded-full font-medium text-sm transition-colors ${
                  isFollowing
                    ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                {isFollowing ? 'Following' : 'Follow'}
              </button>
            </div>
            <p className="mt-3 text-gray-700 text-sm leading-relaxed">{user.bio}</p>
            <div className="mt-4 flex gap-4 text-sm">
              <span className="text-gray-600">
                <strong className="text-gray-900">{user.following}</strong> Following
              </span>
              <span className="text-gray-600">
                <strong className="text-gray-900">{user.followers}</strong> Followers
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
