import React, { FormEvent, useState } from "react";

type FormState = {
  email: string;
  password: string;
};

type ErrorState = {
  email: string;
  password: string;
};

const initialForm: FormState = {
  email: "",
  password: "",
};

const initialErrors: ErrorState = {
  email: "",
  password: "",
};

export default function LoginForm() {
  const [form, setForm] = useState<FormState>(initialForm);
  const [errors, setErrors] = useState<ErrorState>(initialErrors);
  const [submitted, setSubmitted] = useState(false);

  const validate = (values: FormState): ErrorState => {
    const nextErrors: ErrorState = { email: "", password: "" };
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!values.email.trim()) {
      nextErrors.email = "Email is required.";
    } else if (!emailPattern.test(values.email.trim())) {
      nextErrors.email = "Please enter a valid email address.";
    }

    if (!values.password.trim()) {
      nextErrors.password = "Password cannot be empty.";
    }

    return nextErrors;
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors = validate(form);
    setErrors(nextErrors);
    setSubmitted(!nextErrors.email && !nextErrors.password);
  };

  const handleChange = (field: keyof FormState, value: string) => {
    setForm((previous) => ({ ...previous, [field]: value }));
    if (submitted) {
      setSubmitted(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto w-full max-w-sm rounded-2xl bg-white p-6 shadow-lg">
        <div className="mb-6 text-center">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-sky-600">Welcome back</p>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">Sign in</h1>
          <p className="mt-2 text-sm text-slate-500">Use your email and password to continue.</p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit} noValidate>
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-medium text-slate-700">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={form.email}
              onChange={(event) => handleChange("email", event.target.value)}
              className={`w-full rounded-xl border px-3 py-2.5 text-sm text-slate-900 outline-none transition ${
                errors.email ? "border-rose-400 ring-2 ring-rose-100" : "border-slate-300 focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
              }`}
              placeholder="you@example.com"
            />
            <p className="mt-1 min-h-5 text-xs text-rose-500">{errors.email}</p>
          </div>

          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-700">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={form.password}
              onChange={(event) => handleChange("password", event.target.value)}
              className={`w-full rounded-xl border px-3 py-2.5 text-sm text-slate-900 outline-none transition ${
                errors.password ? "border-rose-400 ring-2 ring-rose-100" : "border-slate-300 focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
              }`}
              placeholder="Enter your password"
            />
            <p className="mt-1 min-h-5 text-xs text-rose-500">{errors.password}</p>
          </div>

          <button
            type="submit"
            className="w-full rounded-xl bg-sky-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-sky-700"
          >
            Log in
          </button>
        </form>

        {submitted && (
          <div className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            Validation passed. Ready to log in.
          </div>
        )}
      </div>
    </div>
  );
}
