import React, { useState } from 'react';

const Counter: React.FC = () => {
  const [n, setN] = useState(0);

  const css: Record<string, React.CSSProperties> = {
    box: { padding: '2rem', textAlign: 'center', border: '1px solid #eee', borderRadius: '8px', margin: '2rem auto', maxWidth: '200px' },
    num: { fontSize: '3rem', fontWeight: 'bold', margin: '1rem 0' },
    btn: { margin: '0.2rem', padding: '0.5rem 1rem', cursor: 'pointer' }
  };

  return (
    <div style={css.box}>
      <div style={css.num}>{n}</div>
      <button style={css.btn} onClick={() => n > 0 && setN(n - 1)}>-</button>
      <button style={css.btn} onClick={() => setN(n + 1)}>+</button>
      <button style={{ ...css.btn, display: 'block', width: '100%', marginTop: '1rem' }} onClick={() => setN(0)}>Reset</button>
    </div>
  );
};

export default Counter;
