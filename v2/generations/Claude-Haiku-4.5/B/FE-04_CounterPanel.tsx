import React, { useState } from 'react';

const Counter = () => {
  const [num, setNum] = useState(0);

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.heading}>Counter App</h1>
        <div style={styles.number}>{num}</div>
        
        <div style={styles.controls}>
          <button style={styles.btn} onClick={() => setNum(num + 1)}>
            Increase
          </button>
          <button style={styles.btn} onClick={() => setNum(Math.max(0, num - 1))}>
            Decrease
          </button>
          <button style={{ ...styles.btn, background: '#dc2626' }} onClick={() => setNum(0)}>
            Clear
          </button>
        </div>
      </div>
    </div>
  );
};

const styles = {
  page: { minHeight: '100vh', background: '#f3f4f6', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' },
  card: { background: 'white', padding: '32px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', textAlign: 'center' as const, maxWidth: '320px' },
  heading: { fontSize: '24px', fontWeight: '600', marginBottom: '24px' },
  number: { fontSize: '56px', fontWeight: 'bold', color: '#2563eb', marginBottom: '32px' },
  controls: { display: 'flex', gap: '8px' },
  btn: { flex: 1, padding: '10px', background: '#2563eb', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: '500' },
};

export default Counter;