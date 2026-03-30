import React, { useState, useRef, useEffect } from 'react';

interface MessageProps { id: number; text: string; sender: 'me' | 'other'; time: string; }

const mockMessages: Message[] = [
  { id: 1, text: 'Hey! How are you?', sender: 'other', time: '10:00' },
  { id: 2, text: 'I\'m good! Working on a project.', sender: 'me', time: '10:01' },
  { id: 3, text: 'What kind of project?', sender: 'other', time: '10:02' },
  { id: 4, text: 'A chat interface component 😄', sender: 'me', time: '10:03' },
];

const ChatInterface: React.FunctionalComponent = () => {
  const [messages, setMessages] = useState<Message[]>(mockMessages);
  const [input, setInput] = useState('');
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
    <div className="flex flex-col h-screen max-w-md mx-auto bg-gray-50">
      <div className="bg-white shadow-sm px-4 py-3 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold">A</div>
        <div><p className="font-semibold text-sm">Alice</p><p className="text-xs text-green-500">Online</p></div>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.sender === 'me' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[75%] px-4 py-2 rounded-2xl text-sm ${
              msg.sender === 'me' ? 'bg-blue-500 text-white rounded-br-md' : 'bg-white text-gray-800 rounded-bl-md shadow-sm'
            }`}>
              <p>{msg.text}</p>
              <p className={`text-[10px] mt-1 ${msg.sender === 'me' ? 'text-blue-100' : 'text-gray-400'}`}>{msg.time}</p>
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <div className="bg-white p-3 flex gap-2 border-t">
        <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="Type a message..." className="flex-1 px-4 py-2 bg-gray-100 rounded-full text-sm focus:outline-none" />
        <button onClick={send} className="bg-blue-500 text-white px-4 py-2 rounded-full text-sm font-medium hover:bg-blue-600">Send</button>
      </div>
    </div>
  );
};

export default ChatInterface;
