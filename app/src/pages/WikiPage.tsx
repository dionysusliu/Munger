import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, ArrowUpRight, FileText, Link2, Loader2 } from 'lucide-react';
import WikiMarkdown from '@/components/wiki/WikiMarkdown';
import {
  getRelatedWikiPages,
  getWikiLinks,
  getWikiPageBySlug,
  type RelatedWikiPage,
  type WikiLinkEntry,
  type WikiPageResponse,
} from '@/lib/api';
import { splitFrontmatter } from '@/lib/frontmatter';
import { fetchAllTitleSlugMap, formatPageType, getWikiAttributeRows } from '@/lib/wiki';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function RelatedPageLink({ page }: { page: RelatedWikiPage }) {
  return (
    <Link
      to={`/wiki/${page.slug}`}
      className="flex items-start gap-2 rounded-md px-2 py-2 transition-colors hover:bg-bg-hover"
    >
      <FileText className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
      <div className="min-w-0">
        <p className="truncate text-body-sm text-text-primary">{page.title}</p>
        <p className="text-mono-sm text-text-muted">
          {formatPageType(page.page_type)} · {page.word_count} words
        </p>
      </div>
    </Link>
  );
}

function WikiLinkRow({ link, currentPageId }: { link: WikiLinkEntry; currentPageId: number }) {
  const isOutgoing = link.from_page_id === currentPageId;
  const slug = isOutgoing ? link.to_page_slug : link.from_page_slug;
  const title = isOutgoing ? link.to_page_title : link.from_page_title;

  return (
    <Link
      to={`/wiki/${slug}`}
      className="block rounded-md px-2 py-2 transition-colors hover:bg-bg-hover"
    >
      <div className="flex items-center gap-2">
        <Link2 className="h-3.5 w-3.5 shrink-0 text-amber-400" />
        <span className="truncate text-body-sm text-text-primary">{title}</span>
        <ArrowUpRight className="ml-auto h-3.5 w-3.5 shrink-0 text-text-muted" />
      </div>
      <p className="mt-1 pl-5 text-mono-sm text-text-muted">
        {isOutgoing ? 'Outgoing' : 'Incoming'} · {link.link_type}
      </p>
      {link.context && <p className="mt-1 pl-5 text-body-sm text-text-secondary">{link.context}</p>}
    </Link>
  );
}

export default function WikiPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [page, setPage] = useState<WikiPageResponse | null>(null);
  const [relatedPages, setRelatedPages] = useState<RelatedWikiPage[]>([]);
  const [links, setLinks] = useState<WikiLinkEntry[]>([]);
  const [titleSlugMap, setTitleSlugMap] = useState<Map<string, string>>(new Map());
  const [frontmatter, setFrontmatter] = useState<Record<string, string>>({});
  const [markdownBody, setMarkdownBody] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) {
      setLoading(false);
      setError('Page not found');
      return;
    }

    const pageSlug = slug;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [pageData, slugMap] = await Promise.all([
          getWikiPageBySlug(pageSlug),
          fetchAllTitleSlugMap(),
        ]);

        if (cancelled) return;

        const parsed = splitFrontmatter(pageData.content);
        setPage(pageData);
        setTitleSlugMap(slugMap);
        setFrontmatter(parsed.frontmatter);
        setMarkdownBody(parsed.body);

        const [relatedData, linksData] = await Promise.all([
          getRelatedWikiPages(pageData.id),
          getWikiLinks(pageData.id),
        ]);

        if (cancelled) return;

        setRelatedPages(relatedData.related_pages);
        setLinks([...linksData.outgoing, ...linksData.incoming]);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load wiki page');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const attributeRows = useMemo(() => (page ? getWikiAttributeRows(page) : []), [page]);

  const frontmatterRows = useMemo(() => {
    const rows: Array<{ key: string; value: string }> = [];
    for (const [key, value] of Object.entries(frontmatter)) {
      if (value) rows.push({ key, value });
    }
    return rows;
  }, [frontmatter]);

  const sidebarRelated = useMemo(() => {
    if (!page) return [];
    const linkedSlugs = new Set(
      links.map((link) =>
        link.from_page_id === page.id ? link.to_page_slug : link.from_page_slug,
      ),
    );
    return relatedPages.filter((related) => related.slug !== page.slug && !linkedSlugs.has(related.slug));
  }, [links, page, relatedPages]);

  if (loading) {
    return (
      <div className="flex min-h-full items-center justify-center gap-2 text-text-muted">
        <Loader2 className="h-5 w-5 animate-spin" />
        Loading page...
      </div>
    );
  }

  if (error || !page) {
    return (
      <div className="min-h-full p-6 md:p-8">
        <button
          type="button"
          onClick={() => navigate('/wiki')}
          className="mb-6 inline-flex items-center gap-2 text-body-md text-text-secondary hover:text-amber-400"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Wiki
        </button>
        <div className="rounded-lg border border-error/20 bg-error/10 px-4 py-3 text-body-md text-error">
          {error || 'Page not found'}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-full p-6 md:p-8">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <button
          type="button"
          onClick={() => navigate('/wiki')}
          className="mb-6 inline-flex items-center gap-2 text-body-md text-text-secondary hover:text-amber-400"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Wiki
        </button>

        <header className="mb-8 border-b border-amber-800/10 pb-6">
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-md bg-amber-500/15 px-2.5 py-1 text-mono-sm text-amber-300">
              {formatPageType(page.page_type)}
            </span>
            <span className="text-mono-sm text-text-muted">{page.word_count} words</span>
            <span className="text-mono-sm text-text-muted">updated {formatDate(page.updated_at)}</span>
          </div>
          <h1 className="mt-3 font-display text-display-lg text-text-primary">{page.title}</h1>
        </header>

        <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div>
            <WikiMarkdown content={markdownBody} titleSlugMap={titleSlugMap} />
          </div>

          <aside className="space-y-4">
            {frontmatterRows.length > 0 && (
              <section className="rounded-xl border border-amber-800/10 bg-bg-surface p-4">
                <h2 className="text-heading-sm text-text-primary">Frontmatter</h2>
                <dl className="mt-3 space-y-3">
                  {frontmatterRows.map((row) => (
                    <div key={row.key}>
                      <dt className="text-mono-sm uppercase tracking-wide text-text-muted">{row.key}</dt>
                      <dd className="mt-1 text-body-sm text-text-secondary">{row.value}</dd>
                    </div>
                  ))}
                </dl>
              </section>
            )}

            <section className="rounded-xl border border-amber-800/10 bg-bg-surface p-4">
              <h2 className="text-heading-sm text-text-primary">Attributes</h2>
              <dl className="mt-3 space-y-3">
                {attributeRows.map((row) => (
                  <div key={row.key}>
                    <dt className="text-mono-sm uppercase tracking-wide text-text-muted">{row.label}</dt>
                    <dd className="mt-1 text-body-sm text-text-secondary">{row.value}</dd>
                  </div>
                ))}
              </dl>
            </section>

            {links.length > 0 && (
              <section className="rounded-xl border border-amber-800/10 bg-bg-surface p-4">
                <h2 className="text-heading-sm text-text-primary">Linked pages</h2>
                <div className="mt-2 divide-y divide-amber-800/10">
                  {links.map((link) => (
                    <WikiLinkRow key={link.id} link={link} currentPageId={page.id} />
                  ))}
                </div>
              </section>
            )}

            {sidebarRelated.length > 0 && (
              <section className="rounded-xl border border-amber-800/10 bg-bg-surface p-4">
                <h2 className="text-heading-sm text-text-primary">Related pages</h2>
                <div className="mt-2">
                  {sidebarRelated.map((related) => (
                    <RelatedPageLink key={related.id} page={related} />
                  ))}
                </div>
              </section>
            )}
          </aside>
        </div>
      </motion.div>
    </div>
  );
}
