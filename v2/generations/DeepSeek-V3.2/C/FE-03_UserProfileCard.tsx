import React, { useState } from 'react';

const UserProfileCard: React.FC = () => {
  const [isFollowing, setIsFollowing] = useState<boolean>(false);

  const profile = {
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Jordan',
    fullName: 'Jordan Lee',
    description: 'Senior UX/UI Designer with a focus on accessibility and user-centered design. Constantly exploring new design tools and methodologies.',
    metrics: {
      followersCount: 2156,
      followingCount: 634,
      designsCount: 112,
    },
  };

  const handleFollowToggle = () => {
    setIsFollowing(!isFollowing);
  };

  const updatedFollowers = isFollowing 
    ? profile.metrics.followersCount + 1 
    : profile.metrics.followersCount;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 to-black p-6">
      <div className="max-w-lg w-full bg-gradient-to-br from-gray-800 to-gray-900 rounded-4xl shadow-4xl overflow-hidden border-2 border-gray-700">
        {/* Banner */}
        <div className="h-56 bg-gradient-to-r from-cyan-500 to-blue-700 relative">
          <div className="absolute inset-0 opacity-20">
            <div className="w-full h-full bg-gradient-to-b from-transparent to-black"></div>
          </div>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-white text-8xl opacity-20">🎨</div>
          </div>
        </div>

        {/* Main content */}
        <div className="px-12 pb-16 pt-4">
          {/* Avatar */}
          <div className="relative -top-32 mb-8">
            <div className="w-48 h-48 mx-auto">
              <div className="w-full h-full rounded-full border-8 border-gray-800 shadow-3xl overflow-hidden">
                <img
                  src={profile.avatar}
                  alt={profile.fullName}
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          </div>

          {/* Information */}
          <div className="text-center mb-12">
            <h1 className="text-5xl font-black text-white mb-6">
              {profile.fullName}
            </h1>
            <p className="text-gray-400 text-xl leading-relaxed">
              {profile.description}
            </p>
          </div>

          {/* Statistics */}
          <div className="grid grid-cols-3 gap-8 mb-12">
            <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-3xl border-2 border-gray-700 text-center">
              <p className="text-4xl font-extrabold text-cyan-400 mb-4">
                {updatedFollowers.toLocaleString()}
              </p>
              <p className="text-gray-300 font-bold">Followers</p>
            </div>
            <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-3xl border-2 border-gray-700 text-center">
              <p className="text-4xl font-extrabold text-blue-400 mb-4">
                {profile.metrics.followingCount}
              </p>
              <p className="text-gray-300 font-bold">Following</p>
            </div>
            <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-3xl border-2 border-gray-700 text-center">
              <p className="text-4xl font-extrabold text-purple-400 mb-4">
                {profile.metrics.designsCount}
              </p>
              <p className="text-gray-300 font-bold">Designs</p>
            </div>
          </div>

          {/* Follow action */}
          <div className="mb-10">
            <button
              onClick={handleFollowToggle}
              className={`w-full py-6 text-2xl font-black rounded-3xl transition-all duration-500 ${isFollowing ? 'bg-gradient-to-r from-gray-700 to-gray-800 text-gray-300 border-2 border-gray-600 hover:border-gray-500 hover:from-gray-600 hover:to-gray-700' : 'bg-gradient-to-r from-cyan-600 to-blue-700 text-white border-2 border-cyan-500 hover:border-cyan-400 hover:from-cyan-500 hover:to-blue-600 hover:scale-105'}`}
            >
              {isFollowing ? '✅ FOLLOWING' : '🟢 FOLLOW'}
            </button>
          </div>

          {/* Status indicator */}
          <div className="text-center mb-8">
            <div className={`inline-flex items-center px-8 py-4 rounded-full ${isFollowing ? 'bg-gradient-to-r from-green-900 to-emerald-900 text-emerald-300' : 'bg-gradient-to-r from-gray-800 to-gray-900 text-gray-400'}`}>
              <span className="text-lg font-bold">
                {isFollowing ? 'You are now following this designer' : 'Follow to see latest designs'}
              </span>
            </div>
          </div>

          {/* Footer note */}
          <div className="mt-16 pt-12 border-t-2 border-gray-800 text-center">
            <p className="text-gray-500 text-base">
              Mock designer profile card with interactive follow button
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserProfileCard;