import React, { useState, useCallback } from "react";

export default function CounterPanel() {
  const [count, setCount] = useState(0);

  const inc = useCallback(() => setCount((n) => n + 1), []);
  const dec = useCallback(() => setCount((n) => (n > 0 ? n - 1 : 0)), []);
  const rst = useCallback(() => setCount(0), []);

  return (
    <>
      <style>{`
        .ctr-wrap {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
          background: #fafaf9;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }
        .ctr-panel {
          width: 100%;
          max-width: 380px;
          background: #fff;
          border: 1px solid #e7e5e4;
          border-radius: 18px;
          padding: 32px 24px;
          text-align: center;
        }
        .ctr-label {
          display: inline-block;
          background: #ecfdf5;
          color: #059669;
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          padding: 4px 10px;
          border-radius: 100px;
          margin-bottom: 12px;
        }
        .ctr-title {
          font-size: 24px;
          font-weight: 700;
          color: #1c1917;
          margin: 0 0 6px;
        }
        .ctr-desc {
          font-size: 13px;
          color: #78716c;
          margin: 0 0 28px;
        }
        .ctr-number {
          font-size: 68px;
          font-weight: 800;
          color: #0c0a09;
          margin: 0 0 28px;
          line-height: 1;
        }
        .ctr-btns {
          display: flex;
          gap: 10px;
        }
        .ctr-btn {
          flex: 1;
          padding: 12px;
          border: none;
          border-radius: 12px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
        }
        .ctr-btn:hover { filter: brightness(0.95); }
        .ctr-btn--add { background: #10b981; color: #fff; }
        .ctr-btn--sub { background: #f5f5f4; color: #44403c; }
        .ctr-btn--zero { background: #292524; color: #fff; }
        .ctr-note {
          margin-top: 14px;
          font-size: 11px;
          color: #a8a29e;
        }
        @media (max-width: 440px) {
          .ctr-panel { padding: 24px 16px; }
          .ctr-number { font-size: 52px; }
          .ctr-btns { flex-direction: column; }
        }
      `}</style>
      <div className="ctr-wrap">
        <div className="ctr-panel">
          <span className="ctr-label">Counter</span>
          <h1 className="ctr-title">Count Tracker</h1>
          <p className="ctr-desc">Tap the buttons. Minimum is zero.</p>
          <div className="ctr-number">{count}</div>
          <div className="ctr-btns">
            <button type="button" className="ctr-btn ctr-btn--add" onClick={inc}>+1</button>
            <button type="button" className="ctr-btn ctr-btn--sub" onClick={dec}>−1</button>
            <button type="button" className="ctr-btn ctr-btn--zero" onClick={rst}>Reset</button>
          </div>
          <p className="ctr-note">Responsive layout · Floor = 0</p>
        </div>
      </div>
    </>
  );
}
