import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Search, FileText, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import { listWikiPages, type WikiPageResponse } from '@/lib/api';

const PAGE_SIZE = 24;

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export default function WikiBrowser() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialSearch = searchParams.get('search') || '';
  const pageParam = parseInt(searchParams.get('page') || '1', 10);
  const currentPage = Number.isNaN(pageParam) || pageParam < 1 ? 1 : pageParam;
  const [search, setSearch] = useState(initialSearch);
  const [pages, setPages] = useState<WikiPageResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  useEffect(() => {
    setSearch(initialSearch);
  }, [initialSearch]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await listWikiPages({
          search: initialSearch || undefined,
          page: currentPage,
          page_size: PAGE_SIZE,
        });
        if (!cancelled) {
          setPages(response.items);
          setTotal(response.total);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load wiki pages');
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
  }, [initialSearch, currentPage]);

  // Build the next URL query, preserving search while changing the page.
  const setQuery = (next: { search?: string; page?: number }) => {
    const params: Record<string, string> = {};
    const nextSearch = next.search !== undefined ? next.search : initialSearch;
    const nextPage = next.page !== undefined ? next.page : currentPage;
    if (nextSearch) params.search = nextSearch;
    if (nextPage > 1) params.page = String(nextPage);
    setSearchParams(params);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // Reset to first page whenever a new search is submitted.
    setQuery({ search: search.trim(), page: 1 });
  };

  const goToPage = (target: number) => {
    const clamped = Math.min(Math.max(1, target), totalPages);
    setQuery({ page: clamped });
  };

  // Compute a compact window of page numbers around the current page.
  const pageNumbers = useMemo(() => {
    const windowSize = 5;
    let start = Math.max(1, currentPage - Math.floor(windowSize / 2));
    const end = Math.min(totalPages, start + windowSize - 1);
    start = Math.max(1, end - windowSize + 1);
    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  }, [currentPage, totalPages]);

  return (
    <div className="min-h-full p-6 md:p-8">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="font-display text-display-lg text-text-primary">Wiki</h1>
        <p className="mt-2 text-body-md text-text-secondary">
          Browse knowledge pages generated from ingested sources.
        </p>
      </motion.div>

      <motion.form
        onSubmit={handleSearch}
        className="mt-6 flex gap-2"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search wiki pages..."
            className="w-full rounded-lg border border-amber-800/20 bg-bg-elevated py-2.5 pl-10 pr-4 text-body-md text-text-primary placeholder:text-text-muted focus:border-amber-500/50 focus:outline-none"
          />
        </div>
        <button
          type="submit"
          className="rounded-lg bg-amber-500 px-4 py-2.5 text-body-md font-medium text-text-inverse hover:bg-amber-400"
        >
          Search
        </button>
      </motion.form>

      <motion.div
        className="mt-6 rounded-xl border border-amber-800/10 bg-bg-surface"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
      >
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-16 text-text-muted">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading wiki pages...
          </div>
        ) : error ? (
          <div className="px-6 py-12 text-center text-body-md text-error">{error}</div>
        ) : pages.length === 0 ? (
          <div className="px-6 py-12 text-center text-body-md text-text-muted">
            No wiki pages found. Ingest a source to create pages.
          </div>
        ) : (
          <>
            <div className="border-b border-amber-800/10 px-4 py-3 text-mono-sm text-text-muted">
              {total} page{total !== 1 ? 's' : ''} · showing{' '}
              {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, total)}
            </div>
            <div className="divide-y divide-amber-800/10">
              {pages.map((page) => (
                <button
                  key={page.id}
                  type="button"
                  onClick={() => navigate(`/wiki/${page.slug}`)}
                  className="flex w-full items-center gap-4 px-4 py-4 text-left transition-colors hover:bg-bg-hover"
                >
                  <FileText className="h-5 w-5 shrink-0 text-amber-400" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-body-md font-medium text-text-primary">{page.title}</p>
                    <p className="mt-0.5 text-mono-sm text-text-muted">
                      {page.page_type} · {page.word_count} words · updated {formatDate(page.updated_at)}
                    </p>
                  </div>
                </button>
              ))}
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-1 border-t border-amber-800/10 px-4 py-4">
                <button
                  type="button"
                  onClick={() => goToPage(currentPage - 1)}
                  disabled={currentPage <= 1}
                  aria-label="Previous page"
                  className="flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary transition-colors hover:bg-bg-hover disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                {pageNumbers[0] > 1 && (
                  <span className="px-1 text-mono-sm text-text-muted">…</span>
                )}
                {pageNumbers.map((num) => (
                  <button
                    key={num}
                    type="button"
                    onClick={() => goToPage(num)}
                    aria-current={num === currentPage ? 'page' : undefined}
                    className={`h-9 min-w-9 rounded-lg px-3 text-body-sm font-medium transition-colors ${
                      num === currentPage
                        ? 'bg-amber-500 text-text-inverse'
                        : 'text-text-secondary hover:bg-bg-hover'
                    }`}
                  >
                    {num}
                  </button>
                ))}
                {pageNumbers[pageNumbers.length - 1] < totalPages && (
                  <span className="px-1 text-mono-sm text-text-muted">…</span>
                )}
                <button
                  type="button"
                  onClick={() => goToPage(currentPage + 1)}
                  disabled={currentPage >= totalPages}
                  aria-label="Next page"
                  className="flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary transition-colors hover:bg-bg-hover disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            )}
          </>
        )}
      </motion.div>
    </div>
  );
}
