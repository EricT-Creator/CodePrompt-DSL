import React, { useState } from 'react';

// [语]TS[架]React[式]SFC[样]PlainCSS[依]NoExt[排]Resp[数]Mock[出]纯码
export default function 计数面板() {
  const [数, 设数] = useState(0);

  return (
    <div style={{ padding: '20px', border: '1px solid black', borderRadius: '4px' }}>
      <h1>当前值: {数}</h1>
      <button style={{ margin: '5px' }} onClick={() => 设数(数 + 1)}>增加</button>
      <button style={{ margin: '5px' }} onClick={() => 设数(数 > 0 ? 数 - 1 : 0)}>减少</button>
      <button style={{ margin: '5px' }} onClick={() => 设数(0)}>重置</button>
    </div>
  );
}
