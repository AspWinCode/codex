import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function Markdown({ content }: { content: string }) {
  return (
    <div className="prose prose-sm max-w-none prose-headings:text-dark-800 prose-code:bg-surface-100 prose-code:px-1 prose-code:rounded prose-pre:bg-dark-900 prose-pre:text-surface-100">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
