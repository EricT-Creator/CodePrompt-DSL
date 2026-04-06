import React, { useState } from "react";

export default function LoginForm() {
  const [email, setEmail] = useState("");
  const [pwd, setPwd] = useState("");
  const [errEmail, setErrEmail] = useState("");
  const [errPwd, setErrPwd] = useState("");
  const [ok, setOk] = useState(false);

  const onEmailChange = (v: string) => {
    setEmail(v);
    if (errEmail) setErrEmail("");
  };
  const onPwdChange = (v: string) => {
    setPwd(v);
    if (errPwd) setErrPwd("");
  };

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let valid = true;
    if (!email.trim()) { setErrEmail("Email required"); valid = false; }
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setErrEmail("Bad email format"); valid = false; }
    if (!pwd.trim()) { setErrPwd("Password required"); valid = false; }
    if (valid) setOk(true);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-stone-50 p-4">
      <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow">
        <h1 className="mb-1 text-center text-lg font-semibold text-stone-900">Login</h1>
        <p className="mb-5 text-center text-xs text-stone-400">Enter your credentials</p>
        <form onSubmit={onSubmit} className="space-y-3">
          <div>
            <label htmlFor="e" className="mb-0.5 block text-xs font-medium text-stone-600">Email</label>
            <input id="e" type="email" value={email} onChange={e => onEmailChange(e.target.value)}
              className="w-full rounded-md border border-stone-200 px-3 py-1.5 text-sm focus:border-blue-400 focus:outline-none" />
            {errEmail && <p className="mt-0.5 text-[11px] text-red-500">{errEmail}</p>}
          </div>
          <div>
            <label htmlFor="p" className="mb-0.5 block text-xs font-medium text-stone-600">Password</label>
            <input id="p" type="password" value={pwd} onChange={e => onPwdChange(e.target.value)}
              className="w-full rounded-md border border-stone-200 px-3 py-1.5 text-sm focus:border-blue-400 focus:outline-none" />
            {errPwd && <p className="mt-0.5 text-[11px] text-red-500">{errPwd}</p>}
          </div>
          <button type="submit" className="w-full rounded-md bg-stone-900 py-1.5 text-sm text-white hover:bg-stone-700">Login</button>
        </form>
        {ok && <p className="mt-3 text-center text-xs text-emerald-600">Success!</p>}
      </div>
    </div>
  );
}
