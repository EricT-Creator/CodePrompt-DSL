import React, { useState } from 'react';

const UserProfileCard: React.FC = () => {
  const [following, setFollowing] = useState(false);

  const profile = {
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Midnight',
    username: 'Alex Chen',
    bio: 'Full-stack developer. Open source contributor. Building the future one commit at a time.',
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="bg-gray-800 rounded-xl shadow-2xl overflow-hidden max-w-sm w-full">
        <div className="h-24 bg-gradient-to-r from-cyan-500 to-blue-500"></div>
        <div className="px-6 pb-6">
          <div className="flex justify-center -mt-12 mb-4">
            <div className="relative">
              <img
                src={profile.avatar}
                alt="Avatar"
                className="w-24 h-24 rounded-full border-4 border-gray-800 shadow-lg"
              />
              <div className="absolute bottom-0 right-0 w-6 h-6 bg-green-500 rounded-full border-2 border-gray-800"></div>
            </div>
          </div>
          <div className="text-center">
            <h2 className="text-2xl font-bold text-white mb-2">{profile.username}</h2>
            <p className="text-gray-400 mb-6">{profile.bio}</p>
            <button
              onClick={() => setFollowing(!following)}
              className={`w-full py-3 px-4 rounded-lg font-semibold transition duration-200 ${
                following
                  ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  : 'bg-cyan-600 text-white hover:bg-cyan-700'
              }`}
            >
              {following ? 'Following' : 'Follow'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserProfileCard;
