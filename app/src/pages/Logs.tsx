import { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  ChevronDown,
  Download,
  Radio,
  Clock,
  FileText,
  AlertTriangle,
  CheckCircle,
  Sparkles,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// --- Types ---

interface LogEntry {
  id: string;
  timestamp: Date;
  type: 'ingest' | 'analysis' | 'wiki' | 'entity' | 'system';
  level: 'info' | 'warning' | 'error' | 'success';
  message: string;
  source: string | null;
  details: Record<string, unknown> | null;
}

// --- Constants ---

const TYPE_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  ingest: { label: 'Ingest', color: '#D97706', icon: <FileText className="size-3" /> },
  wiki: { label: 'Wiki', color: '#5A9B8A', icon: <CheckCircle className="size-3" /> },
  analysis: { label: 'Analysis', color: '#7C6BFF', icon: <Sparkles className="size-3" /> },
  entity: { label: 'Entity', color: '#C97B7B', icon: <AlertTriangle className="size-3" /> },
  system: { label: 'System', color: '#7A8B9A', icon: <Clock className="size-3" /> },
};

const LEVEL_COLORS: Record<string, string> = {
  info: '#7C6BFF',
  warning: '#CA8A04',
  error: '#B91C1C',
  success: '#65A30D',
};

// --- Mock Data ---

function createMockLogs(): LogEntry[] {
  const now = new Date();
  const entries: LogEntry[] = [
    {
      id: '1',
      timestamp: new Date(now.getTime() - 2 * 60 * 1000),
      type: 'ingest',
      level: 'success',
      message: "Ingested 'Thinking Fast and Slow.pdf' — 12 entities extracted, 3 wiki pages created",
      source: 'Thinking Fast and Slow.pdf',
      details: { fileSize: '4.2 MB', pages: 452, entities: 12, wikiPages: ['cognitive-bias', 'loss-aversion', 'anchoring-effect'], processingTime: '8.3s' },
    },
    {
      id: '2',
      timestamp: new Date(now.getTime() - 5 * 60 * 1000),
      type: 'wiki',
      level: 'info',
      message: "Updated wiki page 'Cognitive Bias' — 3 new links added, 1 entity refined",
      source: 'Cognitive Bias',
      details: { addedLinks: ['availability-heuristic', 'confirmation-bias', 'hindsight-bias'], refinedEntity: 'Bias (psychology)', editTime: '2.1s' },
    },
    {
      id: '3',
      timestamp: new Date(now.getTime() - 12 * 60 * 1000),
      type: 'analysis',
      level: 'info',
      message: "Completed Munger analysis for 'Mental Models' — 11 of 12 dimensions analyzed",
      source: 'Mental Models',
      details: { dimensionsAnalyzed: 11, totalDimensions: 12, topDimension: 'Inversion', confidence: 0.94, processingTime: '15.7s' },
    },
    {
      id: '4',
      timestamp: new Date(now.getTime() - 18 * 60 * 1000),
      type: 'entity',
      level: 'success',
      message: "Extracted 8 new entities from 'The Checklist Manifesto' — 5 concepts, 2 principles, 1 model",
      source: 'The Checklist Manifesto',
      details: { totalEntities: 8, byType: { concept: 5, principle: 2, model: 1 }, confidence: 0.91 },
    },
    {
      id: '5',
      timestamp: new Date(now.getTime() - 25 * 60 * 1000),
      type: 'system',
      level: 'info',
      message: 'System health check passed — all services operational, 42 wiki pages indexed',
      source: null,
      details: { uptime: '3d 14h 22m', memoryUsage: '1.2GB', wikiPages: 42, entities: 186 },
    },
    {
      id: '6',
      timestamp: new Date(now.getTime() - 32 * 60 * 1000),
      type: 'ingest',
      level: 'warning',
      message: "Ingested 'Behavioral Economics Notes.md' — low confidence on 3 entities, manual review recommended",
      source: 'Behavioral Economics Notes.md',
      details: { fileSize: '12 KB', entities: 7, lowConfidence: 3, wikiPages: 1 },
    },
    {
      id: '7',
      timestamp: new Date(now.getTime() - 45 * 60 * 1000),
      type: 'wiki',
      level: 'info',
      message: "Created new wiki page 'First Principles Thinking' — linked to 4 existing pages",
      source: 'First Principles Thinking',
      details: { slug: 'first-principles', wordCount: 3890, linkedPages: ['mental-models', 'inversion', 'elon-musk', 'physics'] },
    },
    {
      id: '8',
      timestamp: new Date(now.getTime() - 55 * 60 * 1000),
      type: 'analysis',
      level: 'error',
      message: "Munger analysis failed for 'Probability Theory' — LLM timeout after 60s, retry queued",
      source: 'Probability Theory',
      details: { error: 'LLM_REQUEST_TIMEOUT', dimensionsAttempted: 3, retryIn: '5 minutes' },
    },
    {
      id: '9',
      timestamp: new Date(now.getTime() - 60 * 60 * 1000),
      type: 'entity',
      level: 'info',
      message: "Entity merge: 'Cognitive Bias' and 'Cognitive Distortion' merged — 6 duplicate relationships resolved",
      source: 'Cognitive Bias',
      details: { mergedEntities: 2, resolvedDuplicates: 6, confidence: 0.88 },
    },
    {
      id: '10',
      timestamp: new Date(now.getTime() - 2 * 60 * 60 * 1000),
      type: 'ingest',
      level: 'success',
      message: "Ingested 'Poor Charlie's Almanack.epub' — 24 entities extracted, 7 wiki pages created",
      source: "Poor Charlie's Almanack.epub",
      details: { fileSize: '8.7 MB', pages: 312, entities: 24, wikiPages: 7, processingTime: '22.1s' },
    },
    {
      id: '11',
      timestamp: new Date(now.getTime() - 3 * 60 * 60 * 1000),
      type: 'wiki',
      level: 'info',
      message: "Updated wiki page 'Compound Interest' — added 2 new sources, 1 related model linked",
      source: 'Compound Interest',
      details: { addedSources: 2, linkedModel: 'exponential-growth', wordCountChange: '+340' },
    },
    {
      id: '12',
      timestamp: new Date(now.getTime() - 4 * 60 * 60 * 1000),
      type: 'analysis',
      level: 'success',
      message: "Completed Munger analysis for 'Circle of Competence' — all 12 dimensions analyzed with 0.92 avg confidence",
      source: 'Circle of Competence',
      details: { dimensionsAnalyzed: 12, avgConfidence: 0.92, topDimension: 'Circle of Competence', processingTime: '18.4s' },
    },
    {
      id: '13',
      timestamp: new Date(now.getTime() - 5 * 60 * 60 * 1000),
      type: 'system',
      level: 'warning',
      message: 'Storage usage at 78% — consider archiving old logs or exporting data',
      source: null,
      details: { storageUsed: '7.8 GB', storageTotal: '10 GB', usagePercent: 78 },
    },
    {
      id: '14',
      timestamp: new Date(now.getTime() - 6 * 60 * 60 * 1000),
      type: 'ingest',
      level: 'success',
      message: "Ingested 'Antifragile.pdf' — 18 entities extracted, concept 'Antifragility' created",
      source: 'Antifragile.pdf',
      details: { fileSize: '6.1 MB', entities: 18, newConcept: 'Antifragility', processingTime: '14.2s' },
    },
    {
      id: '15',
      timestamp: new Date(now.getTime() - 8 * 60 * 60 * 1000),
      type: 'wiki',
      level: 'info',
      message: "Auto-linked 'Margin of Safety' to 3 new pages via semantic similarity",
      source: 'Margin of Safety',
      details: { newLinks: ['circle-of-competence', 'first-principles', 'inversion'], similarityScores: [0.91, 0.87, 0.82] },
    },
    {
      id: '16',
      timestamp: new Date(now.getTime() - 10 * 60 * 60 * 1000),
      type: 'entity',
      level: 'success',
      message: "Batch entity extraction completed — 34 entities from 3 documents, 12 cross-references found",
      source: 'Batch Job #2847',
      details: { documents: 3, entities: 34, crossReferences: 12, avgConfidence: 0.89 },
    },
    {
      id: '17',
      timestamp: new Date(now.getTime() - 12 * 60 * 60 * 1000),
      type: 'analysis',
      level: 'info',
      message: "Munger analysis started for 'Second-Order Thinking' — queued behind 1 job",
      source: 'Second-Order Thinking',
      details: { queuePosition: 2, estimatedTime: '45s', dimensions: 12 },
    },
    {
      id: '18',
      timestamp: new Date(now.getTime() - 14 * 60 * 60 * 1000),
      type: 'system',
      level: 'info',
      message: 'Daily backup completed — 156 MB exported to /backups/2026-01-15.zip',
      source: null,
      details: { backupSize: '156 MB', location: '/backups/2026-01-15.zip', pages: 42, entities: 186 },
    },
    {
      id: '19',
      timestamp: new Date(now.getTime() - 16 * 60 * 60 * 1000),
      type: 'ingest',
      level: 'error',
      message: "Failed to ingest 'corrupted-file.pdf' — PDF parsing error, file may be encrypted or damaged",
      source: 'corrupted-file.pdf',
      details: { error: 'PDF_PARSE_ERROR', fileSize: '2.3 MB', suggestion: 'Try converting to text first' },
    },
    {
      id: '20',
      timestamp: new Date(now.getTime() - 18 * 60 * 60 * 1000),
      type: 'wiki',
      level: 'info',
      message: "Refactored wiki page 'Lollapalooza Effect' — reorganized into 5 sections, added 2 examples",
      source: 'Lollapalooza Effect',
      details: { sections: 5, addedExamples: 2, wordCount: 1890, linkedPages: 8 },
    },
    {
      id: '21',
      timestamp: new Date(now.getTime() - 20 * 60 * 60 * 1000),
      type: 'analysis',
      level: 'success',
      message: "Completed Munger analysis for 'Inversion' — strong scores in Principles (0.98) and Mental Models (0.95)",
      source: 'Inversion',
      details: { dimensionsAnalyzed: 12, topScore: 0.98, topDimension: 'Principles', processingTime: '12.3s' },
    },
    {
      id: '22',
      timestamp: new Date(now.getTime() - 22 * 60 * 60 * 1000),
      type: 'system',
      level: 'info',
      message: 'LLM model switched to GPT-4o — connection test passed in 1.2s',
      source: null,
      details: { model: 'gpt-4o', provider: 'OpenAI', latency: '1.2s', testResult: 'PASS' },
    },
    {
      id: '23',
      timestamp: new Date(now.getTime() - 24 * 60 * 60 * 1000),
      type: 'entity',
      level: 'warning',
      message: "Entity 'Bias' has 7 ambiguous references — disambiguation review needed",
      source: 'Bias',
      details: { entity: 'Bias', references: 7, contexts: ['psychology', 'statistics', 'machine-learning', 'finance', 'media', 'cognitive', 'neuroscience'] },
    },
    {
      id: '24',
      timestamp: new Date(now.getTime() - 26 * 60 * 60 * 1000),
      type: 'ingest',
      level: 'success',
      message: "Ingested 'Nassim Taleb URL clip' — 6 entities from web article, auto-summarized",
      source: 'https://foo.com/taleb-article',
      details: { url: 'https://foo.com/taleb-article', entities: 6, summaryLength: '340 words', processingTime: '6.7s' },
    },
    {
      id: '25',
      timestamp: new Date(now.getTime() - 30 * 60 * 60 * 1000),
      type: 'wiki',
      level: 'info',
      message: "Created wiki page 'Multidisciplinary Approach' from 4 linked source pages",
      source: 'Multidisciplinary Approach',
      details: { sourcePages: 4, wordCount: 3560, dimensions: [3, 9, 2], autoGenerated: true },
    },
  ];
  return entries;
}

// --- Helpers ---

function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function relativeTime(date: Date): string {
  const diff = Date.now() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function isWithinDays(date: Date, days: number): boolean {
  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
  return date.getTime() >= cutoff;
}

function isToday(date: Date): boolean {
  const now = new Date();
  return date.getDate() === now.getDate() && date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear();
}

// --- Component ---

export default function Logs() {
  const [logs] = useState<LogEntry[]>(createMockLogs);
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [dateFilter, setDateFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [isLive, setIsLive] = useState(false);
  const tableRef = useRef<HTMLDivElement>(null);

  const typeFilters = ['all', 'ingest', 'wiki', 'analysis', 'entity', 'system'];
  const dateFilters = [
    { key: 'today', label: 'Today' },
    { key: '7days', label: 'Last 7 days' },
    { key: '30days', label: 'Last 30 days' },
    { key: 'all', label: 'All' },
  ];

  // Filtered logs
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      if (typeFilter !== 'all' && log.type !== typeFilter) return false;
      if (dateFilter === 'today' && !isToday(log.timestamp)) return false;
      if (dateFilter === '7days' && !isWithinDays(log.timestamp, 7)) return false;
      if (dateFilter === '30days' && !isWithinDays(log.timestamp, 30)) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return (
          log.message.toLowerCase().includes(q) ||
          (log.source && log.source.toLowerCase().includes(q)) ||
          log.type.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [logs, typeFilter, dateFilter, searchQuery]);

  // Toggle row expansion
  const toggleRow = useCallback((id: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  // Simulate live mode with auto-scroll
  useEffect(() => {
    if (isLive && tableRef.current) {
      tableRef.current.scrollTop = 0;
    }
  }, [isLive, filteredLogs.length]);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
        className="px-6 pt-8 pb-4 shrink-0"
      >
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="font-display text-4xl font-semibold text-[#EDE4D3]">System Logs</h1>
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[#65A30D15]">
                <span className="relative flex size-2">
                  <span className="absolute inline-flex h-full w-full rounded-full bg-[#65A30D] animate-live-dot" />
                  <span className="relative inline-flex rounded-full size-2 bg-[#65A30D]" />
                </span>
                <span className="text-[11px] font-medium text-[#65A30D]">Live</span>
              </div>
            </div>
            <p className="text-[15px] text-[#B8A88A] mt-1">
              Complete audit trail of all system activities
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* Live toggle */}
            <button
              onClick={() => setIsLive(!isLive)}
              className={cn(
                'flex items-center gap-1.5 h-8 px-3 rounded-md text-xs font-medium transition-all border',
                isLive
                  ? 'bg-[#65A30D20] text-[#65A30D] border-[#65A30D40]'
                  : 'bg-[#251F18] text-[#B8A88A] border-[#78350F30] hover:text-[#EDE4D3]'
              )}
            >
              <Radio className="size-3.5" />
              {isLive ? 'Live' : 'Paused'}
            </button>
            {/* Export button */}
            <button
              className="flex items-center gap-1.5 h-8 px-3 rounded-md text-xs font-medium border text-[#B8A88A] hover:text-[#EDE4D3] hover:bg-[#251F18] transition-all"
              style={{ borderColor: '#78350F30' }}
              onClick={() => alert('Export functionality coming soon!')}
            >
              <Download className="size-3.5" />
              Export
            </button>
          </div>
        </div>
        <div className="text-[12px] text-[#7A6B5A] font-mono mt-2">{filteredLogs.length} entries</div>
      </motion.div>

      {/* Filter Bar */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="px-6 py-3 border-b shrink-0 flex flex-wrap items-center gap-4"
        style={{
          background: '#0C0907',
          borderColor: 'rgba(120, 53, 15, 0.1)',
          backdropFilter: 'blur(8px)',
        }}
      >
        {/* Search */}
        <div className="relative flex-1 max-w-[320px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-[#7A6B5A]" />
          <input
            type="text"
            placeholder="Search logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-8 pl-8 pr-7 text-sm rounded-md border bg-transparent text-[#EDE4D3] placeholder-[#7A6B5A] outline-none focus:border-[#D97706] transition-colors"
            style={{ borderColor: 'rgba(120, 53, 15, 0.25)', background: '#0F0C09' }}
          />
          {searchQuery && (
            <button
              className="absolute right-2 top-1/2 -translate-y-1/2 text-[#7A6B5A] hover:text-[#EDE4D3]"
              onClick={() => setSearchQuery('')}
            >
              <X className="size-3" />
            </button>
          )}
        </div>

        {/* Type filter pills */}
        <div className="flex items-center gap-1">
          {typeFilters.map((tf) => {
            const isActive = typeFilter === tf;
            const config = TYPE_CONFIG[tf];
            return (
              <motion.button
                key={tf}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.2 }}
                onClick={() => setTypeFilter(tf)}
                className={cn(
                  'h-7 px-3 rounded-full text-[11px] font-medium transition-all',
                  isActive
                    ? 'text-[#14100D]'
                    : 'bg-[#251F18] text-[#B8A88A] hover:bg-[#2D2620] hover:text-[#EDE4D3]'
                )}
                style={
                  isActive
                    ? { background: config?.color || '#D97706', color: '#14100D' }
                    : {}
                }
              >
                {config?.label || 'All'}
              </motion.button>
            );
          })}
        </div>

        {/* Date range pills */}
        <div className="flex items-center gap-1 ml-auto">
          {dateFilters.map((df) => (
            <button
              key={df.key}
              onClick={() => setDateFilter(df.key)}
              className={cn(
                'h-7 px-3 rounded-full text-[11px] font-medium transition-all',
                dateFilter === df.key
                  ? 'bg-[#FBBF2420] text-[#FBBF24] border border-[#FBBF2440]'
                  : 'text-[#7A6B5A] hover:text-[#B8A88A] hover:bg-[#251F18]'
              )}
            >
              {df.label}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Log Table */}
      <div ref={tableRef} className="flex-1 overflow-y-auto">
        <div className="px-6 py-4">
          {/* Table Header */}
          <div
            className="grid gap-2 px-3 h-11 items-center text-[11px] font-semibold text-[#7A6B5A] uppercase tracking-wider border-b sticky top-0 z-10"
            style={{
              gridTemplateColumns: '100px 90px 1fr 140px 40px',
              background: '#14100D',
              borderColor: 'rgba(120, 53, 15, 0.15)',
            }}
          >
            <div>Time</div>
            <div>Type</div>
            <div>Action</div>
            <div>Source</div>
            <div />
          </div>

          {/* Table Rows */}
          <AnimatePresence mode="popLayout">
            {filteredLogs.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center py-20"
              >
                <p className="text-lg font-display text-[#EDE4D3]">No log entries match your filters</p>
                <p className="text-sm text-[#B8A88A] mt-1">Try adjusting your filter criteria</p>
                <button
                  onClick={() => { setTypeFilter('all'); setDateFilter('all'); setSearchQuery(''); }}
                  className="mt-4 h-8 px-4 rounded-md text-xs font-medium border text-[#B8A88A] hover:text-[#EDE4D3] hover:bg-[#251F18] transition-all"
                  style={{ borderColor: '#78350F60' }}
                >
                  Clear filters
                </button>
              </motion.div>
            ) : (
              filteredLogs.map((log, index) => {
                const typeConfig = TYPE_CONFIG[log.type];
                const isExpanded = expandedRows.has(log.id);

                return (
                  <motion.div
                    key={log.id}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.25, delay: index * 0.02, ease: [0.4, 0, 0.2, 1] as [number, number, number, number] }}
                  >
                    {/* Main row */}
                    <div
                      className={cn(
                        'grid gap-2 px-3 py-3 border-b items-center cursor-pointer transition-colors hover:bg-[#251F1850]',
                        isExpanded && 'bg-[#251F1830]'
                      )}
                      style={{ gridTemplateColumns: '100px 90px 1fr 140px 40px', borderColor: 'rgba(120, 53, 15, 0.06)' }}
                      onClick={() => log.details && toggleRow(log.id)}
                    >
                      {/* Time */}
                      <div className="flex flex-col">
                        <span className="font-mono text-[11px] text-[#7A6B5A]">{formatTime(log.timestamp)}</span>
                        <span className="font-mono text-[10px] text-[#7A6B5A] opacity-60">{formatDate(log.timestamp)}</span>
                      </div>

                      {/* Type */}
                      <div className="flex items-center gap-1.5">
                        <span className="size-2 rounded-full shrink-0" style={{ background: typeConfig.color }} />
                        <span className="font-mono text-[11px]" style={{ color: typeConfig.color }}>
                          {typeConfig.label}
                        </span>
                      </div>

                      {/* Message */}
                      <div className="flex items-center gap-2 min-w-0">
                        {/* Level dot */}
                        <span
                          className="size-1.5 rounded-full shrink-0"
                          style={{ background: LEVEL_COLORS[log.level] }}
                        />
                        <span
                          className={cn(
                            'text-[13px] truncate',
                            log.level === 'error' ? 'text-[#B91C1C]' : 'text-[#EDE4D3]'
                          )}
                        >
                          {log.message}
                        </span>
                      </div>

                      {/* Source */}
                      <div className="truncate">
                        {log.source ? (
                          <span className="text-[11px] text-[#B8A88A] truncate block" title={log.source}>
                            {log.source}
                          </span>
                        ) : (
                          <span className="text-[11px] text-[#7A6B5A]">—</span>
                        )}
                      </div>

                      {/* Expand chevron */}
                      <div className="flex justify-center">
                        {log.details && (
                          <ChevronDown
                            className={cn(
                              'size-4 text-[#7A6B5A] transition-transform duration-300',
                              isExpanded && 'rotate-180'
                            )}
                          />
                        )}
                      </div>
                    </div>

                    {/* Expanded details */}
                    <AnimatePresence>
                      {isExpanded && log.details && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] as [number, number, number, number] }}
                          className="overflow-hidden"
                        >
                          <div
                            className="px-3 py-4 border-l-[3px]"
                            style={{
                              background: '#251F1840',
                              borderLeftColor: typeConfig.color,
                            }}
                          >
                            <div className="pl-4">
                              <div className="text-[11px] text-[#7A6B5A] font-mono mb-2 uppercase tracking-wider">
                                Details
                              </div>
                              <pre className="text-[12px] font-mono text-[#B8A88A] leading-relaxed overflow-x-auto whitespace-pre-wrap break-all">
                                {JSON.stringify(log.details, null, 2)}
                              </pre>
                              {log.source && (
                                <div className="mt-3 flex items-center gap-2">
                                  <span className="text-[11px] text-[#7A6B5A]">
                                    {relativeTime(log.timestamp)}
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
