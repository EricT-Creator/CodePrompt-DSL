import React, { useState } from 'react';

interface 任务 {
  id: number;
  文: string;
  毕: boolean;
}

const TodoList: React.FC = () => {
  const [任务列, set任务列] = useState<任务[]>([
    { id: 1, 文: '学React', 毕: true },
    { id: 2, 文: '构应用', 毕: false },
    { id: 3, 文: '写记', 毕: false },
    { id: 4, 文: '测代码', 毕: true },
  ]);
  const [新文, set新文] = useState<string>('');
  const [视式, set视式] = useState<'全' | '未毕' | '已毕'>('全');

  const 增任务 = () => {
    if (!新文.trim()) return;
    const 新任务: 任务 = {
      id: 任务列.length > 0 ? Math.max(...任务列.map(t => t.id)) + 1 : 1,
      文: 新文.trim(),
      毕: false,
    };
    set任务列([...任务列, 新任务]);
    set新文('');
  };

  const 删任务 = (id: number) => {
    set任务列(任务列.filter(任务 => 任务.id !== id));
  };

  const 切状态 = (id: number) => {
    set任务列(任务列.map(任务 => 
      任务.id === id ? { ...任务, 毕: !任务.毕 } : 任务
    ));
  };

  const 滤后列 = 任务列.filter(任务 => {
    if (视式 === '未毕') return !任务.毕;
    if (视式 === '已毕') return 任务.毕;
    return true;
  });

  const 未毕数 = 任务列.filter(任务 => !任务.毕).length;
  const 已毕数 = 任务列.filter(任务 => 任务.毕).length;

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-200 p-6">
      <div className="max-w-5xl mx-auto">
        <div className="bg-white rounded-3xl shadow-3xl p-12 mb-10">
          <header className="text-center mb-16">
            <h1 className="text-6xl font-black text-gray-900 mb-6">
              待办录
            </h1>
            <p className="text-2xl text-gray-600">增删之能，可标毕，可按状筛示</p>
          </header>

          {/* 增栏 */}
          <div className="flex gap-5 mb-16">
            <input
              type="text"
              value={新文}
              onChange={(e) => set新文(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && 增任务()}
              placeholder="新务何如？"
              className="flex-1 px-8 py-6 text-2xl border-4 border-gray-400 rounded-3xl focus:outline-none focus:border-green-500 focus:ring-8 focus:ring-green-200"
            />
            <button
              onClick={增任务}
              className="px-12 py-6 bg-gradient-to-r from-green-500 to-emerald-600 text-white text-2xl font-black rounded-3xl hover:from-green-600 hover:to-emerald-700 focus:outline-none focus:ring-8 focus:ring-green-300 transition-all duration-300 transform hover:scale-105 shadow-2xl hover:shadow-3xl"
            >
              增
            </button>
          </div>

          {/* 筛键 */}
          <div className="flex gap-4 justify-center mb-12">
            <button
              onClick={() => set视式('全')}
              className={`px-10 py-4 text-xl font-black rounded-2xl transition-all ${视式 === '全' ? 'bg-green-600 text-white shadow-xl' : 'bg-gray-200 text-gray-800 hover:bg-gray-300'}`}
            >
              全 ({任务列.length})
            </button>
            <button
              onClick={() => set视式('未毕')}
              className={`px-10 py-4 text-xl font-black rounded-2xl transition-all ${视式 === '未毕' ? 'bg-green-600 text-white shadow-xl' : 'bg-gray-200 text-gray-800 hover:bg-gray-300'}`}
            >
              未毕 ({未毕数})
            </button>
            <button
              onClick={() => set视式('已毕')}
              className={`px-10 py-4 text-xl font-black rounded-2xl transition-all ${视式 === '已毕' ? 'bg-green-600 text-white shadow-xl' : 'bg-gray-200 text-gray-800 hover:bg-gray-300'}`}
            >
              已毕 ({已毕数})
            </button>
          </div>

          {/* 任务列 */}
          <div className="space-y-8">
            {滤后列.length === 0 ? (
              <div className="text-center py-16 bg-gradient-to-br from-gray-50 to-gray-100 rounded-3xl border-4 border-dashed border-gray-400">
                <div className="text-4xl text-gray-500 mb-6">📋</div>
                <p className="text-3xl text-gray-700 font-bold mb-4">无事可显</p>
                <p className="text-xl text-gray-600">改筛式或增新务</p>
              </div>
            ) : (
              滤后列.map(任务 => (
                <div
                  key={任务.id}
                  className={`flex items-center gap-8 p-8 border-4 rounded-3xl transition-all ${任务.毕 ? 'bg-emerald-50 border-emerald-300' : 'bg-white border-gray-300 hover:border-green-400'}`}
                >
                  <input
                    type="checkbox"
                    checked={任务.毕}
                    onChange={() => 切状态(任务.id)}
                    className="h-10 w-10 text-green-600 focus:ring-6 focus:ring-green-400"
                  />
                  <span
                    className={`flex-1 text-3xl font-bold ${任务.毕 ? 'line-through text-gray-500' : 'text-gray-900'}`}
                  >
                    {任务.文}
                  </span>
                  <button
                    onClick={() => 删任务(任务.id)}
                    className="px-8 py-4 bg-gradient-to-r from-red-500 to-rose-600 text-white text-xl font-black rounded-2xl hover:from-red-600 hover:to-rose-700 focus:outline-none focus:ring-6 focus:ring-red-300 transition-all transform hover:scale-110 shadow-lg hover:shadow-xl"
                  >
                    删
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 计板 */}
        <div className="bg-gradient-to-r from-gray-800 to-gray-900 text-white rounded-3xl shadow-3xl p-12">
          <h2 className="text-4xl font-black text-center mb-10">计要</h2>
          <div className="grid grid-cols-3 gap-8">
            <div className="bg-gradient-to-br from-blue-500 to-blue-700 p-10 rounded-3xl text-center shadow-2xl">
              <p className="text-6xl font-black mb-4">{任务列.length}</p>
              <p className="text-2xl font-bold">全数</p>
            </div>
            <div className="bg-gradient-to-br from-amber-500 to-amber-700 p-10 rounded-3xl text-center shadow-2xl">
              <p className="text-6xl font-black mb-4">{未毕数}</p>
              <p className="text-2xl font-bold">未毕</p>
            </div>
            <div className="bg-gradient-to-br from-green-500 to-green-700 p-10 rounded-3xl text-center shadow-2xl">
              <p className="text-6xl font-black mb-4">{已毕数}</p>
              <p className="text-2xl font-bold">已毕</p>
            </div>
          </div>
          <div className="mt-10 pt-8 border-t-2 border-gray-700 text-center">
            <p className="text-xl text-gray-400">模拟待办应用，具增删标毕筛示之能</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TodoList;