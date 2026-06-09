import { useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import {
  ChevronDown,
  ChevronUp,
  Lightbulb,
  Target,
  BookOpen,
  Quote,
  Network,
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/* 12 Dimension Configuration                                           */
/* ------------------------------------------------------------------ */

interface DimensionConfig {
  number: number;
  name: string;
  chineseName: string;
  color: string;
  icon: string;
  description: string;
}

const DIMENSIONS: DimensionConfig[] = [
  { number: 1, name: 'Source', chineseName: '溯源', color: '#C26A5C', icon: 'source', description: 'Trace the origin and provenance of ideas' },
  { number: 2, name: 'Claim', chineseName: '断言', color: '#D4A843', icon: 'claim', description: 'Evaluate central claims and assertions' },
  { number: 3, name: 'Concept', chineseName: '概念', color: '#7D9B76', icon: 'concept', description: 'Define core concepts and their boundaries' },
  { number: 4, name: 'Model', chineseName: '模型', color: '#B87333', icon: 'model', description: 'Identify underlying mental models' },
  { number: 5, name: 'Mechanism', chineseName: '机制', color: '#5A9B7D', icon: 'mechanism', description: 'Understand the mechanisms at work' },
  { number: 6, name: 'Incentive', chineseName: '激励', color: '#6B7FA3', icon: 'incentive', description: 'Analyze incentives and motivations' },
  { number: 7, name: 'Psychology', chineseName: '心理', color: '#A0553D', icon: 'psychology', description: 'Recognize psychological factors and biases' },
  { number: 8, name: 'Dual-Track', chineseName: '双轨', color: '#C4963C', icon: 'dual-track', description: 'Consider both conscious and unconscious processes' },
  { number: 9, name: 'Counterargument', chineseName: '反驳', color: '#6B8E5A', icon: 'counterargument', description: 'Seek out opposing viewpoints' },
  { number: 10, name: 'Checklist', chineseName: '清单', color: '#C4902A', icon: 'checklist', description: 'Systematic verification of reasoning' },
  { number: 11, name: 'Case', chineseName: '案例', color: '#7A8B9A', icon: 'case', description: 'Reference historical cases and examples' },
  { number: 12, name: 'Decision', chineseName: '决策', color: '#B85C3E', icon: 'decision', description: 'Synthesize into actionable decisions' },
];

/* ------------------------------------------------------------------ */
/* Mock Analysis Data                                                   */
/* ------------------------------------------------------------------ */

interface DimensionAnalysis {
  dimension: number;
  confidence: number;
  insights: string[];
  analysis: string[];
  evidence: string[];
  keyThemes: string[];
}

const MOCK_ANALYSIS_DATA: DimensionAnalysis[] = [
  {
    dimension: 1,
    confidence: 92,
    insights: [
      'Charlie Munger developed his framework through decades of practical investing experience at Berkshire Hathaway',
      'The 12-dimension approach draws heavily from Benjamin Graham\'s value investing principles',
      'Munger\'s concept of "worldly wisdom" synthesizes multiple academic disciplines',
    ],
    analysis: [
      'Charlie Munger\'s mental model framework emerged from his partnership with Warren Buffett at Berkshire Hathaway, where they applied multidisciplinary thinking to investment decisions over five decades. The framework wasn\'t created in a vacuum—it was forged in the crucible of real capital allocation decisions involving billions of dollars.',
      'The intellectual lineage traces back to Benjamin Graham\'s "The Intelligent Investor," which introduced the margin of safety concept. However, Munger extended far beyond Graham, incorporating insights from psychology, physics, mathematics, and biology. His famous speech "The Psychology of Human Misjudgment" at Harvard in 1995 crystallized many of these ideas.',
      'The source material reveals that Munger\'s approach evolved through continuous learning—he reportedly spends 80% of his day reading. The framework represents a synthesis of his reading across history, biography, science, and philosophy, applied through the lens of practical business judgment.',
    ],
    evidence: [
      'We both (Charlie Munger and I) insist on a lot of time being available, almost every day, to just sit and think. That is very uncommon in American business. We do so much more thinking than others. — Warren Buffett',
      'The best thing a human being can do is to read a great book and try to live by it. — Charlie Munger',
    ],
    keyThemes: ['Berkshire Hathaway', 'Value Investing', 'Worldly Wisdom'],
  },
  {
    dimension: 2,
    confidence: 88,
    insights: [
      'Munger claims that multidisciplinary thinking is essential for avoiding catastrophic errors',
      'The central assertion: single-discipline expertise creates dangerous blind spots',
      'Inversion—avoiding stupidity—is claimed to be more reliable than pursuing brilliance',
    ],
    analysis: [
      'Munger\'s primary claim is that the human mind operates with a "man-with-a-hammer" tendency—when you have only one tool (one discipline), every problem looks like a nail. He argues this is not merely suboptimal but actively dangerous in complex decision-making environments.',
      'The framework claims that by assembling a "latticework of mental models" from diverse disciplines, one can develop what he calls "worldly wisdom"—the ability to see problems from multiple angles simultaneously. This isn\'t about being a polymath in the traditional sense, but about having enough familiarity with major ideas across fields to recognize their applicability.',
      'A secondary but crucial claim is that avoiding obvious stupidity through inversion (asking "what would guarantee failure?") is more reliably achievable than directly pursuing genius-level insight. This connects to his famous advice: "Invert, always invert."',
    ],
    evidence: [
      'You must know the big ideas in the big disciplines, and use them routinely—all of them, not just a few. Most people are trained in one model—economics, for example—and try to solve all problems in one way. You know the saying: To the man with a hammer, the world looks like a nail. — Charlie Munger',
      'It is remarkable how much long-term advantage people like us have gotten by trying to be consistently not stupid, instead of trying to be very intelligent. — Charlie Munger',
    ],
    keyThemes: ['Man with a Hammer', 'Inversion', 'Latticework of Models'],
  },
  {
    dimension: 3,
    confidence: 85,
    insights: [
      '"Lollapalooza Effect" is Munger\'s signature concept for multi-factor compounding',
      'The "Circle of Competence" defines the boundaries of reliable knowledge',
      '"Margin of Safety" originated from engineering but was adapted for investing',
    ],
    analysis: [
      'The concept of the "Lollapalooza Effect" is central to Munger\'s framework. It describes situations where multiple psychological tendencies or mental models combine to produce extreme outcomes—often non-linearly greater than the sum of individual effects. This concept explains everything from cult formation to market bubbles to successful business models like Coca-Cola\'s brand moat.',
      'The "Circle of Competence" concept defines the critical boundary between what we genuinely understand and what we merely think we understand. Munger emphasizes that the most dangerous decisions occur just outside this circle, where overconfidence is highest. The key insight is not just knowing what\'s inside your circle, but recognizing the hard edges where your expertise genuinely ends.',
      'The "Margin of Safety" concept, borrowed from engineering (where bridges are built to withstand far more weight than their maximum expected load), becomes in Munger\'s hands a universal principle for decision-making under uncertainty. It applies to investing (buying below intrinsic value), engineering (safety factors), and life decisions (maintaining optionality).',
    ],
    evidence: [
      'The Lollapalooza effect is when two or three or four forces are all operating in the same direction. And you get a lollapalooza effect when they combine in a way that\'s not linear. That\'s the big effect you\'re always looking for. — Charlie Munger',
      'Knowing what you don\'t know is more useful than being brilliant. — Charlie Munger',
    ],
    keyThemes: ['Lollapalooza Effect', 'Circle of Competence', 'Margin of Safety'],
  },
  {
    dimension: 4,
    confidence: 90,
    insights: [
      'Munger uses probability theory as his primary decision-making model',
      'The Bayesian updating model features prominently in his thinking',
      'Complex adaptive systems thinking provides the meta-framework',
    ],
    analysis: [
      'Munger\'s primary analytical model is probabilistic thinking. He consistently frames decisions in terms of expected value—multiplying the probability of various outcomes by their payoffs. This model underlies his famous advice to bet heavily when the odds are strongly in your favor (the "fat pitch" concept from baseball).',
      'Bayesian reasoning—the process of updating beliefs based on new evidence—permeates Munger\'s approach. He emphasizes starting with a "base rate" (the prior probability from similar situations) and adjusting based on specific evidence. This model helps counter the tendency to overweight recent or vivid information.',
      'At the meta-level, Munger views markets, businesses, and human societies as complex adaptive systems—networks of interacting agents that evolve over time. This model explains why linear thinking fails in complex domains: feedback loops, emergent properties, and phase transitions create fundamentally unpredictable dynamics.',
    ],
    evidence: [
      'If you don\'t get this elementary, but mildly unnatural, mathematics of elementary probability into your repertoire, then you go through a long life like a one-legged man in an ass-kicking contest. — Charlie Munger',
      'The big money is not in the buying and the selling, but in the waiting. — Charlie Munger',
    ],
    keyThemes: ['Expected Value', 'Bayesian Reasoning', 'Complex Adaptive Systems'],
  },
  {
    dimension: 5,
    confidence: 87,
    insights: [
      'Reinforcement feedback loops drive both success and catastrophic failure',
      'Second-order effects are the primary mechanism of surprise in complex systems',
      'Incentive-caused bias operates as a powerful distorting mechanism in human judgment',
    ],
    analysis: [
      'The central mechanism in Munger\'s framework is the feedback loop—particularly reinforcement loops where success breeds more success (or failure breeds more failure). He applies this mechanism to explain moats in business (strong brands attract more customers, which funds more advertising), compounding in investing, and the formation of expertise through deliberate practice.',
      'Second-order thinking—considering the consequences of consequences—is the primary mechanism for avoiding unintended outcomes. Munger emphasizes that first-order thinking (what happens immediately) is common, but second and third-order thinking (what happens as a result of what happens) is where competitive advantage lies.',
      'The mechanism of "incentive-caused bias"—where people\'s reasoning becomes distorted by their incentives—is perhaps the most powerful explanation Munger offers for why smart people do dumb things. Understanding this mechanism is the foundation of his skepticism toward professional advice and his emphasis on aligning incentives in any organizational design.',
    ],
    evidence: [
      'Show me the incentive and I will show you the outcome. — Charlie Munger',
      'Never, ever, think about something else when you should be thinking about the power of incentives. — Charlie Munger',
    ],
    keyThemes: ['Feedback Loops', 'Second-Order Effects', 'Incentive-Caused Bias'],
  },
  {
    dimension: 6,
    confidence: 94,
    insights: [
      'Incentive alignment is the single most powerful lever for predicting behavior',
      'Agency costs create systematic divergences between principal and agent interests',
      'Social proof and authority incentives drive conformity in organizations',
    ],
    analysis: [
      'Munger\'s analysis of incentives is perhaps his most practically valuable contribution. He argues that understanding the incentive structure of any situation provides more predictive power than understanding the personalities or stated intentions of the people involved. This is because humans are remarkably good at aligning their behavior with their incentives, often unconsciously.',
      'The concept of agency costs—the losses that occur when a principal (owner) delegates decision-making to an agent (manager)—is central to Munger\'s business analysis. He examines how compensation structures, promotion criteria, and organizational culture create incentive landscapes that either align or misalign agent behavior with owner interests.',
      'Beyond financial incentives, Munger identifies social incentives (desire for status, affiliation) and psychological incentives (desire for consistency, commitment) as equally powerful drivers. The most dangerous situations occur when multiple incentive types align in the same direction—creating what he would later call a "Lollapalooza effect" of motivation.',
    ],
    evidence: [
      'The compensation system is the most important thing in the world. If you have a really good compensation system, the rest is easy. If you have a bad one, it\'s almost impossible to make things work. — Charlie Munger',
      'I think I\'ve been in the top 5% of my age cohort all my life in understanding the power of incentives, and yet I\'ve always underestimated them. — Charlie Munger',
    ],
    keyThemes: ['Agency Costs', 'Incentive Alignment', 'Social Proof'],
  },
  {
    dimension: 7,
    confidence: 96,
    insights: [
      '25 standard causes of human misjudgment form the backbone of the psychology dimension',
      'Confirmation bias and availability bias are the most pervasive cognitive distortions',
      'Deprival-superreaction tendency explains irrational risk aversion',
    ],
    analysis: [
      'Munger\'s psychology dimension is the most extensively developed in his framework. His speech "The Psychology of Human Misjudgment" identifies 25 standard causes of human misjudgment, organized into categories of psychological tendencies. These include reward/punishment superresponse, liking/loving tendency, disliking/hating tendency, doubt-avoidance tendency, inconsistency-avoidance tendency, curiosity tendency, and Kantian fairness tendency, among others.',
      'The most pervasive bias in Munger\'s analysis is confirmation bias—the tendency to search for, interpret, and remember information in a way that confirms one\'s preexisting beliefs. Munger argues this operates almost automatically and requires systematic counter-procedures (like seeking out disconfirming evidence) to mitigate.',
      'The "deprival-superreaction tendency"—the irrational overreaction to losing something one already possesses—is a key psychological mechanism that explains loss aversion in investing, resistance to change in organizations, and the sunk cost fallacy. Understanding this tendency is essential for making rational decisions about when to exit losing positions or abandon failed projects.',
    ],
    evidence: [
      'The human mind is a lot like the human egg, and the human egg has a shut-off device. When one sperm gets in, it shuts down so the next one can\'t get in. The human mind has a big tendency of the same sort. — Charlie Munger on confirmation bias',
      'The brain of man is programmed with a tendency to quickly remove doubt by reaching some decision. It is easy to see how evolution would make animals, over the eons, drift toward such quick elimination of doubt. — Charlie Munger',
    ],
    keyThemes: ['Cognitive Biases', 'Confirmation Bias', 'Loss Aversion'],
  },
  {
    dimension: 8,
    confidence: 82,
    insights: [
      'System 1 (fast) and System 2 (slow) thinking operate in parallel tracks',
      'Emotional and rational processing often produce conflicting outputs',
      'The unconscious mind processes vastly more information than conscious reasoning',
    ],
    analysis: [
      'The dual-track framework draws explicitly from Daniel Kahneman\'s System 1/System 2 model, though Munger developed similar ideas independently through his own observations. System 1 thinking is fast, automatic, emotional, and largely unconscious—responsible for pattern recognition, gut feelings, and snap judgments. System 2 is slow, deliberate, analytical, and conscious—responsible for calculation, logical analysis, and complex reasoning.',
      'The critical insight for decision-making is that these two tracks often produce conflicting outputs. The gut feeling (System 1) might say "this feels right" while the analysis (System 2) identifies serious problems. Munger argues that good decision-making requires being aware of which system is dominant in any given situation and knowing when to override System 1 with System 2 analysis.',
      'Munger extends the dual-track concept to organizational decision-making, arguing that organizations develop their own "organizational System 1"—the culture, habits, and heuristics that operate automatically. When this organizational autopilot is well-calibrated (as at Berkshire Hathaway), it enables fast, high-quality decisions. When it\'s poorly calibrated, it leads to systematic organizational blindness.',
    ],
    evidence: [
      'It is remarkable how much long-term advantage people like us have gotten by trying to be consistently not stupid, instead of trying to be very intelligent. There must be some wisdom in the folk saying: "It\'s the strong swimmers who drown." — Charlie Munger',
    ],
    keyThemes: ['System 1 & 2', 'Gut Feelings', 'Organizational Autopilot'],
  },
  {
    dimension: 9,
    confidence: 79,
    insights: [
      'Strong ideas require strong counterarguments to reach their full potential',
      'The "iron Presbytorian" approach: seek out those who disagree with you',
      'Survivorship bias systematically distorts our understanding of success',
    ],
    analysis: [
      'Munger\'s approach to counterargument is unusually rigorous. He actively seeks out the strongest possible case against his own positions—a practice he attributes to the influence of Darwin, who trained himself to note disconfirming evidence immediately upon encountering it. This dimension of the framework requires steel-manning opposing views rather than straw-manning them.',
      'The concept of survivorship bias is a key counterargument tool. Munger emphasizes that we systematically overestimate the predictability of success because we only study the winners—we don\'t see the thousands of failed businesses that used the same strategies as the few successes. This bias distorts our understanding of what actually works.',
      'Munger also applies inversion to counterargument: rather than asking "why am I right?", he asks "what would prove me wrong?" and then actively seeks that evidence. This procedural approach to counterargument creates a systematic check on overconfidence and confirmation bias.',
    ],
    evidence: [
      'I have what I call an "iron Presbytorian" conscience: I try to figure out what I\'m doing that doesn\'t work, and I stop doing it. — Charlie Munger',
      'The human mind has a big tendency, when one thing works very well, to overuse it. — Charlie Munger',
    ],
    keyThemes: ['Steel-manning', 'Survivorship Bias', 'Disconfirming Evidence'],
  },
  {
    dimension: 10,
    confidence: 91,
    insights: [
      'Checklists prevent avoidable errors by enforcing systematic review',
      'Pilot\'s checklist model adapted for investment decision-making',
      'Pre-mortem analysis identifies failure modes before they occur',
    ],
    analysis: [
      'The checklist dimension draws heavily from Atul Gawande\'s "The Checklist Manifesto," which Munger has recommended. The core insight is that even world-class experts make avoidable errors through omission—skipping steps, forgetting factors, or overlooking obvious risks. Checklists force systematic review and catch these errors.',
      'Munger\'s checklist includes items like: Have I identified all major psychological biases operating on this decision? Am I staying within my circle of competence? Have I considered the incentive structures? What\'s the second and third order effects? What would make me wrong? What\'s the base rate for this type of situation?',
      'The pre-mortem technique—imagining the decision has failed and working backward to identify why—is a particularly powerful checklist item. This overcomes the natural optimism bias by creating a safe space for considering failure modes before they occur, when psychological investment in the decision is still low.',
    ],
    evidence: [
      'No pilot takes off without going through a checklist. Why should an investor make a major capital allocation without one? — Charlie Munger (paraphrased through Berkshire methodology)',
      'When you\'re thinking about something, always ask: What could go wrong here? What don\'t I know? What am I missing? — Charlie Munger',
    ],
    keyThemes: ['Decision Checklists', 'Pre-mortem', 'Error Prevention'],
  },
  {
    dimension: 11,
    confidence: 86,
    insights: [
      'See\'s Candies as the paradigmatic case of brand-based pricing power',
      'Berkshire\'s investment in Coca-Cola illustrates the power of durable moats',
      'The Salomon Brothers crisis demonstrates the importance of decisive action',
    ],
    analysis: [
      'Case analysis is central to Munger\'s teaching method. Rather than presenting abstract principles, he almost always illustrates through specific historical cases. The See\'s Candies acquisition is perhaps his most frequently cited example: Berkshire paid $25 million for a business that has since generated over $2 billion in pre-tax earnings, teaching the lesson that paying a fair price for an exceptional business is superior to buying a mediocre business cheaply.',
      'The Coca-Cola investment illustrates multiple dimensions simultaneously: brand moat (psychology), global distribution network (mechanism), pricing power (incentives), and management alignment (incentives again). Munger uses this case to demonstrate how multiple mental models converge to create a "Lollapalooza effect" of business quality.',
      'The Salomon Brothers crisis (where Munger and Buffett had to step in to prevent the firm\'s collapse due to a Treasury bond trading scandal) serves as a cautionary case about the dangers of misaligned incentives and the importance of rapid, decisive action when integrity failures occur. The lesson: a culture of integrity is not optional—it\'s existential.',
    ],
    evidence: [
      'See\'s was the first time we really paid up for quality. And it taught us a wonderful lesson. We\'ve been paying up for quality ever since. — Charlie Munger',
      'It\'s not supposed to be easy. Anyone who finds it easy is stupid. — Charlie Munger',
    ],
    keyThemes: ['See\'s Candies', 'Coca-Cola Moat', 'Salomon Crisis'],
  },
  {
    dimension: 12,
    confidence: 89,
    insights: [
      'Decision quality is best evaluated by process, not outcome',
      'Optionality preservation maintains flexibility under uncertainty',
      'The "too hard" pile is a critical decision tool—know what to avoid',
    ],
    analysis: [
      'Munger\'s decision framework starts with process over outcome. He emphasizes that a good decision process can produce bad outcomes due to luck, while a bad process can produce good outcomes through randomness. The key is to consistently apply the right process and let the law of large numbers work in your favor over time.',
      'Maintaining optionality—preserving choices and avoiding irreversible commitments—is a core decision principle. Munger and Buffett\'s massive cash holdings during expensive market periods reflect this: they sacrifice some returns to maintain the option to deploy capital aggressively when opportunities arise.',
      'The "too hard" pile—consciously deciding not to decide—is one of Munger\'s most underrated tools. When a situation is too complex, too uncertain, or outside their circle of competence, they simply pass. This filters out a vast number of potential errors at the cost of missing some opportunities—a trade-off they consider highly favorable.',
    ],
    evidence: [
      'The difference between a good business and a bad business is that good businesses throw up one easy decision after another. The bad businesses throw up painful decisions—painful decisions that kill you. — Charlie Munger',
      'We don\'t leap seven-foot fences. Instead, we look for one-foot fences with big rewards on the other side. — Charlie Munger',
    ],
    keyThemes: ['Process vs Outcome', 'Optionality', 'Circle of Competence'],
  },
];

const SOURCE_TITLE = 'Charlie Munger: The Complete Investor';
const KEY_THEMES = ['Mental Models', 'Inversion', 'Compounding', 'Margin of Safety', 'Psychology', 'Incentives', 'Circle of Competence'];

/* ------------------------------------------------------------------ */
/* Helper Components                                                    */
/* ------------------------------------------------------------------ */

function InsightCard({ insight, color, index }: { insight: string; color: string; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 + index * 0.06, duration: 0.3 }}
      className="rounded-lg bg-bg-hover p-4"
    >
      <div className="flex items-start gap-3">
        <Lightbulb className="mt-0.5 h-4 w-4 flex-shrink-0" style={{ color }} />
        <p className="text-body-sm text-text-secondary">{insight}</p>
      </div>
    </motion.div>
  );
}

function EvidenceBlock({ quote, color }: { quote: string; color: string }) {
  return (
    <blockquote
      className="rounded-md border-l-[3px] bg-bg-hover px-4 py-3"
      style={{ borderLeftColor: color }}
    >
      <div className="flex items-start gap-2">
        <Quote className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-text-muted" />
        <p className="text-body-md italic text-text-secondary font-wiki">"{quote}"</p>
      </div>
    </blockquote>
  );
}

function ScoreCircle({ score, color }: { score: number; color: string }) {
  const radius = 20;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center">
      <svg width="48" height="48" viewBox="0 0 48 48">
        <circle
          cx="24"
          cy="24"
          r={radius}
          fill="none"
          stroke={color}
          strokeOpacity={0.15}
          strokeWidth="4"
        />
        <motion.circle
          cx="24"
          cy="24"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 0.8, ease: [0.23, 1, 0.32, 1] as [number, number, number, number], delay: 0.2 }}
          transform="rotate(-90 24 24)"
        />
      </svg>
      <span className="absolute text-heading-sm text-text-primary">{score}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Radar Chart Tooltip                                                  */
/* ------------------------------------------------------------------ */

function RadarTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: { dimension: string; confidence: number; description: string } }> }) {
  if (!active || !payload?.length) return null;
  const data = payload[0].payload;
  return (
    <div className="rounded-lg border border-amber-800/20 bg-bg-elevated px-3 py-2 shadow-lg">
      <p className="text-body-sm font-medium text-text-primary">{data.dimension}</p>
      <p className="text-mono-sm text-amber-300">{data.confidence}%</p>
      <p className="mt-1 text-mono-sm text-text-muted">{data.description}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main Page Component                                                  */
/* ------------------------------------------------------------------ */

export default function Analysis() {
  const { sourceId } = useParams<{ sourceId: string }>();
  const [activeDimension, setActiveDimension] = useState<number | null>(null);
  const [expandedDimensions, setExpandedDimensions] = useState<Set<number>>(
    new Set([1, 2, 3]) // First 3 expanded by default
  );

  /* Derived data */
  const radarData = useMemo(
    () =>
      DIMENSIONS.map((d) => {
        const analysis = MOCK_ANALYSIS_DATA.find((a) => a.dimension === d.number);
        return {
          dimension: d.name,
          confidence: analysis?.confidence ?? 0,
          fullMark: 100,
          description: d.description,
          color: d.color,
        };
      }),
    []
  );

  const avgConfidence = Math.round(
    MOCK_ANALYSIS_DATA.reduce((sum, d) => sum + d.confidence, 0) / MOCK_ANALYSIS_DATA.length
  );

  const sortedByConfidence = [...MOCK_ANALYSIS_DATA].sort((a, b) => b.confidence - a.confidence);
  const top3 = sortedByConfidence.slice(0, 3);
  const bottom3 = sortedByConfidence.slice(-3).reverse();

  /* Toggle expand */
  const toggleExpand = (dimNumber: number) => {
    setExpandedDimensions((prev) => {
      const next = new Set(prev);
      if (next.has(dimNumber)) {
        next.delete(dimNumber);
      } else {
        next.add(dimNumber);
      }
      return next;
    });
  };

  /* Filter dimensions */
  const visibleDimensions = activeDimension
    ? DIMENSIONS.filter((d) => d.number === activeDimension)
    : DIMENSIONS;

  return (
    <div className="min-h-full p-6 md:p-8">
      {/* ========== Page Header ========== */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
      >
        <h1 className="font-display text-display-lg text-text-primary">Munger Analysis</h1>
        {sourceId && (
          <p className="mt-1 text-body-md text-amber-300">
            Analysis for: {SOURCE_TITLE}
          </p>
        )}
        <motion.p
          className="mt-2 text-body-md text-text-secondary"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
        >
          12-dimensional thinking framework
        </motion.p>
      </motion.div>

      {/* ========== Overall Summary Card ========== */}
      <motion.div
        className="mt-8 rounded-xl border border-amber-800/10 bg-bg-surface p-5 shadow-md shadow-inner-card"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.15 }}
      >
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-body-sm text-text-muted">Source Being Analyzed</p>
            <p className="mt-1 font-display text-display-md text-text-primary">{SOURCE_TITLE}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {KEY_THEMES.map((theme) => (
                <span
                  key={theme}
                  className="rounded-full bg-amber-500/10 px-3 py-1 text-body-sm text-amber-300"
                >
                  {theme}
                </span>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-8">
            <div className="text-center">
              <p className="text-body-sm text-text-muted">Overall Confidence</p>
              <motion.p
                className="mt-1 font-display text-display-xl text-amber-300"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                {avgConfidence}%
              </motion.p>
            </div>
            <div className="text-center">
              <p className="text-body-sm text-text-muted">Dimensions</p>
              <p className="mt-1 font-display text-display-xl text-text-primary">
                12<span className="text-text-muted">/12</span>
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* ========== Dimension Selector ========== */}
      <motion.div
        className="sticky top-0 z-10 mt-6 -mx-2 border-b border-amber-800/10 bg-bg-void/90 px-2 py-3 backdrop-blur-md"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
      >
        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-hide">
          <button
            onClick={() => setActiveDimension(null)}
            className={`flex-shrink-0 rounded-full px-4 py-1.5 text-body-sm font-medium transition-all ${
              activeDimension === null
                ? 'bg-amber-500/15 text-amber-300 border border-amber-500'
                : 'bg-bg-surface text-text-secondary border border-amber-800/20 hover:bg-amber-500/8'
            }`}
          >
            All
          </button>
          {DIMENSIONS.map((d) => (
            <button
              key={d.number}
              onClick={() => setActiveDimension(activeDimension === d.number ? null : d.number)}
              className={`flex-shrink-0 flex items-center gap-2 rounded-full px-3 py-1.5 text-body-sm font-medium transition-all border ${
                activeDimension === d.number
                  ? 'text-white'
                  : 'bg-bg-surface text-text-secondary border-transparent hover:bg-opacity-10'
              }`}
              style={
                activeDimension === d.number
                  ? { backgroundColor: `${d.color}25`, borderColor: d.color, color: d.color }
                  : { borderColor: 'transparent' }
              }
            >
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ backgroundColor: d.color }}
              />
              <span className="text-text-muted">{d.number}.</span>
              <span>{d.name}</span>
            </button>
          ))}
        </div>
      </motion.div>

      {/* ========== Radar Chart + Summary ========== */}
      <motion.div
        className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, delay: 0.2, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
      >
        {/* Radar Chart */}
        <div className="rounded-xl border border-amber-800/10 bg-bg-surface p-5 shadow-md shadow-inner-card">
          <h3 className="mb-4 text-heading-md text-text-primary">Dimension Coverage</h3>
          <div className="flex justify-center" style={{ height: 380 }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                <PolarGrid
                  stroke="rgba(120, 53, 15, 0.25)"
                  strokeWidth={1}
                />
                <PolarAngleAxis
                  dataKey="dimension"
                  tick={{ fill: '#B8A88A', fontSize: 12, fontFamily: 'JetBrains Mono, monospace' }}
                />
                <PolarRadiusAxis
                  angle={90}
                  domain={[0, 100]}
                  tick={{ fill: '#7A6B5A', fontSize: 10 }}
                  axisLine={false}
                />
                <Tooltip content={<RadarTooltip />} />
                <Radar
                  name="Confidence"
                  dataKey="confidence"
                  stroke="#F59E0B"
                  strokeWidth={2}
                  fill="url(#radarGradient)"
                  fillOpacity={0.25}
                  dot={(props: { cx: number; cy: number; payload: { color: string } }) => {
                    const { cx, cy, payload } = props;
                    return (
                      <circle
                        cx={cx}
                        cy={cy}
                        r={5}
                        fill={payload.color}
                        stroke="#14100D"
                        strokeWidth={1.5}
                        style={{ cursor: 'pointer' }}
                      />
                    );
                  }}
                />
                <defs>
                  <linearGradient id="radarGradient" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#F59E0B" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#D97706" stopOpacity={0.1} />
                  </linearGradient>
                </defs>
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Summary Panel */}
        <div className="rounded-xl border border-amber-800/10 bg-bg-surface p-5 shadow-md shadow-inner-card">
          <h3 className="mb-4 text-heading-md text-text-primary">Score Summary</h3>

          {/* Top 3 */}
          <div>
            <p className="text-heading-sm text-text-secondary mb-3 flex items-center gap-2">
              <Target className="h-4 w-4 text-success" />
              Strongest Dimensions
            </p>
            <div className="space-y-3">
              {top3.map((dim, i) => {
                const config = DIMENSIONS.find((d) => d.number === dim.dimension)!;
                return (
                  <motion.div
                    key={dim.dimension}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 + i * 0.1 }}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-body-sm text-text-primary">{config.name}</span>
                      <span className="text-mono-sm" style={{ color: config.color }}>
                        {dim.confidence}%
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-bg-hover">
                      <motion.div
                        className="h-full rounded-full"
                        style={{ backgroundColor: config.color }}
                        initial={{ width: 0 }}
                        animate={{ width: `${dim.confidence}%` }}
                        transition={{ duration: 0.6, delay: 0.4 + i * 0.1, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
                      />
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>

          {/* Divider */}
          <div className="my-5 h-px bg-amber-800/10" />

          {/* Bottom 3 */}
          <div>
            <p className="text-heading-sm text-text-secondary mb-3 flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-warning" />
              Areas for Deeper Analysis
            </p>
            <div className="space-y-3">
              {bottom3.map((dim, i) => {
                const config = DIMENSIONS.find((d) => d.number === dim.dimension)!;
                return (
                  <motion.div
                    key={dim.dimension}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.6 + i * 0.1 }}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-body-sm text-text-primary">{config.name}</span>
                      <span className="text-mono-sm text-text-muted">{dim.confidence}%</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-bg-hover">
                      <motion.div
                        className="h-full rounded-full bg-text-muted"
                        initial={{ width: 0 }}
                        animate={{ width: `${dim.confidence}%` }}
                        transition={{ duration: 0.6, delay: 0.7 + i * 0.1, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
                      />
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>

          {/* Quote */}
          <motion.div
            className="mt-5 rounded-md border-l-[3px] border-amber-500 bg-bg-hover px-4 py-3"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.8, duration: 0.5 }}
          >
            <p className="text-body-md italic text-text-secondary">
              "The wisest analysis comes from looking at problems through multiple lenses simultaneously."
            </p>
            <p className="mt-2 text-body-sm text-text-muted">— Charlie Munger</p>
          </motion.div>
        </div>
      </motion.div>

      {/* ========== Dimension Sections ========== */}
      <div className="mt-8 space-y-4">
        <div className="flex items-center gap-2 mb-4">
          <Network className="h-5 w-5 text-amber-400" />
          <h2 className="text-heading-lg text-text-primary">Dimension Analysis</h2>
        </div>

        <AnimatePresence>
          {visibleDimensions.map((dim) => {
            const analysis = MOCK_ANALYSIS_DATA.find((a) => a.dimension === dim.number);
            if (!analysis) return null;

            const isExpanded = expandedDimensions.has(dim.number);

            return (
              <motion.div
                key={dim.number}
                layout
                className="rounded-xl border bg-bg-surface shadow-md shadow-inner-card overflow-hidden"
                style={{ borderColor: `${dim.color}20`, borderLeftWidth: 4, borderLeftColor: dim.color }}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
              >
                {/* Section Header */}
                <button
                  onClick={() => toggleExpand(dim.number)}
                  className="flex w-full items-center justify-between px-5 py-4 text-left transition-colors hover:bg-bg-hover"
                >
                  <div className="flex items-center gap-4 min-w-0 flex-1">
                    {/* Number circle */}
                    <span
                      className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-mono-sm font-bold text-white"
                      style={{ backgroundColor: dim.color }}
                    >
                      {dim.number}
                    </span>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-heading-md text-text-primary">
                          {dim.chineseName} · {dim.name}
                        </span>
                      </div>
                      <p className="text-body-sm text-text-secondary mt-0.5">{dim.description}</p>
                    </div>

                    {/* Mini bar */}
                    <div className="hidden md:block w-20">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-mono-sm" style={{ color: dim.color }}>
                          {analysis.confidence}%
                        </span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-bg-hover">
                        <div
                          className="h-full rounded-full transition-all duration-600"
                          style={{ width: `${analysis.confidence}%`, backgroundColor: dim.color }}
                        />
                      </div>
                    </div>

                    {/* Score circle */}
                    <div className="flex-shrink-0 hidden sm:block">
                      <ScoreCircle score={analysis.confidence} color={dim.color} />
                    </div>
                  </div>

                  <div className="ml-3 flex-shrink-0">
                    {isExpanded ? (
                      <ChevronUp className="h-5 w-5 text-text-muted" />
                    ) : (
                      <ChevronDown className="h-5 w-5 text-text-muted" />
                    )}
                  </div>
                </button>

                {/* Expanded Content */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] as [number, number, number, number] }}
                      className="overflow-hidden"
                    >
                      <div className="border-t border-amber-800/10 px-5 py-5">
                        {/* Key Insights */}
                        <div>
                          <p className="text-heading-sm text-text-primary mb-3 flex items-center gap-2">
                            <Lightbulb className="h-4 w-4" style={{ color: dim.color }} />
                            Key Insights
                          </p>
                          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                            {analysis.insights.map((insight, i) => (
                              <InsightCard key={i} insight={insight} color={dim.color} index={i} />
                            ))}
                          </div>
                        </div>

                        {/* Analysis Text */}
                        <div className="mt-5">
                          <p className="text-heading-sm text-text-primary mb-3">Analysis</p>
                          <div className="space-y-3">
                            {analysis.analysis.map((para, i) => (
                              <p key={i} className="text-body-lg text-text-primary font-wiki leading-relaxed">
                                {para}
                              </p>
                            ))}
                          </div>
                        </div>

                        {/* Evidence Quotes */}
                        <div className="mt-5">
                          <p className="text-heading-sm text-text-primary mb-3">Evidence from Source</p>
                          <div className="space-y-3">
                            {analysis.evidence.map((quote, i) => (
                              <EvidenceBlock key={i} quote={quote} color={dim.color} />
                            ))}
                          </div>
                        </div>

                        {/* Key Themes */}
                        <div className="mt-5">
                          <p className="text-body-sm text-text-muted mb-2">Key Themes</p>
                          <div className="flex flex-wrap gap-2">
                            {analysis.keyThemes.map((theme) => (
                              <span
                                key={theme}
                                className="rounded-full px-3 py-1 text-body-sm text-text-secondary border"
                                style={{ borderColor: `${dim.color}30`, backgroundColor: `${dim.color}10` }}
                              >
                                {theme}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {/* ========== Cross-Dimension Insights ========== */}
      <motion.div
        className="mt-8 mb-12 rounded-xl border border-amber-800/10 bg-bg-surface p-6 shadow-md shadow-inner-card"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
      >
        <div className="flex items-center gap-2 mb-2">
          <Network className="h-5 w-5 text-amber-400" />
          <h2 className="text-heading-md text-text-primary">Cross-Dimension Insights</h2>
        </div>
        <p className="text-body-sm text-text-muted mb-5">Patterns that emerge across multiple dimensions</p>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {[
            {
              title: 'Incentive-Psychology Feedback Loop',
              description: 'Munger\'s analysis reveals that incentive structures and psychological biases form a self-reinforcing loop: incentives shape behavior, which creates psychological commitments, which then resist changes to the original incentives.',
              dimensions: [6, 7],
            },
            {
              title: 'The Lollapalooza Threshold',
              description: 'When three or more dimensions align positively (high confidence in Source, Model, Mechanism, and Decision), Munger identifies a "Lollapalooza threshold" where the whole becomes dramatically greater than the sum of parts.',
              dimensions: [1, 4, 5, 12],
            },
            {
              title: 'Circle of Competence as Meta-Filter',
              description: 'The Checklist and Counterargument dimensions both converge on the Circle of Competence concept—it serves as the primary filter for determining when to engage System 2 thinking versus delegating to the "too hard" pile.',
              dimensions: [9, 10],
            },
            {
              title: 'Dual-Track Decision Architecture',
              description: 'The psychology and dual-track dimensions together suggest that optimal decision-making requires creating organizational structures where System 1 (intuition) and System 2 (analysis) operate in productive tension rather than either dominating.',
              dimensions: [7, 8],
            },
          ].map((insight, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + i * 0.1 }}
              className="rounded-lg bg-bg-hover p-5"
            >
              <div className="flex gap-1.5 mb-3">
                {insight.dimensions.map((dn) => {
                  const dc = DIMENSIONS.find((d) => d.number === dn)!;
                  return (
                    <span
                      key={dn}
                      className="inline-block h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: dc.color }}
                      title={dc.name}
                    />
                  );
                })}
              </div>
              <h3 className="text-heading-sm text-text-primary mb-2">{insight.title}</h3>
              <p className="text-body-md text-text-secondary">{insight.description}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
