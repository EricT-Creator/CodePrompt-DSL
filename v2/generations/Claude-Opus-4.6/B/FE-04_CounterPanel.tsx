import React, { useState } from "react";

export default function CounterPanel() {
  const [value, setValue] = useState(0);

  return (
    <>
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        .cp-page {
          min-height: 100vh;
          display: grid;
          place-items: center;
          background: linear-gradient(135deg, #f0f4ff 0%, #e8edf5 100%);
          padding: 24px;
          font-family: 'Segoe UI', system-ui, sans-serif;
        }
        .cp-card {
          width: 100%;
          max-width: 420px;
          background: #ffffff;
          border-radius: 20px;
          padding: 36px 28px;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.06);
        }
        .cp-header {
          text-align: center;
          margin-bottom: 28px;
        }
        .cp-header h1 {
          font-size: 22px;
          font-weight: 700;
          color: #1e293b;
        }
        .cp-header p {
          font-size: 13px;
          color: #94a3b8;
          margin-top: 4px;
        }
        .cp-value {
          text-align: center;
          font-size: 80px;
          font-weight: 800;
          color: #0f172a;
          line-height: 1;
          margin-bottom: 32px;
        }
        .cp-actions {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
        }
        .cp-btn {
          padding: 14px 0;
          border: none;
          border-radius: 12px;
          font-size: 15px;
          font-weight: 700;
          cursor: pointer;
          transition: transform 0.1s ease;
        }
        .cp-btn:active { transform: scale(0.97); }
        .cp-btn-inc { background: #4f46e5; color: white; }
        .cp-btn-dec { background: #e2e8f0; color: #334155; }
        .cp-btn-rst { background: #0f172a; color: white; }
        .cp-floor {
          text-align: center;
          font-size: 12px;
          color: #94a3b8;
          margin-top: 20px;
        }
        @media (max-width: 480px) {
          .cp-card { padding: 24px 16px; }
          .cp-value { font-size: 60px; }
          .cp-actions { grid-template-columns: 1fr; }
        }
      `}</style>
      <div className="cp-page">
        <section className="cp-card">
          <div className="cp-header">
            <h1>Counter Panel</h1>
            <p>Increment, decrement, or reset. Floor is zero.</p>
          </div>
          <div className="cp-value">{value}</div>
          <div className="cp-actions">
            <button type="button" className="cp-btn cp-btn-inc" onClick={() => setValue((v) => v + 1)}>
              Increment
            </button>
            <button type="button" className="cp-btn cp-btn-dec" onClick={() => setValue((v) => Math.max(0, v - 1))}>
              Decrement
            </button>
            <button type="button" className="cp-btn cp-btn-rst" onClick={() => setValue(0)}>
              Reset
            </button>
          </div>
          <p className="cp-floor">Value will not drop below 0</p>
        </section>
      </div>
    </>
  );
}
