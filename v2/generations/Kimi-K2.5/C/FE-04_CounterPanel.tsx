import React, { useState } from 'react';

export default function CounterPanel() {
  const [count, setCount] = useState(0);

  return (
    <>
      <style>{`
        * { margin: 0; padding: 0; box-sizing: border-box; }
        .wrap {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #0f172a;
          padding: 16px;
        }
        .card {
          background: #1e293b;
          border-radius: 24px;
          padding: 48px;
          border: 1px solid #334155;
          box-shadow: 0 0 60px rgba(6,182,212,0.15);
          text-align: center;
        }
        .num {
          font-size: 96px;
          font-weight: 900;
          background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          font-family: ui-monospace, monospace;
          margin: 24px 0;
          text-shadow: 0 0 40px rgba(6,182,212,0.3);
        }
        .btns {
          display: flex;
          gap: 12px;
          justify-content: center;
        }
        .btn {
          padding: 14px 24px;
          border: 2px solid;
          border-radius: 12px;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          background: transparent;
          transition: all 0.2s;
        }
        .btn:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }
        .btn-neon-red {
          border-color: #ef4444;
          color: #ef4444;
        }
        .btn-neon-red:hover:not(:disabled) {
          background: #ef4444;
          color: #0f172a;
          box-shadow: 0 0 30px rgba(239,68,68,0.5);
        }
        .btn-neon-gray {
          border-color: #64748b;
          color: #94a3b8;
        }
        .btn-neon-gray:hover {
          background: #64748b;
          color: #0f172a;
        }
        .btn-neon-green {
          border-color: #10b981;
          color: #10b981;
        }
        .btn-neon-green:hover {
          background: #10b981;
          color: #0f172a;
          box-shadow: 0 0 30px rgba(16,185,129,0.5);
        }
        .btn:disabled {
          opacity: 0.3;
          cursor: not-allowed;
        }
      `}</style>
      <div className="wrap">
        <div className="card">
          <div className="num">{count}</div>
          <div className="btns">
            <button 
              onClick={() => setCount(c => Math.max(0, c - 1))}
              disabled={count === 0}
              className="btn btn-neon-red"
            >
              −
            </button>
            <button onClick={() => setCount(0)} className="btn btn-neon-gray">
              Reset
            </button>
            <button onClick={() => setCount(c => c + 1)} className="btn btn-neon-green">
              +
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
