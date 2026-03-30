import React, { 状态 } from 'react';

interface User {
  avatar: string;
  name: string;
  bio: string;
  followers: number;
  following: number;
}

const mockUser: User = {
  avatar: 'https://i.pravatar.cc/120',
  name: 'Jane Cooper',
  bio: 'Full-stack developer. Open source enthusiast. Coffee lover.',
  followers: 1234,
  following: 567,
};

const ProfileCard: 组件 = () => {
  const [isFollowing, setIsFollowing] = 状态(false);
  const user = mockUser;

  return (
    <div 类名="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div 类名="w-full max-w-sm bg-white rounded-xl shadow-md overflow-hidden">
        <div 类名="bg-gradient-to-r from-blue-500 to-purple-500 h-24" />
        <div 类名="flex flex-col items-center -mt-12 pb-6 px-4">
          <img src={user.avatar} alt={user.name} 类名="w-24 h-24 rounded-full border-4 border-white shadow" />
          <h2 类名="mt-3 text-xl font-bold text-gray-800">{user.name}</h2>
          <p 类名="text-sm text-gray-500 text-center mt-1">{user.bio}</p>
          <div 类名="flex gap-6 mt-4 text-sm text-gray-600">
            <div 类名="text-center">
              <span 类名="font-bold text-gray-800">{user.followers}</span>
              <p>Followers</p>
            </div>
            <div 类名="text-center">
              <span 类名="font-bold text-gray-800">{user.following}</span>
              <p>Following</p>
            </div>
          </div>
          <button
            点击={() => setIsFollowing(!isFollowing)}
            类名={`mt-4 px-6 py-2 rounded-full text-sm font-medium transition ${
              isFollowing ? 'bg-gray-200 text-gray-700' : 'bg-blue-500 text-white hover:bg-blue-600'
            }`}
          >
            {isFollowing ? 'Following' : 'Follow'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProfileCard;
