import React, { useState } from 'react';

const 计数器: React.FC = () => {
  const [数, 设数] = useState(0);

  const 样式: Record<string, React.CSSProperties> = {
    框: { textAlign: 'center', padding: '50px', border: '2px solid #333', display: 'inline-block', position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' },
    字: { fontSize: '4em', margin: '20px 0' },
    键: { margin: '10px', padding: '10px 20px', fontSize: '1.2em' }
  };

  return (
    <div style={样式.框}>
      <div style={样式.字}>{数}</div>
      <button style={样式.键} onClick={() => 设数(数 + 1)}>增</button>
      <button style={样式.键} onClick={() => 数 > 0 && 设数(数 - 1)}>减</button>
      <button style={样式.键} onClick={() => 设数(0)}>归零</button>
    </div>
  );
};

export default 计数器;
