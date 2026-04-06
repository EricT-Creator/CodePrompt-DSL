import React, { useState } from "react";

export default function CounterPanel() {
  const [count, setCount] = useState(0);

  return (
    <>
      <style>{`
        * { box-sizing: border-box; }
        body { margin: 0; font-family: Inter, Arial, sans-serif; background: #f4f7fb; }
        .counter-page {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 24px;
        }
        .counter-card {
          width: min(100%, 520px);
          background: #ffffff;
          border-radius: 24px;
          padding: 32px;
          box-shadow: 0 20px 40px rgba(15, 23, 42, 0.08);
        }
        .eyebrow {
          margin: 0;
          color: #2563eb;
          font-size: 12px;
          font-weight: 700;
          letter-spacing: 0.18em;
          text-transform: uppercase;
        }
        .title {
          margin: 12px 0 8px;
          font-size: clamp(30px, 5vw, 40px);
          color: #0f172a;
        }
        .description {
          margin: 0 0 24px;
          color: #64748b;
          line-height: 1.6;
        }
        .count {
          margin: 0 0 24px;
          font-size: clamp(56px, 12vw, 80px);
          font-weight: 800;
          text-align: center;
          color: #111827;
        }
        .actions {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
        }
        button {
          border: none;
          border-radius: 16px;
          padding: 14px 16px;
          font-size: 16px;
          font-weight: 700;
          cursor: pointer;
          transition: transform 0.18s ease, opacity 0.18s ease;
        }
        button:hover {
          transform: translateY(-1px);
        }
        .primary { background: #2563eb; color: #ffffff; }
        .secondary { background: #e2e8f0; color: #0f172a; }
        .danger { background: #111827; color: #ffffff; }
        .hint {
          margin-top: 18px;
          text-align: center;
          color: #475569;
          font-size: 14px;
        }
        @media (max-width: 560px) {
          .counter-card { padding: 24px; }
          .actions { grid-template-columns: 1fr; }
        }
      `}</style>
      <div className="counter-page">
        <section className="counter-card">
          <p className="eyebrow">Counter panel</p>
          <h1 className="title">Keep count without going below zero</h1>
          <p className="description">Use the buttons to increment, decrement, or reset the value. The decrement button respects the minimum bound.</p>
          <p className="count">{count}</p>
          <div className="actions">
            <button className="primary" type="button" onClick={() => setCount((value) => value + 1)}>
              +1
            </button>
            <button className="secondary" type="button" onClick={() => setCount((value) => Math.max(0, value - 1))}>
              -1
            </button>
            <button className="danger" type="button" onClick={() => setCount(0)}>
              Reset
            </button>
          </div>
          <div className="hint">Minimum value: 0</div>
        </section>
      </div>
    </>
  );
}
