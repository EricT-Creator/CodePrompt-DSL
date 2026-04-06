import React, { useState } from 'react';

const UserProfileCard: React.FC = () => {
  const [已关注, set已关注] = useState<boolean>(false);

  const 用户 = {
    头像: 'https://api.dicebear.com/7.x/avataaars/svg?seed=云',
    名: '云开发者',
    简介: '专注前端框架与设计系统，常游开源社区，好爬山与摄影，以代码为乐，以协作为荣。',
    计数: {
      关注者: 1523,
      关注中: 426,
      作品数: 78,
    },
  };

  const 切关注 = () => {
    set已关注(!已关注);
  };

  const 更新关注者数 = 已关注 
    ? 用户.计数.关注者 + 1 
    : 用户.计数.关注者;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 to-black p-6">
      <div className="max-w-lg w-full bg-gradient-to-br from-gray-800 to-gray-900 rounded-4xl shadow-4xl overflow-hidden border-2 border-gray-700">
        {/* 顶图 */}
        <div className="h-56 bg-gradient-to-r from-emerald-600 to-teal-700 relative">
          <div className="absolute inset-0 opacity-20">
            <div className="w-full h-full bg-gradient-to-b from-transparent to-black"></div>
          </div>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-white text-8xl opacity-20">👤</div>
          </div>
        </div>

        {/* 主区 */}
        <div className="px-12 pb-16 pt-4">
          {/* 头像 */}
          <div className="relative -top-32 mb-8">
            <div className="w-48 h-48 mx-auto">
              <div className="w-full h-full rounded-full border-8 border-gray-800 shadow-3xl overflow-hidden">
                <img
                  src={用户.头像}
                  alt={用户.名}
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          </div>

          {/* 信息 */}
          <div className="text-center mb-12">
            <h1 className="text-5xl font-black text-white mb-6">
              {用户.名}
            </h1>
            <p className="text-gray-400 text-xl leading-relaxed">
              {用户.简介}
            </p>
          </div>

          {/* 计板 */}
          <div className="grid grid-cols-3 gap-8 mb-12">
            <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-3xl border-2 border-gray-700 text-center">
              <p className="text-4xl font-extrabold text-emerald-400 mb-4">
                {更新关注者数.toLocaleString()}
              </p>
              <p className="text-gray-300 font-bold">关注者</p>
            </div>
            <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-3xl border-2 border-gray-700 text-center">
              <p className="text-4xl font-extrabold text-blue-400 mb-4">
                {用户.计数.关注中}
              </p>
              <p className="text-gray-300 font-bold">关注中</p>
            </div>
            <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-3xl border-2 border-gray-700 text-center">
              <p className="text-4xl font-extrabold text-purple-400 mb-4">
                {用户.计数.作品数}
              </p>
              <p className="text-gray-300 font-bold">作品</p>
            </div>
          </div>

          {/* 关注键 */}
          <div className="mb-10">
            <button
              onClick={切关注}
              className={`w-full py-6 text-2xl font-black rounded-3xl transition-all duration-500 ${已关注 ? 'bg-gradient-to-r from-gray-700 to-gray-800 text-gray-300 border-2 border-gray-600 hover:border-gray-500 hover:from-gray-600 hover:to-gray-700' : 'bg-gradient-to-r from-emerald-600 to-teal-700 text-white border-2 border-emerald-500 hover:border-emerald-400 hover:from-emerald-500 hover:to-teal-600 hover:scale-105'}`}
            >
              {已关注 ? '✅ 已关注' : '🟢 关注'}
            </button>
          </div>

          {/* 状态示 */}
          <div className="text-center mb-8">
            <div className={`inline-flex items-center px-8 py-4 rounded-full ${已关注 ? 'bg-gradient-to-r from-green-900 to-emerald-900 text-emerald-300' : 'bg-gradient-to-r from-gray-800 to-gray-900 text-gray-400'}`}>
              <span className="text-lg font-bold">
                {已关注 ? '你已关注此用户' : '点关注以观其动态'}
              </span>
            </div>
          </div>

          {/* 底注 */}
          <div className="mt-16 pt-12 border-t-2 border-gray-800 text-center">
            <p className="text-gray-500 text-base">
              模拟用户卡，示头像、名、简介与关注键
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserProfileCard;