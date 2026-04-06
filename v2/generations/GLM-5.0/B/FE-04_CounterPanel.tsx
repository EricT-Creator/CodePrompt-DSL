import React, { useState } from 'react';

const CounterPanel: React.FC = () => {
  const [value, setValue] = useState(0);

  const operations = {
    increase: () => setValue(prev => prev + 1),
    decrease: () => setValue(prev => Math.max(0, prev - 1)),
    resetToZero: () => setValue(0),
  };

  return (
    <div className="panel-wrapper">
      <style>{`
        .panel-wrapper {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        }

        .panel-content {
          background: rgba(255, 255, 255, 0.95);
          backdrop-filter: blur(10px);
          border-radius: 20px;
          padding: 50px 60px;
          box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
          text-align: center;
          max-width: 420px;
          width: 90%;
        }

        .panel-header {
          font-size: 28px;
          font-weight: 700;
          color: #2d3748;
          margin-bottom: 40px;
          letter-spacing: -0.5px;
        }

        .counter-value-container {
          margin: 40px 0;
        }

        .counter-value {
          font-size: 80px;
          font-weight: 800;
          background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .button-group {
          display: flex;
          gap: 12px;
          margin-bottom: 20px;
        }

        .action-button {
          flex: 1;
          padding: 16px 24px;
          font-size: 20px;
          font-weight: 600;
          border: none;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .btn-subtract {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
        }

        .btn-subtract:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        }

        .btn-add {
          background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
          color: white;
        }

        .btn-add:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 20px rgba(240, 147, 251, 0.4);
        }

        .btn-reset {
          width: 100%;
          padding: 14px;
          font-size: 16px;
          font-weight: 600;
          background: #edf2f7;
          color: #4a5568;
          border: none;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.2s ease;
          margin-top: 12px;
        }

        .btn-reset:hover {
          background: #e2e8f0;
          transform: translateY(-1px);
        }

        @media (max-width: 600px) {
          .panel-content {
            padding: 40px 30px;
          }

          .counter-value {
            font-size: 64px;
          }

          .action-button {
            padding: 14px 20px;
            font-size: 18px;
          }
        }
      `}</style>

      <div className="panel-content">
        <h2 className="panel-header">Counter Panel</h2>
        <div className="counter-value-container">
          <div className="counter-value">{value}</div>
        </div>
        <div className="button-group">
          <button className="action-button btn-subtract" onClick={operations.decrease}>
            − Decrease
          </button>
          <button className="action-button btn-add" onClick={operations.increase}>
            + Increase
          </button>
        </div>
        <button className="btn-reset" onClick={operations.resetToZero}>
          Reset to Zero
        </button>
      </div>
    </div>
  );
};

export default CounterPanel;
