export type AnalysisEvidencePreviewAction = {
  label: string;
  href?: string;
  evidenceId?: string;
};

export type AnalysisEvidencePreviewItem = {
  id: string;
  source: string;
  title: string;
  excerpt: string;
  meta?: string;
  badges: string[];
  action?: AnalysisEvidencePreviewAction;
};

export type AnalysisEvidencePreviewModel = {
  key: string;
  items: AnalysisEvidencePreviewItem[];
  action: AnalysisEvidencePreviewAction;
};

export type AnalysisEvidencePreviewMap = Record<string, AnalysisEvidencePreviewModel>;

export type AnalysisEvidencePreviewEntryInput = {
  id?: string;
  eyebrow?: string;
  title?: string;
  description?: string;
  meta?: string;
  badges?: string[];
  action?: AnalysisEvidencePreviewAction;
};

export type AnalysisEvidencePreviewStatInput = {
  label?: string;
  value?: string;
  hint?: string;
};

export type AnalysisEvidencePreviewLensInput = {
  id: string;
  eyebrow?: string;
  title?: string;
  summary?: string;
  meta?: string;
  stats?: AnalysisEvidencePreviewStatInput[];
  entries?: AnalysisEvidencePreviewEntryInput[];
  emptyMessage?: string;
};

export type AnalysisEvidencePreviewArtifactInput = {
  key: string;
  source: string;
  title?: string | null;
  excerpt?: string | null;
  meta?: string | null;
  badges?: string[];
  href: string;
  action?: AnalysisEvidencePreviewAction;
};

export type BuildAnalysisEvidencePreviewMapInput = {
  lenses: AnalysisEvidencePreviewLensInput[];
  artifacts?: AnalysisEvidencePreviewArtifactInput[];
  maxItems?: number;
};

function cleanText(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

function truncate(value: string, max = 118): string {
  if (value.length <= max) return value;
  return `${value.slice(0, max - 1)}…`;
}

function compactBadges(values: Array<string | null | undefined>): string[] {
  const out: string[] = [];
  for (const value of values) {
    const cleaned = cleanText(value);
    if (!cleaned || out.includes(cleaned)) continue;
    out.push(cleaned);
  }
  return out;
}

function normalizeAction(
  action: AnalysisEvidencePreviewAction | null | undefined,
): AnalysisEvidencePreviewAction | undefined {
  const label = cleanText(action?.label);
  const href = cleanText(action?.href);
  const evidenceId = cleanText(action?.evidenceId);
  if (!label || (!href && !evidenceId)) return undefined;
  return {
    label,
    ...(href ? { href } : {}),
    ...(evidenceId ? { evidenceId } : {}),
  };
}

function normalizeEntry(
  entry: AnalysisEvidencePreviewEntryInput,
  index: number,
  fallbackSource: string,
): AnalysisEvidencePreviewItem | null {
  const title = cleanText(entry.title);
  const excerpt = cleanText(entry.description);
  if (!title && !excerpt) return null;

  const source = cleanText(entry.eyebrow) ?? fallbackSource;

  return {
    id: cleanText(entry.id) ?? `${source}-${index}`,
    source,
    title: truncate(title ?? source, 74),
    excerpt: truncate(excerpt ?? title ?? '這是一個可展開查看的實際依據。'),
    meta: cleanText(entry.meta) ?? undefined,
    badges: compactBadges(entry.badges ?? []),
    action: normalizeAction(entry.action),
  };
}

function normalizeStat(
  stat: AnalysisEvidencePreviewStatInput,
  index: number,
  fallbackSource: string,
): AnalysisEvidencePreviewItem | null {
  const label = cleanText(stat.label);
  const value = cleanText(stat.value);
  const hint = cleanText(stat.hint);
  if (!label && !value && !hint) return null;

  return {
    id: `${fallbackSource}-stat-${index}`,
    source: fallbackSource,
    title: truncate([label, value].filter(Boolean).join(' · ') || fallbackSource, 74),
    excerpt: truncate(hint ?? '這個數字只是定位依據，不是關係診斷。'),
    badges: compactBadges(['數據定位']),
  };
}

function buildFallbackItem(
  lens: AnalysisEvidencePreviewLensInput,
): AnalysisEvidencePreviewItem {
  const source = cleanText(lens.eyebrow) ?? 'Evidence';
  return {
    id: `${lens.id}-fallback`,
    source,
    title: truncate(cleanText(lens.title) ?? '等待更清楚的依據', 74),
    excerpt: truncate(
      cleanText(lens.emptyMessage) ??
        cleanText(lens.summary) ??
        '目前可展開的具體片段還不多，Haven 會保守呈現，不補寫不存在的依據。',
    ),
    badges: compactBadges(['保守讀法']),
  };
}

function buildLensPreview(
  lens: AnalysisEvidencePreviewLensInput,
  maxItems: number,
): AnalysisEvidencePreviewModel {
  const fallbackSource = cleanText(lens.eyebrow) ?? 'Evidence';
  const entryItems = (lens.entries ?? [])
    .map((entry, index) => normalizeEntry(entry, index, fallbackSource))
    .filter((item): item is AnalysisEvidencePreviewItem => Boolean(item));
  const statItems = (lens.stats ?? [])
    .map((stat, index) => normalizeStat(stat, index, fallbackSource))
    .filter((item): item is AnalysisEvidencePreviewItem => Boolean(item));
  const items = [...entryItems, ...statItems].slice(0, maxItems);

  return {
    key: lens.id,
    items: items.length ? items : [buildFallbackItem(lens)],
    action: {
      label: '展開完整依據',
      evidenceId: lens.id,
    },
  };
}

function buildArtifactPreview(
  artifact: AnalysisEvidencePreviewArtifactInput,
): AnalysisEvidencePreviewModel | null {
  const source = cleanText(artifact.source);
  const title = cleanText(artifact.title);
  const excerpt = cleanText(artifact.excerpt);
  const href = cleanText(artifact.href);

  if (!source || !href || (!title && !excerpt)) return null;

  return {
    key: artifact.key,
    items: [
      {
        id: `${artifact.key}-artifact`,
        source,
        title: truncate(title ?? source, 74),
        excerpt: truncate(excerpt ?? '這個判讀指向一個已存在的關係系統位置。'),
        meta: cleanText(artifact.meta) ?? undefined,
        badges: compactBadges(artifact.badges ?? [source]),
        action: normalizeAction(artifact.action) ?? {
          label: '打開來源',
          href,
        },
      },
    ],
    action: {
      label: '打開原始位置',
      href,
    },
  };
}

export function buildAnalysisEvidencePreviewMap(
  input: BuildAnalysisEvidencePreviewMapInput,
): AnalysisEvidencePreviewMap {
  const maxItems = Math.max(1, Math.min(3, Math.round(input.maxItems ?? 2)));
  const map: AnalysisEvidencePreviewMap = {};

  for (const lens of input.lenses) {
    const id = cleanText(lens.id);
    if (!id) continue;
    map[id] = buildLensPreview({ ...lens, id }, maxItems);
  }

  for (const artifact of input.artifacts ?? []) {
    const key = cleanText(artifact.key);
    if (!key) continue;
    const preview = buildArtifactPreview({ ...artifact, key });
    if (preview) {
      map[key] = preview;
    }
  }

  return map;
}
