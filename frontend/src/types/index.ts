/** PLM Dashboard — TypeScript type definitions matching the FastAPI backend. */

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
}

export interface ScrapeRecord {
  id: number;
  data_type: string;
  raw_data: Record<string, unknown>;
  scraped_at: string | null;
  created_at: string | null;
}

export interface ScrapeCurrent {
  id: number;
  data_type: string;
  item_key: string;
  item_index: string | null;
  raw_data: Record<string, unknown>;
  scraped_at: string | null;
  created_at: string | null;
}

export interface ScrapeLog {
  id: number;
  data_type: string;
  status: string;
  records_count: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface ScrapeRunResponse {
  status: string;
  message: string;
  results: Record<string, { records: number; error: string | null }> | null;
}

export interface SchedulerStatusResponse {
  running: boolean;
}

export interface SchedulerJob {
  id: string;
  name: string;
  trigger: string;
  next_run: string | null;
  last_run: string | null;
  max_instances: number;
  coalesce: boolean;
}

export interface SummaryResponse {
  total: number;
  latest_scraped_at: string | null;
  oldest_scraped_at: string | null;
}

export interface CountResponse {
  data_type: string;
  history_count: number;
  current_count: number;
}

export interface PartStatsCategory {
  name: string;
  value: number;
}

export interface DocumentStatsResponse {
  total: number;
  category_breakdown: Record<string, number>;
  daily_breakdown: Array<{
    date: string;
    categories: Record<string, number>;
  }>;
}

export interface PartStatsDaily {
  date: string;
  Normal: number;
  MigPartsBlocked: number;
  TemplateNotFilled: number;
}

export interface ConversionStatsItem {
  source: string;
  state: string;
  target_format: string;
  created_utc: string | null;
  wait_seconds: number | null;
}

export interface ConversionStatsResponse {
  total: number;
  failed_count: number;
  items: ConversionStatsItem[];
}

export interface PartStatsResponse {
  category_breakdown: PartStatsCategory[];
  daily_breakdown: PartStatsDaily[];
  current_count: number;
}

export interface PruneResponse {
  records_deleted: number;
  logs_deleted: number;
}

export interface NotificationTestResponse {
  success: boolean;
  message: string;
}

export type DataType = 'part' | 'document' | 'conversion';
export const DATA_TYPES: DataType[] = ['part', 'document', 'conversion'];
export const DATA_TYPE_LABELS: Record<DataType, string> = {
  part: 'Parts',
  document: 'Documents',
  conversion: 'Conversion',
};
