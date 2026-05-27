import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import StatCard from '../StatCard';

describe('StatCard', () => {
  it('renders title and value', () => {
    render(<StatCard title="Parts" value={42} />);
    expect(screen.getByText('Parts')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('renders subtitle when provided', () => {
    render(<StatCard title="Parts" value={10} subtitle="Last update: today" />);
    expect(screen.getByText('Last update: today')).toBeInTheDocument();
  });

  it('shows loading placeholder when loading', () => {
    render(<StatCard title="Parts" value={10} loading />);
    expect(screen.getByText('---')).toBeInTheDocument();
  });

  it('applies custom color via icon color', () => {
    const { container } = render(
      <StatCard title="Errors" value={3} color="danger" icon={<span>!</span>} />,
    );
    const icon = container.querySelector('.stat-icon');
    expect(icon).toBeInTheDocument();
  });
});
