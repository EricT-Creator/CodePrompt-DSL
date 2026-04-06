import React, { useState } from 'react';

export default function UserProfileCard() {
  const [followed, setFollowed] = useState(false);

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-slate-800 rounded-xl shadow-xl overflow-hidden border border-slate-700">
        <div className="h-20 bg-gradient-to-r from-cyan-600 to-blue-600"></div>
        <div className="px-6 pb-6">
          <div className="relative -top-10 mb-[-24px]">
            <img
              src="https://api.dicebear.com/7.x/avataaars/svg?seed=User"
              alt="Profile"
              className="w-20 h-20 rounded-full border-4 border-slate-800 bg-slate-700"
            />
            <span className="absolute bottom-1 right-1 w-4 h-4 bg-green-500 border-2 border-slate-800 rounded-full"></span>
          </div>
          <div className="mt-12">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-lg font-bold text-white">Jordan Lee</h2>
                <p className="text-slate-400 text-sm">@jordanlee</p>
              </div>
              <button
                onClick={() => setFollowed(!followed)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  followed
                    ? 'bg-slate-700 text-slate-300 border border-slate-600'
                    : 'bg-cyan-600 text-white hover:bg-cyan-700'
                }`}
              >
                {followed ? 'Following' : 'Follow'}
              </button>
            </div>
            <p className="mt-3 text-slate-300 text-sm">
              Software engineer building scalable systems. Open source contributor.
            </p>
            <div className="mt-4 flex gap-4 text-sm">
              <span className="text-slate-400">
                <strong className="text-white">456</strong> <span className="text-slate-500">following</span>
              </span>
              <span className="text-slate-400">
                <strong className="text-white">2.1k</strong> <span className="text-slate-500">followers</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
