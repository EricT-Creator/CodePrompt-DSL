import React, { useState } from "react";

const profile = {
  avatar: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&w=300&q=80",
  username: "Mia Chen",
  bio: "Turns messy specs into repeatable systems and practical execution plans.",
};

export default function UserProfileCard() {
  const [following, setFollowing] = useState(false);

  return (
    <main className="min-h-screen bg-zinc-950 px-4 py-10 text-white">
      <section className="mx-auto max-w-sm rounded-3xl bg-zinc-900 p-6 ring-1 ring-white/10">
        <div className="flex flex-col items-center text-center">
          <div className="relative">
            <img
              src={profile.avatar}
              alt={profile.username}
              className="h-24 w-24 rounded-full object-cover"
            />
            <span className="absolute bottom-1 right-1 h-4 w-4 rounded-full border-2 border-zinc-900 bg-emerald-400" />
          </div>
          <h1 className="mt-4 text-2xl font-bold">{profile.username}</h1>
          <p className="mt-3 text-sm leading-6 text-zinc-400">{profile.bio}</p>
          <button
            type="button"
            onClick={() => setFollowing((prev) => !prev)}
            className={`mt-6 rounded-2xl px-5 py-3 text-sm font-semibold transition ${
              following ? "bg-white text-zinc-950 hover:bg-zinc-200" : "bg-emerald-400 text-zinc-950 hover:bg-emerald-300"
            }`}
          >
            {following ? "Following" : "Follow"}
          </button>
        </div>
      </section>
    </main>
  );
}
