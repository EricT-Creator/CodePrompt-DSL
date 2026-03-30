import React from 'react';

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

export default ProfileCard;