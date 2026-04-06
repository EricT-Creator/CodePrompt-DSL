import React, { useState } from "react";

export default function CounterPanel() {
  const [count, setCount] = useState(0);

  return (
    <>
      <style>{`
        body {
          margin: 0;
          font-family: Inter, Arial, sans-serif;
          background: #f5f5f4;
        }
        .wrap {
          min-height: 100vh;
          display: flex;
          justify-content: center;
          align-items: center;
          padding: 24px;
        }
        .panel {
          width: min(100%, 540px);
          background: #ffffff;
          border-radius: 28px;
          padding: 28px;
          border: 1px solid #e7e5e4;
          box-shadow: 0 16px 36px rgba(28, 25, 23, 0.08);
        }
        .tag {
          display: inline-block;
          padding: 7px 12px;
          border-radius: 999px;
          background: #fef3c7;
          color: #92400e;
          font-size: 12px;
          font-weight: 700;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }
        .title {
          margin: 14px 0 8px;
          font-size: clamp(28px, 5vw, 40px);
          color: #1c1917;
        }
        .subtitle {
          margin: 0 0 22px;
          color: #57534e;
          line-height: 1.6;
        }
        .value {
          margin: 0 0 22px;
          text-align: center;
          font-size: clamp(58px, 10vw, 82px);
          font-weight: 800;
          color: #1c1917;
        }
        .buttons {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
        }
        button {
          border: none;
          border-radius: 18px;
          padding: 14px 16px;
          font-size: 15px;
          font-weight: 700;
          cursor: pointer;
        }
        .inc { background: #f59e0b; color: white; }
        .dec { background: #e7e5e4; color: #292524; }
        .rst { background: #292524; color: white; }
        .foot {
          margin-top: 18px;
          text-align: center;
          color: #78716c;
          font-size: 14px;
        }
        @media (max-width: 560px) {
          .buttons { grid-template-columns: 1fr; }
          .panel { padding: 24px; }
        }
      `}</style>
      <div className="wrap">
        <section className="panel">
          <div className="tag">Counter</div>
          <h1 className="title">Counter Panel</h1>
          <p className="subtitle">Use the increase, decrease, and reset buttons. The value is never allowed to become negative.</p>
          <p className="value">{count}</p>
          <div className="buttons">
            <button className="inc" type="button" onClick={() => setCount((value) => value + 1)}>
              Increase
            </button>
            <button className="dec" type="button" onClick={() => setCount((value) => Math.max(0, value - 1))}>
              Decrease
            </button>
            <button className="rst" type="button" onClick={() => setCount(0)}>
              Reset
            </button>
          </div>
          <div className="foot">Responsive layout with a zero floor.</div>
        </section>
      </div>
    </>
  );
}
