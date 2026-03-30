import React, { useState } from 'react';

const MarkdownEditor: React.FC = () => {
  const [text, setText] = useState('# Hello World\n\nThis is a **markdown** editor.\n\n- Item one\n- Item two\n\n> A blockquote\n\n`inline code`');

  const renderMarkdown = (md: string): string => {
    let html = md
      .replace(/^### (.+)$/gm, '<h3 style="font-size:1.1em;font-weight:bold;margin:12px 0 4px">$1</h3>')
      .replace(/^## (.+)$/gm, '<h2 style="font-size:1.3em;font-weight:bold;margin:14px 0 6px">$1</h2>')
      .replace(/^# (.+)$/gm, '<h1 style="font-size:1.6em;font-weight:bold;margin:16px 0 8px">$1</h1>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`(.+?)`/g, '<code style="background:#f0f0f0;padding:2px 4px;border-radius:3px;font-size:0.9em">$1</code>')
      .replace(/^> (.+)$/gm, '<blockquote style="border-left:3px solid #ccc;padding-left:12px;color:#666;margin:8px 0">$1</blockquote>')
      .replace(/^- (.+)$/gm, '<li style="margin-left:20px">$1</li>')
      .replace(/\n/g, '<br/>');
    return html;
  };

  return (
    <div style={{ display: 'flex', height: '100vh', fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRight: '1px solid #ddd' }}>
        <div style={{ padding: '8px 12px', background: '#f5f5f5', borderBottom: '1px solid #ddd', fontSize: '13px', fontWeight: 600, color: '#555' }}>
          Editor
        </div>
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          style={{ flex: 1, padding: '16px', border: 'none', outline: 'none', resize: 'none', fontFamily: 'monospace', fontSize: '14px', lineHeight: 1.6 }}
        />
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '8px 12px', background: '#f5f5f5', borderBottom: '1px solid #ddd', fontSize: '13px', fontWeight: 600, color: '#555' }}>
          Preview
        </div>
        <div
          style={{ flex: 1, padding: '16px', overflow: 'auto', lineHeight: 1.6, fontSize: '14px' }}
          dangerouslySetInnerHTML={{ __html: renderMarkdown(text) }}
        />
      </div>
    </div>
  );
};

export default MarkdownEditor;
