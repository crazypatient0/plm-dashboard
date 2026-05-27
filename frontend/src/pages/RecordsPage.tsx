import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { fetchHistoryRecords, searchRecords, fetchRecordsByRange } from '../api/client';
import DataTable from '../components/DataTable';
import type { ScrapeRecord, DataType } from '../types';
import type { Column } from '../components/DataTable';

const DATA_TYPE_LABELS: Record<string, string> = {
  part: 'Parts',
  document: 'Documents',
  conversion: 'Conversion',
};

const RAW_FIELDS = ['item_number', 'name', 'revision', 'item_name', 'description', 'state'];

export default function RecordsPage() {
  const { dataType } = useParams<{ dataType: string }>();
  const dt = (dataType as DataType) || 'part';
  const [searchField, setSearchField] = useState('item_number');
  const [searchValue, setSearchValue] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [mode, setMode] = useState<'latest' | 'search' | 'range'>('latest');

  const fetchFn = () => {
    if (mode === 'search' && searchValue.trim()) {
      return searchRecords(dt, searchField, searchValue.trim());
    }
    if (mode === 'range' && dateFrom) {
      return fetchRecordsByRange(dt, new Date(dateFrom).toISOString(), dateTo ? new Date(dateTo).toISOString() : undefined);
    }
    return fetchHistoryRecords(dt, 100);
  };

  const { data, loading } = useApi(fetchFn, [dt, mode, searchField, searchValue, dateFrom, dateTo]);
  const records = data ?? [];

  const columns: Column<ScrapeRecord>[] = [
    {
      key: 'id',
      header: 'ID',
      width: '70px',
      render: (r) => <code className="text-sm">{r.id}</code>,
    },
    {
      key: 'data_type',
      header: 'Type',
      width: '100px',
      render: (r) => r.data_type.charAt(0).toUpperCase() + r.data_type.slice(1),
    },
    {
      key: 'raw_data',
      header: 'Fields',
      render: (r) => {
        const fields = RAW_FIELDS.filter((f) => r.raw_data[f]);
        return (
          <div className="flex-row" style={{ flexWrap: 'wrap', gap: 4 }}>
            {fields.map((f) => (
              <code
                key={f}
                className="text-sm"
                style={{ background: 'var(--color-code-bg)', padding: '1px 6px', borderRadius: 'var(--radius-sm)' }}
              >
                {f}: {String(r.raw_data[f]).slice(0, 60)}
              </code>
            ))}
          </div>
        );
      },
    },
    {
      key: 'scraped_at',
      header: 'Scraped At',
      width: '170px',
      render: (r) => (
        <span className="text-sm text-secondary">
          {r.scraped_at ? new Date(r.scraped_at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : '\u2014'}
        </span>
      ),
    },
  ];

  return (
    <div>
      <div className="section">
        <div className="section-header">
          <h2 className="section-title">{DATA_TYPE_LABELS[dt] || dt} — Full History</h2>
          <div className="flex-row">
            {(['part', 'document', 'conversion'] as DataType[]).map((t) => (
              <Link
                key={t}
                to={`/records/${t}`}
                className={`btn btn-sm${t === dt ? ' btn-primary' : ''}`}
              >
                {DATA_TYPE_LABELS[t]}
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* History indicator */}
      {/* Filter tabs */}

      {/* Filter tabs */}
      <div className="card mb-16">
        <div className="card-body">
          <div className="flex-row" style={{ gap: 8, marginBottom: 12 }}>
            <button className={`btn btn-sm${mode === 'latest' ? ' btn-primary' : ''}`} onClick={() => setMode('latest')}>
              Latest
            </button>
            <button className={`btn btn-sm${mode === 'search' ? ' btn-primary' : ''}`} onClick={() => { setMode('search'); setSearchValue(''); }}>
              Search
            </button>
            <button className={`btn btn-sm${mode === 'range' ? ' btn-primary' : ''}`} onClick={() => { setMode('range'); setDateFrom(''); }}>
              Date Range
            </button>
          </div>

          {mode === 'search' && (
            <div className="flex-row" style={{ gap: 8 }}>
              <select className="form-select" value={searchField} onChange={(e) => setSearchField(e.target.value)} style={{ width: 150 }}>
                {RAW_FIELDS.map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
              <input
                className="form-input"
                type="text"
                placeholder="Search value..."
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                style={{ minWidth: 200 }}
              />
            </div>
          )}

          {mode === 'range' && (
            <div className="flex-row" style={{ gap: 12 }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">From</label>
                <input className="form-input" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">To</label>
                <input className="form-input" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Table */}
      <DataTable
        columns={columns}
        data={records}
        keyExtractor={(r) => r.id}
        loading={loading}
        emptyMessage="No records found."
      />
    </div>
  );
}
