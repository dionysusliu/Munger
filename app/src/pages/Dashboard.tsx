import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BookOpen, Upload, FileText, Database, Link2 } from 'lucide-react';
import { getStats, type StatsResponse } from '@/lib/api';

export default function Dashboard() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await getStats();
        if (!cancelled) {
          setStats(data);
        }
      } catch (err) {
        if (!cancelled) {
          setStatsError(err instanceof Error ? err.message : 'Failed to load stats');
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-full p-6 md:p-8">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="font-display text-display-lg text-text-primary">Dashboard</h1>
        <p className="mt-2 text-body-md text-text-secondary">
          Ingest sources and explore your wiki knowledge base.
        </p>
      </motion.div>

      <motion.div
        className="mt-8 grid gap-4 sm:grid-cols-2"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <Link
          to="/ingest"
          className="group rounded-xl border border-amber-800/10 bg-bg-surface p-6 transition-colors hover:border-amber-500/30 hover:bg-bg-elevated"
        >
          <Upload className="h-8 w-8 text-amber-400" />
          <h2 className="mt-4 text-heading-md text-text-primary">Ingest sources</h2>
          <p className="mt-2 text-body-md text-text-secondary">
            Upload PDF or Markdown files and track ingestion progress.
          </p>
        </Link>

        <Link
          to="/wiki"
          className="group rounded-xl border border-amber-800/10 bg-bg-surface p-6 transition-colors hover:border-amber-500/30 hover:bg-bg-elevated"
        >
          <BookOpen className="h-8 w-8 text-amber-400" />
          <h2 className="mt-4 text-heading-md text-text-primary">Browse wiki</h2>
          <p className="mt-2 text-body-md text-text-secondary">
            Search and read knowledge pages created from your sources.
          </p>
        </Link>
      </motion.div>

      {stats && (
        <motion.div
          className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <StatCard icon={FileText} label="Sources" value={stats.total_sources} />
          <StatCard icon={BookOpen} label="Wiki pages" value={stats.total_wiki_pages} />
          <StatCard icon={Database} label="Entities" value={stats.total_entities} />
          <StatCard icon={Link2} label="Links" value={stats.total_links} />
        </motion.div>
      )}

      {statsError && (
        <p className="mt-4 text-body-sm text-text-muted">Stats unavailable: {statsError}</p>
      )}
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof FileText;
  label: string;
  value: number;
}) {
  return (
    <div className="rounded-xl border border-amber-800/10 bg-bg-surface p-5">
      <div className="flex items-center gap-3">
        <Icon className="h-5 w-5 text-amber-400" />
        <span className="text-mono-sm text-text-muted">{label}</span>
      </div>
      <p className="mt-3 font-display text-display-md text-text-primary">{value}</p>
    </div>
  );
}
