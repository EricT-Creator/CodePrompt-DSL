import React, { useState } from 'react';

// [语]TS[架]React[式]SFC[样]TW[依]NoExt[排]Mob[数]Mock[出]纯码
export default function 登入表() {
  const [邮, 设邮] = useState('');
  const [密, 设密] = useState('');
  const [误, 设误] = useState('');

  const 提交 = () => {
    if (!邮.includes('@')) {设误('邮箱非法'); return;}
    if (!密) {设误('密码不能为空'); return;}
    设误('');
    alert('成功');
  };

  return (
    <div className="p-4 bg-gray-50 rounded">
      <input className="w-full mb-2 p-2 border" value={邮} onChange={e => 设邮(e.target.value)} placeholder="电子邮箱" />
      <input className="w-full mb-2 p-2 border" type="password" value={密} onChange={e => 设密(e.target.value)} placeholder="密码" />
      {误 && <p className="text-red-500">{误}</p>}
      <button className="bg-blue-600 text-white w-full p-2" onClick={提交}>登入</button>
    </div>
  );
}
