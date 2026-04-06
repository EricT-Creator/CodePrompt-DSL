import React, { useState } from 'react';

const 计数器 = () => {
  const [数值, set数值] = useState(0);

  return (
    <div style={样式.容器}>
      <div style={样式.面板}>
        <h1 style={样式.标题}>计数器</h1>
        <div style={样式.显示}>{数值}</div>

        <div style={样式.按钮组}>
          <button style={样式.按钮} onClick={() => set数值(数值 + 1)}>
            增
          </button>
          <button style={样式.按钮} onClick={() => set数值(Math.max(0, 数值 - 1))}>
            减
          </button>
          <button style={{ ...样式.按钮, background: '#ef4444' }} onClick={() => set数值(0)}>
            归零
          </button>
        </div>
      </div>
    </div>
  );
};

const 样式 = {
  容器: {
    minHeight: '100vh',
    background: '#f3f4f6',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '16px',
  },
  面板: {
    background: 'white',
    borderRadius: '8px',
    padding: '40px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    textAlign: 'center' as const,
    maxWidth: '300px',
    width: '100%',
  },
  标题: {
    fontSize: '24px',
    fontWeight: 'bold',
    marginBottom: '20px',
    color: '#1f2937',
  },
  显示: {
    fontSize: '48px',
    fontWeight: 'bold',
    color: '#3b82f6',
    marginBottom: '30px',
  },
  按钮组: {
    display: 'flex',
    gap: '10px',
  },
  按钮: {
    flex: 1,
    padding: '12px',
    fontSize: '16px',
    fontWeight: 'bold',
    background: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
};

export default 计数器;