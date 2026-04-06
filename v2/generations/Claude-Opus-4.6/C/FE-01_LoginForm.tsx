import React, { useState } from "react";

export default function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [loginOk, setLoginOk] = useState(false);

  const isValidEmail = (val: string) =>
    /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(val.trim());

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const nextErrors: { email?: string; password?: string } = {};

    if (!email.trim()) {
      nextErrors.email = "Email is required";
    } else if (!isValidEmail(email)) {
      nextErrors.email = "Enter a valid email";
    }

    if (!password) {
      nextErrors.password = "Password is required";
    }

    setErrors(nextErrors);
    setLoginOk(Object.keys(nextErrors).length === 0);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl">
        <h1 className="text-center text-2xl font-bold text-gray-800 mb-1">Sign In</h1>
        <p className="text-center text-gray-400 text-sm mb-6">
          Use your email and password
        </p>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1" htmlFor="c-email">
              Email Address
            </label>
            <input
              id="c-email"
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setErrors((p) => ({ ...p, email: undefined }));
                setLoginOk(false);
              }}
              placeholder="name@domain.com"
              className={`w-full rounded-lg border px-3 py-2 text-sm outline-none transition ${
                errors.email
                  ? "border-rose-400 ring-2 ring-rose-100"
                  : "border-gray-300 focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
              }`}
            />
            {errors.email && (
              <span className="text-xs text-rose-500 mt-0.5 block">{errors.email}</span>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1" htmlFor="c-pw">
              Password
            </label>
            <input
              id="c-pw"
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setErrors((p) => ({ ...p, password: undefined }));
                setLoginOk(false);
              }}
              placeholder="Your password"
              className={`w-full rounded-lg border px-3 py-2 text-sm outline-none transition ${
                errors.password
                  ? "border-rose-400 ring-2 ring-rose-100"
                  : "border-gray-300 focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
              }`}
            />
            {errors.password && (
              <span className="text-xs text-rose-500 mt-0.5 block">{errors.password}</span>
            )}
          </div>

          <button
            type="submit"
            className="w-full rounded-lg bg-sky-600 py-2.5 text-sm font-semibold text-white hover:bg-sky-700 transition"
          >
            Log In
          </button>
        </form>

        {loginOk && (
          <p className="text-green-600 text-sm text-center mt-4">
            Validation passed.
          </p>
        )}
      </div>
    </div>
  );
}
