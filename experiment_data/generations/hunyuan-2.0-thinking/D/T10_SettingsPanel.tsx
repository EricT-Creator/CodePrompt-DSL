import React, { useState } from 'react';

interface SettingsProps {
  darkMode: boolean;
  notifications: boolean;
  autoSave: boolean;
  language: string;
  fontSize: string;
}

const SettingsPanel: React.FunctionalComponent = () => {
  const [settings, setSettings] = useState<Settings>({
    darkMode: false, notifications: true, autoSave: true, language: 'en', fontSize: 'medium',
  });
  const [saved, setSaved] = useState(false);

  const toggle = (key: keyof Settings) =>
    setSettings(prev => ({ ...prev, [key]: !prev[key] }));

  const update = (key: keyof Settings, value: string) =>
    setSettings(prev => ({ ...prev, [key]: value }));

  const save = () => { setSaved(true); setTimeout(() => setSaved(false), 2000); };

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-lg mx-auto">
        <h1 className="text-2xl font-bold mb-6">Settings</h1>
        <div className="bg-white rounded-xl shadow-sm divide-y">
          {[
            { label: 'Dark Mode', key: 'darkMode' as const },
            { label: 'Notifications', key: 'notifications' as const },
            { label: 'Auto Save', key: 'autoSave' as const },
          ].map(item => (
            <div key={item.key} className="flex items-center justify-between px-4 py-4">
              <span className="text-gray-700 font-medium">{item.label}</span>
              <button onClick={() => toggle(item.key)}
                className={`w-12 h-6 rounded-full relative transition ${settings[item.key] ? 'bg-blue-500' : 'bg-gray-300'}`}>
                <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition ${settings[item.key] ? 'left-6' : 'left-0.5'}`} />
              </button>
            </div>
          ))}
          <div className="flex items-center justify-between px-4 py-4">
            <span className="text-gray-700 font-medium">Language</span>
            <select value={settings.language} onChange={e => update('language', e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="en">English</option>
              <option value="zh">中文</option>
              <option value="ja">日本語</option>
            </select>
          </div>
          <div className="flex items-center justify-between px-4 py-4">
            <span className="text-gray-700 font-medium">Font Size</span>
            <select value={settings.fontSize} onChange={e => update('fontSize', e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="small">Small</option>
              <option value="medium">Medium</option>
              <option value="large">Large</option>
            </select>
          </div>
        </div>
        <button onClick={save}
          className={`w-full mt-6 py-3 rounded-lg font-medium text-white transition ${saved ? 'bg-green-500' : 'bg-blue-500 hover:bg-blue-600'}`}>
          {saved ? '✓ Saved!' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
};

export default SettingsPanel;
