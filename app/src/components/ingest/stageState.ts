/**
 * Pure helper: derive per-stage status from polled events.
 * Exported as a module so it's easy to test in isolation.
 *
 * Re-run semantics: the LATEST event per step_key wins.
 * e.g. start → fail → start → complete  →  status = done  (latest is complete)
 *      start → complete → start          →  status = running (if job active)
 */
import type { PipelineStage, IngestTimelineEvent } from '@/lib/api';

export type StageStatus = 'pending' | 'running' | 'done' | 'failed';

export interface StageView {
  key: string;
  label: string;
  status: StageStatus;
  durationMs?: number;
  metrics?: Record<string, unknown>;
  failureMessage?: string;
}

/**
 * Backend statuses that mean the job is still actively running.
 * Covers both raw backend values and the UI-mapped 'processing'.
 */
const ACTIVE_STATUSES = new Set([
  'pending',
  'processing',
  'claimed',
  'running',
  'extracting',
  'chunking',
  'summarizing',
  'extracting_entities',
  'creating_pages',
  'analyzing',
]);

/**
 * Derive a StageView array from a topology + accumulated event list + job status.
 *
 * @param topology  - ordered list of stages from GET /api/pipeline/topology
 * @param events    - all accumulated IngestTimelineEvents for this source/job
 * @param jobStatus - raw backend status string (e.g. 'processing', 'completed', 'failed')
 */
export function deriveStages(
  topology: PipelineStage[],
  events: IngestTimelineEvent[],
  jobStatus: string,
): StageView[] {
  const isActive = ACTIVE_STATUSES.has(jobStatus);

  // Accumulate latest event per step_key per event type (later ID = later event)
  const latestComplete: Record<string, IngestTimelineEvent> = {};
  const latestFailed: Record<string, IngestTimelineEvent> = {};
  const latestStart: Record<string, IngestTimelineEvent> = {};

  for (const ev of events) {
    const key = String(ev.payload?.step_key ?? '');
    if (!key) continue;
    if (ev.event_type === 'pipeline_step_complete') {
      if (!latestComplete[key] || ev.id > latestComplete[key].id) latestComplete[key] = ev;
    } else if (ev.event_type === 'pipeline_step_failed') {
      if (!latestFailed[key] || ev.id > latestFailed[key].id) latestFailed[key] = ev;
    } else if (ev.event_type === 'pipeline_step_start') {
      if (!latestStart[key] || ev.id > latestStart[key].id) latestStart[key] = ev;
    }
  }

  return topology.map((stage): StageView => {
    const complete = latestComplete[stage.key];
    const failed = latestFailed[stage.key];
    const start = latestStart[stage.key];

    const completeId = complete?.id ?? -1;
    const failedId = failed?.id ?? -1;
    const startId = start?.id ?? -1;
    const maxId = Math.max(completeId, failedId, startId);

    // No events at all for this stage
    if (maxId < 0) {
      return { key: stage.key, label: stage.label, status: 'pending' };
    }

    // Complete event is the latest — stage is done
    if (maxId === completeId) {
      const payload = (complete!.payload ?? {}) as Record<string, unknown>;
      return {
        key: stage.key,
        label: stage.label,
        status: 'done',
        durationMs: typeof payload.duration_ms === 'number' ? payload.duration_ms : undefined,
        metrics:
          payload.metrics !== null && typeof payload.metrics === 'object'
            ? (payload.metrics as Record<string, unknown>)
            : undefined,
      };
    }

    // Failed event is the latest — stage failed
    if (maxId === failedId) {
      const payload = (failed!.payload ?? {}) as Record<string, unknown>;
      return {
        key: stage.key,
        label: stage.label,
        status: 'failed',
        failureMessage: typeof payload.message === 'string' ? payload.message : 'Step failed',
      };
    }

    // Start event is the latest — running if job is active, else treat as pending
    return {
      key: stage.key,
      label: stage.label,
      status: isActive ? 'running' : 'pending',
    };
  });
}
