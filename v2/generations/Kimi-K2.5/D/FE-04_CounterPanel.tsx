import React, { useState } from 'react';

export default function 计数器() {
  const [当前数, 设当前数] = useState(0);

  const 增 = () => 设当前数(数 => 数 + 1);
  const 减 = () => 设当前数(数 => Math.max(0, 数 - 1));
  const 归零 = () => 设当前数(0);

  return (
    <>
      <style>{`
        .器壳 {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #fafaf9;
          padding: 20px;
        }
        .器板 {
          background: white;
          border-radius: 16px;
          padding: 40px;
          box-shadow: 0 10px 40px rgba(0,0,0,0.1);
          text-align: center;
          border: 2px solid #e7e5e4;
        }
        .器题 {
          font-size: 24px;
          font-weight: bold;
          color: #44403c;
          margin-bottom: 20px;
        }
        .示数 {
          font-size: 80px;
          font-weight: bold;
          color: #b45309;
          margin: 30px 0;
          font-family: monospace;
        }
        .键行 {
          display: flex;
          gap: 12px;
          justify-content: center;
        }
        .键 {
          padding: 12px 24px;
          border: 2px solid #d6d3d1;
          border-radius: 8px;
          font-size: 18px;
          font-weight: 600;
          cursor: pointer;
          background: white;
          color: #57534e;
          transition: all 0.2s;
        }
        .键:hover:not(:disabled) {
          background: #f5f5f4;
          border-color: #a8a29e;
          transform: translateY(-2px);
        }
        .键:disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }
        .减键 { color: #dc2626; border-color: #fecaca; }
        .减键:hover:not(:disabled) { background: #fee2e2; border-color: #ef4444; }
        .归键 { color: #57534e; }
        .增键 { color: #16a34a; border-color: #bbf7d0; }
        .增键:hover { background: #dcfce7; border-color: #22c55e; }
      `}</style>
      <div className="器壳">
        <div className="器板">
          <h2 className="器题">计数器</h2>
          <div className="示数">{当前数}</div>
          <div className="键行">
            <button onClick={减} disabled={当前数 === 0} className="键 减键">
              减
            </button>
            <button onClick={归零} className="键 归键">
              归零
            </button>
            <button onClick={增} className="键 增键">
              增
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
