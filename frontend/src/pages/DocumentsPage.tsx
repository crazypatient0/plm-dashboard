import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { fetchRecordsCount, fetchLatestRecords, fetchSummary } from '../api/client';
import DataTable from '../components/DataTable';
import type { ScrapeCurrent } from '../types';
import type { Column } from '../components/DataTable';

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
  });
}

export default function DocumentsPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(30);

  useEffect(() => {
    const tid = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          setRefreshKey((k) => k + 1);
          return 30;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(tid);
  }, []);

  const deps = [refreshKey];

  const { data: countData } = useApi(() => fetchRecordsCount('document'), deps);
  const { data: summary } = useApi(() => fetchSummary('document'), deps);
  const { data: records, loading } = useApi(() => fetchLatestRecords('document', 100), deps);

  const columns: Column<ScrapeCurrent>[] = [
    {
      key: 'item_key',
      header: 'Document No',
      width: '30%',
      render: (r) => (
        <span className="text-sm" style={{ fontWeight: 500 }}>{r.item_key}</span>
      ),
    },
    {
      key: 'item_index',
      header: 'Index',
      width: '15%',
      render: (r) => <span className="text-secondary text-sm">{r.item_index ?? '---'}</span>,
    },
    {
      key: 'eai_message',
      header: 'EAI Message',
      render: (r) => {
        const msg = (r.raw_data as Record<string, unknown>)?.eai_message as string | null;
        return msg ? (
          <span className="text-sm" style={{ color: 'var(--color-danger)' }}>{msg}</span>
        ) : (
          <span className="text-secondary text-sm">---</span>
        );
      },
    },
    {
      key: 'scraped_at',
      header: 'Scraped At',
      width: '25%',
      render: (r) => <span className="text-secondary text-sm">{fmtTime(r.scraped_at)}</span>,
    },
  ];

  return (
    <div>
      <div className="section">
        <div className="section-header">
          <div>
            <h2 className="section-title">Documents</h2>
            <div className="text-secondary text-sm" style={{ marginTop: 4, paddingLeft: 2 }}>
              Auto-refresh in{' '}
              <span style={{ color: 'var(--color-primary)', fontWeight: 600 }}>{secondsLeft}s</span>
            </div>
          </div>
        </div>
      </div>

      {!loading && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
          <div className="card" style={{ padding: '12px 16px' }}>
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Current</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-text)', marginTop: 4 }}>{countData?.current_count ?? 0}</div>
          </div>
          <div className="card" style={{ padding: '12px 16px' }}>
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>History Total</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-text)', marginTop: 4 }}>{countData?.history_count ?? 0}</div>
          </div>
          <div className="card" style={{ padding: '12px 16px' }}>
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Latest Scrape</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-primary)', marginTop: 4 }}>
              {summary?.latest_scraped_at ? fmtTime(summary.latest_scraped_at) : '---'}
            </div>
          </div>
        </div>
      )}

      <DataTable
        columns={columns}
        data={records ?? []}
        keyExtractor={(r) => r.id}
        loading={loading}
        emptyMessage="No document records found."
      />
    </div>
  );
}
