import React, { FormEvent, useState } from "react";

type Model = {
  email: string;
  password: string;
};

type IssueMap = Record<keyof Model, string>;

const blankModel: Model = { email: "", password: "" };
const blankIssues: IssueMap = { email: "", password: "" };

export default function LoginForm() {
  const [model, setModel] = useState<Model>(blankModel);
  const [issues, setIssues] = useState<IssueMap>(blankIssues);
  const [ready, setReady] = useState(false);

  const validate = (): IssueMap => {
    const next = { ...blankIssues };
    const email = model.email.trim();
    const password = model.password.trim();

    if (!email) {
      next.email = "Email is required.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      next.email = "Please use a valid email address.";
    }

    if (!password) {
      next.password = "Password is required.";
    }

    return next;
  };

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const next = validate();
    setIssues(next);
    setReady(Object.values(next).every((value) => value === ""));
  };

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100">
      <section className="mx-auto w-full max-w-sm rounded-3xl bg-slate-900/80 p-6 shadow-2xl ring-1 ring-white/10 backdrop-blur">
        <header className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan-500/20 text-lg font-bold text-cyan-300">
            IN
          </div>
          <h1 className="text-2xl font-bold">Login</h1>
          <p className="mt-2 text-sm text-slate-400">A compact email-and-password sign in form.</p>
        </header>

        <form className="space-y-4" onSubmit={onSubmit} noValidate>
          <div>
            <label htmlFor="login-email" className="mb-1 block text-sm font-medium text-slate-200">
              Email address
            </label>
            <input
              id="login-email"
              type="email"
              value={model.email}
              onChange={(event) => {
                const value = event.target.value;
                setModel((previous) => ({ ...previous, email: value }));
                setIssues((previous) => ({ ...previous, email: "" }));
                setReady(false);
              }}
              className={`w-full rounded-2xl border bg-slate-950/60 px-4 py-3 text-sm outline-none transition ${
                issues.email ? "border-rose-400" : "border-slate-700 focus:border-cyan-400"
              }`}
              placeholder="mail@example.com"
            />
            <div className="mt-1 min-h-5 text-xs text-rose-300">{issues.email}</div>
          </div>

          <div>
            <label htmlFor="login-password" className="mb-1 block text-sm font-medium text-slate-200">
              Password
            </label>
            <input
              id="login-password"
              type="password"
              value={model.password}
              onChange={(event) => {
                const value = event.target.value;
                setModel((previous) => ({ ...previous, password: value }));
                setIssues((previous) => ({ ...previous, password: "" }));
                setReady(false);
              }}
              className={`w-full rounded-2xl border bg-slate-950/60 px-4 py-3 text-sm outline-none transition ${
                issues.password ? "border-rose-400" : "border-slate-700 focus:border-cyan-400"
              }`}
              placeholder="••••••••"
            />
            <div className="mt-1 min-h-5 text-xs text-rose-300">{issues.password}</div>
          </div>

          <button
            type="submit"
            className="w-full rounded-2xl bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400"
          >
            Log in
          </button>
        </form>

        <div className="mt-4 min-h-11 rounded-2xl bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
          {ready ? "Validation complete. Credentials look ready to submit." : "Submit the form to validate the inputs."}
        </div>
      </section>
    </main>
  );
}
