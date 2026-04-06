import React, { useState } from 'react';

const CounterPanel: React.FC = () => {
  const [count, setCount] = useState(0);

  const increment = () => {
    setCount(count + 1);
  };

  const decrement = () => {
    setCount(Math.max(0, count - 1));
  };

  const reset = () => {
    setCount(0);
  };

  return (
    <div className="counter-container">
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
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
          padding: 48px;
          text-align: center;
          max-width: 400px;
          width: 100%;
        }

        .counter-title {
          font-size: 24px;
          font-weight: bold;
          color: #333;
          margin-bottom: 32px;
        }

        .counter-display {
          font-size: 72px;
          font-weight: bold;
          color: #667eea;
          margin: 32px 0;
        }

        .counter-buttons {
          display: flex;
          gap: 16px;
          justify-content: center;
          margin-bottom: 24px;
        }

        .counter-button {
          padding: 16px 32px;
          font-size: 18px;
          font-weight: 600;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .button-increment {
          background-color: #667eea;
          color: white;
        }

        .button-increment:hover {
          background-color: #5568d3;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .button-decrement {
          background-color: #f093fb;
          color: white;
        }

        .button-decrement:hover {
          background-color: #e07be8;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(240, 147, 251, 0.4);
        }

        .button-reset {
          background-color: #e2e8f0;
          color: #4a5568;
          width: 100%;
          margin-top: 16px;
        }

        .button-reset:hover {
          background-color: #cbd5e0;
          transform: translateY(-2px);
        }

        @media (max-width: 480px) {
          .counter-card {
            padding: 32px 24px;
          }

          .counter-display {
            font-size: 56px;
          }

          .counter-button {
            padding: 12px 24px;
            font-size: 16px;
          }

          .counter-buttons {
            flex-direction: column;
          }
        }
      `}</style>

      <div className="counter-card">
        <h2 className="counter-title">Counter</h2>
        <div className="counter-display">{count}</div>
        <div className="counter-buttons">
          <button className="counter-button button-decrement" onClick={decrement}>
            -1
          </button>
          <button className="counter-button button-increment" onClick={increment}>
            +1
          </button>
        </div>
        <button className="counter-button button-reset" onClick={reset}>
          Reset
        </button>
      </div>
    </div>
  );
};

export default CounterPanel;
