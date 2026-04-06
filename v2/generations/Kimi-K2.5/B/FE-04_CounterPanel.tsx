import React, { useState } from 'react';

interface CounterState {
  value: number;
  min: number;
}

interface CounterOperations {
  increment: () => void;
  decrement: () => void;
  reset: () => void;
}

export default function CounterPanel() {
  const [state, setState] = useState<CounterState>({ value: 0, min: 0 });

  const operations: CounterOperations = {
    increment: () => setState(s => ({ ...s, value: s.value + 1 })),
    decrement: () => setState(s => ({ ...s, value: Math.max(s.min, s.value - 1) })),
    reset: () => setState(s => ({ ...s, value: 0 }))
  };

  return (
    <>
      <style>{`
        .container {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
          padding: 20px;
        }
        .panel {
          background: rgba(255,255,255,0.95);
          border-radius: 20px;
          padding: 50px;
          box-shadow: 0 25px 80px rgba(0,0,0,0.25);
          text-align: center;
          backdrop-filter: blur(10px);
        }
        .title {
          font-size: 28px;
          font-weight: 800;
          color: #1f2937;
          margin-bottom: 20px;
          letter-spacing: -0.5px;
        }
        .value-box {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 16px;
          padding: 30px 60px;
          margin: 30px 0;
        }
        .value {
          font-size: 80px;
          font-weight: 900;
          color: white;
          font-family: 'SF Mono', monospace;
          text-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }
        .controls {
          display: flex;
          gap: 16px;
          justify-content: center;
        }
        .op-btn {
          padding: 16px 28px;
          border: none;
          border-radius: 12px;
          font-size: 18px;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .op-btn:hover:not(:disabled) {
          transform: scale(1.05) translateY(-3px);
          box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .op-btn:active:not(:disabled) {
          transform: scale(0.98);
        }
        .op-btn:disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }
        .btn-dec { background: #fee2e2; color: #dc2626; }
        .btn-res { background: #e5e7eb; color: #4b5563; }
        .btn-inc { background: #d1fae5; color: #059669; }
        @media (max-width: 480px) {
          .panel { padding: 30px; }
          .value { font-size: 60px; }
          .controls { flex-direction: column; }
        }
      `}</style>
      <div className="container">
        <div className="panel">
          <h2 className="title">Counter Panel</h2>
          <div className="value-box">
            <div className="value">{state.value}</div>
          </div>
          <div className="controls">
            <button 
              onClick={operations.decrement} 
              disabled={state.value === state.min}
              className="op-btn btn-dec"
            >
              − Minus
            </button>
            <button onClick={operations.reset} className="op-btn btn-res">
              ↺ Reset
            </button>
            <button onClick={operations.increment} className="op-btn btn-inc">
              + Plus
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
