import React, { useState } from 'react';

export default function UserProfileCard() {
  const [isFollowing, setIsFollowing] = useState(false);

  const toggleFollow = () => {
    setIsFollowing(!isFollowing);
  };

  const user = {
    name: 'Jane Doe',
    avatarUrl: 'https://i.pravatar.cc/150?u=a042581f4e29026704d',
    bio: 'Frontend developer passionate about building beautiful and accessible user interfaces. Loves coffee and open source.',
  };

  return (
    <div className="flex justify-center items-center min-h-screen bg-gray-100 p-4">
      <div className="max-w-sm w-full bg-white shadow-lg rounded-xl overflow-hidden flex flex-col items-center p-6">
        <div className="w-24 h-24 mb-4">
          <img
            className="w-full h-full object-cover rounded-full border-4 border-gray-200"
            src={user.avatarUrl}
            alt={`${user.name}'s avatar`}
          />
        </div>
        
        <h2 className="text-xl font-semibold text-gray-800 mb-2">{user.name}</h2>
        
        <p className="text-center text-gray-600 mb-6 text-sm px-4 leading-relaxed">
          {user.bio}
        </p>
        
        <button
          onClick={toggleFollow}
          className={`w-full py-2 px-4 rounded-full font-medium transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 ${
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
