import React, { useState } from 'react';

export default function UserProfileCard() {
  const [isFollowing, setIsFollowing] = useState(false);

  const handleFollowClick = () => {
    setIsFollowing((prev) => !prev);
  };

  const user = {
    avatarUrl: 'https://i.pravatar.cc/150?u=a042581f4e29026704d',
    name: 'Jane Doe',
    bio: 'Software Engineer specializing in front-end technologies. Coffee enthusiast and open-source contributor.',
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 p-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-lg overflow-hidden flex flex-col items-center p-6 transform transition-all hover:-translate-y-1 hover:shadow-xl">
        <div className="relative mb-4">
          <img
            className="w-24 h-24 rounded-full object-cover border-4 border-white shadow-md"
            src={user.avatarUrl}
            alt={`${user.name}'s avatar`}
          />
          <div className="absolute bottom-0 right-0 h-4 w-4 rounded-full bg-green-500 border-2 border-white"></div>
        </div>

        <h2 className="text-xl font-bold text-gray-800 mb-1">{user.name}</h2>
        
        <p className="text-sm text-gray-500 text-center mb-6 px-4 leading-relaxed">
          {user.bio}
        </p>

        <button
          onClick={handleFollowClick}
          className={`w-full py-2 px-6 rounded-full font-semibold transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 ${
            isFollowing
              ? 'bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-gray-400'
              : 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500'
          }`}
        >
          {isFollowing ? 'Following' : 'Follow'}
        </button>
      </div>
    </div>
  );
}
