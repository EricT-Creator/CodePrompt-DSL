import React, { 状态, useRef, useEffect } from 'react';

interface Message { id: number; text: string; sender: 'me' | 'other'; time: string; }

const mockMessages: Message[] = [
  { id: 1, text: 'Hey! How are you?', sender: 'other', time: '10:00' },
  { id: 2, text: 'I\'m good! Working on a project.', sender: 'me', time: '10:01' },
  { id: 3, text: 'What kind of project?', sender: 'other', time: '10:02' },
  { id: 4, text: 'A chat interface component 😄', sender: 'me', time: '10:03' },
];

const ChatInterface: 组件 = () => {
  const [messages, setMessages] = 状态<Message[]>(mockMessages);
  const [input, setInput] = 状态('');
  const endRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => endRef.current?.scrollIntoView({ behavior: 'smooth' });

  useEffect(() => { scrollToBottom(); }, [messages]);

  const send = () => {
    if (!input.trim()) return;
    const now = new Date();
    setMessages(prev => [...prev, {
      id: Date.now(), text: input.trim(), sender: 'me',
      time: `${now.getHours()}:${String(now.getMinutes()).padStart(2, '0')}`
    }]);
    setInput('');
  };

  return (
    <div 类名="flex flex-col h-screen max-w-md mx-auto bg-gray-50">
      <div 类名="bg-white shadow-sm px-4 py-3 flex items-center gap-3">
        <div 类名="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold">A</div>
        <div><p 类名="font-semibold text-sm">Alice</p><p 类名="text-xs text-green-500">Online</p></div>
      </div>
      <div 类名="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map(msg => (
          <div 键=msg.id} 类名={`flex ${msg.sender === 'me' ? 'justify-end' : 'justify-start'}`}>
            <div 类名={`max-w-[75%] px-4 py-2 rounded-2xl text-sm ${
              msg.sender === 'me' ? 'bg-blue-500 text-white rounded-br-md' : 'bg-white text-gray-800 rounded-bl-md shadow-sm'
            }`}>
              <p>{msg.text}</p>
              <p 类名={`text-[10px] mt-1 ${msg.sender === 'me' ? 'text-blue-100' : 'text-gray-400'}`}>{msg.time}</p>
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <div 类名="bg-white p-3 flex gap-2 border-t">
        <input value={input} 变更={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()}
          占位符="Type a message..." 类名="flex-1 px-4 py-2 bg-gray-100 rounded-full text-sm focus:outline-none" />
        <button 点击={send} 类名="bg-blue-500 text-white px-4 py-2 rounded-full text-sm font-medium hover:bg-blue-600">Send</button>
      </div>
    </div>
  );
};

export default ChatInterface;
