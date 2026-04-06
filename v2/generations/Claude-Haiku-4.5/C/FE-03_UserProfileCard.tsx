import React, { useState } from 'react';

const ProfileCard = () => {
  const [followers, setFollowers] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow p-8 w-full max-w-sm">
        <div className="flex flex-col items-center text-center">
          <img
            src="https://api.dicebear.com/7.x/avataaars/svg?seed=profile3"
            alt="Profile"
            className="w-24 h-24 rounded-full border-2 border-indigo-500 mb-4"
          />
          <h2 className="text-xl font-bold text-gray-900">Alex Johnson</h2>
          <p className="text-gray-700 text-sm mt-2">Passionate about tech and design</p>

          <button
            onClick={() => setFollowers(!followers)}
            className={`mt-6 w-full py-2 rounded font-medium transition ${
              followers ? 'bg-gray-200 text-gray-900' : 'bg-indigo-600 text-white'
            }`}
          >
            {followers ? 'Following' : 'Follow'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProfileCard;