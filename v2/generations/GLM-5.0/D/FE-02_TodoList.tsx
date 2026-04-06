import React, { useState } from 'react';

interface 待办事项 {
  编号: number;
  内容: string;
  是否完成: boolean;
}

const TodoList: React.FC = () => {
  const [事项列表, set事项列表] = useState<待办事项[]>([
    { 编号: 1, 内容: '买菜', 是否完成: false },
    { 编号: 2, 内容: '读书', 是否完成: true },
  ]);
  const [新事项, set新事项] = useState('');
  const [筛选状态, set筛选状态] = useState<'全部' | '未完成' | '已完成'>('全部');

  const 添加事项 = () => {
    if (新事项.trim()) {
      set事项列表([
        ...事项列表,
        { 编号: Date.now(), 内容: 新事项.trim(), 是否完成: false },
      ]);
      set新事项('');
    }
  };

  const 删除事项 = (编号: number) => {
    set事项列表(事项列表.filter(事项 => 事项.编号 !== 编号));
  };

  const 切换完成状态 = (编号: number) => {
    set事项列表(
      事项列表.map(事项 =>
        事项.编号 === 编号 ? { ...事项, 是否完成: !事项.是否完成 } : 事项
      )
    );
  };

  const 筛选后列表 = 事项列表.filter(事项 => {
    if (筛选状态 === '未完成') return !事项.是否完成;
    if (筛选状态 === '已完成') return 事项.是否完成;
    return true;
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 to-orange-50 py-8 px-4">
      <div className="max-w-md mx-auto bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="bg-gradient-to-r from-amber-500 to-orange-500 px-6 py-4">
          <h1 className="text-2xl font-bold text-white">待办事项</h1>
        </div>

        <div className="p-6">
          <div className="flex gap-2 mb-6">
            <input
              type="text"
              value={新事项}
              onChange={(事件) => set新事项(事件.target.value)}
              onKeyPress={(事件) => {
                if (事件.key === 'Enter') {
                  添加事项();
                }
              }}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent"
              placeholder="添加新事项..."
            />
            <button
              onClick={添加事项}
              className="px-6 py-3 bg-amber-600 text-white font-semibold rounded-lg hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 transition"
            >
              添加
            </button>
          </div>

          <div className="flex gap-2 mb-6">
            {(['全部', '未完成', '已完成'] as const).map((状态) => (
              <button
                key={状态}
                onClick={() => set筛选状态(状态)}
                className={`px-4 py-2 rounded-lg font-medium transition ${
                  筛选状态 === 状态
                    ? 'bg-amber-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {状态}
              </button>
            ))}
          </div>

          <ul className="space-y-3">
            {筛选后列表.map((事项) => (
              <li
                key={事项.编号}
                className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
              >
                <input
                  type="checkbox"
                  checked={事项.是否完成}
                  onChange={() => 切换完成状态(事项.编号)}
                  className="w-5 h-5 text-amber-600 rounded focus:ring-2 focus:ring-amber-500"
                />
                <span
                  className={`flex-1 ${
                    事项.是否完成 ? 'line-through text-gray-400' : 'text-gray-800'
                  }`}
                >
                  {事项.内容}
                </span>
                <button
                  onClick={() => 删除事项(事项.编号)}
                  className="text-red-500 hover:text-red-700 font-medium focus:outline-none transition"
                >
                  删除
                </button>
              </li>
            ))}
          </ul>

          {筛选后列表.length === 0 && (
            <p className="text-center text-gray-400 mt-6">暂无事项</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default TodoList;
