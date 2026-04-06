import React, { useState } from 'react';

export default function UserProfileCard() {
  const [isFollowing, setIsFollowing] = useState(false);

  const toggleFollow = () => {
    setIsFollowing(!isFollowing);
  };

  const user = {
    name: '李小明',
    avatarUrl: 'https://i.pravatar.cc/150?u=a042581f4e29026704d',
    bio: '前端开发工程师，热衷于构建美观且易用的用户界面。喜欢阅读和旅行。',
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 p-4 font-sans">
      <div className="bg-white rounded-2xl shadow-lg p-6 max-w-sm w-full flex flex-col items-center transform transition duration-300 hover:shadow-xl hover:-translate-y-1">
        <div className="w-24 h-24 mb-4 relative">
          <img
            className="w-full h-full rounded-full object-cover border-4 border-white shadow-md"
            src={user.avatarUrl}
            alt={`${user.name}的头像`}
          />
          <span className="absolute bottom-1 right-1 block w-4 h-4 bg-green-500 border-2 border-white rounded-full"></span>
        </div>
        
        <h2 className="text-xl font-bold text-gray-800 mb-2">{user.name}</h2>
        
        <p className="text-sm text-gray-600 text-center mb-6 leading-relaxed px-2">
          {user.bio}
        </p>

        <button
          onClick={toggleFollow}
          className={`w-full py-2.5 px-4 rounded-full font-semibold transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 ${
            isFollowing
              ? 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200 focus:ring-gray-400'
              : 'bg-blue-600 text-white hover:bg-blue-700 shadow-md hover:shadow-lg focus:ring-blue-500'
          }`}
        >
          {isFollowing ? '已关注' : '关注'}
        </button>
      </div>
    </div>
  );
}
