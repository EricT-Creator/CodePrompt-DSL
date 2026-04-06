import React, { useState } from 'react';

export default function UserProfileCard() {
  const [isFollowing, setIsFollowing] = useState(false);

  const toggleFollow = () => {
    setIsFollowing(!isFollowing);
  };

  const user = {
    avatarUrl: 'https://i.pravatar.cc/150?u=a042581f4e29026704d',
    name: 'Jane Doe',
    bio: 'Software Engineer specializing in front-end development. Loves React and Tailwind CSS.',
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 p-4">
      <div className="bg-white shadow-xl rounded-2xl p-6 max-w-xs w-full flex flex-col items-center transform transition duration-500 hover:scale-105">
        <div className="relative">
          <img
            className="w-24 h-24 rounded-full object-cover border-4 border-blue-500 shadow-md mb-4"
            src={user.avatarUrl}
            alt={`${user.name}'s avatar`}
          />
        </div>
        
        <h2 className="text-xl font-bold text-gray-800 mb-2">{user.name}</h2>
        
        <p className="text-center text-gray-600 text-sm mb-6 px-2 leading-relaxed">
          {user.bio}
        </p>

        <button
          onClick={toggleFollow}
          className={`w-full py-2 px-4 rounded-full font-semibold shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors duration-300 ${
            isFollowing
              ? 'bg-gray-200 text-gray-700 hover:bg-gray-300 focus:ring-gray-400'
              : 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500'
          }`}
        >
          {isFollowing ? 'Following' : 'Follow'}
        </button>
      </div>
    </div>
  );
}
