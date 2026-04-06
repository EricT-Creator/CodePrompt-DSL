import React, { useState } from 'react';

const UserProfileCard: React.FC = () => {
  const [isFollowing, setIsFollowing] = useState(false);

  const user = {
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Felix',
    username: 'John Doe',
    bio: 'Frontend developer passionate about React and TypeScript. Love building beautiful user interfaces.',
  };

  const toggleFollow = () => {
    setIsFollowing(!isFollowing);
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-md p-6 max-w-sm w-full">
        <div className="flex flex-col items-center">
          <img
            src={user.avatar}
            alt="Avatar"
            className="w-24 h-24 rounded-full border-4 border-blue-500 mb-4"
          />
          <h2 className="text-xl font-bold text-gray-800 mb-2">{user.username}</h2>
          <p className="text-gray-600 text-center mb-4">{user.bio}</p>
          <button
            onClick={toggleFollow}
            className={`w-full py-2 px-4 rounded font-semibold transition duration-200 ${
              isFollowing
                ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
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
