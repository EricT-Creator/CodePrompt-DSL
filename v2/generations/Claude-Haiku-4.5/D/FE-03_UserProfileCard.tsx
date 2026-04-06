import React, { useState } from 'react';

const 用户卡 = () => {
  const [已关注, set已关注] = useState(false);

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-lg p-8 w-full max-w-sm text-center">
        <img
          src="https://api.dicebear.com/7.x/avataaars/svg?seed=user4"
          alt="头像"
          className="w-24 h-24 rounded-full mx-auto mb-4 border-4 border-blue-500"
        />
        <h2 className="text-2xl font-bold mb-2">李华</h2>
        <p className="text-gray-600 mb-6">设计师 | 创意思想家</p>

        <button
          onClick={() => set已关注(!已关注)}
          className={`w-full py-2 rounded-lg font-semibold transition ${
            已关注 ? 'bg-gray-200 text-gray-900' : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {已关注 ? '已关注' : '关注'}
        </button>
      </div>
    </div>
  );
};

export default 用户卡;