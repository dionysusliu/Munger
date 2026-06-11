/**
 * MapProgressDonut — tiny donut chart for map-phase fan-out progress.
 *
 * Shows done / running / failed / pending slices.
 * Center label: "{done}/{total}".
 * Renders nothing when total === 0.
 */
import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import type { MapProgress } from '@/lib/api';

interface DonutSlice {
  name: string;
  value: number;
  fill: string;
}

function buildSlices(p: MapProgress): DonutSlice[] {
  return [
    { name: 'done', value: p.done, fill: '#4ade80' },    // green-400
    { name: 'running', value: p.running, fill: '#f59e0b' }, // amber-400
    { name: 'failed', value: p.failed, fill: '#f87171' }, // red-400
    { name: 'pending', value: p.pending, fill: '#404040' }, // neutral-700
  ].filter((s) => s.value > 0);
}

export interface MapProgressDonutProps {
  progress: MapProgress;
}

const MapProgressDonut = React.memo(function MapProgressDonut({
  progress,
}: MapProgressDonutProps) {
  if (progress.total === 0) return null;

  const slices = buildSlices(progress);

  return (
    <div className="flex flex-col items-center gap-1">
      <p className="text-mono-sm text-text-muted">Chunks</p>
      <div className="relative" style={{ width: 96, height: 96 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={slices}
              innerRadius={30}
              outerRadius={44}
              paddingAngle={slices.length > 1 ? 2 : 0}
              dataKey="value"
              startAngle={90}
              endAngle={-270}
              isAnimationActive={false}
              stroke="none"
            >
              {slices.map((slice) => (
                <Cell key={slice.name} fill={slice.fill} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        {/* Center label */}
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-sm font-bold tabular-nums text-neutral-200">
            {progress.done}
          </span>
          <span className="text-[10px] tabular-nums text-neutral-500">
            /{progress.total}
          </span>
        </div>
      </div>

      {/* Legend row */}
      <div className="flex flex-wrap justify-center gap-x-2 gap-y-0.5">
        {progress.failed > 0 && (
          <span className="text-[9px] text-red-400">{progress.failed} failed</span>
        )}
        {progress.running > 0 && (
          <span className="text-[9px] text-amber-400">{progress.running} running</span>
        )}
        {progress.pending > 0 && (
          <span className="text-[9px] text-neutral-500">{progress.pending} pending</span>
        )}
      </div>
    </div>
  );
});

export default MapProgressDonut;
