import { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { fetchLogs } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import type { ScrapeLog } from '../types';
import type { Column } from '../components/DataTable';

const STATUS_BADGE: Record<string, 'success' | 'running' | 'error' | 'idle'> = {
  success: 'success',
  running: 'running',
  error: 'error',
  skipped: 'idle',
};

export default function LogsPage() {
  const [dataType, setDataType] = useState('');
  const [limit, setLimit] = useState(50);

  const { data, loading, refetch } = useApi(
    () => fetchLogs(dataType || undefined, limit),
    [dataType, limit],
  );

  const logs = data ?? [];

  const columns: Column<ScrapeLog>[] = [
    {
      key: 'started_at',
      header: 'Started',
      width: '170px',
        render: (l) => (
        <span className="text-sm text-secondary">
          {l.started_at ? new Date(l.started_at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : '\u2014'}
        </span>
      ),
    },
    {
      key: 'data_type',
      header: 'Type',
      width: '100px',
      render: (l) => l.data_type.charAt(0).toUpperCase() + l.data_type.slice(1),
    },
    {
      key: 'status',
      header: 'Status',
      width: '100px',
      render: (l) => <StatusBadge status={STATUS_BADGE[l.status] ?? 'idle'} label={l.status} />,
    },
    {
      key: 'records_count',
      header: 'Records',
      width: '80px',
    },
    {
      key: 'error_message',
      header: 'Error',
      render: (l) =>
        l.error_message ? (
          <span className="text-sm" style={{ color: 'var(--color-danger)' }}>{l.error_message}</span>
        ) : (
          '\u2014'
        ),
    },
  ];

  return (
    <div>
      <div className="section">
        <div className="section-header">
          <h2 className="section-title">Scrape Logs</h2>
          <button className="btn btn-sm" onClick={refetch}>Refresh</button>
        </div>
      </div>

      <div className="card mb-16">
        <div className="card-body">
          <div className="flex-row" style={{ gap: 12 }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Data Type</label>
              <select className="form-select" value={dataType} onChange={(e) => setDataType(e.target.value)} style={{ width: 140 }}>
                <option value="">All</option>
                <option value="part">Part</option>
                <option value="document">Document</option>
                <option value="conversion">Conversion</option>
              </select>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Limit</label>
              <select className="form-select" value={limit} onChange={(e) => setLimit(Number(e.target.value))} style={{ width: 100 }}>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={logs}
        keyExtractor={(l) => l.id}
        loading={loading}
        emptyMessage="No log entries found."
      />
    </div>
  );
}
