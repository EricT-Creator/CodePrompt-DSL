import React, { useState } from 'react';

export default function CounterPanel() {
  const [count, setCount] = useState(0);

  const style = {
    padding: '20px',
    border: '1px solid #ccc',
    borderRadius: '8px',
    textAlign: 'center' as const
  };

  return (
    <div style={style}>
      <h2>Counter: {count}</h2>
      <button onClick={() => setCount(count + 1)}>Increment</button>
      <button onClick={() => setCount(Math.max(0, count - 1))}>Decrement</button>
      <button onClick={() => setCount(0)}>Reset</button>
    </div>
  );
}
