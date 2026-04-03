export interface SharedFutureReadModel {
  baseNote: string | null;
  nextSteps: string[];
  cadences: string[];
  hasStructuredRefinements: boolean;
}

const NEXT_STEP_PREFIX = '下一步：';
const CADENCE_PREFIX = '節奏：';

function normalizeBaseNote(lines: string[]): string | null {
  const normalized = lines.map((line) => line.trim());

  while (normalized[0] === '') {
    normalized.shift();
  }
  while (normalized.at(-1) === '') {
    normalized.pop();
  }

  const collapsed: string[] = [];
  for (const line of normalized) {
    if (line === '' && collapsed.at(-1) === '') {
      continue;
    }
    collapsed.push(line);
  }

  return collapsed.length > 0 ? collapsed.join('\n') : null;
}

function extractStructuredLine(line: string): { kind: 'nextStep' | 'cadence'; content: string } | null {
  const trimmed = line.trim();

  if (trimmed.startsWith(NEXT_STEP_PREFIX)) {
    const content = trimmed.slice(NEXT_STEP_PREFIX.length).trim();
    return content ? { kind: 'nextStep', content } : null;
  }

  if (trimmed.startsWith(CADENCE_PREFIX)) {
    const content = trimmed.slice(CADENCE_PREFIX.length).trim();
    return content ? { kind: 'cadence', content } : null;
  }

  return null;
}

export function parseSharedFutureNotes(notes?: string | null): SharedFutureReadModel {
  if (!notes?.trim()) {
    return {
      baseNote: null,
      nextSteps: [],
      cadences: [],
      hasStructuredRefinements: false,
    };
  }

  const baseLines: string[] = [];
  const nextSteps: string[] = [];
  const cadences: string[] = [];

  for (const line of notes.split(/\r?\n/)) {
    const structuredLine = extractStructuredLine(line);
    if (!structuredLine) {
      baseLines.push(line);
      continue;
    }

    if (structuredLine.kind === 'nextStep') {
      nextSteps.push(structuredLine.content);
      continue;
    }

    cadences.push(structuredLine.content);
  }

  return {
    baseNote: normalizeBaseNote(baseLines),
    nextSteps,
    cadences,
    hasStructuredRefinements: nextSteps.length > 0 || cadences.length > 0,
  };
}
