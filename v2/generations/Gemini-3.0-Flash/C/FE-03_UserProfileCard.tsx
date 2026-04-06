import React, { useState } from 'react';

const UserCard: React.FC = () => {
  const [follow, setFollow] = useState(false);
  
  return (
    <div className="flex items-center justify-center h-screen bg-zinc-50 font-sans">
      <div className="w-64 bg-white p-6 rounded-2xl shadow-sm border border-zinc-200 text-center">
        <img 
          src="https://api.dicebear.com/7.x/avataaars/svg?seed=Lucky" 
          className="w-16 h-16 rounded-full mx-auto mb-4 bg-zinc-100" 
          alt="User" 
        />
        <h4 className="font-bold text-zinc-900">John Smith</h4>
        <p className="text-xs text-zinc-400 mt-1 mb-4 px-2">Creative engineer focused on building interactive and responsive web experiences.</p>
        <button 
          onClick={() => setFollow(!follow)}
          className={`w-full py-2 rounded-lg text-xs font-bold transition ${follow ? 'bg-zinc-100 text-zinc-600' : 'bg-black text-white'}`}
        >
          {follow ? 'Following' : 'Follow'}
        </button>
      </div>
    </div>
  );
};

export default UserCard;
