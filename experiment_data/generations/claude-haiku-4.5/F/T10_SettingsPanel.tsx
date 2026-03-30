import React, { useState } from 'react';

const 设置Panel: React.FC = () => {
  const [settings, set设置] = useState({
    notifications: true,
    darkMode: false,
    theme: 'blue',
  });

  const toggleNotif = () => set设置({ ...settings, notifications: !settings.notifications });
  const toggleDark = () => set设置({ ...settings, darkMode: !settings.darkMode });
  const set主题 = (t: string) => set设置({ ...settings, theme: t });
  const save = () => alert('设置 saved!');

  return (
    <div className={`min-h-screen p-6 ${settings.darkMode ? 'bg-gray-900 text-white' : 'bg-gray-50'}`}>
      <h1 className="text-3xl font-bold mb-8">设置</h1>
      <div className="max-w-md space-y-6">
        <div className="flex justify-between items-center">
          <label>通知</label>
          <button
            onClick={toggleNotif}
            className={`w-12 h-6 rounded-full ${settings.notifications ? 'bg-green-500' : 'bg-gray-400'}`}
          />
        </div>
        <div className="flex justify-between items-center">
          <label>暗黑模式</label>
          <button
            onClick={toggleDark}
            className={`w-12 h-6 rounded-full ${settings.darkMode ? 'bg-green-500' : 'bg-gray-400'}`}
          />
        </div>
        <div>
          <label className="block mb-2">主题</label>
          <select
            value={settings.theme}
            onChange={e => set主题(e.target.value)}
            className="w-full px-3 py-2 border rounded"
          >
            <option>blue</option>
            <option>green</option>
            <option>red</option>
          </select>
        </div>
        <button onClick={save} className="w-full bg-blue-500 text-white py-2 rounded hover:bg-blue-600">
          保存
        </button>
      </div>
    </div>
  );
};

export default 设置Panel;