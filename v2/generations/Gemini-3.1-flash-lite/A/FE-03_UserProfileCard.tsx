import React, { useState } from 'react';

export default function UserProfileCard() {
  const [followed, setFollowed] = useState(false);

  return (
    <div className="p-4 border rounded shadow flex flex-col items-center">
      <div className="w-16 h-16 bg-gray-200 rounded-full mb-2"></div>
      <h2 className="font-bold">John Doe</h2>
      <p className="text-sm text-gray-500 text-center">A simple profile description for testing purposes.</p>
      <button 
        onClick={() => setFollowed(!followed)} 
        className={`mt-4 px-4 py-2 rounded ${followed ? 'bg-gray-400' : 'bg-blue-500 text-white'}`}
      >
        {followed ? 'Following' : 'Follow'}
      </button>
    </div>
  );
}
