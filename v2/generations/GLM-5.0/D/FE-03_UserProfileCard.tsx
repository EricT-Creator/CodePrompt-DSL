import React, { useState } from 'react';

const UserProfileCard: React.FC = () => {
  const [已关注, set已关注] = useState(false);

  const 用户资料 = {
    头像: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Chinese',
    用户名: '张三',
    简介: '热爱编程的软件工程师，专注于前端开发与用户体验设计。',
  };

  const 切换关注 = () => {
    set已关注(!已关注);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 to-orange-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-lg overflow-hidden max-w-sm w-full">
        <div className="h-20 bg-gradient-to-r from-amber-400 to-orange-400"></div>
        <div className="px-6 pb-6">
          <div className="flex justify-center -mt-12 mb-4">
            <img
              src={用户资料.头像}
              alt="头像"
              className="w-24 h-24 rounded-full border-4 border-white shadow-lg"
            />
          </div>
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-800 mb-2">{用户资料.用户名}</h2>
            <p className="text-gray-600 mb-6">{用户资料.简介}</p>
            <button
              onClick={切换关注}
              className={`w-full py-3 px-4 rounded-lg font-semibold transition duration-200 ${
                已关注
                  ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  : 'bg-amber-600 text-white hover:bg-amber-700'
              }`}
            >
              {已关注 ? '已关注' : '关注'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserProfileCard;
