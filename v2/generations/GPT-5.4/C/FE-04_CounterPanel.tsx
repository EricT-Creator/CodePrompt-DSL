import React, { useState } from "react";

export default function CounterPanel() {
  const [value, setValue] = useState(0);

  return (
    <>
      <style>{`
        * { box-sizing: border-box; }
        body {
          margin: 0;
          font-family: Inter, Arial, sans-serif;
          background: #09090b;
        }
        .shell {
          min-height: 100vh;
          display: grid;
          place-items: center;
          padding: 24px;
        }
        .card {
          width: min(100%, 560px);
          border-radius: 28px;
          background: #18181b;
          color: #fafafa;
          padding: 28px;
          box-shadow: 0 25px 55px rgba(0, 0, 0, 0.35);
        }
        .meta {
          display: inline-flex;
          margin-bottom: 16px;
          border-radius: 999px;
          background: rgba(34, 197, 94, 0.15);
          color: #86efac;
          padding: 8px 12px;
          font-size: 13px;
          font-weight: 700;
        }
        h1 {
          margin: 0;
          font-size: clamp(28px, 5vw, 40px);
        }
        .copy {
          margin: 10px 0 24px;
          color: #a1a1aa;
          line-height: 1.6;
        }
        .number {
          margin: 0 0 24px;
          text-align: center;
          font-size: clamp(60px, 11vw, 84px);
          font-weight: 800;
        }
        .grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
        }
        button {
          border: none;
          border-radius: 18px;
          padding: 14px;
          font-size: 15px;
          font-weight: 700;
          cursor: pointer;
        }
        .plus { background: #22c55e; color: #052e16; }
        .minus { background: #27272a; color: #fafafa; }
        .reset { background: #fafafa; color: #18181b; }
        .note {
          margin-top: 18px;
          text-align: center;
          font-size: 14px;
          color: #86efac;
        }
        @media (max-width: 600px) {
          .grid { grid-template-columns: 1fr; }
          .card { padding: 24px; }
        }
      `}</style>
      <div className="shell">
        <section className="card">
          <span className="meta">Responsive Counter</span>
          <h1>Count safely</h1>
          <p className="copy">This counter includes increment, decrement, and reset actions. The decrement action clamps the value at zero.</p>
          <p className="number">{value}</p>
          <div className="grid">
            <button className="plus" type="button" onClick={() => setValue((current) => current + 1)}>
              Add one
            </button>
            <button className="minus" type="button" onClick={() => setValue((current) => (current > 0 ? current - 1 : 0))}>
              Subtract one
            </button>
            <button className="reset" type="button" onClick={() => setValue(0)}>
              Reset
            </button>
          </div>
          <div className="note">Lower bound enforced: 0</div>
        </section>
      </div>
    </>
  );
}
