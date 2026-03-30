import React from 'react';

interface User {
  avatar: string;
  name: string;
  bio: string;
}

const ProfileCard: React.FC = () => {
  const user: User = {
    avatar: '👤',
    name: '张三',
    bio: '前端工程师 | UI设计师',
  };

  const [is已关注, setIs已关注] = React.useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-lg p-8 max-w-sm text-center">
        <div className="text-5xl mb-4">{user.avatar}</div>
        <h2 className="text-2xl font-bold mb-2">{user.name}</h2>
        <p className="text-gray-600 mb-6">{user.bio}</p>
        <button
          onClick={() => setIs已关注(!is已关注)}
          className={`px-6 py-2 rounded-lg font-medium ${is已关注 ? 'bg-gray-300' : 'bg-blue-500 text-white hover:bg-blue-600'}`}
        >
          {is已关注 ? '已关注' : '关注'}
        </button>
      </div>
    </div>
  );
};

export default ProfileCard;