import React, { useState } from 'react';

// [L]TS[S]React[F]SFC[Y]TW[D]NOX[M]MOB[DT]MOCK[O]CODE
export default function UserProfileCard() {
  const [f, setF] = useState(false);
  return (
    <div className="p-4 border rounded">
      <div className="w-12 h-12 bg-gray-200 rounded-full" />
      <h4 className="font-bold">User</h4>
      <p>Bio text...</p>
      <button className="bg-blue-500 text-white p-2" onClick={() => setF(!f)}>
        {f ? 'Unfollow' : 'Follow'}
      </button>
    </div>
  );
}
