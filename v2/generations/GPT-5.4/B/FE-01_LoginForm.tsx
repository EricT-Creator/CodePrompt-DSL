import React, { FormEvent, useMemo, useState } from "react";

type Values = {
  email: string;
  password: string;
};

type FieldErrors = Partial<Record<keyof Values, string>>;

const emptyValues: Values = {
  email: "",
  password: "",
};

const validateEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());

export default function LoginForm() {
  const [values, setValues] = useState<Values>(emptyValues);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [message, setMessage] = useState("");

  const fieldMeta = useMemo(
    () => [
      { key: "email" as const, label: "Email", type: "email", placeholder: "name@example.com" },
      { key: "password" as const, label: "Password", type: "password", placeholder: "Enter password" },
    ],
    []
  );

  const buildErrors = (nextValues: Values): FieldErrors => {
    const nextErrors: FieldErrors = {};

    if (!nextValues.email.trim()) {
      nextErrors.email = "Email is required.";
    } else if (!validateEmail(nextValues.email)) {
      nextErrors.email = "Email format is invalid.";
    }

    if (!nextValues.password.trim()) {
      nextErrors.password = "Password is required.";
    }

    return nextErrors;
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors = buildErrors(values);
    setErrors(nextErrors);

    if (Object.keys(nextErrors).length === 0) {
      setMessage("Form validation passed.");
    } else {
      setMessage("");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-200 px-4 py-8">
      <div className="mx-auto w-full max-w-md rounded-3xl bg-white p-6 shadow-xl shadow-slate-200/60">
        <div className="mb-6">
          <span className="inline-flex rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold text-indigo-700">
            Account Access
          </span>
          <h1 className="mt-3 text-2xl font-bold text-slate-900">Login form</h1>
          <p className="mt-2 text-sm text-slate-500">Enter your credentials and resolve any validation issues.</p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit} noValidate>
          {fieldMeta.map((field) => (
            <div key={field.key}>
              <label htmlFor={field.key} className="mb-1.5 block text-sm font-medium text-slate-700">
                {field.label}
              </label>
              <input
                id={field.key}
                type={field.type}
                value={values[field.key]}
                onChange={(event) => {
                  const nextValue = event.target.value;
                  setValues((previous) => ({ ...previous, [field.key]: nextValue }));
                  setErrors((previous) => ({ ...previous, [field.key]: "" }));
                  setMessage("");
                }}
                placeholder={field.placeholder}
                className={`w-full rounded-2xl border px-4 py-3 text-sm text-slate-900 outline-none transition ${
                  errors[field.key]
                    ? "border-rose-400 bg-rose-50/70 focus:ring-2 focus:ring-rose-100"
                    : "border-slate-300 bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                }`}
              />
              <div className="mt-1 min-h-5 text-xs text-rose-500">{errors[field.key]}</div>
            </div>
          ))}

          <button
            type="submit"
            className="w-full rounded-2xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700"
          >
            Login
          </button>
        </form>

        <div className="mt-4 min-h-11 rounded-2xl border border-dashed border-slate-200 px-4 py-3 text-sm text-slate-600">
          {message || "Validation feedback will appear here after submission."}
        </div>
      </div>
    </div>
  );
}
