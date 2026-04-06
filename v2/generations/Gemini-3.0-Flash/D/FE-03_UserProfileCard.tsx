import React, { useState } from 'react';

const 用户卡: React.FC = () => {
  const [已关, 设关] = useState(false);

  const 用户 = {
    号: 'https://i.pravatar.cc/100',
    名: '张三',
    述: '志在青云，笔耕不置。好访山水，亦爱代码。',
  };

  return (
    <div className="flex justify-center items-center h-screen bg-gray-50 p-4">
      <div className="w-full max-w-sm p-8 bg-white rounded-3xl shadow-xl flex flex-col items-center">
        <img src={用户.号} alt="头像" className="w-20 h-20 rounded-full mb-4 shadow-md" />
        <h3 className="text-xl font-bold mb-2">{用户.名}</h3>
        <p className="text-gray-500 text-center mb-6">{用户.述}</p>
        <button
          onClick={() => 设关(!已关)}
          className={`w-full py-3 rounded-2xl font-bold transition-all ${
            已关 ? 'bg-gray-100 text-gray-500' : 'bg-indigo-600 text-white shadow-indigo-200 shadow-lg'
          }`}
        >
          {已关 ? '已关注' : '关注'}
        </button>
      </div>
    </div>
  );
};

export default 用户卡;
