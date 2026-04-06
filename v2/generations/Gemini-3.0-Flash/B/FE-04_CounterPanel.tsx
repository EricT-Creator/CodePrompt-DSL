import React, { useState } from 'react';

const Counter: React.FC = () => {
  const [val, setVal] = useState(0);

  const containerStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    fontFamily: 'Arial, sans-serif'
  };

  const displayStyle: React.CSSProperties = {
    fontSize: '64px',
    margin: '20px'
  };

  const btnStyle: React.CSSProperties = {
    padding: '10px 20px',
    margin: '5px',
    fontSize: '18px',
    cursor: 'pointer'
  };

  return (
    <div style={containerStyle}>
      <div style={displayStyle}>{val}</div>
      <div>
        <button style={btnStyle} onClick={() => setVal(Math.max(0, val - 1))}>Decrease</button>
        <button style={btnStyle} onClick={() => setVal(val + 1)}>Increase</button>
        <button style={btnStyle} onClick={() => setVal(0)}>Reset</button>
      </div>
    </div>
  );
};

export default Counter;
