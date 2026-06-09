import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  X,
  ArrowRight,
  Users,
  Lightbulb,
  Box,
  BookOpen,
  Building2,
  FileText,
  FlaskConical,
  Calendar,
  Tag,
  Link2,
  Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type EntityType =
  | 'person'
  | 'concept'
  | 'model'
  | 'book'
  | 'paper'
  | 'organization'
  | 'field'
  | 'event'
  | 'principle';

interface Entity {
  id: string;
  name: string;
  type: EntityType;
  description: string;
  mentions: number;
  connectedPages: string[];
  relatedEntities: string[];
  dateAdded: string;
}

/* ------------------------------------------------------------------ */
/*  Entity Type Config                                                 */
/* ------------------------------------------------------------------ */

const ENTITY_CONFIG: Record<
  EntityType,
  {
    label: string;
    color: string;
    bgColor: string;
    borderColor: string;
    icon: React.ReactNode;
  }
> = {
  person: {
    label: 'Person',
    color: 'text-[#C97B7B]',
    bgColor: 'bg-[#C97B7B]/15',
    borderColor: 'border-[#C97B7B]/30',
    icon: <Users className="w-3.5 h-3.5" />,
  },
  concept: {
    label: 'Concept',
    color: 'text-[#7D9B76]',
    bgColor: 'bg-[#7D9B76]/15',
    borderColor: 'border-[#7D9B76]/30',
    icon: <Lightbulb className="w-3.5 h-3.5" />,
  },
  model: {
    label: 'Model',
    color: 'text-[#D4A843]',
    bgColor: 'bg-[#D4A843]/15',
    borderColor: 'border-[#D4A843]/30',
    icon: <Box className="w-3.5 h-3.5" />,
  },
  book: {
    label: 'Book',
    color: 'text-[#B45309]',
    bgColor: 'bg-[#B45309]/15',
    borderColor: 'border-[#B45309]/30',
    icon: <BookOpen className="w-3.5 h-3.5" />,
  },
  paper: {
    label: 'Paper',
    color: 'text-[#7C6BFF]',
    bgColor: 'bg-[#7C6BFF]/15',
    borderColor: 'border-[#7C6BFF]/30',
    icon: <FileText className="w-3.5 h-3.5" />,
  },
  organization: {
    label: 'Organization',
    color: 'text-[#7B8FC9]',
    bgColor: 'bg-[#7B8FC9]/15',
    borderColor: 'border-[#7B8FC9]/30',
    icon: <Building2 className="w-3.5 h-3.5" />,
  },
  field: {
    label: 'Field',
    color: 'text-[#5A9B7D]',
    bgColor: 'bg-[#5A9B7D]/15',
    borderColor: 'border-[#5A9B7D]/30',
    icon: <Layers className="w-3.5 h-3.5" />,
  },
  event: {
    label: 'Event',
    color: 'text-[#C26A5C]',
    bgColor: 'bg-[#C26A5C]/15',
    borderColor: 'border-[#C26A5C]/30',
    icon: <Calendar className="w-3.5 h-3.5" />,
  },
  principle: {
    label: 'Principle',
    color: 'text-[#B85C3E]',
    bgColor: 'bg-[#B85C3E]/15',
    borderColor: 'border-[#B85C3E]/30',
    icon: <FlaskConical className="w-3.5 h-3.5" />,
  },
};

/* ------------------------------------------------------------------ */
/*  Mock Data                                                          */
/* ------------------------------------------------------------------ */

const MOCK_ENTITIES: Entity[] = [
  {
    id: 'e1',
    name: 'Charlie Munger',
    type: 'person',
    description: 'American businessman, investor, and philanthropist. Vice chairman of Berkshire Hathaway and a lifelong proponent of multidisciplinary mental models for better decision-making.',
    mentions: 47,
    connectedPages: ['Mental Models', 'Lollapalooza Effect', 'Inversion Principle', 'Berkshire Hathaway'],
    relatedEntities: ['Warren Buffett', 'Berkshire Hathaway', 'Poor Charlie\'s Almanack'],
    dateAdded: '2023-11-01',
  },
  {
    id: 'e2',
    name: 'Compound Interest',
    type: 'concept',
    description: 'The addition of interest to the principal sum of a loan or deposit, or in other words, interest on interest. One of the most powerful forces in finance and life.',
    mentions: 32,
    connectedPages: ['Finance Basics', 'Mental Models', 'Warren Buffett Investment Strategy'],
    relatedEntities: ['Warren Buffett', 'Exponential Growth', 'Time Value of Money'],
    dateAdded: '2023-11-05',
  },
  {
    id: 'e3',
    name: 'GPT-4',
    type: 'model',
    description: 'A large multimodal language model developed by OpenAI. It exhibits human-level performance on various professional and academic benchmarks.',
    mentions: 56,
    connectedPages: ['LLM Architecture', 'Transformer Models', 'AI Capabilities', 'OpenAI'],
    relatedEntities: ['OpenAI', 'Transformer', 'Attention Mechanism'],
    dateAdded: '2023-11-10',
  },
  {
    id: 'e4',
    name: 'Poor Charlie\'s Almanack',
    type: 'book',
    description: 'A curated collection of Charlie Munger\'s speeches, essays, and wisdom compiled by Peter Kaufman. The definitive guide to Munger\'s multidisciplinary approach to thinking.',
    mentions: 28,
    connectedPages: ['Charlie Munger', 'Mental Models', 'Inversion Principle'],
    relatedEntities: ['Charlie Munger', 'Peter Kaufman', 'Berkshire Hathaway'],
    dateAdded: '2023-11-12',
  },
  {
    id: 'e5',
    name: 'OpenAI',
    type: 'organization',
    description: 'An artificial intelligence research and deployment company dedicated to ensuring that artificial general intelligence benefits all of humanity. Founded in 2015.',
    mentions: 41,
    connectedPages: ['GPT-4', 'LLM Architecture', 'AI Safety', 'ChatGPT'],
    relatedEntities: ['GPT-4', 'Sam Altman', 'Deep Learning'],
    dateAdded: '2023-11-15',
  },
  {
    id: 'e6',
    name: 'Attention Is All You Need',
    type: 'paper',
    description: 'The seminal 2017 paper by Vaswani et al. that introduced the Transformer architecture, revolutionizing natural language processing and forming the basis for modern LLMs.',
    mentions: 38,
    connectedPages: ['Transformer Models', 'LLM Architecture', 'Neural Networks'],
    relatedEntities: ['Transformer', 'GPT-4', 'BERT'],
    dateAdded: '2023-11-18',
  },
  {
    id: 'e7',
    name: 'First Principles Thinking',
    type: 'principle',
    description: 'A reasoning approach that breaks down complex problems into their fundamental truths and builds up solutions from the ground up, avoiding analogy-based thinking.',
    mentions: 24,
    connectedPages: ['Mental Models', 'Elon Musk', 'Problem Solving'],
    relatedEntities: ['Elon Musk', 'Mental Models', 'Reasoning'],
    dateAdded: '2023-11-20',
  },
  {
    id: 'e8',
    name: 'Warren Buffett',
    type: 'person',
    description: 'American business magnate, investor, and philanthropist. Chairman and CEO of Berkshire Hathaway, widely considered one of the most successful investors of all time.',
    mentions: 35,
    connectedPages: ['Value Investing', 'Berkshire Hathaway', 'Charlie Munger'],
    relatedEntities: ['Charlie Munger', 'Berkshire Hathaway', 'Value Investing'],
    dateAdded: '2023-11-22',
  },
  {
    id: 'e9',
    name: 'Transformer Architecture',
    type: 'concept',
    description: 'A deep learning architecture based on self-attention mechanisms that has become the dominant approach for natural language processing and is increasingly used in computer vision.',
    mentions: 43,
    connectedPages: ['LLM Architecture', 'Attention Is All You Need', 'GPT-4', 'BERT'],
    relatedEntities: ['GPT-4', 'BERT', 'Attention Mechanism'],
    dateAdded: '2023-11-25',
  },
  {
    id: 'e10',
    name: 'Machine Learning',
    type: 'field',
    description: 'A subfield of artificial intelligence that gives computers the ability to learn without being explicitly programmed. Encompasses supervised, unsupervised, and reinforcement learning.',
    mentions: 62,
    connectedPages: ['Neural Networks', 'Deep Learning', 'Supervised Learning'],
    relatedEntities: ['Deep Learning', 'Neural Networks', 'AI'],
    dateAdded: '2023-12-01',
  },
  {
    id: 'e11',
    name: 'Attention Mechanism',
    type: 'concept',
    description: 'A technique in neural networks that allows the model to focus on different parts of the input sequence when producing each part of the output, enabling better handling of long-range dependencies.',
    mentions: 29,
    connectedPages: ['Transformer Models', 'Neural Networks', 'LLM Architecture'],
    relatedEntities: ['Transformer', 'GPT-4', 'Seq2Seq Models'],
    dateAdded: '2023-12-05',
  },
  {
    id: 'e12',
    name: 'Inversion Principle',
    type: 'principle',
    description: 'A mental model that involves approaching problems backwards. Instead of asking how to succeed, ask how to fail, then systematically avoid those things. One of Munger\'s favorites.',
    mentions: 19,
    connectedPages: ['Mental Models', 'Charlie Munger', 'Problem Solving'],
    relatedEntities: ['Charlie Munger', 'First Principles Thinking', 'Mental Models'],
    dateAdded: '2023-12-10',
  },
  {
    id: 'e13',
    name: 'BERT',
    type: 'model',
    description: 'Bidirectional Encoder Representations from Transformers. A transformer-based machine learning technique for natural language processing pre-training developed by Google.',
    mentions: 22,
    connectedPages: ['NLP Models', 'Transformer Models', 'Google AI'],
    relatedEntities: ['Google', 'Transformer', 'NLP'],
    dateAdded: '2023-12-12',
  },
  {
    id: 'e14',
    name: 'Deep Learning',
    type: 'field',
    description: 'A subset of machine learning based on artificial neural networks with multiple layers. It has driven breakthroughs in computer vision, NLP, speech recognition, and game playing.',
    mentions: 51,
    connectedPages: ['Neural Networks', 'Machine Learning', 'AI Fundamentals'],
    relatedEntities: ['Neural Networks', 'Machine Learning', 'Backpropagation'],
    dateAdded: '2023-12-15',
  },
  {
    id: 'e15',
    name: 'Berkshire Hathaway',
    type: 'organization',
    description: 'A multinational conglomerate holding company headquartered in Omaha, Nebraska. Led by Warren Buffett and Charlie Munger, it is known for its long-term value investment strategy.',
    mentions: 26,
    connectedPages: ['Warren Buffett', 'Value Investing', 'Charlie Munger'],
    relatedEntities: ['Warren Buffett', 'Charlie Munger', 'Value Investing'],
    dateAdded: '2023-12-18',
  },
  {
    id: 'e16',
    name: 'The Psychology of Human Misjudgment',
    type: 'event',
    description: 'Charlie Munger\'s famous 1995 speech at Harvard on the 24 standard causes of human misjudgment. Widely regarded as one of the most important talks on human psychology and decision-making.',
    mentions: 15,
    connectedPages: ['Charlie Munger', 'Cognitive Bias', 'Mental Models'],
    relatedEntities: ['Charlie Munger', 'Cognitive Bias', 'Behavioral Economics'],
    dateAdded: '2023-12-20',
  },
];

const ALL_TYPES: EntityType[] = [
  'person',
  'concept',
  'model',
  'book',
  'paper',
  'organization',
  'field',
  'event',
  'principle',
];

type SortOption = 'az' | 'mentions' | 'recent';

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function EntitiesPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<EntityType | 'all'>('all');
  const [sortBy, setSortBy] = useState<SortOption>('az');
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);

  /* filtered + sorted entities */
  const filteredEntities = useMemo(() => {
    let list = [...MOCK_ENTITIES];

    /* search */
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (e) =>
          e.name.toLowerCase().includes(q) ||
          e.description.toLowerCase().includes(q)
      );
    }

    /* type filter */
    if (selectedType !== 'all') {
      list = list.filter((e) => e.type === selectedType);
    }

    /* sort */
    if (sortBy === 'az') {
      list.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortBy === 'mentions') {
      list.sort((a, b) => b.mentions - a.mentions);
    } else if (sortBy === 'recent') {
      list.sort((a, b) => new Date(b.dateAdded).getTime() - new Date(a.dateAdded).getTime());
    }

    return list;
  }, [searchQuery, selectedType, sortBy]);

  /* ---------------------------------------------------------------- */
  /*  Render                                                             */
  /* ---------------------------------------------------------------- */

  return (
    <div className="min-h-full flex flex-col">
      {/* ====== PAGE HEADER ====== */}
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
        className="px-6 lg:px-8 pt-8 pb-4"
      >
        <div className="flex items-center gap-3 mb-2">
          <motion.h1
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
            className="text-display-lg font-display text-text-primary"
          >
            Entities
          </motion.h1>
          <motion.span
            initial={{ scale: 0.85, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.3, ease: [0.34, 1.56, 0.64, 1] as [number, number, number, number], delay: 0.2 }}
            className="px-2.5 py-1 rounded-full bg-amber-900 text-amber-300 text-mono-sm font-medium"
          >
            {MOCK_ENTITIES.length.toLocaleString()}
          </motion.span>
        </div>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.35, duration: 0.4 }}
          className="text-body-md text-text-secondary"
        >
          People, concepts, models, and more extracted from your sources
        </motion.p>
      </motion.section>

      {/* ====== FILTER BAR ====== */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.2 }}
        className="sticky top-0 z-20 px-6 lg:px-8 py-3 bg-bg-void/80 backdrop-blur-md border-b border-amber-800/10 flex flex-col sm:flex-row items-start sm:items-center gap-3"
      >
        {/* Search */}
        <div className="relative flex-1 max-w-[360px] w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search entities..."
            className={cn(
              'w-full h-9 pl-9 pr-8 rounded-md bg-bg-input border text-body-md text-text-primary',
              'border-amber-800/25 focus:border-amber-500 focus:shadow-glow-amber outline-none transition-all duration-200',
              'placeholder:text-text-muted'
            )}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded text-text-muted hover:text-text-primary"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Type pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <TypePill
            label="All"
            count={MOCK_ENTITIES.length}
            active={selectedType === 'all'}
            onClick={() => setSelectedType('all')}
          />
          {ALL_TYPES.map((t) => (
            <TypePill
              key={t}
              label={ENTITY_CONFIG[t].label}
              count={MOCK_ENTITIES.filter((e) => e.type === t).length}
              active={selectedType === t}
              color={ENTITY_CONFIG[t].color}
              bgColor={ENTITY_CONFIG[t].bgColor}
              borderColor={ENTITY_CONFIG[t].borderColor}
              onClick={() => setSelectedType(t)}
            />
          ))}
        </div>

        {/* Sort dropdown */}
        <div className="ml-auto">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
            className={cn(
              'h-9 px-3 pr-8 rounded-md bg-bg-input border border-amber-800/25 text-body-sm text-text-primary',
              'focus:border-amber-500 focus:shadow-glow-amber outline-none transition-all duration-200',
              'appearance-none cursor-pointer'
            )}
            style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%237A6B5A' stroke-width='2'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E")`,
              backgroundRepeat: 'no-repeat',
              backgroundPosition: 'right 8px center',
            }}
          >
            <option value="az">Name A-Z</option>
            <option value="mentions">Most Mentions</option>
            <option value="recent">Recently Added</option>
          </select>
        </div>
      </motion.div>

      {/* ====== ENTITY GRID ====== */}
      <div className="flex-1 px-6 lg:px-8 py-6">
        {filteredEntities.length === 0 ? (
          /* EMPTY STATE */
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center py-16 text-center"
          >
            <motion.img
              src="/empty-state-search.jpg"
              alt="No entities"
              className="w-56 h-auto rounded-xl mb-6"
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            />
            <p className="text-heading-lg text-text-primary mb-2">No entities found</p>
            <p className="text-body-md text-text-secondary mb-4">
              Try adjusting your filters or search terms
            </p>
            <button
              onClick={() => {
                setSearchQuery('');
                setSelectedType('all');
              }}
              className="px-4 py-2 rounded-md bg-bg-elevated border border-amber-700 text-body-md text-text-primary hover:bg-bg-hover hover:border-amber-500 transition-all duration-200"
            >
              Clear all filters
            </button>
          </motion.div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            <AnimatePresence mode="popLayout">
              {filteredEntities.map((entity, i) => (
                <EntityCard
                  key={entity.id}
                  entity={entity}
                  index={i}
                  onClick={() => setSelectedEntity(entity)}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* ====== ENTITY DETAIL MODAL ====== */}
      <AnimatePresence>
        {selectedEntity && (
          <EntityDetailModal
            entity={selectedEntity}
            onClose={() => setSelectedEntity(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function TypePill({
  label,
  count,
  active,
  onClick,
  color,
  bgColor,
  borderColor,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
  color?: string;
  bgColor?: string;
  borderColor?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-1.5 px-3 py-1 rounded-full text-body-sm transition-all duration-200 whitespace-nowrap',
        active
          ? cn(bgColor || 'bg-bg-active', color || 'text-amber-300', borderColor || 'border-amber-700/40', 'border')
          : 'bg-bg-hover text-text-secondary hover:bg-bg-active hover:text-text-primary'
      )}
    >
      {label}
      <span className="text-mono-sm opacity-70">{count}</span>
    </button>
  );
}

function EntityCard({
  entity,
  index,
  onClick,
}: {
  entity: Entity;
  index: number;
  onClick: () => void;
}) {
  const config = ENTITY_CONFIG[entity.type];
  const [hovered, setHovered] = useState(false);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{
        delay: index * 0.05,
        duration: 0.4,
        ease: [0.23, 1, 0.32, 1] as [number, number, number, number],
        layout: { duration: 0.3 },
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={onClick}
      className={cn(
        'group relative bg-bg-surface border border-amber-800/12 rounded-lg p-4 cursor-pointer',
        'shadow-md shadow-inner-card min-h-[160px] flex flex-col',
        'hover:-translate-y-[3px] hover:shadow-lg hover:border-amber-600/40',
        'transition-all duration-200'
      )}
    >
      {/* Top row: type badge + mention count */}
      <div className="flex items-start justify-between mb-3">
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-mono-sm border',
            config.bgColor,
            config.color,
            config.borderColor,
            hovered && 'opacity-100',
            'opacity-80 transition-opacity duration-200'
          )}
        >
          {config.icon}
          {config.label}
        </span>
        <span className="text-mono-sm text-text-muted">{entity.mentions} mentions</span>
      </div>

      {/* Entity name */}
      <h3 className="text-heading-md text-text-primary mb-2 line-clamp-2">{entity.name}</h3>

      {/* Description */}
      <p className="text-body-sm text-text-secondary line-clamp-3 mb-3 flex-1">{entity.description}</p>

      {/* Connected pages preview */}
      <div className="pt-2 border-t border-amber-800/8 flex flex-wrap gap-1">
        {entity.connectedPages.slice(0, 3).map((page) => (
          <span
            key={page}
            className="px-1.5 py-0.5 rounded-sm bg-bg-hover text-mono-sm text-text-muted hover:text-amber-300 hover:bg-bg-active transition-colors"
          >
            {page}
          </span>
        ))}
        {entity.connectedPages.length > 3 && (
          <span className="px-1.5 py-0.5 text-mono-sm text-text-muted">
            +{entity.connectedPages.length - 3}
          </span>
        )}
      </div>

      {/* Hover overlay */}
      <AnimatePresence>
        {hovered && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="absolute inset-0 bg-bg-surface/90 rounded-lg flex items-center justify-center"
          >
            <span className="flex items-center gap-1.5 text-amber-300 text-body-md font-medium">
              View Details
              <ArrowRight className="w-4 h-4" />
            </span>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Entity Detail Modal                                                */
/* ------------------------------------------------------------------ */

function EntityDetailModal({ entity, onClose }: { entity: Entity; onClose: () => void }) {
  const config = ENTITY_CONFIG[entity.type];

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[5vh] px-4">
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
      />

      {/* Modal */}
      <motion.div
        initial={{ scale: 0.92, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.92, opacity: 0 }}
        transition={{ duration: 0.4, ease: [0.34, 1.56, 0.64, 1] as [number, number, number, number] }}
        className="relative w-full max-w-[600px] max-h-[85vh] overflow-y-auto bg-bg-elevated rounded-xl shadow-xl border border-amber-800/15"
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-bg-hover transition-colors z-10"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="p-6">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <span
              className={cn(
                'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-body-sm border mb-3',
                config.bgColor,
                config.color,
                config.borderColor
              )}
            >
              {config.icon}
              {config.label}
            </span>
            <h2 className="text-display-md font-display text-text-primary mb-3">{entity.name}</h2>
            <p className="text-body-lg text-text-secondary leading-relaxed">{entity.description}</p>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="grid grid-cols-3 gap-4 mt-6 py-4 border-y border-amber-800/10"
          >
            <div className="text-center">
              <p className="text-heading-sm text-text-primary">{entity.mentions}</p>
              <p className="text-body-sm text-text-muted">Mentions</p>
            </div>
            <div className="text-center">
              <p className="text-heading-sm text-text-primary">{entity.connectedPages.length}</p>
              <p className="text-body-sm text-text-muted">Connected Pages</p>
            </div>
            <div className="text-center">
              <p className="text-heading-sm text-text-primary">{entity.relatedEntities.length}</p>
              <p className="text-body-sm text-text-muted">Related</p>
            </div>
          </motion.div>

          {/* Connected Pages */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mt-5"
          >
            <h3 className="flex items-center gap-2 text-heading-sm text-text-primary mb-3">
              <Link2 className="w-4 h-4 text-amber-400" />
              Appears in
            </h3>
            <div className="space-y-1.5">
              {entity.connectedPages.map((page) => (
                <div
                  key={page}
                  className="flex items-center gap-2 px-3 py-2 rounded-md bg-bg-hover text-body-sm text-text-secondary hover:text-amber-300 hover:bg-bg-active transition-colors cursor-pointer"
                >
                  <BookOpen className="w-3.5 h-3.5 text-text-muted" />
                  {page}
                </div>
              ))}
            </div>
          </motion.div>

          {/* Related Entities */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-5"
          >
            <h3 className="flex items-center gap-2 text-heading-sm text-text-primary mb-3">
              <Tag className="w-4 h-4 text-amber-400" />
              Related Entities
            </h3>
            <div className="flex flex-wrap gap-2">
              {entity.relatedEntities.map((rel) => (
                <span
                  key={rel}
                  className="px-3 py-1.5 rounded-full bg-bg-hover text-body-sm text-text-secondary hover:text-amber-300 hover:bg-bg-active transition-colors cursor-pointer"
                >
                  {rel}
                </span>
              ))}
            </div>
          </motion.div>

          {/* Footer */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="mt-6 pt-4 border-t border-amber-800/10 flex items-center justify-between"
          >
            <span className="text-mono-sm text-text-muted">
              Added {entity.dateAdded}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-md text-body-md text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-all duration-200"
              >
                Close
              </button>
              <button className="flex items-center gap-1.5 px-4 py-2 rounded-md bg-amber-500 text-text-inverse text-body-md font-medium hover:bg-amber-400 hover:shadow-glow-amber transition-all duration-200">
                View full page
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}
