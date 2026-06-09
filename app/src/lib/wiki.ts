export const PAGE_TYPE_LABELS: Record<string, string> = {
  summary: 'Summary',
  entity: 'Entity',
  concept: 'Concept',
  model: 'Mental Model',
  mechanism: 'Mechanism',
  incentive: 'Incentive Structure',
  incentive_structure: 'Incentive Structure',
  psychology: 'Psychology',
  comparison: 'Comparison',
  analysis: 'Analysis',
  overview: 'Overview',
  index: 'Index',
  log: 'Log',
  person: 'Person',
  book: 'Book',
  paper: 'Paper',
  organization: 'Organization',
  field: 'Field',
  event: 'Event',
  principle: 'Principle',
};

export const PAGE_TYPE_ATTRIBUTES: Record<string, string[]> = {
  summary: ['page_type', 'word_count', 'source_id', 'updated_at'],
  entity: ['page_type', 'source_id', 'word_count', 'updated_at'],
  concept: ['page_type', 'word_count', 'updated_at'],
  model: ['page_type', 'word_count', 'updated_at'],
  mechanism: ['page_type', 'word_count', 'updated_at'],
  person: ['page_type', 'source_id', 'word_count', 'updated_at'],
  book: ['page_type', 'source_id', 'word_count', 'updated_at'],
  principle: ['page_type', 'word_count', 'updated_at'],
};

const ATTRIBUTE_LABELS: Record<string, string> = {
  page_type: 'Type',
  word_count: 'Word count',
  source_id: 'Source',
  parent_id: 'Parent page',
  created_at: 'Created',
  updated_at: 'Updated',
};

export function formatPageType(pageType: string): string {
  return PAGE_TYPE_LABELS[pageType] || pageType.replace(/_/g, ' ');
}

import { listWikiPages } from '@/lib/api';

export function buildTitleSlugMap(
  pages: Array<{ title: string; slug: string }>,
): Map<string, string> {
  const map = new Map<string, string>();
  for (const page of pages) {
    map.set(page.title.toLowerCase(), page.slug);
  }
  return map;
}

export async function fetchAllTitleSlugMap(): Promise<Map<string, string>> {
  const map = new Map<string, string>();
  const pageSize = 100;
  let page = 1;
  let total = 0;

  do {
    const response = await listWikiPages({ page, page_size: pageSize });
    for (const item of response.items) {
      map.set(item.title.toLowerCase(), item.slug);
    }
    total = response.total;
    page += 1;
  } while ((page - 1) * pageSize < total);

  return map;
}

export interface WikiAttributeRow {
  key: string;
  label: string;
  value: string;
}

export function getWikiAttributeRows(page: {
  page_type: string;
  word_count: number;
  source_id: number | null;
  parent_id?: number | null;
  created_at: string;
  updated_at: string;
  metadata_json?: string | null;
}): WikiAttributeRow[] {
  const rows: WikiAttributeRow[] = [];
  const keys = PAGE_TYPE_ATTRIBUTES[page.page_type] || [
    'page_type',
    'word_count',
    'source_id',
    'updated_at',
  ];

  const values: Record<string, string> = {
    page_type: formatPageType(page.page_type),
    word_count: page.word_count.toLocaleString(),
    source_id: page.source_id ? `#${page.source_id}` : '—',
    parent_id: page.parent_id ? `#${page.parent_id}` : '—',
    created_at: new Date(page.created_at).toLocaleDateString(),
    updated_at: new Date(page.updated_at).toLocaleDateString(),
  };

  for (const key of keys) {
    rows.push({
      key,
      label: ATTRIBUTE_LABELS[key] || key,
      value: values[key] ?? '—',
    });
  }

  if (page.metadata_json) {
    try {
      const metadata = JSON.parse(page.metadata_json) as Record<string, unknown>;
      for (const [key, value] of Object.entries(metadata)) {
        if (value === null || value === undefined || value === '') continue;
        rows.push({
          key: `metadata.${key}`,
          label: key.replace(/_/g, ' '),
          value: typeof value === 'string' ? value : JSON.stringify(value),
        });
      }
    } catch {
      rows.push({
        key: 'metadata_json',
        label: 'Metadata',
        value: page.metadata_json,
      });
    }
  }

  return rows;
}
