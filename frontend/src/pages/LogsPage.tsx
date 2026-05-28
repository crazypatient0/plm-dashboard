import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { fetchLogs } from '../api/client';
import type { ScrapeLog } from '../types';

type DataType = 'part' | 'document' | 'conversion';

const DATA_TYPES: { value: DataType | ''; label: string }[] = [
  { value: '', label: 'All' },
  { value: 'part', label: 'Parts' },
  { value: 'document', label: 'Documents' },
  { value: 'conversion', label: 'Conversion' },
];

const LIMIT_OPTIONS = [20, 50, 100, 200];

const TYPE_COLORS: Record<string, string> = {
  part: '#60a5fa',
  document: '#34d399',
  conversion: '#c084fc',
};

const STATUS_BADGE: Record<string, 'success' | 'running' | 'error' | 'idle'> = {
  success: 'success',
  running: 'running',
  error: 'error',
  skipped: 'idle',
};

const STATUS_DOT_COLORS: Record<string, string> = {
  success: '#10b981',
  running: '#f59e0b',
  error: '#ef4444',
  skipped: '#64748b',
};

function fmtTime(iso: string | null): string {
  if (!iso) return '---';
  const d = new Date(iso);
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

function StatCard({ label, value, accent }: { label: string; value: string | number; accent?: string }) {
  return (
    <div className="log-stat-card" style={accent ? { borderLeftColor: accent } : {}}>
      <div className="log-stat-label">{label}</div>
      <div className="log-stat-value" style={accent ? { color: accent } : {}}>{value}</div>
    </div>
  );
}

export default function LogsPage() {
  const [dataType, setDataType] = useState<DataType | ''>('part');
  const [limit, setLimit] = useState(50);
  const [secondsLeft, setSecondsLeft] = useState(30);

  const { data, loading, refetch } = useApi(
    () => fetchLogs(dataType || undefined, limit),
    [dataType, limit],
  );

  const logs: ScrapeLog[] = data ?? [];

  // Summary stats
  const successCount = logs.filter((l) => l.status === 'success').length;
  const errorCount = logs.filter((l) => l.status === 'error').length;
  const lastError = logs.find((l) => l.status === 'error');
  const lastSuccess = logs.find((l) => l.status === 'success');

  // Auto-refresh countdown
  useEffect(() => {
    setSecondsLeft(30);
    const tid = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          refetch();
          return 30;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(tid);
  }, [dataType, limit]);

  return (
    <div>
      {/* Header */}
      <div className="section">
        <div className="section-header">
          <div>
            <h2 className="section-title">Scrape Logs</h2>
            <div className="text-secondary text-sm" style={{ marginTop: 4, paddingLeft: 2 }}>
              Auto-refresh in{' '}
              <span style={{ color: 'var(--color-primary)', fontWeight: 600 }}>{secondsLeft}s</span>
            </div>
          </div>
          <button className="btn btn-sm" onClick={refetch}>Refresh</button>
        </div>
      </div>

      {/* Summary stats */}
      {!loading && logs.length > 0 && (
        <div className="log-stats-row">
          <StatCard label="Total" value={logs.length} />
          <StatCard label="Success" value={successCount} accent="#10b981" />
          <StatCard label="Errors" value={errorCount} accent="#ef4444" />
          <StatCard
            label="Last Error"
            value={lastError ? fmtTime(lastError.started_at) : 'None'}
            accent="#ef4444"
          />
        </div>
      )}

      {/* Filters */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="card-body" style={{ padding: '12px 20px' }}>
          <div className="log-filters">
            {/* DataType tabs */}
            <div className="log-tabs">
              {DATA_TYPES.map((dt) => (
                <button
                  key={dt.value}
                  className={`log-tab${dataType === dt.value ? ' active' : ''}`}
                  onClick={() => setDataType(dt.value as DataType | '')}
                >
                  {dt.label}
                </button>
              ))}
            </div>

            {/* Limit selector */}
            <div className="log-limit-group">
              <span className="text-secondary text-sm">Show</span>
              {LIMIT_OPTIONS.map((opt) => (
                <button
                  key={opt}
                  className={`log-limit-btn${limit === opt ? ' active' : ''}`}
                  onClick={() => setLimit(opt)}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="data-table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: 4, padding: 0 }} />
              <th>Started</th>
              <th>Type</th>
              <th>Status</th>
              <th>Records</th>
              <th>Completed</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <>
                {Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    <td style={{ padding: 0 }}><div className="skeleton" /></td>
                    {[...Array(6)].map((_, j) => (
                      <td key={j}><div className="skeleton">&nbsp;</div></td>
                    ))}
                  </tr>
                ))}
              </>
            )}
            {!loading && logs.length === 0 && (
              <tr>
                <td colSpan={7} className="data-table-empty">No log entries found.</td>
              </tr>
            )}
            {!loading && logs.map((log) => {
              const badge = STATUS_BADGE[log.status] ?? 'idle';
              const dotColor = STATUS_DOT_COLORS[badge] ?? '#64748b';
              const typeColor = TYPE_COLORS[log.data_type] ?? '#94a3b8';
              return (
                <tr key={log.id}>
                  {/* Status indicator bar */}
                  <td style={{ padding: 0, width: 4 }}>
                    <div style={{
                      width: 3,
                      height: '100%',
                      minHeight: 44,
                      background: dotColor,
                      opacity: 0.7,
                    }} />
                  </td>
                  {/* Started */}
                  <td>
                    <span className="text-sm text-secondary">
                      {fmtTime(log.started_at)}
                    </span>
                  </td>
                  {/* Type */}
                  <td>
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                      fontSize: 13,
                      fontWeight: 500,
                    }}>
                      <span style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: typeColor,
                        flexShrink: 0,
                      }} />
                      <span style={{ color: typeColor, textTransform: 'capitalize' }}>
                        {log.data_type}
                      </span>
                    </span>
                  </td>
                  {/* Status badge */}
                  <td>
                    <span className={`status-badge badge-${badge}`}>
                      <span className="status-dot" style={{ background: dotColor, boxShadow: `0 0 4px ${dotColor}60` }} />
                      {log.status}
                    </span>
                  </td>
                  {/* Records */}
                  <td>
                    <span className="text-sm" style={{ fontWeight: 500 }}>
                      {log.records_count.toLocaleString()}
                    </span>
                  </td>
                  {/* Completed */}
                  <td>
                    <span className="text-sm text-secondary">
                      {fmtTime(log.completed_at)}
                    </span>
                  </td>
                  {/* Error */}
                  <td>
                    {log.error_message ? (
                      <span
                        className="text-sm"
                        style={{ color: 'var(--color-danger)', maxWidth: 280, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                        title={log.error_message}
                      >
                        {log.error_message}
                      </span>
                    ) : (
                      <span className="text-secondary text-sm">---</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <style>{`
        .log-stats-row {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 12px;
          margin-bottom: 16px;
        }
        .log-stat-card {
          background: var(--color-surface);
          border: 1px solid var(--color-border);
          border-left: 3px solid var(--color-border);
          border-radius: var(--radius);
          padding: 12px 16px;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .log-stat-label {
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: var(--color-text-muted);
        }
        .log-stat-value {
          font-size: 18px;
          font-weight: 700;
          color: var(--color-text);
          letter-spacing: -0.01em;
        }
        .log-filters {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          flex-wrap: wrap;
        }
        .log-tabs {
          display: flex;
          gap: 2px;
          background: rgba(255,255,255,0.03);
          border: 1px solid var(--color-border);
          border-radius: var(--radius);
          padding: 3px;
        }
        .log-tab {
          padding: 5px 16px;
          border: none;
          border-radius: 5px;
          background: transparent;
          color: var(--color-text-muted);
          font-size: 13px;
          font-weight: 500;
          font-family: var(--font-family);
          cursor: pointer;
          transition: all 160ms ease;
        }
        .log-tab:hover {
          color: var(--color-text);
          background: rgba(255,255,255,0.05);
        }
        .log-tab.active {
          background: var(--color-primary);
          color: #0a0e17;
          font-weight: 700;
        }
        .log-limit-group {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .log-limit-btn {
          padding: 4px 10px;
          border: 1px solid var(--color-border);
          border-radius: var(--radius-sm);
          background: transparent;
          color: var(--color-text-muted);
          font-size: 12px;
          font-weight: 500;
          font-family: var(--font-family);
          cursor: pointer;
          transition: all 120ms ease;
        }
        .log-limit-btn:hover {
          border-color: var(--color-border-light);
          color: var(--color-text);
        }
        .log-limit-btn.active {
          background: rgba(245,158,11,0.12);
          border-color: rgba(245,158,11,0.3);
          color: var(--color-primary);
          font-weight: 700;
        }
        @media (max-width: 640px) {
          .log-stats-row { grid-template-columns: repeat(2, 1fr); }
        }
      `}</style>
    </div>
  );
}
