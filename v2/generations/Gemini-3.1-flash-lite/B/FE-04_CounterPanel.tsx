import React, { useState } from 'react';

// Constraint: { "framework": "React", "language": "TypeScript", "style": "plain_css" }
export default function CounterPanel() {
  const [val, setVal] = useState(0);

  const containerStyle = { padding: '20px', border: '1px solid black' };
  const btnStyle = { margin: '5px' };

  return (
    <div style={containerStyle}>
      <h2>Current: {val}</h2>
      <button style={btnStyle} onClick={() => setVal(val + 1)}>Add</button>
      <button style={btnStyle} onClick={() => setVal(val > 0 ? val - 1 : 0)}>Sub</button>
      <button style={btnStyle} onClick={() => setVal(0)}>Reset</button>
    </div>
  );
}
