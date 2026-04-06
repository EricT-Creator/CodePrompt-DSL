import React, { useState } from 'react';

export default function CounterPanel() {
  const [count, setCount] = useState(0);

  const increment = () => setCount(c => c + 1);
  const decrement = () => setCount(c => Math.max(0, c - 1));
  const reset = () => setCount(0);

  return (
    <>
      <style>{`
        .counter-container {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          padding: 20px;
        }
        .counter-card {
          background: white;
          border-radius: 16px;
          padding: 40px;
          box-shadow: 0 20px 60px rgba(0,0,0,0.3);
          text-align: center;
          min-width: 300px;
        }
        .counter-title {
          font-size: 24px;
          font-weight: bold;
          color: #333;
          margin-bottom: 30px;
        }
        .counter-display {
          font-size: 72px;
          font-weight: bold;
          color: #667eea;
          margin: 30px 0;
          font-family: 'Courier New', monospace;
        }
        .button-row {
          display: flex;
          gap: 12px;
          justify-content: center;
          flex-wrap: wrap;
        }
        .btn {
          padding: 12px 24px;
          border: none;
          border-radius: 8px;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }
        .btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        .btn:active {
          transform: translateY(0);
        }
        .btn-increment {
          background: #10b981;
          color: white;
        }
        .btn-decrement {
          background: #ef4444;
          color: white;
        }
        .btn-reset {
          background: #6b7280;
          color: white;
        }
        .btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
          transform: none;
        }
      `}</style>
      <div className="counter-container">
        <div className="counter-card">
          <h2 className="counter-title">Counter</h2>
          <div className="counter-display">{count}</div>
          <div className="button-row">
            <button onClick={decrement} disabled={count === 0} className="btn btn-decrement">
              − Decrement
            </button>
            <button onClick={reset} className="btn btn-reset">
              ↺ Reset
            </button>
            <button onClick={increment} className="btn btn-increment">
              + Increment
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
