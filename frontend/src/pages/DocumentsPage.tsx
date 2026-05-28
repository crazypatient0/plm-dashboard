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
} from 'recharts';
import { fetchDocumentStats } from '../api/client';
import type { DocumentStatsResponse } from '../types';

interface CategoryItem {
  name: string;
  value: number;
}

interface DailyItem {
  date: string;
  Normal: number;
  StatusFlowError: number;
  MissingOriginals: number;
}

const COLORS: Record<string, string> = {
  Normal: '#60a5fa',
  StatusFlowError: '#f87171',
  MissingOriginals: '#f59e0b',
};

const LABELS: Record<string, string> = {
  Normal: 'Normal',
  StatusFlowError: 'Status/Flow Error',
  MissingOriginals: 'Missing Originals',
};

const CATEGORY_KEYS = ['Normal', 'StatusFlowError', 'MissingOriginals'];

function PieTooltip({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number }> }) {
  if (!active || !payload?.length) return null;
  const { name, value } = payload[0];
  return (
    <div style={{
      background: '#131822',
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
      background: '#131822',
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

export default function DocumentsPage() {
  const [stats, setStats] = useState<DocumentStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [secondsLeft, setSecondsLeft] = useState(30);

  useEffect(() => {
    const load = () => {
      fetchDocumentStats()
        .then((data) => { setStats(data); setLoading(false); })
        .catch(() => setLoading(false));
    };
    load();
    const tid = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          load();
          return 30;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(tid);
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 320 }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 40, height: 40, borderRadius: '50%',
            border: '3px solid var(--color-border)',
            borderTop: '3px solid #f59e0b',
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

  // Transform nested API response into flat arrays for recharts
  const categoryBreakdown: CategoryItem[] = Object.entries(stats.category_breakdown).map(([name, value]) => ({ name, value }));
  const total = stats.total;

  const dailyBreakdown: DailyItem[] = stats.daily_breakdown.map((d) => ({
    date: d.date,
    Normal: d.categories.Normal ?? 0,
    StatusFlowError: d.categories.StatusFlowError ?? 0,
    MissingOriginals: d.categories.MissingOriginals ?? 0,
  }));

  return (
    <div>
      <style>{`
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
          <div>
            <h2 className="section-title">Document Records</h2>
            <div className="text-secondary text-sm" style={{ marginTop: 4, paddingLeft: 2 }}>
              Auto-refresh in{' '}
              <span style={{ color: 'var(--color-primary)', fontWeight: 600 }}>{secondsLeft}s</span>
            </div>
          </div>
        </div>
      </div>

      {/* Summary cards row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
        <div className="card" style={{ padding: '12px 16px' }}>
          <div style={{ fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Total</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-text)', marginTop: 4 }}>{total}</div>
        </div>
        {CATEGORY_KEYS.map((key) => {
          const item = categoryBreakdown.find((c) => c.name === key);
          const count = item?.value ?? 0;
          return (
            <div key={key} className="card" style={{ padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[key], flexShrink: 0 }} />
                {LABELS[key]}
              </div>
              <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-text)', marginTop: 4 }}>{count}</div>
            </div>
          );
        })}
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
              Category Breakdown
            </h3>
            <span style={{ fontSize: 12, color: '#475569', background: '#1e293b', padding: '2px 10px', borderRadius: 20 }}>
              {categoryBreakdown.filter((c) => c.value > 0).length} categories
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
                        data={categoryBreakdown}
                        cx="50%"
                        cy="50%"
                        innerRadius={70}
                        outerRadius={105}
                        paddingAngle={2}
                        dataKey="value"
                        strokeWidth={0}
                      >
                        {categoryBreakdown.map((entry) => (
                          <Cell key={entry.name} fill={COLORS[entry.name] ?? '#475569'} />
                        ))}
                      </Pie>
                      <Tooltip content={<PieTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                  {/* Center total */}
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
                  {categoryBreakdown.map((cat) => {
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
                            background: COLORS[cat.name] ?? '#475569',
                            flexShrink: 0,
                          }} />
                          <span style={{ color: cat.value > 0 ? '#e2e8f0' : '#475569', fontSize: 13 }}>
                            {LABELS[cat.name] ?? cat.name}
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                          <span style={{ color: '#94a3b8', fontSize: 13 }}>{cat.value}</span>
                          <span style={{
                            color: cat.value > 0 ? COLORS[cat.name] ?? '#94a3b8' : '#475569',
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
              {dailyBreakdown.length} days
            </span>
          </div>
          <div className="card-body chart-inner" style={{ transition: 'transform 0.2s ease', padding: '20px 20px 24px' }}>
            {dailyBreakdown.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#475569' }}>No data</div>
            ) : (
              <ResponsiveContainer width="100%" height={360}>
                <BarChart data={dailyBreakdown} margin={{ top: 20, right: 8, left: 36, bottom: 0 }}>
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
                  <Bar dataKey="StatusFlowError" stackId="a" fill={COLORS.StatusFlowError} radius={[0, 0, 0, 0]} />
                  <Bar dataKey="MissingOriginals" stackId="a" fill={COLORS.MissingOriginals} radius={[0, 0, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
