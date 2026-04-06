import React, { useState } from 'react';

const CounterPanel: React.FC = () => {
  const [num, setNum] = useState(0);

  return (
    <div className="wrapper">
      <style>{`
        .wrapper {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #0f172a;
          padding: 20px;
        }

        .card {
          background: #1e293b;
          border-radius: 24px;
          padding: 48px;
          box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.1);
          text-align: center;
          max-width: 400px;
          width: 100%;
        }

        .title {
          font-size: 20px;
          font-weight: 500;
          color: #94a3b8;
          margin-bottom: 32px;
          text-transform: uppercase;
          letter-spacing: 2px;
        }

        .number {
          font-size: 96px;
          font-weight: 700;
          color: #22d3ee;
          margin: 32px 0;
          font-family: 'Courier New', monospace;
        }

        .btn-container {
          display: flex;
          gap: 12px;
          margin-bottom: 16px;
        }

        .btn {
          flex: 1;
          padding: 16px 24px;
          font-size: 18px;
          font-weight: 600;
          border: 2px solid transparent;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .btn-minus {
          background: transparent;
          border-color: #f43f5e;
          color: #f43f5e;
        }

        .btn-minus:hover {
          background: #f43f5e;
          color: white;
          box-shadow: 0 0 20px rgba(244, 63, 94, 0.4);
        }

        .btn-plus {
          background: transparent;
          border-color: #22d3ee;
          color: #22d3ee;
        }

        .btn-plus:hover {
          background: #22d3ee;
          color: #0f172a;
          box-shadow: 0 0 20px rgba(34, 211, 238, 0.4);
        }

        .btn-reset {
          width: 100%;
          padding: 12px;
          font-size: 14px;
          font-weight: 500;
          background: transparent;
          border: 1px solid #475569;
          color: #94a3b8;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s ease;
          margin-top: 16px;
        }

        .btn-reset:hover {
          background: #475569;
          color: white;
        }

        @media (max-width: 640px) {
          .card {
            padding: 32px;
          }

          .number {
            font-size: 72px;
          }

          .btn-container {
            flex-direction: column;
          }

          .btn {
            padding: 14px 20px;
          }
        }
      `}</style>

      <div className="card">
        <div className="title">Counter</div>
        <div className="number">{num}</div>
        <div className="btn-container">
          <button
            className="btn btn-minus"
            onClick={() => setNum(Math.max(0, num - 1))}
          >
            − 1
          </button>
          <button
            className="btn btn-plus"
            onClick={() => setNum(num + 1)}
          >
            + 1
          </button>
        </div>
        <button
          className="btn-reset"
          onClick={() => setNum(0)}
        >
          Reset
        </button>
      </div>
    </div>
  );
};

export default CounterPanel;
