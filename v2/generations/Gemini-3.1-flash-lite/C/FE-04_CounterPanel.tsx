import React, { useState } from 'react';

// [L]TS[S]React[F]SFC[Y]PlainCSS[D]NOX[M]RESP[DT]MOCK[O]CODE
export default function CounterPanel() {
  const [n, setN] = useState(0);

  return (
    <div style={{ border: '1px solid gray', padding: '20px' }}>
      <h1>{n}</h1>
      <button onClick={() => setN(n+1)}>+</button>
      <button onClick={() => setN(Math.max(0, n-1))}>-</button>
      <button onClick={() => setN(0)}>Reset</button>
    </div>
  );
}
