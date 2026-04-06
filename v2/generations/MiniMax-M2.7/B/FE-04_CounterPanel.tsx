import React, { useState } from 'react';

export default function CounterPanel() {
  const [count, setCount] = useState(0);

  const increment = () => {
    setCount(count + 1);
  };

  const decrement = () => {
    if (count > 0) {
      setCount(count - 1);
    }
  };

  const reset = () => {
    setCount(0);
  };

  return (
    <>
      <style>{`
        .counter-container {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background-color: #f5f5f5;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .counter-card {
          background: white;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
          padding: 40px;
          text-align: center;
          min-width: 320px;
        }
        .counter-title {
          font-size: 24px;
          font-weight: 600;
          color: #333;
          margin-bottom: 24px;
        }
        .counter-display {
          font-size: 72px;
          font-weight: 700;
          color: #2563eb;
          margin-bottom: 32px;
          line-height: 1;
        }
        .counter-buttons {
          display: flex;
          gap: 12px;
          justify-content: center;
        }
        .counter-btn {
          padding: 12px 24px;
          font-size: 16px;
          font-weight: 600;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          transition: background-color 0.2s;
        }
        .btn-increment {
          background-color: #10b981;
          color: white;
        }
        .btn-increment:hover {
          background-color: #059669;
        }
        .btn-decrement {
          background-color: #f59e0b;
          color: white;
        }
        .btn-decrement:hover {
          background-color: #d97706;
        }
        .btn-reset {
          background-color: #6b7280;
          color: white;
        }
        .btn-reset:hover {
          background-color: #4b5563;
        }
      `}</style>
      <div className="counter-container">
        <div className="counter-card">
          <div className="counter-title">Counter</div>
          <div class="counter-display">{count}</div>
          <div className="counter-buttons">
            <button className="counter-btn btn-increment" onClick={increment}>
              +1
            </button>
            <button className="counter-btn btn-decrement" onClick={decrement}>
              -1
            </button>
            <button className="counter-btn btn-reset" onClick={reset}>
              Reset
            </button>
          </div>
        </div>
      </div>
    </>
  );
}