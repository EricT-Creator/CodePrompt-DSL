import React, { useState } from 'react';

const UserProfileCard = () => {
  const [isFollowing, setIsFollowing] = useState(false);

  const user = {
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=user1',
    name: 'Sarah Anderson',
    bio: 'Product Designer | Coffee enthusiast | Travel lover',
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-sm w-full">
        <div className="flex flex-col items-center">
          <img
            src={user.avatar}
            alt={user.name}
            className="w-24 h-24 rounded-full mb-4 border-4 border-blue-500"
          />
          <h2 className="text-2xl font-bold text-gray-800 mb-2">{user.name}</h2>
          <p className="text-gray-600 text-center mb-6">{user.bio}</p>

          <button
            onClick={() => setIsFollowing(!isFollowing)}
            className={`px-6 py-2 rounded-full font-semibold transition ${
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
};

export default UserProfileCard;