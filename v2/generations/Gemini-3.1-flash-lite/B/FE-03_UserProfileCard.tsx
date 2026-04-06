import React, { useState } from 'react';

// Constraint: { "framework": "React", "language": "TypeScript", "style": "tailwind" }
export default function UserProfileCard() {
  const [active, setActive] = useState(false);
  return (
    <div className="w-64 p-4 border rounded shadow bg-white flex flex-col items-center">
      <div className="w-20 h-20 bg-gray-300 rounded-full mb-4"></div>
      <h3 className="text-xl font-bold">User Name</h3>
      <p className="text-gray-600 text-center mb-4">Brief bio description goes here.</p>
      <button 
        className={`px-6 py-2 rounded ${active ? 'bg-gray-500' : 'bg-blue-600'} text-white`}
        onClick={() => setActive(!active)}
      >
        {active ? 'Following' : 'Follow'}
      </button>
    </div>
  );
}
