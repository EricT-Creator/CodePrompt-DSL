import React, { useState } from 'react';

export default function 用户卡() {
  const [已关注, 设已关注] = useState(false);

  const 用户 = {
    名: '李明',
    号: '@liming',
    简介: '全栈开发者，热爱编程与开源。专注于用户体验与代码质量。',
    头像: 'https://api.dicebear.com/7.x/avataaars/svg?seed=LiMing',
    关注数: 328,
    粉丝数: 1567
  };

  return (
    <div className="min-h-screen bg-stone-100 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="h-24 bg-gradient-to-r from-amber-600 to-orange-600"></div>
        <div className="px-6 pb-6">
          <div className="relative -top-12 mb-[-32px]">
            <img
              src={用户.头像}
              alt={用户.名}
              className="w-24 h-24 rounded-full border-4 border-white bg-white shadow-md"
            />
          </div>
          <div className="mt-14">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-xl font-bold text-stone-800">{用户.名}</h2>
                <p className="text-stone-500 text-sm">{用户.号}</p>
              </div>
              <button
                onClick={() => 设已关注(!已关注)}
                className={`px-4 py-2 rounded-full font-medium text-sm transition-colors ${
                  已关注
                    ? 'bg-stone-200 text-stone-700 hover:bg-stone-300'
                    : 'bg-amber-700 text-white hover:bg-amber-800'
                }`}
              >
                {已关注 ? '已关注' : '关注'}
              </button>
            </div>
            <p className="mt-3 text-stone-700 text-sm leading-relaxed">{用户.简介}</p>
            <div className="mt-4 flex gap-4 text-sm">
              <span className="text-stone-600">
                <strong className="text-stone-800">{用户.关注数}</strong> 关注
              </span>
              <span className="text-stone-600">
                <strong className="text-stone-800">{用户.粉丝数}</strong> 粉丝
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
