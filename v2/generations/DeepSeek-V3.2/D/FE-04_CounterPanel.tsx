import React, { useState } from 'react';

const CounterPanel: React.FC = () => {
  const [count, setCount] = useState<number>(0);

  const increment = () => {
    setCount(prev => prev + 1);
  };

  const decrement = () => {
    setCount(prev => (prev > 0 ? prev - 1 : 0));
  };

  const reset = () => {
    setCount(0);
  };

  return (
    <div style={{ 
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      backgroundColor: '#f0f0f0',
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: '#fff',
        borderRadius: '12px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
        padding: '40px',
        width: '320px',
        textAlign: 'center'
      }}>
        <h1 style={{
          margin: '0 0 24px 0',
          fontSize: '24px',
          color: '#333',
          fontWeight: '600'
        }}>
          计数器面板
        </h1>
        
        <div style={{
          fontSize: '48px',
          fontWeight: '700',
          color: count === 0 ? '#999' : '#2c3e50',
          marginBottom: '32px',
          minHeight: '64px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          padding: '16px'
        }}>
          {count}
        </div>
        
        <div style={{
          display: 'flex',
          gap: '16px',
          marginBottom: '24px'
        }}>
          <button 
            onClick={increment}
            style={{
              flex: 1,
              backgroundColor: '#3498db',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              padding: '14px 0',
              fontSize: '16px',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'background-color 0.2s'
            }}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#2980b9'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#3498db'}
          >
            加一
          </button>
          
          <button 
            onClick={decrement}
            disabled={count === 0}
            style={{
              flex: 1,
              backgroundColor: count === 0 ? '#bdc3c7' : '#e74c3c',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              padding: '14px 0',
              fontSize: '16px',
              fontWeight: '600',
              cursor: count === 0 ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s'
            }}
            onMouseOver={(e) => count > 0 && (e.currentTarget.style.backgroundColor = '#c0392b')}
            onMouseOut={(e) => count > 0 && (e.currentTarget.style.backgroundColor = '#e74c3c')}
          >
            减一
          </button>
        </div>
        
        <button 
          onClick={reset}
          style={{
            width: '100%',
            backgroundColor: '#95a5a6',
            color: '#fff',
            border: 'none',
            borderRadius: '8px',
            padding: '14px 0',
            fontSize: '16px',
            fontWeight: '600',
            cursor: 'pointer',
            transition: 'background-color 0.2s'
          }}
          onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#7f8c8d'}
          onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#95a5a6'}
        >
          重置
        </button>
        
        <div style={{
          marginTop: '24px',
          fontSize: '14px',
          color: '#7f8c8d'
        }}>
          {count === 0 ? '计数器已归零' : '当前计数正常'}
        </div>
      </div>
    </div>
  );
};

export default CounterPanel;