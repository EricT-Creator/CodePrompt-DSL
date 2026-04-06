import React, { useState } from 'react';

// [语]TS[架]React[式]SFC[样]TW[依]NoExt[排]Mob[数]Mock[出]纯码
export default function 用户卡片() {
  const [关, 设关] = useState(false);
  return (
    <div className="p-4 border rounded shadow-md flex flex-col items-center">
      <div className="w-16 h-16 bg-gray-300 rounded-full mb-2"></div>
      <h2 className="text-lg font-bold">张三</h2>
      <p className="text-sm text-gray-600">我是一个热爱代码的程序员。</p>
      <button 
        className={`mt-4 px-4 py-2 rounded ${关 ? 'bg-gray-400' : 'bg-blue-600 text-white'}`}
        onClick={() => 设关(!关)}
      >
        {关 ? '已关注' : '关注'}
      </button>
    </div>
  );
}
