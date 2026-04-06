import React, { useState } from "react";

export default function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailErr, setEmailErr] = useState("");
  const [passErr, setPassErr] = useState("");
  const [done, setDone] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    let ok = true;
    if (!email) { setEmailErr("Email is required"); ok = false; }
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setEmailErr("Invalid email format"); ok = false; }
    else { setEmailErr(""); }
    if (!password) { setPassErr("Password is required"); ok = false; }
    else { setPassErr(""); }
    if (ok) setDone(true);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-lg w-full max-w-md p-8">
        <h2 className="text-2xl font-bold text-slate-900 text-center mb-2">Welcome</h2>
        <p className="text-slate-500 text-center text-sm mb-6">Sign in to continue</p>
        <form onSubmit={submit} className="space-y-5">
          <div>
            <label className="block text-sm text-slate-700 mb-1">Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            {emailErr && <p className="text-red-500 text-xs mt-1">{emailErr}</p>}
          </div>
          <div>
            <label className="block text-sm text-slate-700 mb-1">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            {passErr && <p className="text-red-500 text-xs mt-1">{passErr}</p>}
          </div>
          <button type="submit" className="w-full bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700">Sign In</button>
        </form>
        {done && <p className="text-green-600 text-sm text-center mt-4">Login successful!</p>}
      </div>
    </div>
  );
}
