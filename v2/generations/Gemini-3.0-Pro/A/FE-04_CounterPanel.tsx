import React, { useState } from 'react';

export default function CounterPanel() {
  const [count, setCount] = useState(0);

  const handleIncrement = () => {
    setCount((prevCount) => prevCount + 1);
  };

  const handleDecrement = () => {
    setCount((prevCount) => (prevCount > 0 ? prevCount - 1 : 0));
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
            style={{ ...styles.button, ...styles.decrementButton }} 
            onClick={handleDecrement}
            disabled={count === 0}
          >
            - 1
          </button>
          
          <button 
            style={{ ...styles.button, ...styles.resetButton }} 
            onClick={handleReset}
          >
            Reset
          </button>
          
          <button 
            style={{ ...styles.button, ...styles.incrementButton }} 
            onClick={handleIncrement}
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
    backgroundColor: '#f5f7fa',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    padding: '20px',
    boxSizing: 'border-box',
  },
  panel: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    boxShadow: '0 8px 30px rgba(0, 0, 0, 0.1)',
    padding: '30px 40px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    maxWidth: '400px',
    width: '100%',
  },
  title: {
    margin: '0 0 20px 0',
    color: '#333333',
    fontSize: '24px',
    fontWeight: '600',
  },
  display: {
    backgroundColor: '#f0f4f8',
    borderRadius: '8px',
    padding: '20px',
    width: '100%',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: '30px',
    boxSizing: 'border-box',
  },
  countText: {
    fontSize: '48px',
    fontWeight: 'bold',
    color: '#2c3e50',
    margin: '0',
    lineHeight: '1',
  },
  buttonGroup: {
    display: 'flex',
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    gap: '10px',
    flexWrap: 'wrap',
  },
  button: {
    padding: '12px 20px',
    border: 'none',
    borderRadius: '6px',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'background-color 0.2s, transform 0.1s',
    flex: '1',
    minWidth: '80px',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  },
  decrementButton: {
    backgroundColor: '#e74c3c',
    color: 'white',
  },
  incrementButton: {
    backgroundColor: '#2ecc71',
    color: 'white',
  },
  resetButton: {
    backgroundColor: '#95a5a6',
    color: 'white',
  },
};
