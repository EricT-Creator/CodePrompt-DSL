import React, { useState } from 'react';

const UserProfileCard: React.FC = () => {
  const [isFollowing, setIsFollowing] = useState(false);

  const user = {
    avatar: 'https://i.pravatar.cc/150?u=a042581f4e29026704d',
    username: 'Jane Doe',
    bio: 'Product Designer & UI Enthusiast. Loving the journey of creating user-centric experiences.',
  };

  const toggleFollow = () => {
    setIsFollowing(!isFollowing);
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 p-4">
      <div className="bg-white rounded-2xl shadow-lg p-6 max-w-sm w-full transition-all hover:shadow-xl">
        <div className="flex flex-col items-center">
          <img
            src={user.avatar}
            alt={user.username}
            className="w-24 h-24 rounded-full border-4 border-indigo-50 object-cover mb-4"
          />
          <h2 className="text-xl font-bold text-gray-800 mb-1">{user.username}</h2>
          <p className="text-sm text-gray-500 mb-4 text-center leading-relaxed">
            {user.bio}
          </p>
          <button
            onClick={toggleFollow}
            className={`w-full py-2.5 rounded-xl font-semibold transition-colors duration-200 ${
              isFollowing
                ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-md'
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
