import React, { useState } from 'react';

const CounterPanel = () => {
  const [value, setValue] = useState(0);

  return (
    <div style={styles.wrapper}>
      <div style={styles.panel}>
        <h2 style={styles.title}>Count</h2>
        <div style={styles.value}>{value}</div>

        <div style={styles.buttons}>
          <button style={styles.btn} onClick={() => setValue(value + 1)}>+</button>
          <button style={styles.btn} onClick={() => setValue(Math.max(0, value - 1))}>-</button>
          <button style={{ ...styles.btn, background: '#f87171' }} onClick={() => setValue(0)}>Reset</button>
        </div>
      </div>
    </div>
  );
};

const styles = {
  wrapper: {
    minHeight: '100vh',
    background: '#e5e7eb',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '16px',
  },
  panel: {
    background: '#fff',
    borderRadius: '8px',
    padding: '40px',
    boxShadow: '0 4px 6px rgba(0,0,0,0.07)',
    textAlign: 'center' as const,
    width: '100%',
    maxWidth: '280px',
  },
  title: {
    fontSize: '22px',
    fontWeight: '700',
    marginBottom: '20px',
    color: '#111827',
  },
  value: {
    fontSize: '52px',
    fontWeight: '900',
    color: '#3b82f6',
    marginBottom: '28px',
  },
  buttons: {
    display: 'flex',
    gap: '10px',
  },
  btn: {
    flex: 1,
    padding: '12px',
    background: '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '16px',
    fontWeight: '600',
  },
};

export default CounterPanel;