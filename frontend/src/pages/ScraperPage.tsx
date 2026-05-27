import { useState } from 'react';
import { useApi, useMutation } from '../hooks/useApi';
import { fetchScrapeStatus, triggerScrape } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import type { DataType } from '../types';

export default function ScraperPage() {
  const { data: status, refetch: refetchStatus } = useApi(
    () => fetchScrapeStatus(),
    [],
  );
  const { mutate, loading: mutating, error: mutateError } = useMutation(triggerScrape);
  const [result, setResult] = useState<{ message: string; results: Record<string, { records: number; error: string | null }> | null } | null>(null);
  const [selectedType, setSelectedType] = useState<DataType | ''>('');

  const handleScrapeAll = async () => {
    setResult(null);
    try {
      const res = await mutate();
      setResult(res);
      refetchStatus();
    } catch {
      // error captured by mutate
    }
  };

  const handleScrapeType = async () => {
    if (!selectedType) return;
    setResult(null);
    try {
      const res = await mutate(selectedType as DataType);
      setResult(res);
      refetchStatus();
    } catch {
      // error captured by mutate
    }
  };

  const initialized = status?.initialized ?? false;

  return (
    <div>
      <div className="section">
        <div className="section-header">
          <h2 className="section-title">PLM Scraper</h2>
          <StatusBadge
            status={initialized ? 'success' : 'idle'}
            label={initialized ? 'Ready' : 'Not Initialized'}
          />
        </div>
      </div>

      {/* Scrape All */}
      <div className="card mb-16">
        <div className="card-header"><h3>Scrape All Types</h3></div>
        <div className="card-body">
          <p className="text-secondary" style={{ marginBottom: 16 }}>
            Trigger a full scrape for all data types (parts, documents, Conversion).
          </p>
          <button className="btn btn-primary" onClick={handleScrapeAll} disabled={mutating || !initialized}>
            {mutating ? 'Scraping...' : 'Start Full Scrape'}
          </button>
        </div>
      </div>

      {/* Scrape Single Type */}
      <div className="card mb-16">
        <div className="card-header"><h3>Scrape Single Type</h3></div>
        <div className="card-body">
          <div className="flex-row" style={{ gap: 12 }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Data Type</label>
              <select className="form-select" value={selectedType} onChange={(e) => setSelectedType(e.target.value as DataType)} style={{ width: 150 }}>
                <option value="">-- Select --</option>
                <option value="part">Part</option>
                <option value="document">Document</option>
                <option value="conversion">Conversion</option>
              </select>
            </div>
            <button className="btn btn-primary" onClick={handleScrapeType} disabled={mutating || !initialized || !selectedType} style={{ alignSelf: 'flex-end' }}>
              {mutating ? 'Scraping...' : 'Scrape'}
            </button>
          </div>
        </div>
      </div>

      {/* Result */}
      {result && (
        <div className="card mb-16">
          <div className="card-header">
            <h3>Result</h3>
            <StatusBadge status={result.message.includes('failed') ? 'error' : 'success'} label="Done" />
          </div>
          <div className="card-body">
            <p className="text-secondary" style={{ marginBottom: 12 }}>{result.message}</p>
            {result.results && (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Records</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(result.results).map(([type, info]) => (
                    <tr key={type}>
                      <td>{type}</td>
                      <td>{info.records}</td>
                      <td>{info.error ? <span className="text-sm" style={{ color: 'var(--color-danger)' }}>{info.error}</span> : '\u2014'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {mutateError && <div className="alert alert-error mt-16">{mutateError}</div>}
    </div>
  );
}
