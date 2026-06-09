import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ZoomIn,
  ZoomOut,
  Maximize,
  Search,
  X,
  Filter,
  ExternalLink,
  Focus,
  GitFork,
  Circle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// --- Types ---

interface GraphNode {
  id: string;
  slug: string;
  title: string;
  type: 'entity' | 'concept' | 'model' | 'summary' | 'principle';
  wordCount: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  dimensions: number[];
}

interface GraphLink {
  source: string;
  target: string;
  strength: number;
}

// --- Mock Data ---

const TYPE_COLORS: Record<string, { fill: string; glow: string; label: string }> = {
  entity: { fill: '#7C6BFF', glow: '#7C6BFF40', label: 'Entity' },
  concept: { fill: '#65A30D', glow: '#65A30D40', label: 'Concept' },
  model: { fill: '#FBBF24', glow: '#FBBF2440', label: 'Model' },
  summary: { fill: '#CA8A04', glow: '#CA8A0440', label: 'Summary' },
  principle: { fill: '#B91C1C', glow: '#B91C1C40', label: 'Principle' },
};

const INITIAL_NODES: GraphNode[] = [
  { id: 'n1', slug: 'cognitive-bias', title: 'Cognitive Bias', type: 'concept', wordCount: 3240, x: 0, y: 0, vx: 0, vy: 0, dimensions: [1, 2, 3, 6] },
  { id: 'n2', slug: 'thinking-fast-slow', title: 'Thinking Fast and Slow', type: 'summary', wordCount: 5680, x: 0, y: 0, vx: 0, vy: 0, dimensions: [1, 2, 6, 7] },
  { id: 'n3', slug: 'confirmation-bias', title: 'Confirmation Bias', type: 'entity', wordCount: 1850, x: 0, y: 0, vx: 0, vy: 0, dimensions: [1, 6] },
  { id: 'n4', slug: 'availability-heuristic', title: 'Availability Heuristic', type: 'entity', wordCount: 2100, x: 0, y: 0, vx: 0, vy: 0, dimensions: [2, 6, 10] },
  { id: 'n5', slug: 'loss-aversion', title: 'Loss Aversion', type: 'concept', wordCount: 2780, x: 0, y: 0, vx: 0, vy: 0, dimensions: [5, 6, 7] },
  { id: 'n6', slug: 'anchoring-effect', title: 'Anchoring Effect', type: 'entity', wordCount: 1620, x: 0, y: 0, vx: 0, vy: 0, dimensions: [2, 6] },
  { id: 'n7', slug: 'mental-models', title: 'Mental Models', type: 'model', wordCount: 4520, x: 0, y: 0, vx: 0, vy: 0, dimensions: [3, 9, 11] },
  { id: 'n8', slug: 'first-principles', title: 'First Principles Thinking', type: 'principle', wordCount: 3890, x: 0, y: 0, vx: 0, vy: 0, dimensions: [2, 3, 9] },
  { id: 'n9', slug: 'inversion', title: 'Inversion', type: 'principle', wordCount: 2450, x: 0, y: 0, vx: 0, vy: 0, dimensions: [1, 3] },
  { id: 'n10', slug: 'opportunity-cost', title: 'Opportunity Cost', type: 'concept', wordCount: 1980, x: 0, y: 0, vx: 0, vy: 0, dimensions: [4, 5] },
  { id: 'n11', slug: 'compound-interest', title: 'Compound Interest', type: 'concept', wordCount: 3120, x: 0, y: 0, vx: 0, vy: 0, dimensions: [5, 11] },
  { id: 'n12', slug: 'margin-of-safety', title: 'Margin of Safety', type: 'principle', wordCount: 2240, x: 0, y: 0, vx: 0, vy: 0, dimensions: [7, 10] },
  { id: 'n13', slug: 'probability', title: 'Probability Theory', type: 'model', wordCount: 5340, x: 0, y: 0, vx: 0, vy: 0, dimensions: [6, 3] },
  { id: 'n14', slug: 'circle-of-competence', title: 'Circle of Competence', type: 'principle', wordCount: 2670, x: 0, y: 0, vx: 0, vy: 0, dimensions: [10, 7] },
  { id: 'n15', slug: 'second-order-thinking', title: 'Second-Order Thinking', type: 'model', wordCount: 2980, x: 0, y: 0, vx: 0, vy: 0, dimensions: [11, 9] },
  { id: 'n16', slug: 'lollapalooza-effect', title: 'Lollapalooza Effect', type: 'concept', wordCount: 1890, x: 0, y: 0, vx: 0, vy: 0, dimensions: [12, 3, 9] },
  { id: 'n17', slug: 'checklist-manifesto', title: 'The Checklist Manifesto', type: 'summary', wordCount: 4120, x: 0, y: 0, vx: 0, vy: 0, dimensions: [8, 7] },
  { id: 'n18', slug: 'multidisciplinary', title: 'Multidisciplinary Approach', type: 'model', wordCount: 3560, x: 0, y: 0, vx: 0, vy: 0, dimensions: [9, 3, 2] },
];

const INITIAL_LINKS: GraphLink[] = [
  { source: 'n1', target: 'n3', strength: 0.9 },
  { source: 'n1', target: 'n4', strength: 0.8 },
  { source: 'n1', target: 'n5', strength: 0.7 },
  { source: 'n1', target: 'n6', strength: 0.75 },
  { source: 'n2', target: 'n1', strength: 0.95 },
  { source: 'n2', target: 'n5', strength: 0.85 },
  { source: 'n2', target: 'n3', strength: 0.6 },
  { source: 'n3', target: 'n6', strength: 0.5 },
  { source: 'n4', target: 'n6', strength: 0.55 },
  { source: 'n5', target: 'n10', strength: 0.7 },
  { source: 'n7', target: 'n8', strength: 0.8 },
  { source: 'n7', target: 'n9', strength: 0.75 },
  { source: 'n7', target: 'n13', strength: 0.65 },
  { source: 'n8', target: 'n9', strength: 0.6 },
  { source: 'n8', target: 'n18', strength: 0.85 },
  { source: 'n9', target: 'n12', strength: 0.5 },
  { source: 'n10', target: 'n11', strength: 0.6 },
  { source: 'n11', target: 'n5', strength: 0.55 },
  { source: 'n12', target: 'n14', strength: 0.8 },
  { source: 'n13', target: 'n3', strength: 0.5 },
  { source: 'n13', target: 'n4', strength: 0.45 },
  { source: 'n14', target: 'n10', strength: 0.4 },
  { source: 'n15', target: 'n7', strength: 0.75 },
  { source: 'n15', target: 'n11', strength: 0.6 },
  { source: 'n16', target: 'n7', strength: 0.7 },
  { source: 'n16', target: 'n18', strength: 0.65 },
  { source: 'n17', target: 'n12', strength: 0.6 },
  { source: 'n17', target: 'n8', strength: 0.45 },
  { source: 'n18', target: 'n7', strength: 0.9 },
  { source: 'n18', target: 'n15', strength: 0.7 },
  { source: 'n1', target: 'n7', strength: 0.4 },
  { source: 'n2', target: 'n8', strength: 0.5 },
];

// --- Helpers ---

function getNodeRadius(wordCount: number) {
  const minR = 10;
  const maxR = 28;
  const minW = 1500;
  const maxW = 5700;
  const t = Math.max(0, Math.min(1, (wordCount - minW) / (maxW - minW)));
  return minR + t * (maxR - minR);
}

function runForceLayout(
  nodes: GraphNode[],
  links: GraphLink[],
  width: number,
  height: number,
  iterations: number = 120
) {
  const centerX = width / 2;
  const centerY = height / 2;

  // Initialize positions in a circle
  nodes.forEach((node, i) => {
    const angle = (i / nodes.length) * Math.PI * 2;
    const radius = Math.min(width, height) * 0.3;
    node.x = centerX + Math.cos(angle) * radius;
    node.y = centerY + Math.sin(angle) * radius;
    node.vx = 0;
    node.vy = 0;
  });

  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  for (let iter = 0; iter < iterations; iter++) {
    // Repulsion
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i];
        const b = nodes[j];
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        let dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = 8000 / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        a.vx += fx;
        a.vy += fy;
        b.vx -= fx;
        b.vy -= fy;
      }
    }

    // Attraction along links
    for (const link of links) {
      const a = nodeMap.get(link.source);
      const b = nodeMap.get(link.target);
      if (!a || !b) continue;
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      let dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const targetDist = 120 + (1 - link.strength) * 60;
      const force = (dist - targetDist) * 0.02;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      a.vx += fx;
      a.vy += fy;
      b.vx -= fx;
      b.vy -= fy;
    }

    // Centering force
    for (const node of nodes) {
      node.vx += (centerX - node.x) * 0.005;
      node.vy += (centerY - node.y) * 0.005;
    }

    // Apply velocity with damping
    for (const node of nodes) {
      node.vx *= 0.6;
      node.vy *= 0.6;
      node.x += node.vx;
      node.y += node.vy;

      // Keep within bounds
      const margin = 40;
      node.x = Math.max(margin, Math.min(width - margin, node.x));
      node.y = Math.max(margin, Math.min(height - margin, node.y));
    }
  }
}

// --- Main Component ---

export default function Graph() {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);

  // Transform state for pan/zoom
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const [isPanning, setIsPanning] = useState(false);
  const panStart = useRef({ x: 0, y: 0, tx: 0, ty: 0 });

  // Node/link state
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [links] = useState<GraphLink[]>(INITIAL_LINKS);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [showFilterDropdown, setShowFilterDropdown] = useState(false);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; node: GraphNode } | null>(null);

  // Initialize force layout
  useEffect(() => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const newNodes = INITIAL_NODES.map((n) => ({ ...n, x: n.x, y: n.y, vx: 0, vy: 0 }));
      runForceLayout(newNodes, INITIAL_LINKS, rect.width, rect.height);
      setNodes(newNodes);
    }
  }, []);

  // Filtered nodes
  const filteredNodes = useMemo(() => {
    return nodes.filter((n) => {
      if (typeFilter !== 'all' && n.type !== typeFilter) return false;
      if (searchQuery && !n.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      return true;
    });
  }, [nodes, typeFilter, searchQuery]);

  const filteredNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  // Connected node IDs for highlighting
  const connectedIds = useMemo(() => {
    if (!selectedNode && !hoveredNode) return new Set<string>();
    const targetId = selectedNode?.id || hoveredNode;
    const ids = new Set<string>();
    ids.add(targetId!);
    links.forEach((l) => {
      if (l.source === targetId) ids.add(l.target);
      if (l.target === targetId) ids.add(l.source);
    });
    return ids;
  }, [selectedNode, hoveredNode, links]);
  void connectedIds;

  // Pan handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.target === e.currentTarget || (e.target as HTMLElement).dataset?.canvas === 'true') {
      setIsPanning(true);
      panStart.current = { x: e.clientX, y: e.clientY, tx: transform.x, ty: transform.y };
    }
  }, [transform]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isPanning) {
      const dx = e.clientX - panStart.current.x;
      const dy = e.clientY - panStart.current.y;
      setTransform((t) => ({ ...t, x: panStart.current.tx + dx, y: panStart.current.ty + dy }));
    }
  }, [isPanning]);

  const handleMouseUp = useCallback(() => {
    setIsPanning(false);
  }, []);

  // Zoom handler
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setTransform((t) => {
      const newScale = Math.max(0.2, Math.min(4, t.scale * delta));
      return { ...t, scale: newScale };
    });
  }, []);

  // Zoom controls
  const zoomIn = useCallback(() => setTransform((t) => ({ ...t, scale: Math.min(4, t.scale * 1.2) })), []);
  const zoomOut = useCallback(() => setTransform((t) => ({ ...t, scale: Math.max(0.2, t.scale / 1.2) })), []);
  const resetView = useCallback(() => setTransform({ x: 0, y: 0, scale: 1 }), []);

  // Node click
  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode((prev) => (prev?.id === node.id ? null : node));
  }, []);

  // Background click to deselect
  const handleBgClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  // Connected nodes for detail panel
  const connectedNodes = useMemo(() => {
    if (!selectedNode) return [];
    const result: { node: GraphNode; strength: number }[] = [];
    links.forEach((l) => {
      if (l.source === selectedNode.id) {
        const n = nodes.find((n2) => n2.id === l.target);
        if (n) result.push({ node: n, strength: l.strength });
      } else if (l.target === selectedNode.id) {
        const n = nodes.find((n2) => n2.id === l.source);
        if (n) result.push({ node: n, strength: l.strength });
      }
    });
    return result.sort((a, b) => b.strength - a.strength);
  }, [selectedNode, links, nodes]);

  // SVG link positions
  const getLinkCoords = useCallback((link: GraphLink) => {
    const s = nodes.find((n) => n.id === link.source);
    const t = nodes.find((n) => n.id === link.target);
    if (!s || !t) return null;
    return { x1: s.x, y1: s.y, x2: t.x, y2: t.y };
  }, [nodes]);

  // Keyboard shortcut
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSelectedNode(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="h-full flex flex-col relative overflow-hidden">
      {/* Full-screen graph canvas */}
      <div
        ref={containerRef}
        className="flex-1 relative cursor-grab active:cursor-grabbing"
        style={{ background: '#0C0907' }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
        onClick={handleBgClick}
        data-canvas="true"
      >
        {/* Subtle dotted grid */}
        <div
          className="absolute inset-0 pointer-events-none opacity-5"
          style={{
            backgroundImage: 'radial-gradient(circle, #78350F 1px, transparent 1px)',
            backgroundSize: '40px 40px',
            transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`,
            transformOrigin: '0 0',
          }}
        />

        {/* Graph content */}
        <div
          className="absolute inset-0"
          style={{
            transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`,
            transformOrigin: '0 0',
          }}
          data-canvas="true"
        >
          {/* SVG Edges */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none" data-canvas="true">
            {links.map((link, i) => {
              const coords = getLinkCoords(link);
              if (!coords) return null;
              const isHighlighted =
                (selectedNode && (link.source === selectedNode.id || link.target === selectedNode.id)) ||
                (hoveredNode && (link.source === hoveredNode || link.target === hoveredNode));
              const isDimmed =
                (selectedNode && link.source !== selectedNode.id && link.target !== selectedNode.id) ||
                (hoveredNode && link.source !== hoveredNode && link.target !== hoveredNode);

              return (
                <line
                  key={i}
                  x1={coords.x1}
                  y1={coords.y1}
                  x2={coords.x2}
                  y2={coords.y2}
                  stroke={isHighlighted ? '#FBBF24' : '#78350F'}
                  strokeWidth={isHighlighted ? 2 : 1}
                  opacity={
                    !filteredNodeIds.has(link.source) || !filteredNodeIds.has(link.target)
                      ? 0.05
                      : isHighlighted
                        ? 0.6
                        : isDimmed
                          ? 0.1
                          : 0.25
                  }
                  style={{ transition: 'all 200ms ease' }}
                />
              );
            })}
          </svg>

          {/* Nodes */}
          {nodes.map((node) => {
            const isFiltered = filteredNodeIds.has(node.id);
            const radius = getNodeRadius(node.wordCount);
            const isSelected = selectedNode?.id === node.id;
            const isHovered = hoveredNode === node.id;
            const color = TYPE_COLORS[node.type];

            return (
              <div
                key={node.id}
                className="absolute"
                style={{
                  left: node.x,
                  top: node.y,
                  transform: `translate(-50%, -50%)`,
                  cursor: 'pointer',
                  opacity: isFiltered ? 1 : 0.08,
                  transition: 'opacity 300ms ease',
                  zIndex: isSelected ? 30 : isHovered ? 20 : 10,
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  handleNodeClick(node);
                }}
                onMouseEnter={(e) => {
                  if (isFiltered) {
                    setHoveredNode(node.id);
                    setTooltip({ x: e.clientX, y: e.clientY - 80, node });
                  }
                }}
                onMouseMove={(e) => {
                  if (tooltip) setTooltip({ x: e.clientX, y: e.clientY - 80, node: tooltip.node });
                }}
                onMouseLeave={() => {
                  setHoveredNode(null);
                  setTooltip(null);
                }}
              >
                {/* Glow */}
                <div
                  className="absolute rounded-full pointer-events-none"
                  style={{
                    width: radius * 2 + 16,
                    height: radius * 2 + 16,
                    left: '50%',
                    top: '50%',
                    transform: `translate(-50%, -50%) scale(${isSelected ? 1.5 : isHovered ? 1.3 : 1})`,
                    background: `radial-gradient(circle, ${color.glow} 0%, transparent 70%)`,
                    transition: 'transform 200ms ease',
                  }}
                />

                {/* Circle */}
                <div
                  className="rounded-full relative"
                  style={{
                    width: radius * 2,
                    height: radius * 2,
                    background: `radial-gradient(circle, #1C1712 30%, ${color.fill}60 100%)`,
                    border: `${isSelected ? 3 : 2}px solid ${isSelected ? '#FBBF24' : color.fill + '99'}`,
                    boxShadow: isSelected ? `0 0 0 3px dashed #FBBF24` : 'none',
                    transition: 'all 200ms ease',
                    transform: `scale(${isSelected ? 1.15 : isHovered ? 1.1 : 1})`,
                  }}
                >
                  {isSelected && (
                    <div
                      className="absolute inset-[-6px] rounded-full pointer-events-none"
                      style={{ border: '2px dashed #FBBF24', opacity: 0.6 }}
                    />
                  )}
                </div>

                {/* Label */}
                <div
                  className="absolute text-center pointer-events-none select-none"
                  style={{
                    left: '50%',
                    top: '100%',
                    transform: `translateX(-50%) translateY(4px)`,
                    width: 120,
                    opacity: transform.scale > 0.5 ? (isFiltered ? 1 : 0.1) : 0,
                    transition: 'opacity 200ms ease',
                  }}
                >
                  <span
                    className={cn(
                      'font-mono text-[11px] leading-tight block',
                      isSelected || isHovered ? 'text-[#EDE4D3]' : 'text-[#B8A88A]'
                    )}
                    style={{
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {node.title}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* --- Toolbar (floating, top-left) --- */}
        <motion.div
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] as [number, number, number, number], delay: 0.3 }}
          className="absolute top-4 left-4 z-40 flex items-center gap-2 px-3 py-2 rounded-lg border"
          style={{
            background: '#1C1712',
            borderColor: 'rgba(120, 53, 15, 0.15)',
            backdropFilter: 'blur(12px)',
            boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
          }}
        >
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 size-3.5 text-[#7A6B5A]" />
            <input
              type="text"
              placeholder="Find node..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-40 h-8 pl-7 pr-2 text-sm rounded-md border bg-transparent text-[#EDE4D3] placeholder-[#7A6B5A] outline-none focus:border-[#D97706] transition-colors"
              style={{ borderColor: 'rgba(120, 53, 15, 0.25)', background: '#0F0C09' }}
              onClick={(e) => e.stopPropagation()}
              onMouseDown={(e) => e.stopPropagation()}
            />
            {searchQuery && (
              <button
                className="absolute right-1.5 top-1/2 -translate-y-1/2 text-[#7A6B5A] hover:text-[#EDE4D3]"
                onClick={(e) => { e.stopPropagation(); setSearchQuery(''); }}
              >
                <X className="size-3" />
              </button>
            )}
          </div>

          <div className="w-px h-5 bg-[#78350F40]" />

          {/* Filter dropdown */}
          <div className="relative">
            <button
              className="flex items-center gap-1.5 h-8 px-2 text-sm rounded-md border text-[#B8A88A] hover:text-[#EDE4D3] hover:bg-[#251F18] transition-colors"
              style={{ borderColor: 'rgba(120, 53, 15, 0.25)', background: '#0F0C09' }}
              onClick={(e) => { e.stopPropagation(); setShowFilterDropdown(!showFilterDropdown); }}
            >
              <Filter className="size-3.5" />
              <span className="text-xs">{typeFilter === 'all' ? 'All Types' : TYPE_COLORS[typeFilter]?.label}</span>
            </button>
            <AnimatePresence>
              {showFilterDropdown && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.2 }}
                  className="absolute top-full mt-1 left-0 z-50 rounded-lg border shadow-xl py-1 min-w-[140px]"
                  style={{ background: '#1C1712', borderColor: 'rgba(120, 53, 15, 0.15)' }}
                >
                  <button
                    className={cn(
                      'w-full text-left px-3 py-1.5 text-xs flex items-center gap-2 hover:bg-[#251F18] transition-colors',
                      typeFilter === 'all' ? 'text-[#FBBF24]' : 'text-[#B8A88A]'
                    )}
                    onClick={(e) => { e.stopPropagation(); setTypeFilter('all'); setShowFilterDropdown(false); }}
                  >
                    <Circle className="size-2" /> All Types
                  </button>
                  {Object.entries(TYPE_COLORS).map(([key, val]) => (
                    <button
                      key={key}
                      className={cn(
                        'w-full text-left px-3 py-1.5 text-xs flex items-center gap-2 hover:bg-[#251F18] transition-colors',
                        typeFilter === key ? 'text-[#FBBF24]' : 'text-[#B8A88A]'
                      )}
                      onClick={(e) => { e.stopPropagation(); setTypeFilter(key); setShowFilterDropdown(false); }}
                    >
                      <span className="size-2 rounded-full" style={{ background: val.fill }} />
                      {val.label}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div className="w-px h-5 bg-[#78350F40]" />

          {/* Zoom controls */}
          <button onClick={(e) => { e.stopPropagation(); zoomOut(); }} className="size-8 flex items-center justify-center rounded-md hover:bg-[#251F18] text-[#B8A88A] hover:text-[#EDE4D3] transition-colors">
            <ZoomOut className="size-4" />
          </button>
          <span className="text-xs text-[#7A6B5A] font-mono w-10 text-center">{Math.round(transform.scale * 100)}%</span>
          <button onClick={(e) => { e.stopPropagation(); zoomIn(); }} className="size-8 flex items-center justify-center rounded-md hover:bg-[#251F18] text-[#B8A88A] hover:text-[#EDE4D3] transition-colors">
            <ZoomIn className="size-4" />
          </button>
          <button onClick={(e) => { e.stopPropagation(); resetView(); }} className="size-8 flex items-center justify-center rounded-md hover:bg-[#251F18] text-[#B8A88A] hover:text-[#EDE4D3] transition-colors" title="Reset view">
            <Maximize className="size-4" />
          </button>
        </motion.div>

        {/* --- Legend (bottom-left) --- */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6, duration: 0.4 }}
          className="absolute bottom-4 left-4 z-30 px-3 py-2 rounded-lg border"
          style={{
            background: '#1C1712',
            borderColor: 'rgba(120, 53, 15, 0.15)',
            backdropFilter: 'blur(8px)',
          }}
        >
          <div className="text-[10px] text-[#7A6B5A] font-mono mb-1.5 uppercase tracking-wider">Page Types</div>
          <div className="flex flex-col gap-1">
            {Object.entries(TYPE_COLORS).map(([key, val]) => (
              <div key={key} className="flex items-center gap-2">
                <span className="size-2.5 rounded-full shrink-0" style={{ background: val.fill }} />
                <span className="text-[11px] text-[#B8A88A]">{val.label}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* --- Node count info --- */}
        <div className="absolute bottom-4 right-4 z-30 text-[11px] text-[#7A6B5A] font-mono">
          {filteredNodes.length} / {nodes.length} nodes
          {selectedNode && (
            <span className="ml-3 text-[#B8A88A]">
              {connectedNodes.length} connections
            </span>
          )}
        </div>

        {/* --- Tooltip --- */}
        <AnimatePresence>
          {tooltip && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="fixed z-50 px-3 py-2 rounded-lg border pointer-events-none"
              style={{
                left: tooltip.x,
                top: tooltip.y,
                background: '#1C1712',
                borderColor: 'rgba(120, 53, 15, 0.2)',
                boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                transform: 'translate(-50%, 0)',
              }}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="size-2 rounded-full" style={{ background: TYPE_COLORS[tooltip.node.type].fill }} />
                <span className="text-xs font-medium text-[#EDE4D3]">{tooltip.node.title}</span>
              </div>
              <div className="text-[10px] text-[#B8A88A] font-mono">
                {TYPE_COLORS[tooltip.node.type].label} · {tooltip.node.wordCount.toLocaleString()} words
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* --- Detail Panel (right sidebar) --- */}
        <AnimatePresence>
          {selectedNode && (
            <>
              {/* Backdrop */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="absolute inset-0 z-30 bg-black/20"
                onClick={() => setSelectedNode(null)}
              />

              {/* Panel */}
              <motion.div
                initial={{ x: 340, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: 340, opacity: 0 }}
                transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
                className="absolute top-4 right-4 bottom-4 z-40 w-[300px] rounded-xl border flex flex-col overflow-hidden"
                style={{
                  background: '#1C1712',
                  borderColor: 'rgba(120, 53, 15, 0.15)',
                  boxShadow: '0 16px 48px rgba(0,0,0,0.6)',
                  backdropFilter: 'blur(16px)',
                }}
                onClick={(e) => e.stopPropagation()}
              >
                {/* Header */}
                <div className="p-5 border-b" style={{ borderColor: 'rgba(120, 53, 15, 0.1)' }}>
                  <button
                    onClick={() => setSelectedNode(null)}
                    className="absolute top-4 right-4 text-[#7A6B5A] hover:text-[#EDE4D3] transition-colors"
                  >
                    <X className="size-4" />
                  </button>

                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15, duration: 0.3 }}
                  >
                    <span
                      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] font-mono mb-3"
                      style={{
                        background: TYPE_COLORS[selectedNode.type].fill + '20',
                        color: TYPE_COLORS[selectedNode.type].fill,
                      }}
                    >
                      <span className="size-1.5 rounded-full" style={{ background: TYPE_COLORS[selectedNode.type].fill }} />
                      {TYPE_COLORS[selectedNode.type].label}
                    </span>

                    <h2 className="font-display text-xl font-medium text-[#EDE4D3] leading-tight">
                      {selectedNode.title}
                    </h2>

                    <div className="flex items-center gap-4 mt-3 text-[11px] text-[#B8A88A] font-mono">
                      <span className="flex items-center gap-1">
                        <GitFork className="size-3" />
                        {connectedNodes.length} connections
                      </span>
                      <span>{selectedNode.wordCount.toLocaleString()} words</span>
                    </div>
                  </motion.div>
                </div>

                {/* Connected nodes */}
                <div className="flex-1 overflow-y-auto p-5">
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.25, duration: 0.3 }}
                  >
                    <h3 className="text-[13px] font-semibold text-[#EDE4D3] mb-3">Connected to</h3>
                    <div className="flex flex-col gap-1">
                      {connectedNodes.map(({ node, strength }) => (
                        <button
                          key={node.id}
                          onClick={() => setSelectedNode(node)}
                          className="flex items-center gap-2.5 w-full text-left px-2.5 py-2 rounded-md hover:bg-[#251F18] transition-colors group"
                        >
                          <div className="relative h-6 flex items-center">
                            <div
                              className="w-1 rounded-full"
                              style={{
                                height: 12 + strength * 12,
                                background: '#D97706',
                                opacity: 0.6 + strength * 0.4,
                              }}
                            />
                          </div>
                          <span className="size-2 rounded-full shrink-0" style={{ background: TYPE_COLORS[node.type].fill }} />
                          <span className="text-xs text-[#B8A88A] group-hover:text-[#FBBF24] transition-colors truncate flex-1">
                            {node.title}
                          </span>
                          <span className="text-[10px] text-[#7A6B5A] font-mono">{Math.round(strength * 100)}%</span>
                        </button>
                      ))}
                    </div>

                    {/* Munger dimensions */}
                    <h3 className="text-[13px] font-semibold text-[#EDE4D3] mt-6 mb-3">Analyzed through</h3>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedNode.dimensions.map((dim) => (
                        <span
                          key={dim}
                          className="size-5 rounded-full flex items-center justify-center text-[9px] font-mono"
                          style={{
                            background: '#2D2620',
                            color: '#B8A88A',
                            border: '1px solid #78350F40',
                          }}
                          title={`Dimension ${dim}`}
                        >
                          {dim}
                        </span>
                      ))}
                    </div>
                  </motion.div>
                </div>

                {/* Actions */}
                <div className="p-5 border-t flex flex-col gap-2" style={{ borderColor: 'rgba(120, 53, 15, 0.1)' }}>
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.35, duration: 0.3 }}
                    className="flex flex-col gap-2"
                  >
                    <button
                      onClick={() => navigate(`/wiki/${selectedNode.slug}`)}
                      className="w-full h-9 flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-all hover:brightness-110 active:scale-[0.97]"
                      style={{ background: '#D97706', color: '#14100D' }}
                    >
                      Open Page
                      <ExternalLink className="size-3.5" />
                    </button>
                    <button
                      onClick={() => {
                        setTransform({
                          x: -(selectedNode.x - (containerRef.current?.clientWidth || 800) / 2),
                          y: -(selectedNode.y - (containerRef.current?.clientHeight || 600) / 2),
                          scale: 1.5,
                        });
                      }}
                      className="w-full h-9 flex items-center justify-center gap-2 rounded-md text-sm font-medium border text-[#EDE4D3] hover:bg-[#251F18] transition-all active:scale-[0.97]"
                      style={{ borderColor: '#78350F60' }}
                    >
                      Focus in Graph
                      <Focus className="size-3.5" />
                    </button>
                  </motion.div>
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
