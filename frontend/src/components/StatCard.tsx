import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: ReactNode;
  color?: 'primary' | 'success' | 'warning' | 'danger';
  loading?: boolean;
  to?: string;
}

const COLOR_MAP: Record<string, string> = {
  primary: 'var(--color-primary)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  danger: 'var(--color-danger)',
};

export default function StatCard({
  title,
  value,
  subtitle,
  icon,
  color = 'primary',
  loading = false,
  to,
}: StatCardProps) {
  const card = (
    <>
      {icon && (
        <div className="stat-icon" style={{ color: COLOR_MAP[color] }}>
          {icon}
        </div>
      )}
      <div className="stat-body">
        <div className="stat-title">{title}</div>
        {loading ? (
          <div className="stat-value stat-value--loading">---</div>
        ) : (
          <div className="stat-value">{value}</div>
        )}
        {subtitle && <div className="stat-subtitle">{subtitle}</div>}
      </div>
    </>
  );

  if (to) {
    return (
      <Link to={to} className="stat-card stat-card--clickable" style={{ textDecoration: 'none', display: 'block' }}>
        {card}
      </Link>
    );
  }

  return <div className="stat-card">{card}</div>;
}
