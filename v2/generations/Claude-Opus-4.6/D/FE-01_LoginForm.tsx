import React, { useState, FormEvent } from "react";

export default function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailErr, setEmailErr] = useState("");
  const [pwErr, setPwErr] = useState("");
  const [ok, setOk] = useState(false);

  const checkEmail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    let eErr = "";
    let pErr = "";

    if (!email.trim()) {
      eErr = "请输入邮箱";
    } else if (!checkEmail(email.trim())) {
      eErr = "邮箱格式不正确";
    }

    if (!password) {
      pErr = "密码不可为空";
    }

    setEmailErr(eErr);
    setPwErr(pErr);
    setOk(!eErr && !pErr);
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-lg p-6">
        <h1 className="text-xl font-bold text-center text-gray-800 mb-6">登入</h1>

        <form onSubmit={submit} noValidate className="space-y-4">
          <div>
            <label htmlFor="d-email" className="block text-sm font-medium text-gray-700 mb-1">
              邮箱
            </label>
            <input
              id="d-email"
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setEmailErr("");
                setOk(false);
              }}
              className={`w-full border rounded-lg px-3 py-2 text-sm outline-none ${
                emailErr
                  ? "border-red-400 bg-red-50"
                  : "border-gray-300 focus:border-blue-500"
              }`}
              placeholder="example@mail.com"
            />
            {emailErr && <p className="text-xs text-red-500 mt-1">{emailErr}</p>}
          </div>

          <div>
            <label htmlFor="d-pw" className="block text-sm font-medium text-gray-700 mb-1">
              密码
            </label>
            <input
              id="d-pw"
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setPwErr("");
                setOk(false);
              }}
              className={`w-full border rounded-lg px-3 py-2 text-sm outline-none ${
                pwErr
                  ? "border-red-400 bg-red-50"
                  : "border-gray-300 focus:border-blue-500"
              }`}
              placeholder="输入密码"
            />
            {pwErr && <p className="text-xs text-red-500 mt-1">{pwErr}</p>}
          </div>

          <button
            type="submit"
            className="w-full bg-blue-600 text-white rounded-lg py-2.5 text-sm font-semibold hover:bg-blue-700 transition"
          >
            登入
          </button>
        </form>

        {ok && (
          <p className="text-green-600 text-sm text-center mt-4">验证通过</p>
        )}
      </div>
    </div>
  );
}
