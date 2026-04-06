import React, { useState } from 'react';

const UserCard = () => {
  const [followed, setFollowed] = useState(false);

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="bg-white rounded shadow-md p-6 max-w-xs">
        <div className="flex flex-col items-center text-center">
          <img
            src="https://api.dicebear.com/7.x/avataaars/svg?seed=user2"
            alt="User"
            className="w-20 h-20 rounded-full mb-4 border-2 border-blue-500"
          />
          <h3 className="text-lg font-bold">Jane Smith</h3>
          <p className="text-sm text-gray-600 my-2">Designer and developer from NYC</p>

          <button
            onClick={() => setFollowed(!followed)}
            className={`mt-4 px-6 py-2 rounded font-medium ${
              followed ? 'bg-gray-300 text-black' : 'bg-blue-600 text-white'
            }`}
          >
            {followed ? 'Following' : 'Follow'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default UserCard;