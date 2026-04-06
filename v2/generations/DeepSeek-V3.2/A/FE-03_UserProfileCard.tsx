import React, { useState } from 'react';

const UserProfileCard: React.FC = () => {
  const [isFollowing, setIsFollowing] = useState<boolean>(false);

  const userData = {
    avatarUrl: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Alex',
    username: 'Alex Johnson',
    bio: 'Full-stack developer passionate about React, TypeScript, and clean code. Loves hiking and photography in free time.',
    followers: 1247,
    following: 532,
    posts: 89,
  };

  const handleFollowClick = () => {
    setIsFollowing(!isFollowing);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-300 p-4">
      <div className="max-w-sm w-full bg-white rounded-3xl shadow-2xl overflow-hidden">
        {/* Cover photo */}
        <div className="h-40 bg-gradient-to-r from-blue-500 to-purple-600"></div>

        {/* Profile content */}
        <div className="px-8 pb-10">
          {/* Avatar */}
          <div className="relative -top-16 mb-4">
            <div className="w-32 h-32 mx-auto">
              <img
                src={userData.avatarUrl}
                alt="Profile avatar"
                className="w-full h-full rounded-full border-8 border-white shadow-xl"
              />
            </div>
          </div>

          {/* User info */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              {userData.username}
            </h1>
            <p className="text-gray-600 mb-6 leading-relaxed">
              {userData.bio}
            </p>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 mb-8">
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{userData.followers}</p>
              <p className="text-sm text-gray-600">Followers</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{userData.following}</p>
              <p className="text-sm text-gray-600">Following</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{userData.posts}</p>
              <p className="text-sm text-gray-600">Posts</p>
            </div>
          </div>

          {/* Follow button */}
          <button
            onClick={handleFollowClick}
            className={`w-full py-4 rounded-xl font-bold text-lg transition-all ${isFollowing ? 'bg-gray-200 text-gray-800 hover:bg-gray-300' : 'bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:from-blue-700 hover:to-purple-700'}`}
          >
            {isFollowing ? 'Following' : 'Follow'}
          </button>

          {/* Follow status indicator */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-500">
              {isFollowing ? 'You are now following this user' : 'Click to follow this user'}
            </p>
          </div>

          {/* Mock data note */}
          <div className="mt-10 pt-6 border-t border-gray-200 text-center">
            <p className="text-xs text-gray-500">Mock user profile card with follow toggle</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserProfileCard;