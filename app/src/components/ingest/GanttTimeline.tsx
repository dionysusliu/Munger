/**
 * GanttTimeline — "where did time go" horizontal bar chart.
 *
 * Technique: recharts stacked BarChart layout="vertical" with:
 *   - An invisible "offset" series (shifts bar rightward by elapsed time
 *     since the first stage started)
 *   - A visible "duration" series colored by stage status
 *
 * Start timestamps are derived from pipeline_step_start events
 * (latest per step_key via created_at). StageView only carries durationMs,
 * not absolute start time, so we need the raw events for offset calculation.
 */
import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import type { IngestTimelineEvent } from '@/lib/api';
import type { StageView } from './stageState';

// ── Constants ────────────────────────────────────────────────────────────────

const ROW_PX = 32; // height per gantt row (px)

const STATUS_FILL: Record<string, string> = {
  done: '#4ade80',    // green-400
  running: '#f59e0b', // amber-400
  failed: '#f87171',  // red-400
  pending: '#404040', // neutral-700
};

// ── Internal types ───────────────────────────────────────────────────────────

interface GanttRow {
  label: string;
  key: string;
  /** Seconds elapsed from the very first stage start until this stage's start */
  offset: number;
  /** Duration of this stage in seconds */
  duration: number;
  status: string;
  /** Original ms value from StageView — used for formatted tooltip display */
  rawDurationMs?: number;
  metrics?: Record<string, unknown>;
}

// ── Helper functions ──────────────────────────────────────────────────────────

function fmtMs(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(2)}s`;
  const m = Math.floor(ms / 60_000);
  const s = Math.floor((ms % 60_000) / 1000);
  return `${m}m ${s}s`;
}

// ── Tooltip ───────────────────────────────────────────────────────────────────

function GanttTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: GanttRow }>;
}) {
  if (!active || !payload?.length) return null;
  // payload[0] is always the "offset" entry (invisible bar); the actual
  // duration data is on the same row payload object.
  const row = payload[0].payload;
  const durMs = row.rawDurationMs ?? row.duration * 1000;
  return (
    <div className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-[11px] shadow-lg">
      <p className="mb-1 font-semibold text-neutral-200">{row.label}</p>
      <p className="text-neutral-400">Duration: {fmtMs(durMs)}</p>
      {row.metrics &&
        Object.entries(row.metrics)
          .slice(0, 4)
          .map(([k, v]) => (
            <p key={k} className="text-neutral-500">
              {k.replace(/_/g, ' ')}: {String(v)}
            </p>
          ))}
    </div>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export interface GanttTimelineProps {
  stages: StageView[];
  events: IngestTimelineEvent[];
}

const GanttTimeline = React.memo(function GanttTimeline({
  stages,
  events,
}: GanttTimelineProps) {
  const rows = useMemo<GanttRow[]>(() => {
    // Derive the latest start timestamp per step_key from pipeline_step_start events.
    // "Latest" = highest event id (or latest created_at), matching stageState semantics.
    const startTs: Record<string, number> = {};
    for (const ev of events) {
      if (ev.event_type !== 'pipeline_step_start') continue;
      const key = String(ev.payload?.step_key ?? '');
      if (!key) continue;
      const ts = new Date(ev.created_at).getTime();
      if (startTs[key] === undefined || ts > startTs[key]) startTs[key] = ts;
    }

    const started = stages.filter(
      (s) => s.status !== 'pending' && startTs[s.key] !== undefined,
    );
    if (started.length === 0) return [];

    const firstMs = Math.min(...Object.values(startTs));

    // Use the latest known event timestamp as the "current time" for running stages.
    // This is pure (no Date.now call) and updates naturally on each 2-second poll.
    let latestEventTs = firstMs;
    for (const ev of events) {
      const ts = new Date(ev.created_at).getTime();
      if (ts > latestEventTs) latestEventTs = ts;
    }

    return started.map((s): GanttRow => {
      // For running stages without a recorded durationMs, use elapsed as of last event.
      const durationMs =
        s.durationMs ?? (s.status === 'running' ? latestEventTs - startTs[s.key] : 0);
      return {
        label: s.label,
        key: s.key,
        offset: (startTs[s.key] - firstMs) / 1000,
        duration: durationMs / 1000,
        status: s.status,
        rawDurationMs: s.durationMs,
        metrics: s.metrics,
      };
    });
  }, [stages, events]);

  if (rows.length === 0) return null;

  const chartH = rows.length * ROW_PX + 24; // 24px for x-axis ticks

  return (
    <div>
      <p className="mb-2 text-mono-sm text-text-muted">Timeline</p>
      <div style={{ height: chartH }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            layout="vertical"
            margin={{ top: 0, right: 16, left: 4, bottom: 0 }}
            barSize={ROW_PX - 8}
          >
            <XAxis
              type="number"
              tickFormatter={(v: number) => `${v.toFixed(0)}s`}
              tick={{ fontSize: 9, fill: '#525252' }}
              axisLine={false}
              tickLine={false}
              tickCount={5}
            />
            <YAxis
              type="category"
              dataKey="label"
              width={88}
              tick={{ fontSize: 10, fill: '#a3a3a3' }}
              axisLine={false}
              tickLine={false}
            />

            {/* Invisible "offset" bar — shifts the duration bar to its real start position */}
            <Bar dataKey="offset" stackId="gantt" fill="transparent" isAnimationActive={false} />

            {/* Colored "duration" bar — colored and optionally pulsing by status */}
            <Bar dataKey="duration" stackId="gantt" isAnimationActive={false} radius={[3, 3, 3, 3]}>
              {rows.map((row) => (
                <Cell
                  key={row.key}
                  fill={STATUS_FILL[row.status] ?? STATUS_FILL.pending}
                  className={row.status === 'running' ? 'animate-pulse' : undefined}
                />
              ))}
            </Bar>

            <Tooltip
              cursor={{ fill: 'rgba(255,255,255,0.03)' }}
              content={GanttTooltip as unknown as React.ReactElement}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});

export default GanttTimeline;
