import React, { useState } from 'react';

export default function CounterPanel() {
  const [count, setCount] = useState(0);

  const handleIncrement = () => {
    setCount((prev) => prev + 1);
  };

  const handleDecrement = () => {
    setCount((prev) => (prev > 0 ? prev - 1 : 0));
  };

  const handleReset = () => {
    setCount(0);
  };

  return (
    <div style={styles.container}>
      <div style={styles.panel}>
        <h2 style={styles.title}>Counter</h2>
        
        <div style={styles.display}>
          <span style={styles.countText}>{count}</span>
        </div>
        
        <div style={styles.buttonGroup}>
          <button 
            style={{...styles.button, ...styles.decrementButton}} 
            onClick={handleDecrement}
            disabled={count === 0}
            onMouseOver={(e) => { if(count > 0) e.currentTarget.style.backgroundColor = '#cc0000' }}
            onMouseOut={(e) => { if(count > 0) e.currentTarget.style.backgroundColor = '#ff4d4d' }}
          >
            - 1
          </button>
          
          <button 
            style={{...styles.button, ...styles.resetButton}} 
            onClick={handleReset}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#7a8b9a'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#95a5a6'}
          >
            Reset
          </button>
          
          <button 
            style={{...styles.button, ...styles.incrementButton}} 
            onClick={handleIncrement}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#219a52'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#2ecc71'}
          >
            + 1
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
    backgroundColor: '#f0f4f8',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    padding: '20px',
    boxSizing: 'border-box',
  },
  panel: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
    padding: '40px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    width: '100%',
    maxWidth: '450px',
  },
  title: {
    margin: '0 0 24px 0',
    color: '#333',
    fontSize: '28px',
    fontWeight: '600',
  },
  display: {
    backgroundColor: '#eef2f5',
    borderRadius: '8px',
    width: '100%',
    padding: '30px',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: '32px',
    boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.05)',
  },
  countText: {
    fontSize: '64px',
    fontWeight: 'bold',
    color: '#2c3e50',
    lineHeight: '1',
  },
  buttonGroup: {
    display: 'flex',
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    gap: '12px',
    flexWrap: 'wrap',
  },
  button: {
    flex: '1',
    minWidth: '80px',
    padding: '14px 20px',
    fontSize: '18px',
    fontWeight: '600',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    color: 'white',
    transition: 'background-color 0.2s ease, transform 0.1s ease',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  },
  decrementButton: {
    backgroundColor: '#ff4d4d',
  },
  incrementButton: {
    backgroundColor: '#2ecc71',
  },
  resetButton: {
    backgroundColor: '#95a5a6',
  },
};
