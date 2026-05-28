import { useState, useEffect } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LabelList,
} from 'recharts';
import { fetchPartStats } from '../api/client';
import type { PartStatsResponse } from '../types';

const COLORS = {
  Normal: '#60a5fa',
  MigPartsBlocked: '#f87171',
  TemplateNotFilled: '#fb923c',
  surface: '#131822',
  border: '#1e293b',
  amber: '#f59e0b',
};

const LABELS: Record<string, string> = {
  Normal: 'Normal',
  MigPartsBlocked: 'MigParts Blocked',
  TemplateNotFilled: 'Template Not Filled',
};

function PieTooltip({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number }> }) {
  if (!active || !payload?.length) return null;
  const { name, value } = payload[0];
  return (
    <div style={{
      background: COLORS.surface,
      border: '1px solid var(--color-border)',
      borderRadius: 6,
      padding: '8px 14px',
      fontSize: 13,
      fontFamily: 'var(--font-family)',
      boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
    }}>
      <div style={{ color: '#94a3b8', marginBottom: 2 }}>{LABELS[name] ?? name}</div>
      <div style={{ color: '#f1f5f9', fontSize: 18, fontWeight: 600 }}>{value}</div>
    </div>
  );
}

function BarTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; fill: string }>; label?: string }) {
  if (!active || !payload?.length) return null;
  const total = payload.reduce((s, p) => s + p.value, 0);
  return (
    <div style={{
      background: COLORS.surface,
      border: '1px solid var(--color-border)',
      borderRadius: 6,
      padding: '10px 16px',
      fontSize: 13,
      fontFamily: 'var(--font-family)',
      boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
      minWidth: 160,
    }}>
      <div style={{ color: '#f1f5f9', fontWeight: 600, marginBottom: 8, fontSize: 14 }}>{label}</div>
      {payload.slice().reverse().map((p) => (
        <div key={p.name} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 4 }}>
          <span style={{ color: p.fill }}>{LABELS[p.name] ?? p.name}</span>
          <span style={{ color: '#f1f5f9', fontWeight: 500 }}>{p.value}</span>
        </div>
      ))}
      <div style={{ borderTop: '1px solid var(--color-border)', marginTop: 8, paddingTop: 8, display: 'flex', justifyContent: 'space-between', gap: 16 }}>
        <span style={{ color: '#94a3b8' }}>Total</span>
        <span style={{ color: '#f59e0b', fontWeight: 600 }}>{total}</span>
      </div>
    </div>
  );
}

function BarValueLabel({ x, y, width, value }: { x: number; y: number; width: number; value: number }) {
  if (value === 0) return null;
  return (
    <text
      x={x + width / 2}
      y={y - 6}
      textAnchor="middle"
      fill="#94a3b8"
      fontSize={11}
      fontFamily="var(--font-family)"
    >
      {value}
    </text>
  );
}

export default function PartsPage() {
  const [stats, setStats] = useState<PartStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = () => {
      fetchPartStats()
        .then((data) => { setStats(data); setLoading(false); })
        .catch(() => setLoading(false));
    };
    load();
    const tid = setInterval(load, 30_000);
    return () => clearInterval(tid);
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 320 }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 40, height: 40, borderRadius: '50%',
            border: `3px solid var(--color-border)`,
            borderTop: `3px solid ${COLORS.amber}`,
            animation: 'spin 0.8s linear infinite',
          }} />
          <span className="text-secondary text-sm">Loading...</span>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 320 }}>
        <span className="text-secondary text-sm">Failed to load stats.</span>
      </div>
    );
  }

  const { category_breakdown, daily_breakdown } = stats;
  const total = category_breakdown.reduce((s, c) => s + c.value, 0);

  return (
    <div>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        .chart-card:hover .chart-inner { transform: translateY(-2px); }
        .recharts-wrapper:focus { outline: none !important; }
        .recharts-wrapper svg { outline: none !important; }
        .recharts-surface:focus { outline: none !important; }
        svg.recharts-surface { outline: none !important; }
        .recharts-sector:focus { outline: none !important; }
        .recharts-sector { outline: none !important; }
        .recharts-pie-sector { outline: none !important; }
        .recharts-bar:focus { outline: none !important; }
        .recharts-bar-rectangle:focus { outline: none !important; }
        .recharts-layer:focus { outline: none !important; }
        g:focus { outline: none !important; }
      `}</style>

      <div className="section">
        <div className="section-header">
          <h2 className="section-title">Parts - Data Analysis</h2>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-6)', marginBottom: 'var(--spacing-6)' }}>

        {/* Donut chart */}
        <div className="card chart-card" style={{ overflow: 'hidden' }}>
          <div style={{
            padding: '20px 24px 12px',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <h3 style={{ fontSize: 15, fontWeight: 600, color: '#f1f5f9', margin: 0, letterSpacing: 0.3 }}>
              SAP Status Breakdown
            </h3>
            <span style={{ fontSize: 12, color: '#475569', background: '#1e293b', padding: '2px 10px', borderRadius: 20 }}>
              {category_breakdown.filter(c => c.value > 0).length} categories
            </span>
          </div>
          <div className="card-body chart-inner" style={{ transition: 'transform 0.2s ease', padding: '20px 24px 24px' }}>
            {total === 0 ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#475569' }}>No data</div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1.7fr 1fr', gap: 24, alignItems: 'center' }}>
                {/* Donut */}
                <div style={{ position: 'relative' }}>
                  <ResponsiveContainer width="100%" height={320}>
                    <PieChart>
                      <Pie
                        data={category_breakdown}
                        cx="50%"
                        cy="50%"
                        innerRadius={70}
                        outerRadius={105}
                        paddingAngle={2}
                        dataKey="value"
                        strokeWidth={0}
                      >
                        {category_breakdown.map((entry) => (
                          <Cell key={entry.name} fill={COLORS[entry.name as keyof typeof COLORS] ?? '#475569'} />
                        ))}
                      </Pie>
                      <Tooltip content={<PieTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                  {/* Center total — absolutely positioned over the donut hole */}
                  <div style={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    textAlign: 'center',
                    pointerEvents: 'none',
                  }}>
                    <div style={{ color: '#64748b', fontSize: 11, marginBottom: 2 }}>Total</div>
                    <div style={{ color: '#f1f5f9', fontSize: 28, fontWeight: 700, lineHeight: 1 }}>{total}</div>
                  </div>
                </div>

                {/* Breakdown list */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {category_breakdown.map((cat) => {
                    const pct = total > 0 ? ((cat.value / total) * 100).toFixed(1) : '0.0';
                    return (
                      <div key={cat.name} style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        borderRadius: 6,
                        background: cat.value > 0 ? '#1a2233' : 'transparent',
                        border: '1px solid var(--color-border)',
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{
                            width: 10, height: 10, borderRadius: '50%',
                            background: COLORS[cat.name as keyof typeof COLORS] ?? '#475569',
                            flexShrink: 0,
                          }} />
                          <span style={{ color: cat.value > 0 ? '#e2e8f0' : '#475569', fontSize: 13 }}>
                            {LABELS[cat.name] ?? cat.name}
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                          <span style={{ color: '#94a3b8', fontSize: 13 }}>{cat.value}</span>
                          <span style={{
                            color: cat.value > 0 ? COLORS[cat.name as keyof typeof COLORS] ?? '#94a3b8' : '#475569',
                            fontSize: 12, fontWeight: 600, minWidth: 44, textAlign: 'right',
                          }}>
                            {cat.value > 0 ? `${pct}%` : '--'}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Stacked bar chart */}
        <div className="card chart-card" style={{ overflow: 'hidden' }}>
          <div style={{
            padding: '20px 24px 12px',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <h3 style={{ fontSize: 15, fontWeight: 600, color: '#f1f5f9', margin: 0, letterSpacing: 0.3 }}>
              Daily Processing Volume
            </h3>
            <span style={{ fontSize: 12, color: '#475569', background: '#1e293b', padding: '2px 10px', borderRadius: 20 }}>
              {daily_breakdown.length} days
            </span>
          </div>
          <div className="card-body chart-inner" style={{ transition: 'transform 0.2s ease', padding: '20px 20px 24px' }}>
            {daily_breakdown.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#475569' }}>No data</div>
            ) : (
              <ResponsiveContainer width="100%" height={360}>
                <BarChart data={daily_breakdown} margin={{ top: 20, right: 8, left: 36, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12, fill: '#64748b' }}
                    tickFormatter={(v) => v.slice(5)}
                    axisLine={{ stroke: '#1e293b' }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 12, fill: '#64748b' }}
                    allowDecimals={false}
                    axisLine={false}
                    tickLine={false}
                    width={32}
                  />
                  <Tooltip content={<BarTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                  <Legend
                    iconType="circle"
                    iconSize={8}
                    formatter={(value) => (
                      <span style={{ color: '#94a3b8', fontSize: 13, fontFamily: 'var(--font-family)' }}>
                        {LABELS[value] ?? value}
                      </span>
                    )}
                    wrapperStyle={{ paddingTop: 12 }}
                  />
                  <Bar dataKey="Normal" stackId="a" fill={COLORS.Normal} radius={[0, 0, 0, 0]} />
                  <Bar dataKey="MigPartsBlocked" stackId="a" fill={COLORS.MigPartsBlocked} radius={[0, 0, 0, 0]} />
                  <Bar dataKey="TemplateNotFilled" stackId="a" fill={COLORS.TemplateNotFilled} radius={[0, 0, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
