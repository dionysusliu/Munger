import { useCallback, useEffect, useRef, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CloudUpload,
  FileText,
  Trash2,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  BookOpen,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import {
  deleteSource,
  getIngestStatus,
  listSources,
  triggerIngest,
  uploadSource,
  type IngestLogEntry,
  type IngestStatusResponse,
  type IngestTimelineEvent,
  type SourceResponse,
} from '@/lib/api';

type UiStatus = 'pending' | 'processing' | 'completed' | 'failed';
type StatusFilter = 'all' | 'pending' | 'processing' | 'completed' | 'failed';
type FileTypeFilter = 'all' | 'pdf' | 'md';

interface IngestJob {
  sourceId: number;
  filename: string;
  fileType: string;
  status: UiStatus;
  backendStatus: string;
  title: string;
  size: string;
  error?: string;
  recentLogs: IngestLogEntry[];
  events: IngestTimelineEvent[];
  lastEventId: number;
  updatedAt?: string;
  currentStep?: IngestStatusResponse['current_step'];
  stepMetrics?: IngestStatusResponse['step_metrics'];
  mapProgress?: IngestStatusResponse['map_progress'];
  wikiProgress?: IngestStatusResponse['wiki_progress'];
}

interface QueueQuery {
  page: number;
  statusFilter: StatusFilter;
  fileTypeFilter: FileTypeFilter;
}

const PAGE_SIZE = 20;
const PROCESSING_FETCH_SIZE = 100;
const POLL_INTERVAL_MS = 2000;
const REFETCH_DEBOUNCE_MS = 3000;

const STATUS_CONFIG: Record<UiStatus, { label: string; bg: string; text: string }> = {
  pending: { label: 'Pending', bg: 'bg-bg-hover', text: 'text-text-muted' },
  processing: { label: 'Processing', bg: 'bg-warning/15', text: 'text-warning' },
  completed: { label: 'Completed', bg: 'bg-success/15', text: 'text-success' },
  failed: { label: 'Failed', bg: 'bg-error/15', text: 'text-error' },
};

const IN_FLIGHT_STATUSES = new Set([
  'pending',
  'extracting',
  'chunking',
  'summarizing',
  'extracting_entities',
  'creating_pages',
  'analyzing',
]);

const PIPELINE_STEPS = [
  { key: 'register_source', label: 'Registering source' },
  { key: 'parse_document', label: 'Reading document' },
  { key: 'hash_dedup', label: 'Checking for duplicates' },
  { key: 'chunk_document', label: 'Splitting into sections' },
  { key: 'map_chunks', label: 'Mapping chunks' },
  { key: 'reduce_entities', label: 'Merging entities' },
  { key: 'link_entities', label: 'Linking entities' },
  { key: 'select_entities', label: 'Selecting key entities' },
  { key: 'summarize_source', label: 'Writing summary' },
  { key: 'generate_wiki_pages', label: 'Creating wiki pages' },
  { key: 'link_wiki_pages', label: 'Linking pages' },
  { key: 'finalize_ingest', label: 'Finishing up' },
] as const;

const NARROWING_FILTERS = new Set<StatusFilter>(['pending', 'completed', 'failed']);

function mapBackendStatus(status: string): UiStatus {
  if (status === 'completed') return 'completed';
  if (status === 'failed') return 'failed';
  if (status === 'pending') return 'pending';
  if (IN_FLIGHT_STATUSES.has(status)) return 'processing';
  return 'pending';
}

function mapFileTypeLabel(fileType: string): string {
  const labels: Record<string, string> = {
    pdf: 'PDF',
    md: 'MD',
    txt: 'TXT',
    html: 'HTML',
    url: 'URL',
  };
  return labels[fileType.toLowerCase()] || fileType.toUpperCase() || 'FILE';
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatRelativeTime(iso?: string): string {
  if (!iso) return 'Just now';
  const then = new Date(iso).getTime();
  const diffMs = Date.now() - then;
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return new Date(iso).toLocaleDateString();
}

function isTerminalStatus(status: string): boolean {
  return status === 'completed' || status === 'failed';
}

function sourceToJob(source: SourceResponse): IngestJob {
  return {
    sourceId: source.id,
    filename: source.filename,
    fileType: mapFileTypeLabel(source.file_type),
    status: mapBackendStatus(source.status),
    backendStatus: source.status,
    title: source.title,
    size: formatFileSize(source.file_size),
    error: source.error_message || undefined,
    recentLogs: [],
    events: [],
    lastEventId: 0,
    updatedAt: source.updated_at,
  };
}

function StatusBadge({ status }: { status: UiStatus }) {
  const cfg = STATUS_CONFIG[status];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-mono-sm font-medium ${cfg.bg} ${cfg.text}`}>
      {status === 'processing' && <Loader2 className="h-3 w-3 animate-spin" />}
      {status === 'completed' && <CheckCircle2 className="h-3 w-3" />}
      {status === 'failed' && <XCircle className="h-3 w-3" />}
      {status === 'pending' && <Clock className="h-3 w-3" />}
      {cfg.label}
    </span>
  );
}

function mergeEvents(existing: IngestTimelineEvent[], incoming: IngestTimelineEvent[]): IngestTimelineEvent[] {
  if (incoming.length === 0) return existing;
  const seen = new Set(existing.map((e) => e.id));
  const merged = [...existing];
  for (const event of incoming) {
    if (!seen.has(event.id)) merged.push(event);
  }
  return merged.sort((a, b) => a.id - b.id);
}

function applyStatusUpdate(job: IngestJob, payload: IngestStatusResponse): IngestJob {
  const events = mergeEvents(job.events, payload.events);
  const lastEventId = events.length > 0 ? events[events.length - 1].id : job.lastEventId;
  return {
    ...job,
    status: mapBackendStatus(payload.status),
    backendStatus: payload.status,
    error: payload.error_message || undefined,
    recentLogs: payload.recent_logs,
    events,
    lastEventId,
    updatedAt: payload.updated_at,
    currentStep: payload.current_step ?? job.currentStep,
    stepMetrics: payload.step_metrics ?? job.stepMetrics,
    mapProgress: payload.map_progress ?? job.mapProgress,
    wikiProgress: payload.wiki_progress ?? job.wikiProgress,
  };
}

function completedStepKeys(events: IngestTimelineEvent[]): Set<string> {
  const done = new Set<string>();
  for (const event of events) {
    if (event.event_type !== 'pipeline_step_complete') continue;
    const key = String(event.payload?.step_key || '');
    if (key) done.add(key);
  }
  return done;
}

function failedStep(events: IngestTimelineEvent[]): { key: string; message: string } | null {
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const event = events[i];
    if (event.event_type !== 'pipeline_step_failed') continue;
    return {
      key: String(event.payload?.step_key || ''),
      message: String(event.payload?.message || 'Step failed'),
    };
  }
  return null;
}

function PipelineProgress({ job }: { job: IngestJob }) {
  const done = completedStepKeys(job.events);
  const failure = failedStep(job.events);
  const activeIndex = job.currentStep?.index ?? (done.size + 1);
  const total = job.currentStep?.total ?? PIPELINE_STEPS.length;
  const metrics = job.stepMetrics ?? {};
  const mapP = job.mapProgress;
  const wikiP = job.wikiProgress;

  return (
    <div className="mb-3 space-y-2">
      <div className="flex items-center justify-between text-mono-sm text-text-muted">
        <span>Pipeline progress</span>
        <span>
          {Math.min(activeIndex, total)}/{total}
        </span>
      </div>
      <div className="space-y-1.5">
        {PIPELINE_STEPS.map((step, idx) => {
          const stepNum = idx + 1;
          const isDone = done.has(step.key);
          const isActive = !isDone && stepNum === activeIndex && job.status === 'processing';
          const isFailed = failure?.key === step.key;
          let statusClass = 'border-amber-800/15 bg-bg-hover text-text-muted';
          if (isDone) statusClass = 'border-success/25 bg-success/10 text-success';
          if (isActive) statusClass = 'border-warning/30 bg-warning/10 text-warning';
          if (isFailed) statusClass = 'border-error/30 bg-error/10 text-error';

          return (
            <div key={step.key} className={`rounded-md border px-3 py-2 text-body-sm ${statusClass}`}>
              <div className="flex items-center justify-between gap-2">
                <span>{step.label}</span>
                {isDone && <CheckCircle2 className="h-4 w-4 shrink-0" />}
                {isActive && <Loader2 className="h-4 w-4 shrink-0 animate-spin" />}
                {isFailed && <XCircle className="h-4 w-4 shrink-0" />}
              </div>
              {isFailed && failure && (
                <p className="mt-1 text-mono-sm text-error">{failure.message}</p>
              )}
              {step.key === 'map_chunks' && mapP && mapP.total > 0 && (
                <p className="mt-1 text-mono-sm text-text-secondary">
                  Chunks: {mapP.done}/{mapP.total} done
                  {mapP.running > 0 && ` · ${mapP.running} running`}
                  {mapP.failed > 0 && ` · ${mapP.failed} failed`}
                  {mapP.pending > 0 && ` · ${mapP.pending} pending`}
                </p>
              )}
              {step.key === 'generate_wiki_pages' && wikiP && wikiP.total > 0 && (
                <p className="mt-1 text-mono-sm text-text-secondary">
                  Wiki: {wikiP.pages_done}/{wikiP.total} pages
                </p>
              )}
            </div>
          );
        })}
      </div>
      {Object.keys(metrics).length > 0 && (
        <div className="rounded-md border border-amber-800/15 bg-bg-hover px-3 py-2 text-mono-sm text-text-secondary">
          {Object.entries(metrics).map(([key, value]) => (
            <span key={key} className="mr-3">
              {key.replace(/_/g, ' ')}: {String(value)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function JobRow({
  job,
  onReingest,
  onRemove,
}: {
  job: IngestJob;
  onReingest: (sourceId: number) => void;
  onRemove: (sourceId: number, filename: string) => void;
}) {
  const navigate = useNavigate();
  const isActive = job.status === 'processing' || job.status === 'pending';
  const [expanded, setExpanded] = useState(isActive);

  useEffect(() => {
    if (isActive) setExpanded(true);
  }, [isActive]);

  return (
    <motion.div layout className="overflow-hidden rounded-lg border border-amber-800/10 bg-bg-elevated">
      <div
        className="flex cursor-pointer items-center justify-between px-4 py-3 transition-colors hover:bg-bg-hover"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <FileText className="h-5 w-5 shrink-0 text-amber-400" />
          <div className="min-w-0">
            <p className="truncate text-body-md text-text-primary">{job.filename}</p>
            <p className="text-mono-sm text-text-muted">
              {job.size} · {job.backendStatus}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <span className="rounded-md bg-bg-hover px-2 py-0.5 text-mono-sm text-text-secondary">
            {job.fileType}
          </span>
          <StatusBadge status={job.status} />
          <span className="hidden text-mono-sm text-text-muted md:inline">
            {formatRelativeTime(job.updatedAt)}
          </span>
          {expanded ? <ChevronUp className="h-4 w-4 text-text-muted" /> : <ChevronDown className="h-4 w-4 text-text-muted" />}
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-amber-800/10 px-4 py-4"
          >
            {job.error && (
              <div className="mb-3 rounded-md border border-error/20 bg-error/10 px-3 py-2 text-body-sm text-error">
                {job.error}
              </div>
            )}

            {(isActive || job.events.length > 0 || job.currentStep) && (
              <div className="mb-3 max-h-80 overflow-y-auto pr-1">
                {job.status === 'pending' && job.events.length === 0 ? (
                  <div className="rounded-md border border-amber-800/20 bg-bg-hover px-3 py-2 text-body-sm text-text-muted">
                    Waiting for worker to pick up this job…
                  </div>
                ) : (
                  <PipelineProgress job={job} />
                )}
              </div>
            )}

            {job.recentLogs.length > 0 && (
              <div className="mb-3">
                <p className="mb-2 text-mono-sm text-text-muted">Recent logs</p>
                <ul className="space-y-1">
                  {job.recentLogs.map((log) => (
                    <li key={log.id} className="text-body-sm text-text-secondary">
                      <span className="text-text-muted">{formatRelativeTime(log.created_at)}</span>
                      {' · '}
                      {log.action}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              {job.status === 'completed' && (
                <button
                  type="button"
                  onClick={() => navigate(`/wiki?search=${encodeURIComponent(job.title)}`)}
                  className="inline-flex items-center gap-1.5 rounded-md bg-success/15 px-3 py-1.5 text-body-sm text-success hover:bg-success/25"
                >
                  <BookOpen className="h-3.5 w-3.5" />
                  View wiki pages
                </button>
              )}
              {(job.status === 'failed' || job.status === 'completed') && (
                <button
                  type="button"
                  onClick={() => onReingest(job.sourceId)}
                  className="inline-flex items-center gap-1.5 rounded-md bg-amber-500/15 px-3 py-1.5 text-body-sm text-amber-300 hover:bg-amber-500/25"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Re-ingest
                </button>
              )}
              <button
                type="button"
                onClick={() => onRemove(job.sourceId, job.filename)}
                className="inline-flex items-center gap-1.5 rounded-md bg-bg-hover px-3 py-1.5 text-body-sm text-text-muted hover:text-error"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Remove
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function Ingest() {
  const [jobs, setJobs] = useState<IngestJob[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [fileTypeFilter, setFileTypeFilter] = useState<FileTypeFilter>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const pollTimers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());
  const lastEventIdRef = useRef<Map<number, number>>(new Map());
  const refetchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const statusFilterRef = useRef(statusFilter);
  const hasLoadedRef = useRef(false);
  const fetchGenerationRef = useRef(0);
  const loadQueueRef = useRef<(query?: Partial<QueueQuery>) => Promise<void>>(async () => {});

  useEffect(() => {
    statusFilterRef.current = statusFilter;
  }, [statusFilter]);

  const updateJob = useCallback((sourceId: number, updater: (job: IngestJob) => IngestJob) => {
    setJobs((prev) => prev.map((job) => (job.sourceId === sourceId ? updater(job) : job)));
  }, []);

  const stopPolling = useCallback((sourceId?: number) => {
    if (sourceId !== undefined) {
      const timer = pollTimers.current.get(sourceId);
      if (timer) clearTimeout(timer);
      pollTimers.current.delete(sourceId);
      return;
    }
    pollTimers.current.forEach((timer) => clearTimeout(timer));
    pollTimers.current.clear();
  }, []);

  const scheduleRefetch = useCallback(() => {
    const filter = statusFilterRef.current;
    if (!NARROWING_FILTERS.has(filter)) return;
    if (refetchDebounceRef.current) return;
    refetchDebounceRef.current = setTimeout(() => {
      refetchDebounceRef.current = null;
      void loadQueueRef.current();
    }, REFETCH_DEBOUNCE_MS);
  }, []);

  const pollStatus = useCallback(
    (sourceId: number) => {
      stopPolling(sourceId);

      const poll = async () => {
        const activeFilter = statusFilterRef.current;
        try {
          const sinceId = lastEventIdRef.current.get(sourceId);
          const payload = await getIngestStatus(sourceId, {
            since_id: sinceId && sinceId > 0 ? sinceId : undefined,
          });
          updateJob(sourceId, (job) => {
            const updated = applyStatusUpdate(job, payload);
            lastEventIdRef.current.set(sourceId, updated.lastEventId);
            return updated;
          });

          if (isTerminalStatus(payload.status)) {
            stopPolling(sourceId);
            if (NARROWING_FILTERS.has(activeFilter)) {
              scheduleRefetch();
            }
            return;
          }

          if (NARROWING_FILTERS.has(activeFilter) && payload.status !== activeFilter) {
            stopPolling(sourceId);
            scheduleRefetch();
            return;
          }

          const timer = setTimeout(() => {
            void poll();
          }, POLL_INTERVAL_MS);
          pollTimers.current.set(sourceId, timer);
        } catch (err) {
          const message = err instanceof Error ? err.message : 'Status polling failed';
          updateJob(sourceId, (job) => ({
            ...job,
            error: job.error || message,
          }));
          const retryTimer = setTimeout(() => {
            void poll();
          }, POLL_INTERVAL_MS);
          pollTimers.current.set(sourceId, retryTimer);
        }
      };

      void poll();
    },
    [scheduleRefetch, stopPolling, updateJob],
  );

  const startPollingForJobs = useCallback(
    (jobList: IngestJob[]) => {
      for (const job of jobList) {
        if (!isTerminalStatus(job.backendStatus)) {
          pollStatus(job.sourceId);
        }
      }
    },
    [pollStatus],
  );

  const loadQueue = useCallback(
    async (overrides?: Partial<QueueQuery>) => {
      const query: QueueQuery = {
        page: overrides?.page ?? page,
        statusFilter: overrides?.statusFilter ?? statusFilter,
        fileTypeFilter: overrides?.fileTypeFilter ?? fileTypeFilter,
      };

      const generation = ++fetchGenerationRef.current;
      const isFirstLoad = !hasLoadedRef.current;

      stopPolling();
      if (isFirstLoad) {
        setIsLoading(true);
      } else {
        setIsRefreshing(true);
      }
      setListError(null);

      try {
        const isProcessingMode = query.statusFilter === 'processing';
        const response = await listSources({
          page: isProcessingMode ? 1 : query.page,
          page_size: isProcessingMode ? PROCESSING_FETCH_SIZE : PAGE_SIZE,
          status_filter:
            !isProcessingMode && query.statusFilter !== 'all' ? query.statusFilter : undefined,
          file_type: query.fileTypeFilter !== 'all' ? query.fileTypeFilter : undefined,
        });

        if (generation !== fetchGenerationRef.current) return;

        let items = response.items.map(sourceToJob);
        if (isProcessingMode) {
          items = items.filter((job) => IN_FLIGHT_STATUSES.has(job.backendStatus));
        }

        setJobs(items);
        setTotal(isProcessingMode ? items.length : response.total);
        hasLoadedRef.current = true;
        startPollingForJobs(items);
      } catch (err) {
        if (generation !== fetchGenerationRef.current) return;
        setListError(err instanceof Error ? err.message : 'Failed to load ingestion queue');
      } finally {
        if (generation !== fetchGenerationRef.current) return;
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [fileTypeFilter, page, startPollingForJobs, statusFilter, stopPolling],
  );

  useEffect(() => {
    loadQueueRef.current = loadQueue;
  }, [loadQueue]);

  useEffect(() => {
    void loadQueueRef.current();
  }, [page, statusFilter, fileTypeFilter]);

  useEffect(() => {
    return () => {
      stopPolling();
      if (refetchDebounceRef.current) {
        clearTimeout(refetchDebounceRef.current);
      }
    };
  }, [stopPolling]);

  const startIngest = useCallback(
    async (sourceId: number) => {
      await triggerIngest(sourceId);
      updateJob(sourceId, (job) => ({
        ...job,
        status: 'pending',
        backendStatus: 'pending',
        error: undefined,
      }));
      pollStatus(sourceId);
    },
    [pollStatus, updateJob],
  );

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;
      setUploadError(null);
      setIsUploading(true);

      setStatusFilter('all');
      setFileTypeFilter('all');
      setPage(1);

      try {
        for (const file of acceptedFiles) {
          try {
            const source = await uploadSource(file, file.name);
            await startIngest(source.id);
          } catch (err) {
            setUploadError(err instanceof Error ? err.message : 'Upload failed');
          }
        }
      } finally {
        setIsUploading(false);
        void loadQueue({ page: 1, statusFilter: 'all', fileTypeFilter: 'all' });
      }
    },
    [loadQueue, startIngest],
  );

  const handleRemove = useCallback(
    async (sourceId: number, filename: string) => {
      if (
        !window.confirm(
          `Delete "${filename}"? This permanently removes the source and related wiki pages.`,
        )
      ) {
        return;
      }

      try {
        stopPolling(sourceId);
        await deleteSource(sourceId);
        if (jobs.length === 1 && page > 1) {
          setPage((current) => current - 1);
        } else {
          await loadQueue();
        }
      } catch (err) {
        setListError(err instanceof Error ? err.message : 'Failed to delete source');
      }
    },
    [jobs.length, loadQueue, page, stopPolling],
  );

  const { getRootProps, getInputProps, open, isDragActive } = useDropzone({
    onDrop: (files) => void onDrop(files),
    accept: {
      'application/pdf': ['.pdf'],
      'text/markdown': ['.md', '.markdown'],
    },
    disabled: isUploading,
    noClick: true,
    noKeyboard: true,
  });

  const isProcessingMode = statusFilter === 'processing';
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const processingCount = jobs.filter((j) => j.status === 'processing' || j.status === 'pending').length;
  const completedCount = jobs.filter((j) => j.status === 'completed').length;

  const handleStatusFilterChange = (value: StatusFilter) => {
    setStatusFilter(value);
    setPage(1);
  };

  const handleFileTypeFilterChange = (value: FileTypeFilter) => {
    setFileTypeFilter(value);
    setPage(1);
  };

  return (
    <div className="min-h-full p-6 md:p-8">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="font-display text-display-lg text-text-primary">Ingest</h1>
        <p className="mt-2 text-body-md text-text-secondary">
          Upload Markdown or PDF sources to build your wiki knowledge base.
        </p>
        <div className="mt-4 flex flex-wrap gap-3 text-body-sm text-text-secondary">
          <span>Active on page: {processingCount}</span>
          <span>Completed on page: {completedCount}</span>
          <span>Total: {total}</span>
        </div>
      </motion.div>

      <motion.div className="mt-8" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <div
          {...getRootProps()}
          className={`rounded-2xl border-2 border-dashed p-8 text-center transition-all ${
            isDragActive ? 'border-amber-400 bg-amber-900/10' : 'border-amber-700/40 bg-bg-surface'
          }`}
        >
          <input {...getInputProps()} />
          <CloudUpload className={`mx-auto h-12 w-12 ${isDragActive ? 'text-amber-400' : 'text-amber-400/70'}`} />
          <p className="mt-4 text-heading-md text-text-primary">Drop PDF or Markdown files here</p>
          <p className="mt-1 text-body-md text-text-secondary">Supported: .pdf, .md, .markdown</p>
          <button
            type="button"
            onClick={open}
            disabled={isUploading}
            className="mt-4 inline-flex items-center gap-2 rounded-md bg-amber-500 px-5 py-2.5 text-body-md font-medium text-text-inverse hover:bg-amber-400 disabled:opacity-50"
          >
            {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <CloudUpload className="h-4 w-4" />}
            {isUploading ? 'Uploading...' : 'Browse files'}
          </button>
        </div>

        {uploadError && (
          <div className="mt-4 rounded-md border border-error/20 bg-error/10 px-4 py-3 text-body-sm text-error">
            {uploadError}
          </div>
        )}
      </motion.div>

      <motion.div
        className="mt-8 rounded-xl border border-amber-800/10 bg-bg-surface p-5"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-heading-md text-text-primary">Ingestion queue</h2>
            {isRefreshing && (
              <Loader2 className="h-4 w-4 animate-spin text-text-muted" aria-label="Refreshing queue" />
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <select
              value={statusFilter}
              onChange={(e) => handleStatusFilterChange(e.target.value as StatusFilter)}
              className="rounded-lg border border-amber-800/20 bg-bg-elevated px-3 py-2 text-body-sm text-text-primary"
            >
              <option value="all">All statuses</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
            <select
              value={fileTypeFilter}
              onChange={(e) => handleFileTypeFilterChange(e.target.value as FileTypeFilter)}
              className="rounded-lg border border-amber-800/20 bg-bg-elevated px-3 py-2 text-body-sm text-text-primary"
            >
              <option value="all">All types</option>
              <option value="pdf">PDF</option>
              <option value="md">Markdown</option>
            </select>
          </div>
        </div>

        {isProcessingMode && (
          <div className="mb-4 rounded-md border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-body-sm text-amber-200">
            Showing in-progress jobs from recent sources.
          </div>
        )}

        {listError && (
          <div className="mb-4 rounded-md border border-error/20 bg-error/10 px-4 py-3 text-body-sm text-error">
            {listError}
          </div>
        )}

        {isLoading && jobs.length === 0 ? (
          <div className="flex items-center justify-center gap-2 py-12 text-text-muted">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading queue...
          </div>
        ) : jobs.length === 0 ? (
          <div className="py-12 text-center text-body-md text-text-muted">
            No ingestion jobs match the current filters.
          </div>
        ) : (
          <div className="space-y-2">
            {jobs.map((job) => (
              <JobRow
                key={job.sourceId}
                job={job}
                onReingest={(sourceId) => void startIngest(sourceId)}
                onRemove={(sourceId, filename) => void handleRemove(sourceId, filename)}
              />
            ))}
          </div>
        )}

        {!isProcessingMode && total > PAGE_SIZE && (
          <div className="mt-4 flex items-center justify-between border-t border-amber-800/10 pt-4">
            <button
              type="button"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={page <= 1 || isLoading}
              className="inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-body-sm text-text-secondary hover:bg-bg-hover disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </button>
            <span className="text-mono-sm text-text-muted">
              Page {page} of {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
              disabled={page >= totalPages || isLoading}
              className="inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-body-sm text-text-secondary hover:bg-bg-hover disabled:opacity-40"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </motion.div>
    </div>
  );
}
