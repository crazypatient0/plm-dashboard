import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import Layout from '../Layout';

describe('Layout', () => {
  it('renders sidebar navigation links', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Layout />
      </MemoryRouter>,
    );

    expect(screen.getByText('PLM')).toBeInTheDocument();
    expect(screen.getAllByText('Dashboard').length).toBe(2);
    expect(screen.getByText('Parts')).toBeInTheDocument();
    expect(screen.getByText('Documents')).toBeInTheDocument();
    expect(screen.getByText('Conversion')).toBeInTheDocument();
    expect(screen.getByText('Scraper')).toBeInTheDocument();
    expect(screen.getByText('Scheduler')).toBeInTheDocument();
    expect(screen.getByText('Logs')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('renders outlet content', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Layout />
      </MemoryRouter>,
    );

    expect(screen.getByText('PLM Data Monitoring Dashboard')).toBeInTheDocument();
  });
});
