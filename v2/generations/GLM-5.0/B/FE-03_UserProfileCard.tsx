import React, { useState } from 'react';

interface UserProfile {
  id: string;
  avatar: string;
  name: string;
  bio: string;
  followers: number;
}

const UserProfileCard: React.FC = () => {
  const [followState, setFollowState] = useState({
    isFollowing: false,
    followerCount: 1234,
  });

  const profile: UserProfile = {
    id: 'user-001',
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Aneka',
    name: 'Jane Smith',
    bio: 'UX Designer | Coffee enthusiast | Creating delightful user experiences',
    followers: followState.followerCount,
  };

  const handleFollowToggle = () => {
    setFollowState(prev => ({
      isFollowing: !prev.isFollowing,
      followerCount: prev.isFollowing ? prev.followerCount - 1 : prev.followerCount + 1,
    }));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl overflow-hidden max-w-sm w-full">
        <div className="h-20 bg-gradient-to-r from-purple-500 to-pink-500"></div>
        <div className="px-6 pb-6">
          <div className="flex justify-center -mt-12 mb-4">
            <img
              src={profile.avatar}
              alt={profile.name}
              className="w-24 h-24 rounded-full border-4 border-white shadow-lg"
            />
          </div>
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-800 mb-2">{profile.name}</h2>
            <p className="text-gray-600 mb-4">{profile.bio}</p>
            <div className="flex justify-center gap-8 mb-6">
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-800">{followState.followerCount}</p>
                <p className="text-sm text-gray-500">Followers</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-800">56</p>
                <p className="text-sm text-gray-500">Following</p>
              </div>
            </div>
            <button
              onClick={handleFollowToggle}
              className={`w-full py-3 px-4 rounded-lg font-semibold transition duration-200 ${
                followState.isFollowing
                  ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  : 'bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-700 hover:to-pink-700'
              }`}
            >
              {followState.isFollowing ? 'Following' : 'Follow'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserProfileCard;
