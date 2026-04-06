import React, { useState } from 'react';

interface UserProfile {
  name: string;
  handle: string;
  bio: string;
  avatar: string;
  stats: {
    followers: number;
    following: number;
  };
}

export default function UserProfileCard() {
  const [following, setFollowing] = useState(false);

  const profile: UserProfile = {
    name: 'Sarah Chen',
    handle: '@sarahchen',
    bio: 'Product designer & frontend enthusiast. Creating intuitive user experiences.',
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Sarah',
    stats: {
      followers: 2847,
      following: 892
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-blue-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden">
        <div className="h-32 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500"></div>
        <div className="px-8 pb-8">
          <div className="relative -top-16 mb-[-48px]">
            <div className="w-32 h-32 rounded-full border-4 border-white bg-white shadow-lg overflow-hidden">
              <img
                src={profile.avatar}
                alt={profile.name}
                className="w-full h-full object-cover"
              />
            </div>
          </div>
          <div className="mt-20">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">{profile.name}</h2>
                <p className="text-gray-500">{profile.handle}</p>
              </div>
              <button
                onClick={() => setFollowing(!following)}
                className={`px-5 py-2.5 rounded-full font-semibold text-sm transition-all ${
                  following
                    ? 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200'
                    : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-md'
                }`}
              >
                {following ? 'Following' : 'Follow'}
              </button>
            </div>
            <p className="mt-4 text-gray-700 leading-relaxed">{profile.bio}</p>
            <div className="mt-6 flex gap-6 py-4 border-t border-gray-100">
              <div className="text-center">
                <p className="text-xl font-bold text-gray-900">{profile.stats.following}</p>
                <p className="text-sm text-gray-500">Following</p>
              </div>
              <div className="text-center">
                <p className="text-xl font-bold text-gray-900">{profile.stats.followers}</p>
                <p className="text-sm text-gray-500">Followers</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
