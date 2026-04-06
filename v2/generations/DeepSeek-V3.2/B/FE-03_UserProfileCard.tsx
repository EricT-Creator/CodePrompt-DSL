import React, { useState } from 'react';

const UserProfileCard: React.FC = () => {
  const [isFollowing, setIsFollowing] = useState<boolean>(false);

  const user = {
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Taylor',
    name: 'Taylor Swift',
    bio: 'Award-winning software engineer with 8+ years of experience in building scalable web applications. Enjoys mentoring junior developers and contributing to open source.',
    stats: {
      followers: 3289,
      following: 812,
      projects: 47,
    },
  };

  const toggleFollow = () => {
    setIsFollowing(!isFollowing);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-purple-100 p-6">
      <div className="max-w-md w-full bg-white rounded-3xl shadow-3xl overflow-hidden border-2 border-gray-200">
        {/* Header with banner */}
        <div className="h-48 bg-gradient-to-r from-indigo-600 to-pink-500 relative">
          <div className="absolute inset-0 flex items-center justify-center opacity-20">
            <div className="text-white text-6xl">👨‍💻</div>
          </div>
        </div>

        {/* Main content */}
        <div className="px-10 pb-12">
          {/* Avatar section */}
          <div className="relative -top-24 mb-8">
            <div className="w-40 h-40 mx-auto">
              <img
                src={user.avatar}
                alt={user.name}
                className="w-full h-full rounded-full border-8 border-white shadow-2xl object-cover"
              />
            </div>
          </div>

          {/* Name and bio */}
          <div className="text-center mb-10">
            <h2 className="text-4xl font-black text-gray-900 mb-4">
              {user.name}
            </h2>
            <p className="text-gray-700 text-lg leading-relaxed">
              {user.bio}
            </p>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-3 gap-6 mb-10">
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-6 rounded-2xl text-center border-2 border-blue-200">
              <p className="text-3xl font-extrabold text-blue-700">
                {user.stats.followers.toLocaleString()}
              </p>
              <p className="text-gray-700 font-semibold mt-2">Followers</p>
            </div>
            <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-6 rounded-2xl text-center border-2 border-purple-200">
              <p className="text-3xl font-extrabold text-purple-700">
                {user.stats.following}
              </p>
              <p className="text-gray-700 font-semibold mt-2">Following</p>
            </div>
            <div className="bg-gradient-to-br from-pink-50 to-pink-100 p-6 rounded-2xl text-center border-2 border-pink-200">
              <p className="text-3xl font-extrabold text-pink-700">
                {user.stats.projects}
              </p>
              <p className="text-gray-700 font-semibold mt-2">Projects</p>
            </div>
          </div>

          {/* Follow button */}
          <div className="mb-8">
            <button
              onClick={toggleFollow}
              className={`w-full py-5 text-xl font-black rounded-2xl transition-all duration-300 transform ${isFollowing ? 'bg-gradient-to-r from-gray-300 to-gray-400 text-gray-800 hover:from-gray-400 hover:to-gray-500' : 'bg-gradient-to-r from-indigo-600 to-pink-600 text-white hover:from-indigo-700 hover:to-pink-700 hover:scale-105'}`}
            >
              {isFollowing ? '✓ Following' : '+ Follow'}
            </button>
          </div>

          {/* Status indicator */}
          <div className="text-center">
            <div className={`inline-flex items-center px-6 py-3 rounded-full ${isFollowing ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'}`}>
              <span className="font-bold">
                {isFollowing ? 'You are following this user' : 'Not following yet'}
              </span>
            </div>
          </div>

          {/* Mock data note */}
          <div className="mt-12 pt-8 border-t-2 border-gray-300 text-center">
            <p className="text-gray-500 text-sm">
              Mock profile card with follow toggle functionality
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserProfileCard;