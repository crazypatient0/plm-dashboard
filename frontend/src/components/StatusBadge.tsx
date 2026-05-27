interface StatusBadgeProps {
  status: 'success' | 'running' | 'error' | 'idle';
  label?: string;
}

const BADGE_CLASS: Record<string, string> = {
  success: 'badge-success',
  running: 'badge-running',
  error: 'badge-error',
  idle: 'badge-idle',
};

const BADGE_LABEL: Record<string, string> = {
  success: 'Success',
  running: 'Running',
  error: 'Error',
  idle: 'Idle',
};

export default function StatusBadge({
  status,
  label,
}: StatusBadgeProps) {
  return (
    <span className={`status-badge ${BADGE_CLASS[status]}`}>
      <span className="status-dot" />
      {label ?? BADGE_LABEL[status]}
    </span>
  );
}
