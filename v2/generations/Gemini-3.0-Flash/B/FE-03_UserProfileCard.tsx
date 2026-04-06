import React, { useState } from 'react';

const UserCard: React.FC = () => {
  const [following, setFollowing] = useState(false);

  const data = {
    name: 'Alex Rivera',
    avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200&h=200&fit=crop',
    bio: 'Full-stack developer who loves building meaningful products with clean code.',
  };

  return (
    <div className="min-h-screen bg-neutral-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-3xl shadow-sm border border-neutral-200 p-8 w-full max-w-xs flex flex-col items-center">
        <img src={data.avatar} alt="Avatar" className="w-20 h-20 rounded-full mb-4 object-cover" />
        <h3 className="text-lg font-bold text-neutral-900">{data.name}</h3>
        <p className="text-neutral-500 text-center text-sm mt-2 mb-6">{data.bio}</p>
        <button
          onClick={() => setFollowing(!following)}
          className={`w-full py-2 rounded-full font-medium text-sm transition-all ${
            following ? 'bg-neutral-100 text-neutral-800 border border-neutral-200' : 'bg-blue-600 text-white shadow-lg'
          }`}
        >
          {following ? 'Following' : 'Follow'}
        </button>
      </div>
    </div>
  );
};

export default UserCard;
