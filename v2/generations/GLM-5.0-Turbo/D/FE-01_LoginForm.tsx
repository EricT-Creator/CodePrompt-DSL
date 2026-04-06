import React, { useState } from "react";

export default function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [success, setSuccess] = useState(false);

  const validate = () => {
    let emailValid = true, passValid = true;
    if (!email) { setEmailError("邮箱不可空"); emailValid = false; }
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setEmailError("邮箱格式不合"); emailValid = false; }
    else setEmailError("");
    if (!password) { setPasswordError("密码不可空"); passValid = false; }
    else setPasswordError("");
    return emailValid && passValid;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) setSuccess(true);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-7">
        <h1 className="text-xl font-bold text-gray-800 text-center mb-1">登入</h1>
        <p className="text-gray-400 text-center text-xs mb-5">输入邮箱与密码以继续</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1 font-medium">邮箱</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent" placeholder="you@example.com" />
            {emailError && <p className="text-red-500 text-xs mt-1">{emailError}</p>}
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1 font-medium">密码</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent" placeholder="输入密码" />
            {passwordError && <p className="text-red-500 text-xs mt-1">{passwordError}</p>}
          </div>
          <button type="submit" className="w-full bg-blue-500 text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-blue-600 transition">登入</button>
        </form>
        {success && <p className="text-green-500 text-sm text-center mt-4 font-medium">登入成功</p>}
      </div>
    </div>
  );
}
