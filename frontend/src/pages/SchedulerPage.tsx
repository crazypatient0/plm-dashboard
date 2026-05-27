import { useApi, useMutation } from '../hooks/useApi';
import {
  fetchSchedulerStatus,
  fetchSchedulerJobs,
  startScheduler,
  stopScheduler,
} from '../api/client';
import StatusBadge from '../components/StatusBadge';
import type { SchedulerJob } from '../types';
import type { Column } from '../components/DataTable';
import DataTable from '../components/DataTable';

export default function SchedulerPage() {
  const { data: status, refetch: refetchStatus } = useApi(
    () => fetchSchedulerStatus(),
    [],
  );
  const { data: jobs, loading: jobsLoading, refetch: refetchJobs } = useApi(
    () => fetchSchedulerJobs(),
    [],
  );
  const { mutate: doStart, loading: starting, error: startError } = useMutation(startScheduler);
  const { mutate: doStop, loading: stopping, error: stopError } = useMutation(stopScheduler);

  const isRunning = status?.running ?? false;
  const error = startError || stopError;

  const handleStart = async () => {
    await doStart();
    refetchStatus();
    refetchJobs();
  };

  const handleStop = async () => {
    await doStop();
    refetchStatus();
    refetchJobs();
  };

  const jobColumns: Column<SchedulerJob>[] = [
    {
      key: 'id',
      header: 'Job ID',
      render: (j) => j.id,
    },
    { key: 'name', header: 'Name' },
    {
      key: 'next_run',
      header: 'Next Run',
      render: (j) =>
        j.next_run ? (
          <span className="text-sm text-secondary">{new Date(j.next_run).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })}</span>
        ) : (
          '\u2014'
        ),
    },
    {
      key: 'last_run',
      header: 'Last Run',
      width: '170px',
      render: (j) =>
        j.last_run ? (
          <span className="text-sm text-secondary">{new Date(j.last_run).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })}</span>
        ) : (
          '\u2014'
        ),
    },
    {
      key: 'trigger',
      header: 'Trigger',
      render: (j) => <code className="text-sm">{j.trigger}</code>,
    },
  ];

  return (
    <div>
      <div className="section">
        <div className="section-header">
          <h2 className="section-title">Scheduler</h2>
          <StatusBadge status={isRunning ? 'running' : 'idle'} label={isRunning ? 'Running' : 'Stopped'} />
        </div>
      </div>

      <div className="card mb-16">
        <div className="card-header"><h3>Controls</h3></div>
        <div className="card-body">
          <div className="flex-row" style={{ gap: 12 }}>
            <button className="btn btn-primary" onClick={handleStart} disabled={isRunning || starting}>
              {starting ? 'Starting...' : 'Start Scheduler'}
            </button>
            <button className="btn btn-danger" onClick={handleStop} disabled={!isRunning || stopping}>
              {stopping ? 'Stopping...' : 'Stop Scheduler'}
            </button>
          </div>
        </div>
      </div>

      {error && <div className="alert alert-error mb-16">{error}</div>}

      <div className="section">
        <div className="section-header">
          <h3 className="section-title">Scheduled Jobs</h3>
          <span className="text-sm text-secondary">{(jobs ?? []).length} job{(jobs ?? []).length !== 1 ? 's' : ''}</span>
        </div>
        <DataTable columns={jobColumns} data={jobs ?? []} keyExtractor={(j) => j.id} loading={jobsLoading} emptyMessage="No jobs scheduled." />
      </div>
    </div>
  );
}
