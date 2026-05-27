import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { fetchRecordsCount, fetchLatestRecords, fetchSummary } from '../api/client';
import StatCard from '../components/StatCard';

/** Return milliseconds until the next 5-minute mark (00, 05, 10, 15, ...). */
function msUntilNext5Min(): number {
  const now = new Date();
  const mins = now.getMinutes();
  const next5 = (Math.floor(mins / 5) + 1) * 5;
  let nextTime = new Date(now);
  if (next5 >= 60) {
    nextTime.setHours(now.getHours() + 1);
    nextTime.setMinutes(0);
  } else {
    nextTime.setMinutes(next5);
  }
  nextTime.setSeconds(0);
  nextTime.setMilliseconds(0);
  return nextTime.getTime() - now.getTime();
}

export default function DashboardPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  // Auto-refresh at 5-minute boundaries: :00, :05, :10, :15, ...
  useEffect(() => {
    const scheduleNext = () => {
      const ms = msUntilNext5Min();
      const tid = setTimeout(() => {
        setRefreshKey((k) => k + 1);
        scheduleNext();
      }, ms);
      return tid;
    };
    const tid = scheduleNext();
    return () => clearTimeout(tid);
  }, []);

  const deps = [refreshKey];

  const partCount = useApi(() => fetchRecordsCount('part'), deps);
  const docCount = useApi(() => fetchRecordsCount('document'), deps);
  const mqCount = useApi(() => fetchRecordsCount('conversion'), deps);
  const partSummary = useApi(() => fetchSummary('part'), deps);
  const docSummary = useApi(() => fetchSummary('document'), deps);
  const mqSummary = useApi(() => fetchSummary('conversion'), deps);

  // Fetch all current records (no limit — show all)
  const { data: recentParts } = useApi(() => fetchLatestRecords('part', 100), deps);
  const { data: recentDocs } = useApi(() => fetchLatestRecords('document', 100), deps);
  const { data: recentMq } = useApi(() => fetchLatestRecords('conversion', 100), deps);

  const loading =
    partCount.loading || docCount.loading || mqCount.loading ||
    partSummary.loading || docSummary.loading || mqSummary.loading;

  const parts = recentParts ?? [];
  const docs = recentDocs ?? [];
  const mqs = recentMq ?? [];

  return (
    <div>
        <div className="section">
        <div className="section-header">
          <h2 className="section-title">Overview</h2>
        </div>

        <div className="grid-3">
          <StatCard
            title="Parts"
            value={partCount.data?.current_count ?? 0}
            subtitle={`Latest: ${partSummary.data?.latest_scraped_at ? new Date(partSummary.data.latest_scraped_at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : 'N/A'}`}
            color="primary"
            loading={loading}
          />
          <StatCard
            title="Documents"
            value={docCount.data?.current_count ?? 0}
            subtitle={`Latest: ${docSummary.data?.latest_scraped_at ? new Date(docSummary.data.latest_scraped_at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : 'N/A'}`}
            color="success"
            loading={loading}
          />
          <StatCard
            title="Conversion"
            value={mqCount.data?.current_count ?? 0}
            subtitle={`Latest: ${mqSummary.data?.latest_scraped_at ? new Date(mqSummary.data.latest_scraped_at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : 'N/A'}`}
            color="warning"
            loading={loading}
          />
        </div>
      </div>

      {/* Part Records */}
      {parts.length > 0 && (
        <div className="section">
          <div className="section-header">
            <h2 className="section-title">Part Records</h2>
          </div>
          <div className="card">
            <div className="card-body" style={{ padding: 0 }}>
              <table className="data-table">
                <colgroup>
                  <col style={{ width: '15%' }} />
                  <col style={{ width: '10%' }} />
                  <col style={{ width: '20%' }} />
                  <col style={{ width: '35%' }} />
                  <col style={{ width: '20%' }} />
                </colgroup>
                <thead>
                  <tr>
                    <th>Part No</th>
                    <th>Index</th>
                    <th>Share Status</th>
                    <th>SAP Info</th>
                    <th>Scraped At</th>
                  </tr>
                </thead>
                <tbody>
                  {parts.map((r) => (
                    <tr key={r.id}>
                      <td>{String(r.raw_data.part_no ?? r.raw_data.item_number ?? '')}</td>
                      <td className="text-sm text-secondary">{String(r.raw_data.index ?? '')}</td>
                      <td className="text-sm text-secondary">{String(r.raw_data.share_status ?? '')}</td>
                      <td className="text-sm" style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{String(r.raw_data.sap_info ?? '')}</td>
                      <td className="text-sm text-secondary">
                        {r.scraped_at ? new Date(r.scraped_at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : '\u2014'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Document Records */}
      {docs.length > 0 && (
        <div className="section">
          <div className="section-header">
            <h2 className="section-title">Document Records</h2>
          </div>
          <div className="card">
            <div className="card-body" style={{ padding: 0 }}>
              <table className="data-table">
                <colgroup>
                  <col style={{ width: '15%' }} />
                  <col style={{ width: '10%' }} />
                  <col style={{ width: '20%' }} />
                  <col style={{ width: '35%' }} />
                  <col style={{ width: '20%' }} />
                </colgroup>
                <thead>
                  <tr>
                    <th>Document No</th>
                    <th>Index</th>
                    <th style={{ pointerEvents: 'none', userSelect: 'none' }} />
                    <th>EAI Message</th>
                    <th>Scraped At</th>
                  </tr>
                </thead>
                <tbody>
                  {docs.map((r) => (
                    <tr key={r.id}>
                      <td>{String(r.raw_data.document_no ?? r.raw_data.item_number ?? '')}</td>
                      <td className="text-sm text-secondary">{String(r.raw_data.doc_index ?? r.raw_data.index ?? '')}</td>
                      <td style={{ pointerEvents: 'none' }} />
                      <td className="text-sm" style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{String(r.raw_data.eai_message ?? '')}</td>
                      <td className="text-sm text-secondary">
                        {r.scraped_at ? new Date(r.scraped_at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : '\u2014'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Conversion Records */}
      {mqs.length > 0 && (
        <div className="section">
          <div className="section-header">
            <h2 className="section-title">Conversion Records</h2>
          </div>
          <div className="card">
            <div className="card-body" style={{ padding: 0 }}>
              <table className="data-table">
                <colgroup>
                  <col style={{ width: '15%' }} />
                  <col style={{ width: '10%' }} />
                  <col style={{ width: '20%' }} />
                  <col style={{ width: '35%' }} />
                  <col style={{ width: '20%' }} />
                </colgroup>
                <thead>
                  <tr>
                    <th>State</th>
                    <th style={{ pointerEvents: 'none', userSelect: 'none' }} />
                    <th style={{ pointerEvents: 'none', userSelect: 'none' }} />
                    <th style={{ pointerEvents: 'none', userSelect: 'none' }} />
                    <th>Scraped At</th>
                  </tr>
                </thead>
                <tbody>
                  {mqs.map((r) => (
                    <tr key={r.id}>
                      <td className="text-sm text-secondary">{String(r.raw_data.state ?? '')}</td>
                      <td style={{ pointerEvents: 'none' }} />
                      <td style={{ pointerEvents: 'none' }} />
                      <td style={{ pointerEvents: 'none' }} />
                      <td className="text-sm text-secondary">
                        {r.scraped_at ? new Date(r.scraped_at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : '\u2014'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {parts.length === 0 && docs.length === 0 && mqs.length === 0 && !loading && (
        <div className="section">
          <div className="card">
            <div className="card-body text-secondary text-sm" style={{ textAlign: 'center', padding: 'var(--spacing-8)' }}>
              No current records. Trigger a scrape to populate data.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
