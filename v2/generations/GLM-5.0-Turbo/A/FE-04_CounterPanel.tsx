import React, { useState } from "react";

export default function CounterPanel() {
  const [count, setCount] = useState(0);

  return (
    <>
      <style>{`
        .cp-root {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #f0f4f8;
          padding: 1rem;
          font-family: system-ui, sans-serif;
        }
        .cp-card {
          background: #fff;
          border-radius: 16px;
          box-shadow: 0 2px 12px rgba(0,0,0,0.08);
          padding: 2rem;
          text-align: center;
          min-width: 280px;
        }
        .cp-title {
          margin: 0 0 0.5rem;
          font-size: 1.25rem;
          color: #1e293b;
        }
        .cp-value {
          font-size: 3.5rem;
          font-weight: 700;
          color: #0f172a;
          margin: 1rem 0;
          line-height: 1;
        }
        .cp-buttons {
          display: flex;
          gap: 0.75rem;
          justify-content: center;
          margin-top: 1rem;
        }
        .cp-btn {
          padding: 0.5rem 1.25rem;
          border: none;
          border-radius: 8px;
          font-size: 0.875rem;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.15s;
        }
        .cp-btn:active { transform: scale(0.96); }
        .cp-btn-inc { background: #2563eb; color: #fff; }
        .cp-btn-inc:hover { background: #1d4ed8; }
        .cp-btn-dec { background: #e2e8f0; color: #334155; }
        .cp-btn-dec:hover { background: #cbd5e1; }
        .cp-btn-reset { background: #0f172a; color: #fff; }
        .cp-btn-reset:hover { background: #1e293b; }
        .cp-hint {
          margin-top: 0.75rem;
          font-size: 0.75rem;
          color: #94a3b8;
        }
        @media (max-width: 400px) {
          .cp-card { padding: 1.25rem; min-width: unset; width: 100%; }
          .cp-buttons { flex-direction: column; }
        }
      `}</style>
      <div className="cp-root">
        <div className="cp-card">
          <h1 className="cp-title">Counter</h1>
          <div className="cp-value">{count}</div>
          <div className="cp-buttons">
            <button className="cp-btn cp-btn-inc" onClick={() => setCount(c => c + 1)}>+1</button>
            <button className="cp-btn cp-btn-dec" onClick={() => setCount(c => Math.max(0, c - 1))}>-1</button>
            <button className="cp-btn cp-btn-reset" onClick={() => setCount(0)}>Reset</button>
          </div>
          <p className="cp-hint">Minimum value: 0</p>
        </div>
      </div>
    </>
  );
}
