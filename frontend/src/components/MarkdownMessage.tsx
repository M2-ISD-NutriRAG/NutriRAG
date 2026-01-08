import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownMessageProps {
  content: string;
  className?: string;
  isUserMessage?: boolean;
}

export function MarkdownMessage({ content, className = '', isUserMessage = false }: MarkdownMessageProps) {
  // Base text color classes
  const textColor = isUserMessage ? 'text-primary-foreground' : 'text-card-foreground';
  const headingColor = isUserMessage ? 'text-primary-foreground' : 'text-foreground';

  return (
    <div className={`prose prose-sm max-w-none ${isUserMessage ? 'prose-invert' : 'dark:prose-invert'} ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Custom styling for markdown elements to match the design
          h1: ({ children }) => (
            <h1 className={`text-lg font-bold mb-3 ${headingColor}`}>{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className={`text-base font-semibold mb-2 ${headingColor}`}>{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className={`text-sm font-medium mb-2 ${headingColor}`}>{children}</h3>
          ),
          p: ({ children }) => (
            <p className={`mb-2 last:mb-0 ${textColor} leading-relaxed`}>{children}</p>
          ),
          ul: ({ children }) => (
            <ul className={`list-disc list-inside mb-2 space-y-1 ${textColor}`}>{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className={`list-decimal list-inside mb-2 space-y-1 ${textColor}`}>{children}</ol>
          ),
          li: ({ children }) => (
            <li className={`${textColor} leading-relaxed`}>{children}</li>
          ),
          strong: ({ children }) => (
            <strong className={`font-semibold ${isUserMessage ? 'text-primary-foreground' : 'text-foreground'}`}>{children}</strong>
          ),
          em: ({ children }) => (
            <em className={`italic ${textColor}`}>{children}</em>
          ),
          code: ({ children, className: codeClassName }) => {
            const isInline = !codeClassName?.includes('language-');
            if (isInline) {
              return (
                <code className={`${isUserMessage ? 'bg-primary-foreground/20 text-primary-foreground' : 'bg-muted text-foreground'} px-1 py-0.5 rounded text-sm font-mono`}>
                  {children}
                </code>
              );
            }
            // Block code
            return (
              <pre className={`${isUserMessage ? 'bg-primary-foreground/20 border-primary-foreground/30' : 'bg-muted border'} rounded-lg p-3 overflow-x-auto`}>
                <code className={`text-sm font-mono ${isUserMessage ? 'text-primary-foreground' : 'text-foreground'}`}>{children}</code>
              </pre>
            );
          },
          pre: ({ children }) => (
            <div className="my-2">{children}</div>
          ),
          blockquote: ({ children }) => (
            <blockquote className={`border-l-4 ${isUserMessage ? 'border-primary-foreground/30 text-primary-foreground/80' : 'border-primary/30 text-muted-foreground'} pl-4 italic my-2`}>
              {children}
            </blockquote>
          ),
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className={`${isUserMessage ? 'text-primary-foreground underline hover:text-primary-foreground/80' : 'text-primary underline hover:text-primary/80'} transition-colors`}
            >
              {children}
            </a>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto my-2">
              <table className={`min-w-full border-collapse border ${isUserMessage ? 'border-primary-foreground/30' : 'border-border'}`}>
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className={`${isUserMessage ? 'bg-primary-foreground/20' : 'bg-muted'}`}>{children}</thead>
          ),
          tbody: ({ children }) => (
            <tbody>{children}</tbody>
          ),
          tr: ({ children }) => (
            <tr className={`border-b ${isUserMessage ? 'border-primary-foreground/30' : 'border-border'}`}>{children}</tr>
          ),
          th: ({ children }) => (
            <th className={`border ${isUserMessage ? 'border-primary-foreground/30 text-primary-foreground' : 'border-border text-foreground'} px-3 py-2 text-left font-medium`}>
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className={`border ${isUserMessage ? 'border-primary-foreground/30' : 'border-border'} px-3 py-2 ${textColor}`}>
              {children}
            </td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
