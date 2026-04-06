import React, { useState } from 'react';

const CounterPanel: React.FC = () => {
  const [当前数, set当前数] = useState(0);

  const 增 = () => {
    set当前数(当前数 + 1);
  };

  const 减 = () => {
    set当前数(Math.max(0, 当前数 - 1));
  };

  const 归零 = () => {
    set当前数(0);
  };

  return (
    <div className="容器">
      <style>{`
        .容器 {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
          padding: 20px;
        }

        .卡片 {
          background: white;
          border-radius: 20px;
          padding: 48px;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
          text-align: center;
          max-width: 380px;
          width: 100%;
        }

        .标题 {
          font-size: 24px;
          font-weight: bold;
          color: #92400e;
          margin-bottom: 32px;
        }

        .数字显示 {
          font-size: 80px;
          font-weight: 800;
          color: #f59e0b;
          margin: 32px 0;
          font-family: 'Courier New', monospace;
        }

        .按钮组 {
          display: flex;
          gap: 12px;
          margin-bottom: 16px;
        }

        .操作按钮 {
          flex: 1;
          padding: 16px 24px;
          font-size: 18px;
          font-weight: 600;
          border: none;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .减按钮 {
          background-color: #fed7aa;
          color: #9a3412;
        }

        .减按钮:hover {
          background-color: #fdba74;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(253, 186, 116, 0.5);
        }

        .增按钮 {
          background-color: #fbbf24;
          color: white;
        }

        .增按钮:hover {
          background-color: #f59e0b;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(245, 158, 11, 0.5);
        }

        .归零按钮 {
          width: 100%;
          padding: 14px;
          font-size: 16px;
          font-weight: 600;
          background-color: #fef3c7;
          color: #92400e;
          border: none;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.3s ease;
          margin-top: 12px;
        }

        .归零按钮:hover {
          background-color: #fde68a;
          transform: translateY(-1px);
        }

        @media (max-width: 480px) {
          .卡片 {
            padding: 32px 24px;
          }

          .数字显示 {
            font-size: 64px;
          }

          .操作按钮 {
            padding: 14px 20px;
            font-size: 16px;
          }

          .按钮组 {
            flex-direction: column;
          }
        }
      `}</style>

      <div className="卡片">
        <h2 className="标题">计数器</h2>
        <div className="数字显示">{当前数}</div>
        <div className="按钮组">
          <button className="操作按钮 减按钮" onClick={减}>
            − 减一
          </button>
          <button className="操作按钮 增按钮" onClick={增}>
            + 增一
          </button>
        </div>
        <button className="归零按钮" onClick={归零}>
          归零
        </button>
      </div>
    </div>
  );
};

export default CounterPanel;
