import React, { useState } from 'react';

const MarkdownEditor: React.FC = () => {
  const [md, setMd] = useState('# Hello\n\nThis is **markdown** text.');

  const basicMdToHtml = (text: string) => {
    let html = text
      .replace(/^### (.*?)$/gim, '<h3>$1</h3>')
      .replace(/^## (.*?)$/gim, '<h2>$1</h2>')
      .replace(/^# (.*?)$/gim, '<h1>$1</h1>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/__(.*?)__/gim, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/gim, '<em>$1</em>')
      .replace(/_(.*?)_/gim, '<em>$1</em>')
      .replace(/\n\n/gim, '</p><p>')
      .replace(/\n/gim, '<br>');
    return '<p>' + html + '</p>';
  };

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <h1 className="text-3xl font-bold mb-4">Markdown编辑器</h1>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">输入</label>
          <textarea
            value={md}
            onChange={e => setMd(e.target.value)}
            className="w-full h-96 p-4 border rounded font-mono text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">预览</label>
          <div
            className="w-full h-96 p-4 border rounded bg-white overflow-auto"
            dangerouslySetInnerHTML={{ __html: basicMdToHtml(md) }}
          />
        </div>
      </div>
    </div>
  );
};

export default MarkdownEditor;