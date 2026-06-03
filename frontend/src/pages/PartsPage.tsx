import { useState, useEffect } from 'react';
import ProcessingTimeChart from '../components/ProcessingTimeChart';

export default function PartsPage() {
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

  return (
    <div className="section">
      <div className="section-header">
        <div>
          <h2 className="section-title">Parts</h2>
          <div className="text-secondary text-sm" style={{ marginTop: 4, paddingLeft: 2 }}>
            Auto-refresh in{' '}
            <span style={{ color: 'var(--color-primary)', fontWeight: 600 }}>{secondsLeft}s</span>
          </div>
        </div>
      </div>
      <ProcessingTimeChart dataType="part" refreshKey={refreshKey} />
    </div>
  );
}
