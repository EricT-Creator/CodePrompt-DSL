import React, { useState } from "react";

export default function CounterPanel() {
  const [count, setCount] = useState(0);

  return (
    <>
      <style>{`
        .count-root {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
          padding: 1rem;
          font-family: system-ui, -apple-system, sans-serif;
        }
        .count-card {
          background: rgba(255, 255, 255, 0.9);
          backdrop-filter: blur(8px);
          border-radius: 20px;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
          padding: 2.5rem;
          text-align: center;
          min-width: 300px;
        }
        .count-title {
          font-size: 1.1rem;
          font-weight: 600;
          color: #92400e;
          margin: 0 0 0.5rem;
        }
        .count-subtitle {
          font-size: 0.75rem;
          color: #b45309;
          margin: 0 0 1.5rem;
          opacity: 0.7;
        }
        .count-display {
          font-size: 4.5rem;
          font-weight: 900;
          color: #78350f;
          line-height: 1;
          margin: 0.5rem 0 1.5rem;
          font-variant-numeric: tabular-nums;
        }
        .count-actions {
          display: flex;
          gap: 0.75rem;
          justify-content: center;
        }
        .count-btn {
          padding: 0.6rem 1.5rem;
          border: none;
          border-radius: 10px;
          font-size: 0.875rem;
          font-weight: 700;
          cursor: pointer;
          transition: transform 0.1s, box-shadow 0.15s;
        }
        .count-btn:active { transform: scale(0.95); }
        .btn-add { background: #d97706; color: #fff; }
        .btn-add:hover { box-shadow: 0 4px 12px rgba(217, 119, 6, 0.3); }
        .btn-sub { background: #fef3c7; color: #92400e; border: 1px solid #fbbf24; }
        .btn-sub:hover { background: #fde68a; }
        .btn-clr { background: #78350f; color: #fff; }
        .btn-clr:hover { background: #92400e; }
        .count-note {
          margin-top: 1rem;
          font-size: 0.7rem;
          color: #b45309;
          opacity: 0.6;
        }
        @media (max-width: 420px) {
          .count-card { padding: 1.5rem; min-width: unset; width: 100%; }
          .count-actions { flex-direction: column; }
          .count-display { font-size: 3.5rem; }
        }
      `}</style>
      <div className="count-root">
        <div className="count-card">
          <h1 className="count-title">计数器</h1>
          <p className="count-subtitle">不可低于零</p>
          <div className="count-display">{count}</div>
          <div className="count-actions">
            <button className="count-btn btn-add" onClick={() => setCount(c => c + 1)}>增一</button>
            <button className="count-btn btn-sub" onClick={() => setCount(c => Math.max(0, c - 1))}>减一</button>
            <button className="count-btn btn-clr" onClick={() => setCount(0)}>归零</button>
          </div>
          <p className="count-note">最小值为 0</p>
        </div>
      </div>
    </>
  );
}
