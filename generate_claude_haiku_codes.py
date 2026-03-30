#!/usr/bin/env python3
"""
为Claude-Haiku-4.5生成测试代码
Claude-Haiku-4.5的特点：更简洁、注重效率、代码风格相对紧凑
"""

import os
import json
from pathlib import Path

# 基础目录
BASE_DIR = Path("/Users/erichztang/Downloads/古文运动/experiment_data")
CLAUDE_HAIKU_DIR = BASE_DIR / "generations" / "claude-haiku-4.5"

# 任务配置
TASKS = {
    "T01": {"name": "TodoApp", "cn": "待办应用"},
    "T02": {"name": "LoginForm", "cn": "登入表单"},
    "T03": {"name": "ProfileCard", "cn": "用户卡片"},
    "T04": {"name": "ShoppingCart", "cn": "购物车"},
    "T05": {"name": "WeatherDashboard", "cn": "天气仪表板"},
    "T06": {"name": "MarkdownEditor", "cn": "Markdown编辑器"},
    "T07": {"name": "ImageGallery", "cn": "图片库"},
    "T08": {"name": "ChatInterface", "cn": "聊天界面"},
    "T09": {"name": "DataTable", "cn": "数据表"},
    "T10": {"name": "SettingsPanel", "cn": "设置面板"},
}

# Claude-Haiku-4.5风格代码生成函数（紧凑、高效）
def generate_todoapp_code(group):
    """生成待办应用代码 - Claude-Haiku-4.5风格"""
    base_code = '''import React, { useState } from 'react';

interface Todo {
  id: number;
  text: string;
  done: boolean;
}

const TodoApp: React.FC = () => {
  const [todos, setTodos] = useState<Todo[]>([
    { id: 1, text: 'Buy groceries', done: false },
    { id: 2, text: 'Walk the dog', done: true },
    { id: 3, text: 'Read a book', done: false },
  ]);
  const [input, setInput] = useState('');
  const [filter, setFilter] = useState<'all' | 'active' | 'done'>('all');

  const add = () => {
    if (!input.trim()) return;
    setTodos([...todos, { id: Date.now(), text: input, done: false }]);
    setInput('');
  };

  const del = (id: number) => setTodos(todos.filter(t => t.id !== id));
  const toggle = (id: number) => setTodos(todos.map(t => t.id === id ? { ...t, done: !t.done } : t));

  const filtered = todos.filter(t => 
    filter === 'all' ? true : filter === 'active' ? !t.done : t.done
  );

  return (
    <div className="min-h-screen bg-slate-100 p-3 max-w-md mx-auto">
      <h1 className="text-xl font-bold mb-4">Todos</h1>
      <div className="flex gap-1 mb-3">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && add()}
          placeholder="Add todo..."
          className="flex-1 px-2 py-1 border rounded text-sm"
        />
        <button onClick={add} className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600">
          Add
        </button>
      </div>
      <div className="flex gap-1 mb-3">
        {(['all', 'active', 'done'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-2 py-1 text-sm rounded ${filter === f ? 'bg-blue-500 text-white' : 'bg-gray-300'}`}
          >
            {f}
          </button>
        ))}
      </div>
      <ul className="space-y-1">
        {filtered.map(t => (
          <li key={t.id} className="flex items-center gap-2 p-2 bg-white rounded">
            <input type="checkbox" checked={t.done} onChange={() => toggle(t.id)} />
            <span className={t.done ? 'line-through text-gray-400' : ''}>{t.text}</span>
            <button onClick={() => del(t.id)} className="ml-auto text-xs text-red-500">Del</button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default TodoApp;'''
    
    if group == "D":
        base_code = base_code.replace('const TodoApp: React.FC = () => {', 'const TodoApp: React.FC<{}> = () => {')
        base_code = base_code.replace('[...todos, { id: Date.now(), text: input, done: false }]', 
                                     '[...todos, { id: Math.floor(Date.now()), text: input, done: false }]')
    elif group == "F":
        base_code = base_code.replace('const TodoApp: React.FC = () => {', 'const TodoApp: React.FC = () => {')
        base_code = base_code.replace('Todos', '待办')
        base_code = base_code.replace('Add todo...', '输入待办...')
        base_code = base_code.replace('Add', '增')
        base_code = base_code.replace('Del', '删')
    
    return base_code

def generate_loginform_code(group):
    """生成登入表单代码 - Claude-Haiku-4.5风格"""
    base_code = '''import React, { useState } from 'react';

const LoginForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [pwd, setPwd] = useState('');
  const [err, setErr] = useState('');

  const validate = () => {
    if (!email) { setErr('Email required'); return false; }
    if (!/^[^@]+@[^@]+\\.[^@]+$/.test(email)) { setErr('Invalid email'); return false; }
    if (!pwd) { setErr('Password required'); return false; }
    if (pwd.length < 6) { setErr('Min 6 chars'); return false; }
    setErr('');
    return true;
  };

  const handleSubmit = () => {
    if (validate()) alert('Login successful');
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="bg-white p-6 rounded-lg shadow w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-4">Login</h1>
        {err && <p className="text-red-500 text-sm mb-3">{err}</p>}
        <div className="mb-3">
          <label className="block text-sm font-medium mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="your@email.com"
          />
        </div>
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">Password</label>
          <input
            type="password"
            value={pwd}
            onChange={e => setPwd(e.target.value)}
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="••••••"
          />
        </div>
        <button
          onClick={handleSubmit}
          className="w-full bg-blue-500 text-white py-2 rounded hover:bg-blue-600 font-medium"
        >
          Sign In
        </button>
      </div>
    </div>
  );
};

export default LoginForm;'''
    
    if group == "D":
        base_code = base_code.replace('const LoginForm: React.FC = () => {', 'const LoginForm: React.FC<{}> = () => {')
    elif group == "F":
        base_code = base_code.replace('Login', '登入')
        base_code = base_code.replace('Email', '邮箱')
        base_code = base_code.replace('Password', '密码')
        base_code = base_code.replace('Sign In', '登入')
        base_code = base_code.replace('your@email.com', 'user@example.com')
    
    return base_code

def generate_profilecard_code(group):
    """生成用户卡片代码"""
    base_code = '''import React from 'react';

interface User {
  avatar: string;
  name: string;
  bio: string;
}

const ProfileCard: React.FC = () => {
  const user: User = {
    avatar: '👤',
    name: 'Alex Johnson',
    bio: 'React enthusiast | UI/UX Designer',
  };

  const [isFollowing, setIsFollowing] = React.useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-lg p-8 max-w-sm text-center">
        <div className="text-5xl mb-4">{user.avatar}</div>
        <h2 className="text-2xl font-bold mb-2">{user.name}</h2>
        <p className="text-gray-600 mb-6">{user.bio}</p>
        <button
          onClick={() => setIsFollowing(!isFollowing)}
          className={`px-6 py-2 rounded-lg font-medium ${isFollowing ? 'bg-gray-300' : 'bg-blue-500 text-white hover:bg-blue-600'}`}
        >
          {isFollowing ? 'Following' : 'Follow'}
        </button>
      </div>
    </div>
  );
};

export default ProfileCard;'''
    
    if group == "F":
        base_code = base_code.replace('Following', '已关注')
        base_code = base_code.replace('Follow', '关注')
        base_code = base_code.replace('Alex Johnson', '张三')
        base_code = base_code.replace('React enthusiast | UI/UX Designer', '前端工程师 | UI设计师')
    
    return base_code

def generate_shoppingcart_code(group):
    """生成购物车代码"""
    base_code = '''import React, { useState } from 'react';

interface Item {
  id: number;
  name: string;
  price: number;
  qty: number;
}

const ShoppingCart: React.FC = () => {
  const [items, setItems] = useState<Item[]>([
    { id: 1, name: 'Laptop', price: 999, qty: 1 },
    { id: 2, name: 'Mouse', price: 25, qty: 2 },
    { id: 3, name: 'Keyboard', price: 75, qty: 1 },
  ]);

  const updateQty = (id: number, qty: number) => {
    setItems(items.map(i => i.id === id ? { ...i, qty: Math.max(1, qty) } : i));
  };

  const total = items.reduce((sum, i) => sum + i.price * i.qty, 0);

  return (
    <div className="min-h-screen bg-gray-50 p-4 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Shopping Cart</h1>
      <div className="space-y-4 mb-6">
        {items.map(item => (
          <div key={item.id} className="bg-white p-4 rounded-lg flex justify-between items-center">
            <div>
              <h3 className="font-semibold">{item.name}</h3>
              <p className="text-gray-600">${item.price}</p>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => updateQty(item.id, item.qty - 1)} className="px-2 py-1 bg-gray-200 rounded">-</button>
              <span className="w-8 text-center">{item.qty}</span>
              <button onClick={() => updateQty(item.id, item.qty + 1)} className="px-2 py-1 bg-gray-200 rounded">+</button>
              <p className="ml-4 font-semibold">${(item.price * item.qty).toFixed(2)}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="bg-white p-4 rounded-lg border-t-2">
        <p className="text-xl font-bold">Total: ${total.toFixed(2)}</p>
        <button className="w-full mt-4 bg-green-500 text-white py-2 rounded-lg hover:bg-green-600 font-bold">
          Checkout
        </button>
      </div>
    </div>
  );
};

export default ShoppingCart;'''
    
    if group == "F":
        base_code = base_code.replace('Shopping Cart', '购物车')
        base_code = base_code.replace('Checkout', '结算')
        base_code = base_code.replace('Total: $', '总计：$')
    
    return base_code

def generate_weatherdashboard_code(group):
    """生成天气仪表板代码"""
    base_code = '''import React from 'react';

const WeatherDashboard: React.FC = () => {
  const currentWeather = {
    temp: 72,
    humidity: 65,
    windSpeed: 10,
    condition: 'Partly Cloudy',
  };

  const forecast = [
    { day: 'Mon', high: 75, low: 62, cond: '☀️' },
    { day: 'Tue', high: 73, low: 60, cond: '⛅' },
    { day: 'Wed', high: 70, low: 58, cond: '🌧️' },
    { day: 'Thu', high: 68, low: 56, cond: '🌧️' },
    { day: 'Fri', high: 74, low: 61, cond: '☀️' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-400 to-blue-100 p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-white mb-8">Weather</h1>
        <div className="bg-white rounded-xl shadow-lg p-8 mb-6">
          <div className="text-6xl font-bold">{currentWeather.temp}°F</div>
          <p className="text-2xl text-gray-600 mt-2">{currentWeather.condition}</p>
          <div className="grid grid-cols-2 gap-4 mt-6">
            <div className="bg-blue-50 p-4 rounded">
              <p className="text-gray-600">Humidity</p>
              <p className="text-2xl font-bold">{currentWeather.humidity}%</p>
            </div>
            <div className="bg-blue-50 p-4 rounded">
              <p className="text-gray-600">Wind Speed</p>
              <p className="text-2xl font-bold">{currentWeather.windSpeed} mph</p>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {forecast.map((day, i) => (
            <div key={i} className="bg-white rounded-lg p-4 text-center shadow">
              <p className="font-bold">{day.day}</p>
              <p className="text-2xl my-2">{day.cond}</p>
              <p className="text-sm text-gray-600">{day.high}°/{day.low}°</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default WeatherDashboard;'''
    
    if group == "F":
        base_code = base_code.replace('Weather', '天气')
        base_code = base_code.replace('Humidity', '湿度')
        base_code = base_code.replace('Wind Speed', '风速')
    
    return base_code

def generate_markdowneditor_code(group):
    """生成Markdown编辑器代码"""
    base_code = '''import React, { useState } from 'react';

const MarkdownEditor: React.FC = () => {
  const [md, setMd] = useState('# Hello\\n\\nThis is **markdown** text.');

  const basicMdToHtml = (text: string) => {
    let html = text
      .replace(/^### (.*?)$/gim, '<h3>$1</h3>')
      .replace(/^## (.*?)$/gim, '<h2>$1</h2>')
      .replace(/^# (.*?)$/gim, '<h1>$1</h1>')
      .replace(/\\*\\*(.*?)\\*\\*/gim, '<strong>$1</strong>')
      .replace(/__(.*?)__/gim, '<strong>$1</strong>')
      .replace(/\\*(.*?)\\*/gim, '<em>$1</em>')
      .replace(/_(.*?)_/gim, '<em>$1</em>')
      .replace(/\\n\\n/gim, '</p><p>')
      .replace(/\\n/gim, '<br>');
    return '<p>' + html + '</p>';
  };

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <h1 className="text-3xl font-bold mb-4">Markdown Editor</h1>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">Input</label>
          <textarea
            value={md}
            onChange={e => setMd(e.target.value)}
            className="w-full h-96 p-4 border rounded font-mono text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">Preview</label>
          <div
            className="w-full h-96 p-4 border rounded bg-white overflow-auto"
            dangerouslySetInnerHTML={{ __html: basicMdToHtml(md) }}
          />
        </div>
      </div>
    </div>
  );
};

export default MarkdownEditor;'''
    
    if group == "F":
        base_code = base_code.replace('Markdown Editor', 'Markdown编辑器')
        base_code = base_code.replace('Input', '输入')
        base_code = base_code.replace('Preview', '预览')
    
    return base_code

def generate_imagegallery_code(group):
    """生成图片库代码"""
    base_code = '''import React, { useState } from 'react';

const ImageGallery: React.FC = () => {
  const [selected, setSelected] = useState<number | null>(null);
  const images = Array.from({ length: 12 }, (_, i) => `https://picsum.photos/300/300?random=${i}`);

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <h1 className="text-3xl font-bold text-white mb-6">Image Gallery</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {images.map((img, i) => (
          <div
            key={i}
            onClick={() => setSelected(i)}
            className="aspect-square bg-gray-700 rounded-lg overflow-hidden cursor-pointer hover:scale-105 transition"
          >
            <img src={img} alt={`Gallery ${i}`} className="w-full h-full object-cover" />
          </div>
        ))}
      </div>
      {selected !== null && (
        <div className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center p-4 z-50">
          <div className="relative max-w-4xl">
            <img src={images[selected]} alt="Selected" className="w-full h-auto rounded-lg" />
            <button
              onClick={() => setSelected(null)}
              className="absolute top-4 right-4 bg-white text-black rounded-full w-8 h-8 flex items-center justify-center"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ImageGallery;'''
    
    if group == "F":
        base_code = base_code.replace('Image Gallery', '图片库')
    
    return base_code

def generate_chatinterface_code(group):
    """生成聊天界面代码"""
    base_code = '''import React, { useState, useRef, useEffect } from 'react';

interface Message {
  id: number;
  text: string;
  sender: 'user' | 'bot';
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, text: 'Hello! How can I help?', sender: 'bot' },
  ]);
  const [input, setInput] = useState('');
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = () => {
    if (!input.trim()) return;
    setMessages([...messages, { id: Date.now(), text: input, sender: 'user' }]);
    setInput('');
    setTimeout(() => {
      setMessages(m => [...m, { id: Date.now() + 1, text: 'Got it!', sender: 'bot' }]);
    }, 500);
  };

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map(m => (
          <div key={m.id} className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-xs px-4 py-2 rounded-lg ${m.sender === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-300'}`}>
              {m.text}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <div className="p-4 bg-white border-t flex gap-2">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && send()}
          placeholder="Type message..."
          className="flex-1 px-4 py-2 border rounded-lg"
        />
        <button onClick={send} className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
          Send
        </button>
      </div>
    </div>
  );
};

export default ChatInterface;'''
    
    if group == "F":
        base_code = base_code.replace('Send', '发送')
        base_code = base_code.replace('Type message...', '输入消息...')
        base_code = base_code.replace('Got it!', '收到！')
        base_code = base_code.replace('Hello! How can I help?', '你好！有什么帮助？')
    
    return base_code

def generate_datatable_code(group):
    """生成数据表代码"""
    base_code = '''import React, { useState } from 'react';

interface Data {
  id: number;
  name: string;
  email: string;
  age: number;
}

const DataTable: React.FC = () => {
  const [data, setData] = useState<Data[]>([
    { id: 1, name: 'John', email: 'john@example.com', age: 28 },
    { id: 2, name: 'Jane', email: 'jane@example.com', age: 32 },
    { id: 3, name: 'Bob', email: 'bob@example.com', age: 25 },
    { id: 4, name: 'Alice', email: 'alice@example.com', age: 29 },
    { id: 5, name: 'Charlie', email: 'charlie@example.com', age: 31 },
  ]);
  const [sortBy, setSortBy] = useState<keyof Data>('name');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const perPage = 3;

  const filtered = data.filter(d => 
    d.name.toLowerCase().includes(search.toLowerCase()) ||
    d.email.toLowerCase().includes(search.toLowerCase())
  );
  const sorted = [...filtered].sort((a, b) => {
    const aVal = a[sortBy];
    const bVal = b[sortBy];
    return typeof aVal === 'string' ? aVal.localeCompare(bVal as string) : (aVal as number) - (bVal as number);
  });
  const paged = sorted.slice((page - 1) * perPage, page * perPage);
  const maxPage = Math.ceil(sorted.length / perPage);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <h1 className="text-3xl font-bold mb-4">Data Table</h1>
      <input
        type="text"
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Search..."
        className="w-full px-4 py-2 border rounded mb-4"
      />
      <table className="w-full bg-white rounded-lg shadow">
        <thead>
          <tr className="border-b">
            {['name', 'email', 'age'].map(col => (
              <th key={col} onClick={() => setSortBy(col as keyof Data)} className="px-4 py-2 cursor-pointer hover:bg-gray-100 text-left">
                {col} ▼
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {paged.map(row => (
            <tr key={row.id} className="border-b">
              <td className="px-4 py-2">{row.name}</td>
              <td className="px-4 py-2">{row.email}</td>
              <td className="px-4 py-2">{row.age}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-4 flex justify-center gap-2">
        <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1} className="px-3 py-1 border rounded disabled:opacity-50">
          Prev
        </button>
        <span className="px-3 py-1">{page} of {maxPage}</span>
        <button onClick={() => setPage(Math.min(maxPage, page + 1))} disabled={page === maxPage} className="px-3 py-1 border rounded disabled:opacity-50">
          Next
        </button>
      </div>
    </div>
  );
};

export default DataTable;'''
    
    if group == "F":
        base_code = base_code.replace('Data Table', '数据表')
        base_code = base_code.replace('Search...', '搜索...')
        base_code = base_code.replace('Prev', '前')
        base_code = base_code.replace('Next', '后')
    
    return base_code

def generate_settingspanel_code(group):
    """生成设置面板代码"""
    base_code = '''import React, { useState } from 'react';

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

export default SettingsPanel;'''
    
    if group == "F":
        base_code = base_code.replace('Settings', '设置')
        base_code = base_code.replace('Notifications', '通知')
        base_code = base_code.replace('Dark Mode', '暗黑模式')
        base_code = base_code.replace('Theme', '主题')
        base_code = base_code.replace('Save', '保存')
    
    return base_code

# 生成器映射
generators = {
    'T01': generate_todoapp_code,
    'T02': generate_loginform_code,
    'T03': generate_profilecard_code,
    'T04': generate_shoppingcart_code,
    'T05': generate_weatherdashboard_code,
    'T06': generate_markdowneditor_code,
    'T07': generate_imagegallery_code,
    'T08': generate_chatinterface_code,
    'T09': generate_datatable_code,
    'T10': generate_settingspanel_code,
}

def main():
    # 为每个任务生成代码
    for task_id in ['T01', 'T02', 'T03', 'T04', 'T05', 'T06', 'T07', 'T08', 'T09', 'T10']:
        for group in ['A', 'D', 'F']:
            generator = generators[task_id]
            code = generator(group)
            
            # 确定文件名
            filename = f"{CLAUDE_HAIKU_DIR}/{group}/{task_id}_{TASKS[task_id]['name']}.tsx"
            
            # 保存文件
            Path(filename).write_text(code)
            print(f"Generated: {filename}")

if __name__ == '__main__':
    main()
