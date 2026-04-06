import React, { useState } from 'react';

interface UserProfile {
  avatar: string;
  username: string;
  bio: string;
  isFollowing: boolean;
}

const UserProfileCard: React.FC = () => {
  const [user, setUser] = useState<UserProfile>({
    avatar: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop&crop=face',
    username: '张三',
    bio: '全栈开发者，热爱 React 和 TypeScript，喜欢构建优美的用户界面。',
    isFollowing: false
  });

  const handleFollowClick = () => {
    setUser(prev => ({ ...prev, isFollowing: !prev.isFollowing }));
  };

  return (
    <div className="max-w-sm mx-auto bg-white rounded-xl shadow-lg overflow-hidden">
      <div className="p-6">
        <div className="flex items-center space-x-4">
          <img
            src={user.avatar}
            alt="头像"
            className="w-16 h-16 rounded-full object-cover"
          />
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-gray-900">{user.username}</h2>
            <p className="text-gray-600 mt-1 text-sm">{user.bio}</p>
          </div>
        </div>
        
        <button
          onClick={handleFollowClick}
          className={`mt-4 w-full py-2 px-4 rounded-md font-medium transition-colors ${user.isFollowing ? 'bg-gray-200 text-gray-800 hover:bg-gray-300' : 'bg-blue-500 text-white hover:bg-blue-600'}`}
        >
          {user.isFollowing ? '已关注' : '关注'}
        </button>
      </div>
    </div>
  );
};

export default UserProfileCard;