import React, { useState, FormEvent } from "react";

type ValidationResult = {
  valid: boolean;
  emailError: string;
  passwordError: string;
};

export default function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [success, setSuccess] = useState(false);

  const validate = (): ValidationResult => {
    let emailErr = "";
    let passwordErr = "";

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      emailErr = "Email address is required";
    } else if (!/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(trimmedEmail)) {
      emailErr = "Invalid email format";
    }

    if (!password) {
      passwordErr = "Password cannot be empty";
    }

    return {
      valid: !emailErr && !passwordErr,
      emailError: emailErr,
      passwordError: passwordErr,
    };
  };

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const result = validate();
    setEmailError(result.emailError);
    setPasswordError(result.passwordError);
    setSuccess(result.valid);
  };

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-md w-full max-w-sm p-6">
        <div className="text-center mb-6">
          <h2 className="text-xl font-semibold text-slate-800">Login</h2>
          <p className="text-slate-500 text-xs mt-1">Enter your credentials to continue</p>
        </div>

        <form onSubmit={onSubmit} noValidate>
          <div className="mb-4">
            <label htmlFor="login-email" className="block text-sm font-medium text-slate-700 mb-1">
              Email
            </label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setEmailError("");
                setSuccess(false);
              }}
              className={`block w-full rounded-md border px-3 py-2 text-sm ${
                emailError
                  ? "border-red-300 bg-red-50 text-red-900"
                  : "border-slate-300 text-slate-900 focus:border-indigo-500 focus:ring-indigo-500"
              } outline-none`}
              placeholder="user@company.com"
            />
            {emailError && <p className="text-red-500 text-xs mt-1">{emailError}</p>}
          </div>

          <div className="mb-5">
            <label htmlFor="login-pw" className="block text-sm font-medium text-slate-700 mb-1">
              Password
            </label>
            <input
              id="login-pw"
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setPasswordError("");
                setSuccess(false);
              }}
              className={`block w-full rounded-md border px-3 py-2 text-sm ${
                passwordError
                  ? "border-red-300 bg-red-50 text-red-900"
                  : "border-slate-300 text-slate-900 focus:border-indigo-500 focus:ring-indigo-500"
              } outline-none`}
              placeholder="••••••••"
            />
            {passwordError && <p className="text-red-500 text-xs mt-1">{passwordError}</p>}
          </div>

          <button
            type="submit"
            className="w-full py-2 rounded-md bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition"
          >
            Log In
          </button>
        </form>

        {success && (
          <div className="mt-4 text-center text-green-600 text-sm">
            Validation passed — ready to log in.
          </div>
        )}
      </div>
    </div>
  );
}
