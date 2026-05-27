import { useState } from 'react';
import { useApi, useMutation } from '../hooks/useApi';
import { fetchHealth, pruneRecords, sendTestNotification } from '../api/client';
import StatusBadge from '../components/StatusBadge';

export default function SettingsPage() {
  const { data: health } = useApi(() => fetchHealth(), []);
  const { mutate: doPrune, loading: pruning, error: pruneError, data: pruneResult } = useMutation(pruneRecords);
  const { mutate: doTestNotification, loading: testingNotif, error: notifError, data: notifResult } = useMutation(sendTestNotification);

  const [retentionDays, setRetentionDays] = useState(90);
  const [notifChannel, setNotifChannel] = useState<'teams' | 'dingtalk'>('teams');

  const handlePrune = async () => {
    await doPrune(retentionDays);
  };

  const handleTestNotification = async () => {
    await doTestNotification(
      notifChannel,
      'PLM Dashboard - Test',
      'This is a test notification from PLM Dashboard.',
    );
  };

  return (
    <div>
      <div className="section">
        <div className="section-header"><h2 className="section-title">Settings</h2></div>
      </div>

      <div className="card mb-16">
        <div className="card-header"><h3>System Status</h3></div>
        <div className="card-body">
          <table className="data-table">
            <tbody>
              <tr>
                <td style={{ fontWeight: 500, width: 200 }}>API Status</td>
                <td><StatusBadge status={health ? 'success' : 'error'} label={health?.status ?? 'unreachable'} /></td>
              </tr>
              <tr>
                <td style={{ fontWeight: 500 }}>Version</td>
                <td className="mono">{health?.version ?? '\u2014'}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="card mb-16">
        <div className="card-header"><h3>Data Pruning</h3></div>
        <div className="card-body">
          <p className="text-secondary" style={{ marginBottom: 16 }}>
            Delete records and logs older than the specified number of days. This action cannot be undone.
          </p>
          <div className="flex-row" style={{ gap: 12 }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Retention (days)</label>
              <input className="form-input" type="number" min={1} value={retentionDays} onChange={(e) => setRetentionDays(Number(e.target.value))} style={{ width: 120 }} />
            </div>
            <button className="btn btn-danger" onClick={handlePrune} disabled={pruning} style={{ alignSelf: 'flex-end' }}>
              {pruning ? 'Pruning...' : 'Prune Old Records'}
            </button>
          </div>
          {pruneResult && (
            <div className="alert alert-success mt-16">
              Deleted {pruneResult.records_deleted} record(s) and {pruneResult.logs_deleted} log(s) older than {retentionDays} days.
            </div>
          )}
          {pruneError && <div className="alert alert-error mt-16">{pruneError}</div>}
        </div>
      </div>

      <div className="card mb-16">
        <div className="card-header"><h3>Notifications</h3></div>
        <div className="card-body">
          <p className="text-secondary" style={{ marginBottom: 16 }}>
            Send a test notification to verify your webhook configuration.
          </p>
          <div className="flex-row" style={{ gap: 12, marginBottom: 12 }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Channel</label>
              <select className="form-select" value={notifChannel} onChange={(e) => setNotifChannel(e.target.value as 'teams' | 'dingtalk')} style={{ width: 120 }}>
                <option value="teams">Teams</option>
                <option value="dingtalk">DingTalk</option>
              </select>
            </div>
            <button className="btn btn-primary" onClick={handleTestNotification} disabled={testingNotif} style={{ alignSelf: 'flex-end' }}>
              {testingNotif ? 'Sending...' : 'Send Test Notification'}
            </button>
          </div>
          {notifResult && (
            <div className="alert alert-success">
              {notifResult.success ? 'Notification sent successfully.' : `Failed: ${notifResult.message}`}
            </div>
          )}
          {notifError && <div className="alert alert-error mt-16">{notifError}</div>}
        </div>
      </div>
    </div>
  );
}
