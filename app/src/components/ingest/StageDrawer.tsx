/**
 * StageDrawer — shadcn Sheet showing per-stage details on node click.
 *
 * Displays: stage label + status, duration, full metrics table,
 * failure message if any, and the raw related events (filtered by step_key).
 */
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { CheckCircle2, XCircle, Loader2, Circle, Clock } from 'lucide-react';
import type { IngestTimelineEvent } from '@/lib/api';
import { type StageView, type StageStatus } from './stageState';

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

function formatTs(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour12: false, timeStyle: 'medium' });
  } catch {
    return iso;
  }
}

function StatusBadge({ status }: { status: StageStatus }) {
  const cfgs: Record<StageStatus, { label: string; cls: string; Icon: React.ElementType }> = {
    done: { label: 'Done', cls: 'bg-green-900/30 text-green-300 border-green-700/30', Icon: CheckCircle2 },
    running: { label: 'Running', cls: 'bg-amber-900/30 text-amber-300 border-amber-700/30', Icon: Loader2 },
    failed: { label: 'Failed', cls: 'bg-red-900/30 text-red-300 border-red-700/30', Icon: XCircle },
    pending: { label: 'Pending', cls: 'bg-neutral-800 text-neutral-400 border-neutral-700/30', Icon: Circle },
  };
  const { label, cls, Icon } = cfgs[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${cls}`}
    >
      <Icon className={`h-3 w-3 ${status === 'running' ? 'animate-spin' : ''}`} />
      {label}
    </span>
  );
}

interface StageDrawerProps {
  stage: StageView | null;
  allEvents: IngestTimelineEvent[];
  open: boolean;
  onClose: () => void;
}

export default function StageDrawer({ stage, allEvents, open, onClose }: StageDrawerProps) {
  // Filter events related to this stage's step_key
  const relatedEvents = stage
    ? allEvents.filter((ev) => {
        const key = String(ev.payload?.step_key ?? '');
        return key === stage.key;
      })
    : [];

  return (
    <Sheet open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <SheetContent
        side="right"
        className="w-full overflow-y-auto border-l border-neutral-800 bg-neutral-950 sm:max-w-md"
      >
        <SheetHeader className="border-b border-neutral-800 pb-4">
          <SheetTitle className="text-base text-neutral-100">
            {stage?.label ?? 'Stage details'}
          </SheetTitle>
          <SheetDescription className="flex items-center gap-2">
            {stage && <StatusBadge status={stage.status} />}
            {stage?.durationMs !== undefined && (
              <span className="flex items-center gap-1 text-xs text-neutral-500">
                <Clock className="h-3 w-3" />
                {formatDuration(stage.durationMs)}
              </span>
            )}
          </SheetDescription>
        </SheetHeader>

        {stage && (
          <div className="space-y-5 px-4 py-4">
            {/* Failure message */}
            {stage.status === 'failed' && stage.failureMessage && (
              <div className="rounded-md border border-red-700/30 bg-red-950/30 px-3 py-2 text-sm text-red-300">
                {stage.failureMessage}
              </div>
            )}

            {/* Metrics table */}
            {stage.metrics && Object.keys(stage.metrics).length > 0 && (
              <section>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-neutral-500">
                  Metrics
                </h3>
                <div className="overflow-hidden rounded-md border border-neutral-800">
                  <table className="w-full text-xs">
                    <tbody>
                      {Object.entries(stage.metrics).map(([k, v]) => (
                        <tr
                          key={k}
                          className="border-b border-neutral-800 last:border-0 hover:bg-neutral-900/50"
                        >
                          <td className="py-1.5 pl-3 pr-4 font-mono text-neutral-400">
                            {k.replace(/_/g, ' ')}
                          </td>
                          <td className="py-1.5 pr-3 text-right font-mono text-neutral-200">
                            {String(v)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {/* Related events */}
            {relatedEvents.length > 0 && (
              <section>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-neutral-500">
                  Events ({relatedEvents.length})
                </h3>
                <ul className="space-y-1.5">
                  {relatedEvents.map((ev) => (
                    <li
                      key={ev.id}
                      className="rounded-md border border-neutral-800 bg-neutral-900/40 px-3 py-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[11px] font-medium text-neutral-300">
                          {ev.event_type.replace(/_/g, ' ')}
                        </span>
                        <span className="text-[10px] tabular-nums text-neutral-600">
                          #{ev.id}
                          {ev.created_at ? ` · ${formatTs(ev.created_at)}` : ''}
                        </span>
                      </div>
                      {/* Show relevant payload fields */}
                      {ev.event_type === 'pipeline_step_complete' && ev.payload?.duration_ms !== undefined && (
                        <p className="mt-0.5 text-[10px] text-neutral-500">
                          {formatDuration(Number(ev.payload.duration_ms))}
                        </p>
                      )}
                      {ev.event_type === 'pipeline_step_failed' && ev.payload?.message != null && (
                        <p className="mt-0.5 text-[10px] text-red-400">
                          {String(ev.payload.message)}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {relatedEvents.length === 0 && (
              <p className="text-sm text-neutral-600">No events recorded for this stage yet.</p>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
