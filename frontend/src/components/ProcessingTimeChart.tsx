import { useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LabelList,
  ResponsiveContainer,
} from 'recharts';
import { fetchProcessingTime } from '../api/client';
import type { ProcessingTimeResponse } from '../types';

interface Props {
  dataType: 'part' | 'document';
  refreshKey?: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius)',
        padding: '8px 12px',
      }}
    >
      <div style={{ color: 'var(--color-text)', fontWeight: 600, fontSize: 14 }}>{label}</div>
      <div style={{ color: 'var(--color-primary)', fontSize: 13 }}>Count: {payload[0].value}</div>
    </div>
  );
}

function formatSeconds(totalSeconds: number | null): string {
  if (totalSeconds === null || totalSeconds === undefined) return '--';
  if (totalSeconds < 60) return `${Math.round(totalSeconds)}s`;
  if (totalSeconds < 3600) {
    const m = Math.floor(totalSeconds / 60);
    const s = Math.round(totalSeconds % 60);
    return s > 0 ? `${m}m ${s}s` : `${m}m`;
  }
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'empty' }
  | { status: 'data'; data: ProcessingTimeResponse };

export default function ProcessingTimeChart({ dataType, refreshKey = 0 }: Props) {
  const [state, setState] = useState<LoadState>({ status: 'loading' });
  const [showAvg, setShowAvg] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setState({ status: 'loading' });

    fetchProcessingTime(dataType)
      .then((res) => {
        if (cancelled) return;
        if (res.total_items === 0 || res.distribution.length === 0) {
          setState({ status: 'empty' });
        } else {
          setState({ status: 'data', data: res });
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setState({
          status: 'error',
          message:
            err instanceof Error ? err.message : 'Failed to load processing time data',
        });
      });

    return () => {
      cancelled = true;
    };
  }, [dataType, refreshKey]);

  const toggleStat = () => setShowAvg((p) => !p);

  // ---- Loading ----
  if (state.status === 'loading') {
    return (
      <div className="text-secondary text-sm" style={{ padding: '24px', textAlign: 'center' }}>
        Loading...
      </div>
    );
  }

  // ---- Error ----
  if (state.status === 'error') {
    return (
      <div className="text-secondary text-sm" style={{ padding: '24px', textAlign: 'center', color: 'var(--color-danger)' }}>
        Error: {state.message}
      </div>
    );
  }

  // ---- Empty ----
  if (state.status === 'empty') {
    return (
      <div className="text-secondary text-sm" style={{ padding: '24px', textAlign: 'center' }}>
        No processing time data available. Items need at least 2 history records to calculate duration.
      </div>
    );
  }

  // ---- Data ----
  const { data } = state;
  const total = data.distribution.reduce((s, b) => s + b.count, 0);
  const chartData = data.distribution.map((b) => ({
    label: b.label,
    count: b.count,
    pct: total > 0 ? Math.round((b.count / total) * 100) : 0,
  }));
  const maxCount = Math.max(...chartData.map((d) => d.count), 5);
  const yMax = Math.ceil(maxCount / 5) * 5;
  const yTicks = Array.from({ length: yMax / 5 + 1 }, (_, i) => i * 5);

  return <>

      {/* Stats row */}
      <div
        className="stats-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 'var(--spacing-4)',
          marginBottom: 'var(--spacing-5)',
        }}
      >
        <div className="stat-card" style={{ cursor: 'pointer' }} onClick={toggleStat} title="Click to toggle avg/median">
          <div className="stat-body">
            <div className="stat-title">{showAvg ? 'Average' : 'Median'}</div>
            <div className="stat-value">{formatSeconds(showAvg ? data.average_seconds : data.median_seconds)}</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-body">
            <div className="stat-title">Min</div>
            <div className="stat-value">{formatSeconds(data.min_seconds)}</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-body">
            <div className="stat-title">Max</div>
            <div className="stat-value">{formatSeconds(data.max_seconds)}</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-body">
            <div className="stat-title">Items Tracked</div>
            <div className="stat-value">{data.total_items}</div>
          </div>
        </div>
      </div>

      {/* Bar chart */}
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 12, fill: 'var(--color-text-secondary)' }}
            axisLine={{ stroke: 'var(--color-border)' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12, fill: 'var(--color-text-secondary)' }}
            axisLine={false}
            tickLine={false}
            domain={[0, yMax]}
            ticks={yTicks}
          />
          <Tooltip content={<CustomTooltip />} cursor={false} />
          <Bar dataKey="count" fill="var(--color-primary)" radius={[4, 4, 0, 0]} activeBar={{ fill: 'var(--color-primary)', stroke: 'none' }} isAnimationActive={false}>
            <LabelList dataKey="count" position="top" fill="var(--color-text)" fontSize={13} fontWeight={600} />
            <LabelList dataKey="pct" position="center" fill="var(--color-bg)" fontSize={13} fontWeight={700} formatter={(v: unknown) => `${(v as number) ?? 0}%`} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </>;
}
