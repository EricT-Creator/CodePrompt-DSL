import React, { useMemo, useState } from "react";

export default function CounterPanel() {
  const [count, setCount] = useState(0);

  const status = useMemo(() => {
    if (count === 0) {
      return "At minimum";
    }
    if (count < 5) {
      return "Low range";
    }
    return "High range";
  }, [count]);

  return (
    <>
      <style>{`
        :root {
          color-scheme: light;
          font-family: Inter, Arial, sans-serif;
        }
        body {
          margin: 0;
          background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
        }
        .page {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 24px;
        }
        .panel {
          width: min(100%, 560px);
          background: white;
          border: 1px solid #e5e7eb;
          border-radius: 28px;
          padding: 28px;
          box-shadow: 0 18px 48px rgba(99, 102, 241, 0.12);
        }
        .header {
          display: flex;
          flex-wrap: wrap;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 24px;
        }
        .badge {
          border-radius: 999px;
          background: #eef2ff;
          color: #4338ca;
          padding: 8px 12px;
          font-size: 13px;
          font-weight: 700;
        }
        h1 {
          margin: 0;
          font-size: clamp(28px, 5vw, 38px);
          color: #111827;
        }
        p {
          margin: 8px 0 0;
          color: #6b7280;
          line-height: 1.6;
        }
        .value {
          margin: 18px 0 22px;
          text-align: center;
          font-size: clamp(52px, 10vw, 76px);
          font-weight: 800;
          color: #111827;
        }
        .controls {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
        }
        .controls button {
          border: none;
          border-radius: 18px;
          padding: 14px;
          font-size: 16px;
          font-weight: 700;
          cursor: pointer;
        }
        .controls button:nth-child(1) { background: #4f46e5; color: white; }
        .controls button:nth-child(2) { background: #dbeafe; color: #1d4ed8; }
        .controls button:nth-child(3) { background: #111827; color: white; }
        .footer {
          margin-top: 18px;
          display: flex;
          justify-content: space-between;
          gap: 12px;
          color: #475569;
          font-size: 14px;
        }
        @media (max-width: 560px) {
          .controls { grid-template-columns: 1fr; }
          .footer { flex-direction: column; }
        }
      `}</style>
      <div className="page">
        <section className="panel">
          <div className="header">
            <div>
              <h1>Counter Panel</h1>
              <p>Increment, decrement, or reset the number. The count never drops below zero.</p>
            </div>
            <div className="badge">{status}</div>
          </div>

          <div className="value">{count}</div>

          <div className="controls">
            <button type="button" onClick={() => setCount((previous) => previous + 1)}>
              Increase
            </button>
            <button type="button" onClick={() => setCount((previous) => Math.max(0, previous - 1))}>
              Decrease
            </button>
            <button type="button" onClick={() => setCount(0)}>
              Reset
            </button>
          </div>

          <div className="footer">
            <span>Responsive single-file counter</span>
            <span>Minimum allowed value: 0</span>
          </div>
        </section>
      </div>
    </>
  );
}
