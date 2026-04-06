import React, { useState } from "react";

export default function CounterPanel() {
  const [count, setCount] = useState(0);

  const increment = () => setCount((c) => c + 1);
  const decrement = () => setCount((c) => Math.max(0, c - 1));
  const reset = () => setCount(0);

  return (
    <>
      <style>{`
        .counter-root {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #f7f7f8;
          padding: 16px;
          font-family: system-ui, -apple-system, sans-serif;
          box-sizing: border-box;
        }
        .counter-card {
          width: 100%;
          max-width: 400px;
          background: #fff;
          border-radius: 16px;
          box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
          padding: 32px;
          text-align: center;
        }
        .counter-title {
          margin: 0 0 8px;
          font-size: 20px;
          font-weight: 700;
          color: #1a1a2e;
        }
        .counter-subtitle {
          margin: 0 0 24px;
          font-size: 14px;
          color: #888;
        }
        .counter-display {
          font-size: 72px;
          font-weight: 800;
          color: #1a1a2e;
          margin: 0 0 32px;
          line-height: 1;
        }
        .counter-buttons {
          display: flex;
          gap: 12px;
        }
        .counter-btn {
          flex: 1;
          padding: 12px 0;
          border: none;
          border-radius: 10px;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          transition: opacity 0.15s;
        }
        .counter-btn:hover {
          opacity: 0.85;
        }
        .counter-btn--inc {
          background: #2563eb;
          color: #fff;
        }
        .counter-btn--dec {
          background: #e5e7eb;
          color: #374151;
        }
        .counter-btn--reset {
          background: #111827;
          color: #fff;
        }
        .counter-hint {
          margin-top: 16px;
          font-size: 12px;
          color: #aaa;
        }
        @media (max-width: 480px) {
          .counter-card { padding: 24px 16px; }
          .counter-display { font-size: 56px; }
          .counter-buttons { flex-direction: column; }
        }
      `}</style>
      <div className="counter-root">
        <div className="counter-card">
          <h1 className="counter-title">Counter</h1>
          <p className="counter-subtitle">Cannot go below zero</p>
          <div className="counter-display">{count}</div>
          <div className="counter-buttons">
            <button type="button" className="counter-btn counter-btn--inc" onClick={increment}>
              + 1
            </button>
            <button type="button" className="counter-btn counter-btn--dec" onClick={decrement}>
              − 1
            </button>
            <button type="button" className="counter-btn counter-btn--reset" onClick={reset}>
              Reset
            </button>
          </div>
          <p className="counter-hint">Minimum value: 0</p>
        </div>
      </div>
    </>
  );
}
