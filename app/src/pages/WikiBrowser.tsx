import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Search, FileText, Loader2 } from 'lucide-react';
import { listWikiPages, type WikiPageResponse } from '@/lib/api';

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
  const [search, setSearch] = useState(initialSearch);
  const [pages, setPages] = useState<WikiPageResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
          page_size: 50,
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
  }, [initialSearch]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (search.trim()) {
      setSearchParams({ search: search.trim() });
    } else {
      setSearchParams({});
    }
  };

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
              {total} page{total !== 1 ? 's' : ''}
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
          </>
        )}
      </motion.div>
    </div>
  );
}
