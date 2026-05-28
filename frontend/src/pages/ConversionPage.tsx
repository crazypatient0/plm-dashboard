import { useState, useEffect } from 'react';
import { fetchConversionStats } from '../api/client';
import type { ConversionStatsResponse } from '../types';

function fmtWait(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.round(seconds % 60);
  return `${h}h ${m}m ${s}s`;
}

function fmtCreatedTime(utc: string | null): string {
  if (!utc) return '---';
  // Parse UTC ISO string and convert to BJ local time
  const d = new Date(utc.endsWith('Z') ? utc : utc + 'Z');
  if (isNaN(d.getTime())) return '---';
  return d.toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    hour12: false,
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

const STATE_COLORS: Record<string, string> = {
  failed: '#EF4444',
  waiting: '#3B82F6',
  processing: '#F59E0B',
  completed: '#22C55E',
  unknown: '#6B7280',
};

function StateBadge({ state }: { state: string }) {
  const color = STATE_COLORS[state.toLowerCase()] ?? STATE_COLORS.unknown;
  return (
    <span style={{
      fontSize: 11,
      fontWeight: 600,
      padding: '2px 8px',
      borderRadius: 20,
      background: `${color}22`,
      color: color,
      border: `1px solid ${color}44`,
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
    }}>
      {state}
    </span>
  );
}

export default function ConversionPage() {
  const [stats, setStats] = useState<ConversionStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [secondsLeft, setSecondsLeft] = useState(30);

  useEffect(() => {
    const load = () => {
      fetchConversionStats()
        .then((data) => { setStats(data); setLoading(false); })
        .catch(() => setLoading(false));
    };
    load();
    const tid = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) { load(); return 30; }
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
            border: `3px solid var(--color-border)`,
            borderTop: `3px solid #F59E0B`,
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

  const { items, total, failed_count } = stats;
  const maxWait = items.reduce(
    (max, item) => Math.max(max, item.wait_seconds ?? 0),
    0
  );
  const waiting_count = total - failed_count;

  return (
    <div>
      <style>{`
        .recharts-wrapper:focus { outline: none !important; }
        .recharts-wrapper svg { outline: none !important; }
        .recharts-surface:focus { outline: none !important; }
        svg.recharts-surface { outline: none !important; }
        .race-row:hover { background: rgba(255,255,255,0.03); }
        .race-row { transition: background 0.15s ease; }
        @keyframes race-in {
          from { width: 0; opacity: 0.4; }
          to   { width: var(--bar-width); opacity: 1; }
        }
        .race-bar {
          animation: race-in 1.2s cubic-bezier(0.22, 0.61, 0.36, 1) forwards;
        }
      `}</style>

      <div className="section">
        <div className="section-header">
          <div>
            <h2 className="section-title">Conversion — Race Track</h2>
            <div className="text-secondary text-sm" style={{ marginTop: 4, paddingLeft: 2 }}>
              Auto-refresh in{' '}
              <span style={{ color: 'var(--color-primary)', fontWeight: 600 }}>{secondsLeft}s</span>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
        <div className="card" style={{ padding: '12px 16px' }}>
          <div style={{ fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Total</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-text)', marginTop: 4 }}>{total}</div>
        </div>
        <div className="card" style={{ padding: '12px 16px' }}>
          <div style={{ fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Failed</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#EF4444', marginTop: 4 }}>{failed_count}</div>
        </div>
        <div className="card" style={{ padding: '12px 16px' }}>
          <div style={{ fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Waiting</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#3B82F6', marginTop: 4 }}>{waiting_count}</div>
        </div>
        <div className="card" style={{ padding: '12px 16px' }}>
          <div style={{ fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Max Wait</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#F59E0B', marginTop: 4 }}>{maxWait > 0 ? fmtWait(maxWait) : '---'}</div>
        </div>
      </div>

      {/* Race Track */}
      {items.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 40, color: '#475569' }}>
          No conversion records.
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {/* Header */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '48px 1fr 90px 90px 90px',
            gap: 12,
            padding: '10px 20px',
            borderBottom: '1px solid var(--color-border)',
            background: '#0d1117',
          }}>
            <div style={{ fontSize: 11, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600, textAlign: 'center' }}>#</div>
            <div style={{ fontSize: 11, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Source</div>
            <div style={{ fontSize: 11, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>State</div>
            <div style={{ fontSize: 11, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Created (BJ)</div>
            <div style={{ fontSize: 11, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Wait Time</div>
          </div>

          {/* Track rows */}
          <div style={{ maxHeight: 600, overflow: 'auto' }}>
            {items.map((item, idx) => {
              const pct = maxWait > 0 && item.wait_seconds != null
                ? (item.wait_seconds / maxWait) * 100
                : 0;
              const stateLower = item.state.toLowerCase();
              const barColor = STATE_COLORS[stateLower] ?? STATE_COLORS.unknown;

              return (
                <div
                  key={item.source}
                  className="race-row"
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '48px 1fr 90px 90px 90px',
                    gap: 12,
                    padding: '10px 20px',
                    borderBottom: '1px solid var(--color-border)',
                    alignItems: 'center',
                  }}
                >
                  {/* Rank */}
                  <div style={{ fontSize: 13, color: '#475569', textAlign: 'center', fontWeight: 600 }}>
                    {idx + 1}
                  </div>

                  {/* Source + progress bar */}
                  <div>
                    <div style={{ fontSize: 13, color: '#e2e8f0', fontWeight: 500, marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.source}
                    </div>
                    {/* Race progress bar */}
                    <div style={{ height: 4, background: '#1e293b', borderRadius: 2, overflow: 'hidden' }}>
                      <div
                        className="race-bar"
                        style={{
                          '--bar-width': `${pct}%`,
                          height: '100%',
                          width: `${pct}%`,
                          background: barColor,
                          borderRadius: 2,
                        } as React.CSSProperties}
                      />
                    </div>
                  </div>

                  {/* State */}
                  <div><StateBadge state={item.state} /></div>

                  {/* Created time */}
                  <div style={{ fontSize: 12, color: '#94a3b8', fontFamily: 'var(--font-family)' }}>
                    {fmtCreatedTime(item.created_utc)}
                  </div>

                  {/* Wait time */}
                  <div style={{ fontSize: 13, fontWeight: 700, color: item.wait_seconds != null && item.wait_seconds > 3600 ? '#F59E0B' : '#e2e8f0', fontFamily: 'var(--font-family)' }}>
                    {item.wait_seconds != null ? fmtWait(item.wait_seconds) : '---'}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
