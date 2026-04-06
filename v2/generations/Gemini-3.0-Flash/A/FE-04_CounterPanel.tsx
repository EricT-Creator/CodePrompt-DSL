import React, { useState } from 'react';

const CounterPanel: React.FC = () => {
  const [count, setCount] = useState(0);

  const increment = () => setCount(count + 1);
  const decrement = () => setCount(Math.max(0, count - 1));
  const reset = () => setCount(0);

  const styles: { [key: string]: React.CSSProperties } = {
    container: {
      fontFamily: 'system-ui, -apple-system, sans-serif',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      backgroundColor: '#f4f4f9',
      padding: '20px',
    },
    panel: {
      backgroundColor: '#fff',
      padding: '40px',
      borderRadius: '12px',
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
      textAlign: 'center',
      width: '100%',
      maxWidth: '300px',
    },
    count: {
      fontSize: '48px',
      fontWeight: 'bold',
      color: '#333',
      marginBottom: '24px',
    },
    buttonGroup: {
      display: 'flex',
      flexDirection: 'row',
      gap: '10px',
      justifyContent: 'center',
      flexWrap: 'wrap',
    },
    button: {
      padding: '10px 20px',
      fontSize: '16px',
      cursor: 'pointer',
      border: 'none',
      borderRadius: '6px',
      transition: 'background-color 0.2s',
    },
    increment: {
      backgroundColor: '#4caf50',
      color: 'white',
    },
    decrement: {
      backgroundColor: '#f44336',
      color: 'white',
    },
    reset: {
      backgroundColor: '#2196f3',
      color: 'white',
      marginTop: '10px',
      width: '100%',
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.panel}>
        <div style={styles.count}>{count}</div>
        <div style={styles.buttonGroup}>
          <button style={{ ...styles.button, ...styles.decrement }} onClick={decrement}>-</button>
          <button style={{ ...styles.button, ...styles.increment }} onClick={increment}>+</button>
        </div>
        <button style={{ ...styles.button, ...styles.reset }} onClick={reset}>Reset</button>
      </div>
    </div>
  );
};

export default CounterPanel;
