import React, { useState } from 'react';

const CounterPanel = () => {
  const [count, setCount] = useState(0);

  const increment = () => setCount(count + 1);
  const decrement = () => setCount(Math.max(0, count - 1));
  const reset = () => setCount(0);

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div style={styles.container}>
        <h1 style={styles.title}>Counter</h1>
        <div style={styles.display}>{count}</div>
        
        <div style={styles.buttonGroup}>
          <button onClick={increment} style={styles.button}>
            +
          </button>
          <button onClick={decrement} style={styles.button}>
            -
          </button>
          <button onClick={reset} style={{ ...styles.button, backgroundColor: '#ef4444' }}>
            Reset
          </button>
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    background: 'white',
    padding: '40px',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    textAlign: 'center' as const,
    maxWidth: '300px',
    width: '100%',
  },
  title: {
    fontSize: '24px',
    fontWeight: 'bold',
    marginBottom: '20px',
    color: '#1f2937',
  },
  display: {
    fontSize: '48px',
    fontWeight: 'bold',
    marginBottom: '30px',
    color: '#3b82f6',
  },
  buttonGroup: {
    display: 'flex',
    gap: '10px',
    justifyContent: 'center',
  },
  button: {
    padding: '10px 20px',
    fontSize: '18px',
    fontWeight: 'bold',
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
};

export default CounterPanel;