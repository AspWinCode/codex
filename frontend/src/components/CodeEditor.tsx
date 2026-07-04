import Editor from '@monaco-editor/react';

interface Props {
  value: string;
  onChange: (v: string) => void;
  language?: string;
  height?: string;
  readOnly?: boolean;
}

export default function CodeEditor({ value, onChange, language = 'python', height = '400px', readOnly = false }: Props) {
  return (
    <div className="border border-surface-300 rounded-lg overflow-hidden">
      <Editor
        height={height}
        language={language}
        value={value}
        onChange={(v) => onChange(v || '')}
        theme="vs-dark"
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          readOnly,
          padding: { top: 12 },
        }}
      />
    </div>
  );
}
