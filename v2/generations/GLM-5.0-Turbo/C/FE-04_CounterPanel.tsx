import React, { useState } from "react";

export default function CounterPanel() {
  const [val, setVal] = useState(0);

  return (
    <>
      <style>{`
        .ctr { min-height:100vh; display:flex; align-items:center; justify-content:center; background:#fafafa; padding:1rem; }
        .ctr-card { background:#fff; border-radius:10px; box-shadow:0 1px 6px rgba(0,0,0,.06); padding:1.5rem; text-align:center; width:100%; max-width:320px; }
        .ctr-h { margin:0 0 .25rem; font-size:1rem; font-weight:600; color:#18181b; }
        .ctr-v { font-size:3rem; font-weight:800; color:#18181b; margin:1rem 0; line-height:1; }
        .ctr-btns { display:flex; gap:.5rem; }
        .ctr-b { flex:1; padding:.5rem; border:none; border-radius:6px; font-size:.8rem; font-weight:600; cursor:pointer; }
        .ctr-b:active { opacity:.8; }
        .b-i { background:#18181b; color:#fff; }
        .b-d { background:#e4e4e7; color:#3f3f46; }
        .b-r { background:#dc2626; color:#fff; }
        .ctr-f { font-size:.7rem; color:#a1a1aa; margin-top:.5rem; }
        @media(max-width:360px){ .ctr-card{padding:1rem;} .ctr-btns{flex-direction:column;} }
      `}</style>
      <div className="ctr">
        <div className="ctr-card">
          <h1 className="ctr-h">Count</h1>
          <div className="ctr-v">{val}</div>
          <div className="ctr-btns">
            <button className="ctr-b b-i" onClick={() => setVal(v => v + 1)}>Increment</button>
            <button className="ctr-b b-d" onClick={() => setVal(v => Math.max(0, v - 1))}>Decrement</button>
            <button className="ctr-b b-r" onClick={() => setVal(0)}>Reset</button>
          </div>
          <p className="ctr-f">Floor: 0</p>
        </div>
      </div>
    </>
  );
}
