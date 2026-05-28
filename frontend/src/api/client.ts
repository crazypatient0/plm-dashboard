/** Axios-based API client for the PLM Dashboard backend. */

import axios from 'axios';
import type {
  CountResponse,
  DataType,
  DocumentStatsResponse,
  HealthResponse,
  NotificationTestResponse,
  PartStatsResponse,
  PruneResponse,
  ScrapeCurrent,
  ScrapeLog,
  ScrapeRecord,
  ScrapeRunResponse,
  SchedulerJob,
  SchedulerStatusResponse,
  SummaryResponse,
} from '../types';

const http = axios.create({
  baseURL: '/api',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await http.get<HealthResponse>('/health');
  return data;
}

// ---------------------------------------------------------------------------
// Records
// ---------------------------------------------------------------------------

export async function fetchLatestRecords(
  dataType: string,
  limit = 100,
): Promise<ScrapeCurrent[]> {
  const { data } = await http.get<ScrapeCurrent[]>(`/records/${dataType}`, {
    params: { limit },
  });
  return data;
}

export async function fetchHistoryRecords(
  dataType: string,
  limit = 100,
): Promise<ScrapeRecord[]> {
  const { data } = await http.get<ScrapeRecord[]>(
    `/records/${dataType}/history`,
    { params: { limit } },
  );
  return data;
}

export async function fetchRecordsByRange(
  dataType: string,
  since: string,
  until?: string,
): Promise<ScrapeRecord[]> {
  const { data } = await http.get<ScrapeRecord[]>(
    `/records/${dataType}/range`,
    { params: { since, until } },
  );
  return data;
}

export async function fetchRecordsCount(
  dataType: string,
): Promise<CountResponse> {
  const { data } = await http.get<CountResponse>(
    `/records/${dataType}/count`,
  );
  return data;
}

export async function fetchPartStats(): Promise<PartStatsResponse> {
  const { data } = await http.get<PartStatsResponse>('/records/part/stats');
  return data;
}

export async function fetchDocumentStats(): Promise<DocumentStatsResponse> {
  const { data } = await http.get<DocumentStatsResponse>(
    '/records/document/stats',
  );
  return data;
}

export async function fetchSummary(
  dataType: string,
): Promise<SummaryResponse> {
  const { data } = await http.get<SummaryResponse>(
    `/records/${dataType}/summary`,
  );
  return data;
}

export async function searchRecords(
  dataType: string,
  field: string,
  value: string,
): Promise<ScrapeRecord[]> {
  const { data } = await http.get<ScrapeRecord[]>(
    `/records/${dataType}/search`,
    { params: { field, value } },
  );
  return data;
}

export async function pruneRecords(
  retentionDays: number,
): Promise<PruneResponse> {
  const { data } = await http.delete<PruneResponse>('/records/prune', {
    params: { retention_days: retentionDays },
  });
  return data;
}

// ---------------------------------------------------------------------------
// Logs
// ---------------------------------------------------------------------------

export async function fetchLogs(
  dataType?: string,
  limit = 20,
): Promise<ScrapeLog[]> {
  const { data } = await http.get<ScrapeLog[]>('/logs', {
    params: { data_type: dataType || undefined, limit },
  });
  return data;
}

// ---------------------------------------------------------------------------
// Scraper
// ---------------------------------------------------------------------------

export async function triggerScrape(
  dataType?: DataType,
): Promise<ScrapeRunResponse> {
  const { data } = await http.post<ScrapeRunResponse>('/scrape/run', {
    data_type: dataType || null,
  });
  return data;
}

export async function fetchScrapeStatus(): Promise<{ initialized: boolean }> {
  const { data } = await http.get<{ initialized: boolean }>(
    '/scrape/status',
  );
  return data;
}

// ---------------------------------------------------------------------------
// Scheduler
// ---------------------------------------------------------------------------

export async function fetchSchedulerStatus(): Promise<SchedulerStatusResponse> {
  const { data } = await http.get<SchedulerStatusResponse>(
    '/scheduler/status',
  );
  return data;
}

export async function fetchSchedulerJobs(): Promise<SchedulerJob[]> {
  const { data } = await http.get<SchedulerJob[]>('/scheduler/jobs');
  return data;
}

export async function startScheduler(): Promise<SchedulerStatusResponse> {
  const { data } = await http.post<SchedulerStatusResponse>(
    '/scheduler/start',
  );
  return data;
}

export async function stopScheduler(): Promise<SchedulerStatusResponse> {
  const { data } = await http.post<SchedulerStatusResponse>(
    '/scheduler/stop',
  );
  return data;
}

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

export async function sendTestNotification(
  channel: 'teams' | 'dingtalk',
  title = 'PLM Dashboard - Test Notification',
  message = 'This is a test notification from PLM Dashboard.',
): Promise<NotificationTestResponse> {
  const { data } = await http.post<NotificationTestResponse>(
    '/notifications/test',
    { channel, title, message },
  );
  return data;
}
