/**
 * RunHistory — compact list of prior ingest jobs for a source, with a
 * duration sparkline to spot regressions at a glance.
 *
 * Fetches /api/sources/{id}/jobs on mount and on refresh.
 * Shows: job id, status chip, relative created_at, duration, error tooltip.
 * Sparkline: recharts BarChart of duration_ms oldest→newest.
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { RefreshCw, CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react';
import { sourceJobs, type SourceJob } from '@/lib/api';

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return '–';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60_000);
  const s = Math.floor((ms % 60_000) / 1000);
  return `${m}m ${s}s`;
}

function fmtRelative(iso: string | null | undefined): string {
  if (!iso) return '–';
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return new Date(iso).toLocaleDateString();
}

const STATUS_CFG: Record<
  string,
  { cls: string; Icon: React.ElementType; spin?: boolean }
> = {
  completed: { cls: 'bg-green-900/30 text-green-300', Icon: CheckCircle2 },
  failed: { cls: 'bg-red-900/30 text-red-300', Icon: XCircle },
  pending: { cls: 'bg-neutral-800 text-neutral-400', Icon: Clock },
};

const IN_FLIGHT = new Set([
  'processing', 'claimed', 'running', 'extracting',
  'chunking', 'summarizing', 'extracting_entities', 'creating_pages', 'analyzing',
]);

function StatusChip({ status }: { status: string }) {
  const cfg = IN_FLIGHT.has(status)
    ? { cls: 'bg-amber-900/30 text-amber-300', Icon: Loader2, spin: true }
    : (STATUS_CFG[status] ?? { cls: 'bg-neutral-800 text-neutral-400', Icon: Clock });
  const { cls, Icon, spin } = cfg;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${cls}`}
    >
      <Icon className={`h-2.5 w-2.5 ${spin ? 'animate-spin' : ''}`} />
      {status}
    </span>
  );
}

// ── Sparkline bar color ────────────────────────────────────────────────────────

function sparkFill(status: string): string {
  if (status === 'completed') return '#4ade80';
  if (status === 'failed') return '#f87171';
  return '#d97706'; // amber-600
}

// ── Component ──────────────────────────────────────────────────────────────────

export interface RunHistoryProps {
  sourceId: number;
}

const RunHistory = React.memo(function RunHistory({ sourceId }: RunHistoryProps) {
  const [jobs, setJobs] = useState<SourceJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await sourceJobs(sourceId);
      // Sort ascending by id (oldest first) — API order is unspecified
      setJobs(res.jobs.slice().sort((a, b) => a.id - b.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load run history');
    } finally {
      setLoading(false);
    }
  }, [sourceId]);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  // Sparkline data: oldest→newest, only jobs with a recorded duration
  const sparkData = jobs
    .filter((j) => j.duration_ms !== null)
    .map((j) => ({ id: j.id, v: j.duration_ms as number, status: j.status }));

  // List: newest first
  const displayJobs = [...jobs].reverse();

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <p className="text-mono-sm text-text-muted">Run history</p>
        <button
          type="button"
          onClick={() => void loadJobs()}
          disabled={loading}
          className="rounded p-0.5 text-neutral-500 hover:text-neutral-300 disabled:opacity-40"
          title="Refresh run history"
        >
          <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {loading && jobs.length === 0 && (
        <div className="flex justify-center py-3">
          <Loader2 className="h-4 w-4 animate-spin text-neutral-600" />
        </div>
      )}

      {error && (
        <p className="text-[10px] text-red-400">{error}</p>
      )}

      {!loading && !error && jobs.length === 0 && (
        <p className="text-[10px] text-neutral-600">No runs recorded yet.</p>
      )}

      {jobs.length > 0 && (
        <>
          {/* Duration sparkline — show only when 2+ data points exist */}
          {sparkData.length >= 2 && (
            <div className="mb-2" style={{ height: 36 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={sparkData}
                  margin={{ top: 0, right: 0, left: 0, bottom: 0 }}
                  barCategoryGap="20%"
                >
                  <Bar dataKey="v" isAnimationActive={false} radius={[2, 2, 0, 0]}>
                    {sparkData.map((d) => (
                      <Cell key={d.id} fill={sparkFill(d.status)} />
                    ))}
                  </Bar>
                  <Tooltip
                    cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const v = payload[0].value as number;
                      return (
                        <div className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1 text-[10px] text-neutral-300">
                          {fmtDuration(v)}
                        </div>
                      );
                    }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Job list */}
          <ul className="space-y-1">
            {displayJobs.map((job) => (
              <li
                key={job.id}
                className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px]"
              >
                <span className="font-mono text-neutral-600">#{job.id}</span>
                <StatusChip status={job.status} />
                <span className="text-neutral-500">{fmtRelative(job.created_at)}</span>
                <span className="ml-auto font-mono tabular-nums text-neutral-400">
                  {fmtDuration(job.duration_ms)}
                </span>
                {job.error_message && (
                  <span
                    title={job.error_message}
                    className="cursor-help text-red-400"
                    aria-label={`Error: ${job.error_message}`}
                  >
                    ⚠
                  </span>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
});

export default RunHistory;
