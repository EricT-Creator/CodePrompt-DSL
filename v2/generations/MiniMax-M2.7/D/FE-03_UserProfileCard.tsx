import React, { useState } from 'react';

interface User {
  name: string;
  handle: string;
  bio: string;
  avatarUrl: string;
}

export default function UserProfileCard() {
  const [isFollowing, setIsFollowing] = useState(false);

  const user: User = {
    name: 'Sarah Chen',
    handle: '@sarah_chen',
    bio: 'Software engineer at TechCorp. Passionate about building great products and mentoring junior developers.',
    avatarUrl: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&h=150&fit=crop&crop=face',
  };

  const toggleFollow = () => {
    setIsFollowing(!isFollowing);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-lg overflow-hidden max-w-sm w-full">
        <div className="h-24 bg-gradient-to-r from-blue-500 to-purple-600"></div>
        <div className="px-6 pb-6">
          <div className="relative -mt-12 mb-4">
            <img
              src={user.avatarUrl}
              alt={user.name}
              className="w-24 h-24 rounded-full border-4 border-white shadow-md"
            />
          </div>
          <h2 className="text-xl font-bold text-gray-900">{user.name}</h2>
          <p className="text-gray-500 mb-4">{user.handle}</p>
          <p className="text-gray-700 mb-6">{user.bio}</p>
          <button
            onClick={toggleFollow}
            className={`px-6 py-2 rounded-full font-semibold transition-colors ${
              isFollowing
                ? 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {isFollowing ? 'Following' : 'Follow'}
          </button>
        </div>
      </div>
    </div>
  );
}