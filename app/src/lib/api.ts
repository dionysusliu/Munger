const DEFAULT_BACKEND_BASE_URL = 'http://localhost:18000';

declare global {
  interface Window {
    __MUNGER_BACKEND_BASE_URL?: string;
  }
}

export const BACKEND_BASE_URL =
  (typeof window !== 'undefined' && window.__MUNGER_BACKEND_BASE_URL) ||
  import.meta.env.VITE_BACKEND_BASE_URL ||
  DEFAULT_BACKEND_BASE_URL;

export interface SourceResponse {
  id: number;
  title: string;
  filename: string;
  file_type: string;
  status: string;
  file_size: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SourceListResponse {
  items: SourceResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface IngestLogEntry {
  id: number;
  action: string;
  log_type: string;
  created_at: string;
}

export interface IngestTimelineEvent {
  id: number;
  event_type: 'agent_message' | 'tool_call' | 'tool_result' | 'status_change' | 'error' | string;
  payload: Record<string, unknown>;
  created_at: string;
  job_id?: number | null;
}

export interface PipelineStepInfo {
  key: string;
  label: string;
  index: number;
  total: number;
}

export interface IngestStatusResponse {
  source_id: number;
  status: string;
  error_message: string | null;
  updated_at: string;
  job_id?: number | null;
  recent_logs: IngestLogEntry[];
  events: IngestTimelineEvent[];
  events_has_more: boolean;
  current_step?: PipelineStepInfo | null;
  step_metrics?: Record<string, number | string>;
}

export interface WikiPageResponse {
  id: number;
  title: string;
  slug: string;
  content: string;
  page_type: string;
  source_id: number | null;
  parent_id?: number | null;
  metadata_json?: string | null;
  word_count: number;
  created_at: string;
  updated_at: string;
}

export interface WikiLinkEntry {
  id: number;
  from_page_id: number;
  to_page_id: number;
  link_type: string;
  context: string | null;
  from_page_title: string;
  from_page_slug: string;
  to_page_title: string;
  to_page_slug: string;
  direction: 'incoming' | 'outgoing';
}

export interface WikiLinksResponse {
  page_id: number;
  outgoing: WikiLinkEntry[];
  incoming: WikiLinkEntry[];
  total: number;
}

export interface RelatedWikiPage {
  id: number;
  title: string;
  slug: string;
  page_type: string;
  word_count: number;
  updated_at: string;
}

export interface RelatedWikiPagesResponse {
  page_id: number;
  related_pages: RelatedWikiPage[];
}

export interface WikiPageListResponse {
  items: WikiPageResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface StatsResponse {
  total_sources: number;
  total_wiki_pages: number;
  total_entities: number;
  total_links: number;
}

async function apiFetch<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const { timeoutMs = 30_000, ...requestInit } = init ?? {};
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${BACKEND_BASE_URL}${path}`, {
      ...requestInit,
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error('Request timed out — the server may be busy processing a large file');
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || body.message || detail;
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export async function listSources(params?: {
  page?: number;
  page_size?: number;
  file_type?: string;
  status_filter?: string;
}): Promise<SourceListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.set('page', String(params.page));
  if (params?.page_size) query.set('page_size', String(params.page_size));
  if (params?.file_type) query.set('file_type', params.file_type);
  if (params?.status_filter) query.set('status_filter', params.status_filter);
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<SourceListResponse>(`/api/sources${suffix}`, { timeoutMs: 15_000 });
}

export async function deleteSource(sourceId: number): Promise<void> {
  return apiFetch(`/api/sources/${sourceId}`, { method: 'DELETE' });
}

export async function uploadSource(file: File, title?: string): Promise<SourceResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (title) {
    formData.append('title', title);
  }
  return apiFetch<SourceResponse>('/api/sources/upload', {
    method: 'POST',
    body: formData,
    timeoutMs: 120_000,
  });
}

export async function triggerIngest(
  sourceId: number,
  skill = 'ingest',
): Promise<{ message: string; source_id: number; job_id?: number; skill_name?: string }> {
  const query = skill !== 'ingest' ? `?skill=${encodeURIComponent(skill)}` : '';
  return apiFetch(`/api/sources/${sourceId}/ingest${query}`, { method: 'POST' });
}

export async function backfillSource(
  sourceId: number,
): Promise<{ message: string; source_id: number; job_id?: number; skill_name?: string }> {
  return apiFetch(`/api/sources/${sourceId}/backfill`, { method: 'POST' });
}

export async function getIngestStatus(
  sourceId: number,
  params?: { since_id?: number; limit?: number },
): Promise<IngestStatusResponse> {
  const query = new URLSearchParams();
  if (params?.since_id !== undefined) query.set('since_id', String(params.since_id));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<IngestStatusResponse>(`/api/sources/${sourceId}/status${suffix}`);
}

export async function listWikiPages(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  page_type?: string;
}): Promise<WikiPageListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.set('page', String(params.page));
  if (params?.page_size) query.set('page_size', String(params.page_size));
  if (params?.search) query.set('search', params.search);
  if (params?.page_type) query.set('page_type', params.page_type);
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<WikiPageListResponse>(`/api/wiki${suffix}`);
}

export async function getWikiPageBySlug(slug: string): Promise<WikiPageResponse> {
  return apiFetch<WikiPageResponse>(`/api/wiki/slug/${encodeURIComponent(slug)}`);
}

export async function getWikiLinks(pageId: number): Promise<WikiLinksResponse> {
  return apiFetch<WikiLinksResponse>(`/api/wiki/${pageId}/links`);
}

export async function getRelatedWikiPages(pageId: number): Promise<RelatedWikiPagesResponse> {
  return apiFetch<RelatedWikiPagesResponse>(`/api/wiki/${pageId}/related`);
}

export async function getStats(): Promise<StatsResponse> {
  return apiFetch<StatsResponse>('/api/stats');
}
