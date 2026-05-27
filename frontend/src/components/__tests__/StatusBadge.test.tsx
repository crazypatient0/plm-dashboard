import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import StatusBadge from '../StatusBadge';

describe('StatusBadge', () => {
  it('renders with default label for success status', () => {
    render(<StatusBadge status="success" />);
    expect(screen.getByText('Success')).toBeInTheDocument();
  });

  it('renders with custom label', () => {
    render(<StatusBadge status="running" label="In Progress" />);
    expect(screen.getByText('In Progress')).toBeInTheDocument();
  });

  it('renders with error status', () => {
    render(<StatusBadge status="error" />);
    expect(screen.getByText('Error')).toBeInTheDocument();
  });

  it('renders with idle status', () => {
    render(<StatusBadge status="idle" />);
    expect(screen.getByText('Idle')).toBeInTheDocument();
  });
});
