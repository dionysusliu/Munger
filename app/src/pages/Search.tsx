import { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  X,
  BookOpen,
  Tag,
  FileText,
  Lightbulb,
  Filter,
  ChevronDown,
  ChevronUp,
  Clock,
  ArrowRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type ResultType = 'wiki' | 'source' | 'entity' | 'concept';
type EntitySubType = 'person' | 'concept' | 'model' | 'book' | 'organization';
type DateRange = '7d' | '30d' | 'all';

interface SearchResult {
  id: string;
  title: string;
  snippet: string;
  type: ResultType;
  entitySubType?: EntitySubType;
  source: string;
  date: string;
  links: number;
}

/* ------------------------------------------------------------------ */
/*  Mock Data                                                          */
/* ------------------------------------------------------------------ */

const MOCK_RESULTS: SearchResult[] = [
  {
    id: '1',
    title: 'Neural Network Architectures',
    snippet: 'Neural networks are a subset of machine learning models inspired by the structure of the human brain. They consist of layers of interconnected nodes that process information.',
    type: 'wiki',
    source: 'Neural_Networks.md',
    date: '2024-01-15',
    links: 24,
  },
  {
    id: '2',
    title: 'Compound Interest',
    snippet: 'Compound interest is the addition of interest to the principal sum of a loan or deposit. It is the result of reinvesting interest, rather than paying it out.',
    type: 'entity',
    entitySubType: 'concept',
    source: 'Finance_Basics.md',
    date: '2024-01-10',
    links: 18,
  },
  {
    id: '3',
    title: 'Charlie Munger',
    snippet: 'Charlie Munger was an American businessman, investor, and philanthropist. He was vice chairman of Berkshire Hathaway and a proponent of multidisciplinary thinking.',
    type: 'entity',
    entitySubType: 'person',
    source: 'People.md',
    date: '2024-01-08',
    links: 42,
  },
  {
    id: '4',
    title: 'First Principles Thinking',
    snippet: 'First principles thinking is the practice of actively questioning every assumption you think you know about a given problem or scenario.',
    type: 'concept',
    source: 'Mental_Models.md',
    date: '2024-01-05',
    links: 31,
  },
  {
    id: '5',
    title: 'Source: The Psychology of Human Misjudgment',
    snippet: 'A transcript of Charlie Munger\'s famous speech on the 24 standard causes of human misjudgment. Essential reading for understanding cognitive biases.',
    type: 'source',
    source: 'Psychology_Misjudgment.pdf',
    date: '2024-01-03',
    links: 15,
  },
  {
    id: '6',
    title: 'Transformers (Attention Is All You Need)',
    snippet: 'The Transformer is a deep learning architecture introduced in 2017 that relies on self-attention mechanisms. It has become the foundation for modern LLMs.',
    type: 'wiki',
    source: 'Attention_Is_All_You_Need.md',
    date: '2023-12-28',
    links: 36,
  },
  {
    id: '7',
    title: 'OpenAI',
    snippet: 'OpenAI is an artificial intelligence research organization. It was founded in 2015 with the goal of ensuring that artificial general intelligence benefits all of humanity.',
    type: 'entity',
    entitySubType: 'organization',
    source: 'Companies.md',
    date: '2023-12-20',
    links: 29,
  },
  {
    id: '8',
    title: 'Poor Charlie\'s Almanack',
    snippet: 'Poor Charlie\'s Almanack is a book compiled by Peter Kaufman about Charlie Munger\'s wisdom, wit, and investment philosophy. It covers his speeches and essays.',
    type: 'entity',
    entitySubType: 'book',
    source: 'Books.md',
    date: '2023-12-15',
    links: 22,
  },
  {
    id: '9',
    title: 'Mental Models: The Best Way to Make Intelligent Decisions',
    snippet: 'A mental model is an explanation of how something works. It is a concept, framework, or worldview that you carry around in your mind to help you interpret the world.',
    type: 'wiki',
    source: 'Mental_Models_Guide.md',
    date: '2023-12-10',
    links: 45,
  },
  {
    id: '10',
    title: 'Inversion Principle',
    snippet: 'Inversion is a powerful mental model that involves thinking backwards. Instead of asking how to do something, ask how to fail at it, then avoid those things.',
    type: 'concept',
    source: 'Mental_Models.md',
    date: '2023-12-05',
    links: 19,
  },
  {
    id: '11',
    title: 'GPT-4 Architecture',
    snippet: 'GPT-4 is a large multimodal model developed by OpenAI. It accepts image and text inputs and produces text outputs, demonstrating human-level performance on various benchmarks.',
    type: 'entity',
    entitySubType: 'model',
    source: 'AI_Models.md',
    date: '2023-11-28',
    links: 53,
  },
  {
    id: '12',
    title: 'Source: Thinking, Fast and Slow - Summary Notes',
    snippet: 'Comprehensive notes on Daniel Kahneman\'s seminal work on behavioral economics. Covers System 1 and System 2 thinking, cognitive biases, and decision making.',
    type: 'source',
    source: 'Thinking_Fast_Slow_Notes.md',
    date: '2023-11-20',
    links: 27,
  },
];

const SUGGESTIONS = [
  'neural networks',
  'compound interest',
  'mental models',
  'first principles',
  'attention mechanism',
  'cognitive bias',
];

const ENTITY_TYPE_OPTIONS: { label: string; value: EntitySubType }[] = [
  { label: 'Person', value: 'person' },
  { label: 'Concept', value: 'concept' },
  { label: 'Model', value: 'model' },
  { label: 'Book', value: 'book' },
  { label: 'Organization', value: 'organization' },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const resultTypeConfig: Record<ResultType, { icon: React.ReactNode; label: string; color: string }> = {
  wiki: { icon: <BookOpen className="w-4 h-4" />, label: 'Wiki Page', color: 'text-amber-400' },
  entity: { icon: <Tag className="w-4 h-4" />, label: 'Entity', color: 'text-info' },
  source: { icon: <FileText className="w-4 h-4" />, label: 'Source', color: 'text-warning' },
  concept: { icon: <Lightbulb className="w-4 h-4" />, label: 'Concept', color: 'text-success' },
};

function highlightMatch(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;
  const parts = text.split(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
  return parts.map((part, i) =>
    part.toLowerCase() === query.toLowerCase() ? (
      <mark key={i} className="bg-amber-900/60 text-amber-200 rounded-sm px-0.5">
        {part}
      </mark>
    ) : (
      part
    )
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [resultTypeFilter, setResultTypeFilter] = useState<ResultType | 'all'>('all');
  const [entityTypeFilters, setEntityTypeFilters] = useState<Set<EntitySubType>>(new Set());
  const [dateRange, setDateRange] = useState<DateRange>('all');
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const [sortBy, setSortBy] = useState<'relevance' | 'newest' | 'az'>('relevance');

  /* debounce query */
  const handleQueryChange = useCallback((val: string) => {
    setQuery(val);
    const t = setTimeout(() => setDebouncedQuery(val), 200);
    return () => clearTimeout(t);
  }, []);

  /* derived filtered results */
  const filteredResults = useMemo(() => {
    let results = [...MOCK_RESULTS];

    /* text filter */
    if (debouncedQuery.trim()) {
      const q = debouncedQuery.toLowerCase();
      results = results.filter(
        (r) =>
          r.title.toLowerCase().includes(q) ||
          r.snippet.toLowerCase().includes(q) ||
          r.source.toLowerCase().includes(q)
      );
    }

    /* result type filter */
    if (resultTypeFilter !== 'all') {
      results = results.filter((r) => r.type === resultTypeFilter);
    }

    /* entity sub-type filter (only when Entities are shown) */
    if ((resultTypeFilter === 'all' || resultTypeFilter === 'entity') && entityTypeFilters.size > 0) {
      results = results.filter(
        (r) => r.type === 'entity' && r.entitySubType && entityTypeFilters.has(r.entitySubType)
      );
    }

    /* date range filter */
    if (dateRange !== 'all') {
      const now = new Date();
      const days = dateRange === '7d' ? 7 : 30;
      const cutoff = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
      results = results.filter((r) => new Date(r.date) >= cutoff);
    }

    /* sort */
    if (sortBy === 'newest') {
      results.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
    } else if (sortBy === 'az') {
      results.sort((a, b) => a.title.localeCompare(b.title));
    }

    return results;
  }, [debouncedQuery, resultTypeFilter, entityTypeFilters, dateRange, sortBy]);

  const isSearching = debouncedQuery.trim().length > 0 || resultTypeFilter !== 'all' || entityTypeFilters.size > 0 || dateRange !== 'all';

  const handleSuggestionClick = (s: string) => {
    setQuery(s);
    setDebouncedQuery(s);
  };

  const toggleEntityType = (t: EntitySubType) => {
    setEntityTypeFilters((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  };

  const clearAllFilters = () => {
    setResultTypeFilter('all');
    setEntityTypeFilters(new Set());
    setDateRange('all');
    setQuery('');
    setDebouncedQuery('');
  };

  /* ---------------------------------------------------------------- */
  /*  Render                                                             */
  /* ---------------------------------------------------------------- */

  return (
    <div className="min-h-full flex flex-col">
      {/* ====== HERO ====== */}
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
        className="relative border-b border-amber-800/12 bg-bg-surface"
        style={{
          backgroundImage: 'radial-gradient(ellipse at 30% 20%, rgba(251,191,36,0.08) 0%, transparent 60%)',
        }}
      >
        <div className="px-6 py-10 flex flex-col items-center text-center">
          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
            className="text-display-lg font-display text-text-primary mb-6"
          >
            Search
          </motion.h1>

          {/* Search bar */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, ease: [0.34, 1.56, 0.64, 1] as [number, number, number, number], delay: 0.2 }}
            className="w-full max-w-3xl relative"
          >
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-amber-400 pointer-events-none" />
              <input
                type="text"
                value={query}
                onChange={(e) => handleQueryChange(e.target.value)}
                placeholder="Search across wiki pages, sources, and entities..."
                className={cn(
                  'w-full h-[52px] pl-12 pr-10 rounded-xl bg-bg-input border text-text-primary body-lg',
                  'border-amber-800/25 focus:border-amber-500 focus:shadow-glow-amber outline-none transition-all duration-200',
                  'placeholder:text-text-muted'
                )}
              />
              {query && (
                <button
                  onClick={() => { setQuery(''); setDebouncedQuery(''); }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-md text-text-muted hover:text-text-primary hover:bg-bg-hover transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
            <p className="mt-2 text-body-sm text-text-muted">
              Press Enter to search or ⌘K for quick commands
            </p>
          </motion.div>

          {/* Suggestions */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.3 }}
            className="mt-4 flex flex-wrap justify-center gap-2"
          >
            {SUGGESTIONS.map((s, i) => (
              <motion.button
                key={s}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 + i * 0.06, duration: 0.3 }}
                onClick={() => handleSuggestionClick(s)}
                className={cn(
                  'px-3 py-1.5 rounded-full text-body-sm text-text-secondary bg-bg-hover',
                  'hover:text-amber-300 hover:bg-bg-active transition-all duration-200'
                )}
              >
                {s}
              </motion.button>
            ))}
          </motion.div>
        </div>
      </motion.section>

      {/* ====== RESULTS HEADER ====== */}
      <AnimatePresence>
        {isSearching && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3 }}
            className="sticky top-0 z-20 px-6 py-3 bg-bg-void/80 backdrop-blur-md border-b border-amber-800/10 flex items-center justify-between"
          >
            <p className="text-body-md text-text-primary">
              Found <span className="text-amber-300 font-medium">{filteredResults.length}</span> results
              {debouncedQuery && (
                <>
                  {' '}for &quot;<span className="bg-amber-900/60 text-amber-200 rounded-sm px-1">{debouncedQuery}</span>&quot;
                </>
              )}
            </p>
            <div className="flex items-center gap-1">
              {(['relevance', 'newest', 'az'] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setSortBy(s)}
                  className={cn(
                    'px-3 py-1 rounded-md text-body-sm capitalize transition-all duration-200',
                    sortBy === s
                      ? 'text-amber-400 font-medium'
                      : 'text-text-muted hover:text-text-secondary'
                  )}
                >
                  {s === 'az' ? 'A-Z' : s}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ====== MAIN: Results + Filters ====== */}
      <div className="flex flex-1">
        {/* --- Mobile filter toggle --- */}
        <div className="lg:hidden px-4 pt-4">
          <button
            onClick={() => setMobileFiltersOpen(!mobileFiltersOpen)}
            className="flex items-center gap-2 px-3 py-2 rounded-md bg-bg-surface border border-amber-800/15 text-body-sm text-text-secondary"
          >
            <Filter className="w-4 h-4" />
            Filters
            {(resultTypeFilter !== 'all' || entityTypeFilters.size > 0 || dateRange !== 'all') && (
              <span className="w-2 h-2 rounded-full bg-amber-400" />
            )}
          </button>
        </div>

        <div className="flex flex-1 px-4 lg:px-6 py-4 gap-6">
          {/* --- Results List --- */}
          <div className="flex-1 min-w-0">
            <AnimatePresence mode="wait">
              {/* EMPTY STATE — no query */}
              {!isSearching ? (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col items-center justify-center py-16 text-center"
                >
                  <motion.img
                    src="/empty-state-search.jpg"
                    alt="Search"
                    className="w-60 h-auto rounded-xl mb-6"
                    animate={{ y: [0, -6, 0] }}
                    transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
                  />
                  <p className="text-heading-lg text-text-primary mb-2">
                    Enter a search query to explore your knowledge base
                  </p>
                  <p className="text-body-md text-text-secondary max-w-md">
                    Search across wiki pages, sources, and entities to find exactly what you&apos;re looking for.
                  </p>
                </motion.div>
              ) : filteredResults.length === 0 ? (
                /* EMPTY STATE — no results */
                <motion.div
                  key="no-results"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col items-center justify-center py-16 text-center"
                >
                  <motion.img
                    src="/empty-state-search.jpg"
                    alt="No results"
                    className="w-60 h-auto rounded-xl mb-6"
                    animate={{ y: [0, -6, 0] }}
                    transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
                  />
                  <p className="text-heading-lg text-text-primary mb-2">
                    No results found{debouncedQuery && ` for "${debouncedQuery}"`}
                  </p>
                  <p className="text-body-md text-text-secondary mb-4">
                    Try different keywords, check your spelling, or adjust your filters.
                  </p>
                  <button
                    onClick={clearAllFilters}
                    className="px-4 py-2 rounded-md bg-bg-elevated border border-amber-700 text-body-md text-text-primary hover:bg-bg-hover hover:border-amber-500 transition-all duration-200"
                  >
                    Clear search
                  </button>
                </motion.div>
              ) : (
                /* RESULTS */
                <motion.div
                  key="results"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-0"
                >
                  {filteredResults.map((result, i) => {
                    const config = resultTypeConfig[result.type];
                    return (
                      <motion.div
                        key={result.id}
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{
                          delay: i * 0.04,
                          duration: 0.3,
                          ease: [0.4, 0, 0.2, 1] as [number, number, number, number],
                        }}
                        className={cn(
                          'group py-4 px-4 -mx-4 border-b border-amber-800/8 cursor-pointer transition-all duration-200',
                          'hover:bg-bg-hover border-l-0 hover:border-l-[3px] hover:border-l-amber-400'
                        )}
                      >
                        {/* Type indicator */}
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className={cn('flex items-center gap-1.5 text-body-sm', config.color)}>
                            {config.icon}
                            <span className="font-medium">{config.label}</span>
                          </span>
                          {result.entitySubType && (
                            <span className="text-mono-sm text-text-muted capitalize">
                              · {result.entitySubType}
                            </span>
                          )}
                        </div>

                        {/* Title */}
                        <h3 className="text-body-lg text-text-primary font-medium mb-1.5">
                          {highlightMatch(result.title, debouncedQuery)}
                        </h3>

                        {/* Snippet */}
                        <p className="text-body-sm text-text-secondary line-clamp-3 mb-2">
                          {highlightMatch(result.snippet, debouncedQuery)}
                        </p>

                        {/* Meta row */}
                        <div className="flex items-center gap-4 text-mono-sm text-text-muted">
                          <span>From: {result.source}</span>
                          <span className="flex items-center gap-1">
                            <ArrowRight className="w-3 h-3" />
                            {result.links} links
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {result.date}
                          </span>
                        </div>
                      </motion.div>
                    );
                  })}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* --- Filter Sidebar --- */}
          <AnimatePresence>
            {mobileFiltersOpen && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-40 bg-black/50 lg:hidden"
                onClick={() => setMobileFiltersOpen(false)}
              />
            )}
          </AnimatePresence>

          <motion.aside
            className={cn(
              'w-60 shrink-0 bg-bg-surface border border-amber-800/12 rounded-lg p-4 space-y-5',
              'lg:block lg:static lg:h-fit',
              mobileFiltersOpen
                ? 'fixed right-4 top-20 z-50 block shadow-xl'
                : 'hidden'
            )}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
          >
            {mobileFiltersOpen && (
              <button
                onClick={() => setMobileFiltersOpen(false)}
                className="absolute top-2 right-2 p-1 rounded-md text-text-muted hover:text-text-primary"
              >
                <X className="w-4 h-4" />
              </button>
            )}

            {/* Result Type */}
            <FilterGroup title="Result Type">
              <CheckboxItem
                label="All"
                checked={resultTypeFilter === 'all'}
                onChange={() => setResultTypeFilter('all')}
              />
              <CheckboxItem
                label="Wiki Pages"
                checked={resultTypeFilter === 'wiki'}
                onChange={() => setResultTypeFilter('wiki')}
              />
              <CheckboxItem
                label="Sources"
                checked={resultTypeFilter === 'source'}
                onChange={() => setResultTypeFilter('source')}
              />
              <CheckboxItem
                label="Entities"
                checked={resultTypeFilter === 'entity'}
                onChange={() => setResultTypeFilter('entity')}
              />
              <CheckboxItem
                label="Concepts"
                checked={resultTypeFilter === 'concept'}
                onChange={() => setResultTypeFilter('concept')}
              />
            </FilterGroup>

            {/* Entity Type (conditional) */}
            <AnimatePresence>
              {(resultTypeFilter === 'all' || resultTypeFilter === 'entity') && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <FilterGroup title="Entity Type">
                    {ENTITY_TYPE_OPTIONS.map((et) => (
                      <CheckboxItem
                        key={et.value}
                        label={et.label}
                        checked={entityTypeFilters.has(et.value)}
                        onChange={() => toggleEntityType(et.value)}
                      />
                    ))}
                  </FilterGroup>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Date Range */}
            <FilterGroup title="Date Range">
              <RadioItem
                label="Last 7 days"
                checked={dateRange === '7d'}
                onChange={() => setDateRange('7d')}
              />
              <RadioItem
                label="Last 30 days"
                checked={dateRange === '30d'}
                onChange={() => setDateRange('30d')}
              />
              <RadioItem
                label="All time"
                checked={dateRange === 'all'}
                onChange={() => setDateRange('all')}
              />
            </FilterGroup>

            {/* Clear filters */}
            {(resultTypeFilter !== 'all' || entityTypeFilters.size > 0 || dateRange !== 'all') && (
              <motion.button
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                onClick={() => {
                  setResultTypeFilter('all');
                  setEntityTypeFilters(new Set());
                  setDateRange('all');
                }}
                className="w-full py-2 text-body-sm text-text-secondary hover:text-text-primary hover:bg-bg-hover rounded-md transition-all duration-200"
              >
                Clear all filters
              </motion.button>
            )}
          </motion.aside>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function FilterGroup({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(true);
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full mb-2 text-heading-sm text-text-primary"
      >
        {title}
        {open ? <ChevronUp className="w-3.5 h-3.5 text-text-muted" /> : <ChevronDown className="w-3.5 h-3.5 text-text-muted" />}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="space-y-1.5 overflow-hidden"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function CheckboxItem({ label, checked, onChange }: { label: string; checked: boolean; onChange: () => void }) {
  return (
    <label className="flex items-center gap-2.5 cursor-pointer group py-1">
      <div
        className={cn(
          'w-4 h-4 rounded-sm border flex items-center justify-center transition-all duration-200',
          checked
            ? 'bg-amber-500 border-amber-500'
            : 'border-amber-700/40 group-hover:border-amber-600'
        )}
        onClick={onChange}
      >
        {checked && (
          <motion.svg
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.2, ease: [0.34, 1.56, 0.64, 1] as [number, number, number, number] }}
            className="w-3 h-3 text-text-inverse"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={3}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </motion.svg>
        )}
      </div>
      <span className="text-body-sm text-text-secondary group-hover:text-text-primary transition-colors">
        {label}
      </span>
    </label>
  );
}

function RadioItem({ label, checked, onChange }: { label: string; checked: boolean; onChange: () => void }) {
  return (
    <label className="flex items-center gap-2.5 cursor-pointer group py-1">
      <div
        className={cn(
          'w-4 h-4 rounded-full border flex items-center justify-center transition-all duration-200',
          checked
            ? 'border-amber-500'
            : 'border-amber-700/40 group-hover:border-amber-600'
        )}
        onClick={onChange}
      >
        {checked && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.2, ease: [0.34, 1.56, 0.64, 1] as [number, number, number, number] }}
            className="w-2 h-2 rounded-full bg-amber-500"
          />
        )}
      </div>
      <span className="text-body-sm text-text-secondary group-hover:text-text-primary transition-colors">
        {label}
      </span>
    </label>
  );
}
