import React, { useState } from 'react';

const SettingsPanel: React.FC = () => {
  const [settings, setSettings] = useState({
    notifications: true,
    darkMode: false,
    theme: 'blue',
  });

  const toggleNotif = () => setSettings({ ...settings, notifications: !settings.notifications });
  const toggleDark = () => setSettings({ ...settings, darkMode: !settings.darkMode });
  const setTheme = (t: string) => setSettings({ ...settings, theme: t });
  const save = () => alert('Settings saved!');

  return (
    <div className={`min-h-screen p-6 ${settings.darkMode ? 'bg-gray-900 text-white' : 'bg-gray-50'}`}>
      <h1 className="text-3xl font-bold mb-8">Settings</h1>
      <div className="max-w-md space-y-6">
        <div className="flex justify-between items-center">
          <label>Notifications</label>
          <button
            onClick={toggleNotif}
            className={`w-12 h-6 rounded-full ${settings.notifications ? 'bg-green-500' : 'bg-gray-400'}`}
          />
        </div>
        <div className="flex justify-between items-center">
          <label>Dark Mode</label>
          <button
            onClick={toggleDark}
            className={`w-12 h-6 rounded-full ${settings.darkMode ? 'bg-green-500' : 'bg-gray-400'}`}
          />
        </div>
        <div>
          <label className="block mb-2">Theme</label>
          <select
            value={settings.theme}
            onChange={e => setTheme(e.target.value)}
            className="w-full px-3 py-2 border rounded"
          >
            <option>blue</option>
            <option>green</option>
            <option>red</option>
          </select>
        </div>
        <button onClick={save} className="w-full bg-blue-500 text-white py-2 rounded hover:bg-blue-600">
          Save
        </button>
      </div>
    </div>
  );
};

export default SettingsPanel;