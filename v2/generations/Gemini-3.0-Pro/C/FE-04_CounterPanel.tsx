import React, { useState } from 'react';

export default function CounterPanel() {
  const [count, setCount] = useState(0);

  const increment = () => setCount((prev) => prev + 1);
  const decrement = () => setCount((prev) => (prev > 0 ? prev - 1 : 0));
  const reset = () => setCount(0);

  return (
    <div style={styles.container}>
      <div style={styles.panel}>
        <div style={styles.displayArea}>
          <span style={styles.countText}>{count}</span>
        </div>
        <div style={styles.controls}>
          <button 
            style={{ ...styles.button, ...styles.decrementBtn }} 
            onClick={decrement}
            disabled={count === 0}
            aria-label="Decrease count"
          >
            -
          </button>
          <button 
            style={{ ...styles.button, ...styles.resetBtn }} 
            onClick={reset}
            aria-label="Reset count"
          >
            Reset
          </button>
          <button 
            style={{ ...styles.button, ...styles.incrementBtn }} 
            onClick={increment}
            aria-label="Increase count"
          >
            +
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
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol"',
    padding: '20px',
    boxSizing: 'border-box',
  },
  panel: {
    backgroundColor: '#ffffff',
    borderRadius: '16px',
    boxShadow: '0 10px 30px rgba(0, 0, 0, 0.1)',
    padding: '32px',
    width: '100%',
    maxWidth: '400px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '32px',
  },
  displayArea: {
    backgroundColor: '#f8fafc',
    border: '2px solid #e2e8f0',
    borderRadius: '12px',
    width: '100%',
    padding: '24px',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    boxShadow: 'inset 0 2px 4px rgba(0, 0, 0, 0.05)',
  },
  countText: {
    fontSize: '64px',
    fontWeight: '700',
    color: '#334155',
    lineHeight: '1',
    margin: 0,
    fontVariantNumeric: 'tabular-nums',
  },
  controls: {
    display: 'flex',
    justifyContent: 'space-between',
    width: '100%',
    gap: '12px',
    flexWrap: 'wrap',
  },
  button: {
    flex: '1',
    padding: '16px 24px',
    fontSize: '18px',
    fontWeight: '600',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'transform 0.1s ease-in-out, filter 0.2s',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    color: 'white',
    minWidth: '80px',
  },
  decrementBtn: {
    backgroundColor: '#ef4444',
  },
  resetBtn: {
    backgroundColor: '#64748b',
    flex: '1.5',
  },
  incrementBtn: {
    backgroundColor: '#22c55e',
  },
};
