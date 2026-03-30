import React, { useState, useRef, useEffect } from 'react';

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

export default ChatInterface;