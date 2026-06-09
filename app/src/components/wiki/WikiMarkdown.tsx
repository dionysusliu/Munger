import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeHighlight from 'rehype-highlight';
import type { Components } from 'react-markdown';
import { remarkWikilink } from '@/lib/remark-wikilink';
import 'katex/dist/katex.min.css';
import 'highlight.js/styles/github-dark.min.css';

const markdownComponents: Components = {
  a: ({ href, children }) => {
    if (href?.startsWith('/wiki/')) {
      return (
        <Link to={href} className="text-amber-400 underline decoration-amber-400/40 hover:text-amber-300">
          {children}
        </Link>
      );
    }
    if (href === '#unresolved') {
      return <span className="text-text-muted underline decoration-dotted">{children}</span>;
    }
    return (
      <a href={href} target="_blank" rel="noreferrer" className="text-amber-400 hover:text-amber-300">
        {children}
      </a>
    );
  },
  table: ({ children }) => (
    <div className="my-6 overflow-x-auto">
      <table className="min-w-full border-collapse text-left text-body-sm">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-amber-800/20 bg-bg-hover px-3 py-2 font-medium text-text-primary">{children}</th>
  ),
  td: ({ children }) => (
    <td className="border border-amber-800/15 px-3 py-2 text-text-secondary">{children}</td>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-amber-500/40 pl-4 italic text-text-secondary">{children}</blockquote>
  ),
  pre: ({ children }) => (
    <pre className="my-4 overflow-x-auto rounded-lg border border-amber-800/20 bg-bg-void p-4 text-body-sm">
      {children}
    </pre>
  ),
  code: ({ className, children }) => {
    const isBlock = Boolean(className);
    if (isBlock) {
      return <code className={className}>{children}</code>;
    }
    return (
      <code className="rounded bg-bg-hover px-1.5 py-0.5 font-mono text-amber-300 text-body-sm">{children}</code>
    );
  },
  img: ({ src, alt }) => (
    <img src={src} alt={alt || ''} className="my-4 max-w-full rounded-lg border border-amber-800/15" loading="lazy" />
  ),
};

export default function WikiMarkdown({
  content,
  titleSlugMap,
}: {
  content: string;
  titleSlugMap: Map<string, string>;
}) {
  const remarkPlugins = useMemo(
    () => [remarkGfm, remarkMath, remarkWikilink(titleSlugMap)],
    [titleSlugMap],
  );

  return (
    <article
      className={[
        'prose prose-invert max-w-none font-wiki',
        'prose-headings:font-display prose-headings:text-text-primary',
        'prose-p:text-text-secondary prose-p:leading-relaxed',
        'prose-a:text-amber-400 prose-strong:text-text-primary',
        'prose-code:text-amber-300 prose-li:text-text-secondary',
        'prose-hr:border-amber-800/20',
      ].join(' ')}
    >
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        rehypePlugins={[rehypeKatex, rehypeHighlight]}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
    </article>
  );
}
