import React, { useState } from "react";

export default function CounterPanel() {
  const [num, setNum] = useState(0);

  const inc = () => setNum(n => n + 1);
  const dec = () => setNum(n => Math.max(0, n - 1));
  const reset = () => setNum(0);

  return (
    <>
      <style>{`
        .panel-wrap {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #f8fafc;
          font-family: 'Segoe UI', system-ui, sans-serif;
        }
        .panel-box {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 2.5rem 3rem;
          text-align: center;
        }
        .panel-label {
          font-size: 0.875rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: #64748b;
          margin: 0;
        }
        .panel-num {
          font-size: 4rem;
          font-weight: 800;
          color: #0f172a;
          margin: 0.75rem 0 1.5rem;
        }
        .panel-row {
          display: flex;
          gap: 0.5rem;
        }
        .panel-btn {
          padding: 0.6rem 1.5rem;
          border: none;
          border-radius: 6px;
          font-size: 0.9rem;
          font-weight: 600;
          cursor: pointer;
        }
        .btn-plus { background: #7c3aed; color: #fff; }
        .btn-plus:hover { background: #6d28d9; }
        .btn-minus { background: #f1f5f9; color: #475569; }
        .btn-minus:hover { background: #e2e8f0; }
        .btn-zero { background: #1e293b; color: #fff; }
        .btn-zero:hover { background: #334155; }
        @media (max-width: 480px) {
          .panel-box { padding: 1.5rem; margin: 1rem; }
          .panel-row { flex-direction: column; }
        }
      `}</style>
      <div className="panel-wrap">
        <div className="panel-box">
          <p className="panel-label">Current Count</p>
          <div className="panel-num">{num}</div>
          <div className="panel-row">
            <button className="panel-btn btn-plus" onClick={inc}>+ 1</button>
            <button className="panel-btn btn-minus" onClick={dec}>- 1</button>
            <button className="panel-btn btn-zero" onClick={reset}>Reset</button>
          </div>
        </div>
      </div>
    </>
  );
}
