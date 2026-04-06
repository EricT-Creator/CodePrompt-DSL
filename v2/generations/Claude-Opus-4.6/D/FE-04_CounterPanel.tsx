import React, { useState } from "react";

export default function CounterPanel() {
  const [n, setN] = useState(0);

  return (
    <>
      <style>{`
        .dcp-page {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #f5f5f0;
          padding: 16px;
          font-family: system-ui, sans-serif;
        }
        .dcp-card {
          width: 100%;
          max-width: 400px;
          background: #fff;
          border-radius: 16px;
          box-shadow: 0 6px 20px rgba(0,0,0,0.07);
          padding: 28px;
          text-align: center;
        }
        .dcp-card h1 {
          font-size: 20px;
          font-weight: 700;
          color: #1a1a1a;
          margin: 0 0 6px;
        }
        .dcp-card .sub {
          font-size: 13px;
          color: #999;
          margin: 0 0 24px;
        }
        .dcp-num {
          font-size: 64px;
          font-weight: 800;
          color: #111;
          margin: 0 0 24px;
          line-height: 1;
        }
        .dcp-row {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
        }
        .dcp-row button {
          padding: 12px;
          border: none;
          border-radius: 10px;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
        }
        .dcp-row button:hover { opacity: 0.9; }
        .dcp-inc { background: #d97706; color: #fff; }
        .dcp-dec { background: #e5e5e5; color: #333; }
        .dcp-rst { background: #1a1a1a; color: #fff; }
        .dcp-info {
          margin-top: 14px;
          font-size: 12px;
          color: #bbb;
        }
        @media (max-width: 440px) {
          .dcp-card { padding: 20px 14px; }
          .dcp-num { font-size: 48px; }
          .dcp-row { grid-template-columns: 1fr; }
        }
      `}</style>
      <div className="dcp-page">
        <section className="dcp-card">
          <h1>计数器</h1>
          <p className="sub">数不可负</p>
          <div className="dcp-num">{n}</div>
          <div className="dcp-row">
            <button type="button" className="dcp-inc" onClick={() => setN((v) => v + 1)}>
              增
            </button>
            <button type="button" className="dcp-dec" onClick={() => setN((v) => Math.max(0, v - 1))}>
              减
            </button>
            <button type="button" className="dcp-rst" onClick={() => setN(0)}>
              归零
            </button>
          </div>
          <p className="dcp-info">下限为零</p>
        </section>
      </div>
    </>
  );
}
