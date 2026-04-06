import React, { FormEvent, useState } from "react";

type LoginData = {
  email: string;
  password: string;
};

type LoginErrors = {
  email?: string;
  password?: string;
};

const seed: LoginData = {
  email: "",
  password: "",
};

export default function LoginForm() {
  const [data, setData] = useState<LoginData>(seed);
  const [errors, setErrors] = useState<LoginErrors>({});
  const [stateText, setStateText] = useState("Please fill in both fields.");

  const check = (draft: LoginData): LoginErrors => {
    const next: LoginErrors = {};

    if (!draft.email.trim()) {
      next.email = "Email cannot be empty.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(draft.email.trim())) {
      next.email = "Email format is invalid.";
    }

    if (!draft.password.trim()) {
      next.password = "Password cannot be empty.";
    }

    return next;
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors = check(data);
    setErrors(nextErrors);
    setStateText(
      Object.keys(nextErrors).length === 0
        ? "Validation passed. The login form is ready."
        : "Please fix the highlighted fields."
    );
  };

  return (
    <div className="min-h-screen bg-stone-100 px-4 py-12">
      <div className="mx-auto w-full max-w-sm rounded-[28px] bg-white p-6 shadow-lg shadow-stone-300/60">
        <div className="mb-6 text-center">
          <div className="mx-auto inline-flex rounded-full bg-stone-900 px-4 py-1 text-xs font-semibold uppercase tracking-[0.25em] text-white">
            Sign In
          </div>
          <h1 className="mt-4 text-2xl font-bold text-stone-900">Account Login</h1>
          <p className="mt-2 text-sm text-stone-500">Enter a valid email and a non-empty password.</p>
        </div>

        <form onSubmit={submit} className="space-y-4" noValidate>
          <div>
            <label htmlFor="field-email" className="mb-1 block text-sm font-medium text-stone-700">
              Email
            </label>
            <input
              id="field-email"
              type="email"
              value={data.email}
              onChange={(event) => {
                const value = event.target.value;
                setData((previous) => ({ ...previous, email: value }));
                setErrors((previous) => ({ ...previous, email: undefined }));
              }}
              className={`w-full rounded-2xl border px-4 py-3 text-sm outline-none transition ${
                errors.email ? "border-red-400 bg-red-50" : "border-stone-300 focus:border-stone-900"
              }`}
              placeholder="hello@example.com"
            />
            <span className="mt-1 block min-h-5 text-xs text-red-500">{errors.email}</span>
          </div>

          <div>
            <label htmlFor="field-password" className="mb-1 block text-sm font-medium text-stone-700">
              Password
            </label>
            <input
              id="field-password"
              type="password"
              value={data.password}
              onChange={(event) => {
                const value = event.target.value;
                setData((previous) => ({ ...previous, password: value }));
                setErrors((previous) => ({ ...previous, password: undefined }));
              }}
              className={`w-full rounded-2xl border px-4 py-3 text-sm outline-none transition ${
                errors.password ? "border-red-400 bg-red-50" : "border-stone-300 focus:border-stone-900"
              }`}
              placeholder="Your password"
            />
            <span className="mt-1 block min-h-5 text-xs text-red-500">{errors.password}</span>
          </div>

          <button
            type="submit"
            className="w-full rounded-2xl bg-stone-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-stone-700"
          >
            Login
          </button>
        </form>

        <div className="mt-4 rounded-2xl bg-stone-100 px-4 py-3 text-sm text-stone-600">{stateText}</div>
      </div>
    </div>
  );
}
