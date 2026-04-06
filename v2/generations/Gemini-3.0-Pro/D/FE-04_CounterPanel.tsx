import React, { useState } from 'react';

export default function CounterPanel() {
  const [count, setCount] = useState(0);

  const increment = () => {
    setCount((prev) => prev + 1);
  };

  const decrement = () => {
    setCount((prev) => (prev > 0 ? prev - 1 : 0));
  };

  const reset = () => {
    setCount(0);
  };

  return (
    <div style={styles.container}>
      <div style={styles.panel}>
        <div style={styles.displayArea}>
          <span style={styles.countText}>{count}</span>
        </div>
        <div style={styles.buttonGroup}>
          <button 
            style={{...styles.button, ...styles.decrementBtn}} 
            onClick={decrement}
            disabled={count === 0}
            onMouseOver={(e) => { if(count > 0) e.currentTarget.style.backgroundColor = '#cc0000' }}
            onMouseOut={(e) => { if(count > 0) e.currentTarget.style.backgroundColor = '#e74c3c' }}
          >
            减
          </button>
          <button 
            style={{...styles.button, ...styles.resetBtn}} 
            onClick={reset}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#7f8c8d'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#95a5a6'}
          >
            归零
          </button>
          <button 
            style={{...styles.button, ...styles.incrementBtn}} 
            onClick={increment}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#27ae60'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#2ecc71'}
          >
            增
          </button>
        </div>
      </div>
    </div>
  );
}

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#f4f6f8',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    padding: '20px',
    boxSizing: 'border-box',
  },
  panel: {
    backgroundColor: '#ffffff',
    borderRadius: '16px',
    boxShadow: '0 8px 30px rgba(0,0,0,0.1)',
    padding: '32px',
    width: '100%',
    maxWidth: '400px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '32px',
  },
  displayArea: {
    backgroundColor: '#f8f9fa',
    border: '2px solid #e9ecef',
    borderRadius: '12px',
    width: '100%',
    padding: '24px',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.05)',
  },
  countText: {
    fontSize: '72px',
    fontWeight: 'bold',
    color: '#2c3e50',
    lineHeight: '1',
    margin: 0,
    fontVariantNumeric: 'tabular-nums',
  },
  buttonGroup: {
    display: 'flex',
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    gap: '16px',
    flexWrap: 'wrap',
  },
  button: {
    flex: '1',
    minWidth: '80px',
    padding: '16px 20px',
    fontSize: '20px',
    fontWeight: '600',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'background-color 0.2s ease',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  },
  decrementBtn: {
    backgroundColor: '#e74c3c',
  },
  resetBtn: {
    backgroundColor: '#95a5a6',
    flex: '1.2',
  },
  incrementBtn: {
    backgroundColor: '#2ecc71',
  },
};
