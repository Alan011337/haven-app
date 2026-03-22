export interface EditorSelectionRange {
  start: number;
  end: number;
}

export interface EditorTransformResult {
  selection: EditorSelectionRange;
  value: string;
}

function clampSelection(value: string, selection: EditorSelectionRange): EditorSelectionRange {
  const start = Math.max(0, Math.min(selection.start, value.length));
  const end = Math.max(start, Math.min(selection.end, value.length));
  return { start, end };
}

export function insertTextAtSelection(
  value: string,
  selection: EditorSelectionRange,
  text: string,
  cursorOffsetFromEnd = 0,
): EditorTransformResult {
  const safeSelection = clampSelection(value, selection);
  const nextValue =
    value.slice(0, safeSelection.start) + text + value.slice(safeSelection.end);
  const cursor = safeSelection.start + text.length - cursorOffsetFromEnd;
  return {
    value: nextValue,
    selection: { start: cursor, end: cursor },
  };
}

export function wrapSelection(
  value: string,
  selection: EditorSelectionRange,
  before: string,
  after: string,
  placeholder: string,
): EditorTransformResult {
  const safeSelection = clampSelection(value, selection);
  const selectedText = value.slice(safeSelection.start, safeSelection.end);
  const nextInner = selectedText || placeholder;
  const nextValue =
    value.slice(0, safeSelection.start) +
    before +
    nextInner +
    after +
    value.slice(safeSelection.end);

  if (selectedText) {
    return {
      value: nextValue,
      selection: {
        start: safeSelection.start + before.length,
        end: safeSelection.start + before.length + nextInner.length,
      },
    };
  }

  return {
    value: nextValue,
    selection: {
      start: safeSelection.start + before.length,
      end: safeSelection.start + before.length + placeholder.length,
    },
  };
}

function getLineRange(value: string, selection: EditorSelectionRange): EditorSelectionRange {
  const safeSelection = clampSelection(value, selection);
  if (safeSelection.start === safeSelection.end) return safeSelection;
  const lineStart = value.lastIndexOf('\n', safeSelection.start - 1) + 1;
  const lineEndIndex = value.indexOf('\n', safeSelection.end);
  const lineEnd = lineEndIndex === -1 ? value.length : lineEndIndex;
  return { start: lineStart, end: lineEnd };
}

export function prefixLines(
  value: string,
  selection: EditorSelectionRange,
  prefix: string,
  placeholder: string,
): EditorTransformResult {
  const safeSelection = clampSelection(value, selection);
  if (safeSelection.start === safeSelection.end) {
    return insertTextAtSelection(
      value,
      safeSelection,
      `${prefix}${placeholder}`,
      placeholder.length,
    );
  }

  const lineRange = getLineRange(value, safeSelection);
  const selectedBlock = value.slice(lineRange.start, lineRange.end);
  const nextBlock = selectedBlock
    .split('\n')
    .map((line) => (line.trim() ? `${prefix}${line}` : line))
    .join('\n');

  return {
    value: value.slice(0, lineRange.start) + nextBlock + value.slice(lineRange.end),
    selection: {
      start: lineRange.start,
      end: lineRange.start + nextBlock.length,
    },
  };
}

export function prefixNumberedLines(
  value: string,
  selection: EditorSelectionRange,
  placeholder: string,
): EditorTransformResult {
  const safeSelection = clampSelection(value, selection);
  if (safeSelection.start === safeSelection.end) {
    return insertTextAtSelection(value, safeSelection, `1. ${placeholder}`, placeholder.length);
  }

  const lineRange = getLineRange(value, safeSelection);
  const selectedBlock = value.slice(lineRange.start, lineRange.end);
  const nextBlock = selectedBlock
    .split('\n')
    .map((line, index) => {
      if (!line.trim()) return line;
      return `${index + 1}. ${line}`;
    })
    .join('\n');

  return {
    value: value.slice(0, lineRange.start) + nextBlock + value.slice(lineRange.end),
    selection: {
      start: lineRange.start,
      end: lineRange.start + nextBlock.length,
    },
  };
}

export function insertCodeBlock(
  value: string,
  selection: EditorSelectionRange,
  placeholder = 'code',
): EditorTransformResult {
  const safeSelection = clampSelection(value, selection);
  const selectedText = value.slice(safeSelection.start, safeSelection.end);
  const body = selectedText || placeholder;
  const block = `\`\`\`\n${body}\n\`\`\``;
  const nextValue =
    value.slice(0, safeSelection.start) + block + value.slice(safeSelection.end);

  return {
    value: nextValue,
    selection: {
      start: safeSelection.start + 4,
      end: safeSelection.start + 4 + body.length,
    },
  };
}

export function insertLink(
  value: string,
  selection: EditorSelectionRange,
  placeholder = '連結文字',
  href = 'https://example.com',
): EditorTransformResult {
  const safeSelection = clampSelection(value, selection);
  const selectedText = value.slice(safeSelection.start, safeSelection.end) || placeholder;
  const snippet = `[${selectedText}](${href})`;
  const nextValue =
    value.slice(0, safeSelection.start) + snippet + value.slice(safeSelection.end);
  const urlStart = safeSelection.start + selectedText.length + 3;
  return {
    value: nextValue,
    selection: {
      start: urlStart,
      end: urlStart + href.length,
    },
  };
}

export function insertMarkdownImage(
  value: string,
  selection: EditorSelectionRange,
  alt: string,
  target: string,
): EditorTransformResult {
  const safeAlt = alt.trim() || 'journal image';
  const snippet = `![${safeAlt}](${target})`;
  const safeSelection = clampSelection(value, selection);
  const before = value.slice(0, safeSelection.start);
  const after = value.slice(safeSelection.end);
  const leadingGap = before.length === 0 ? '' : before.endsWith('\n\n') ? '' : before.endsWith('\n') ? '\n' : '\n\n';
  const trailingGap =
    after.length === 0 ? '' : after.startsWith('\n\n') ? '' : after.startsWith('\n') ? '\n' : '\n\n';
  return insertTextAtSelection(value, safeSelection, `${leadingGap}${snippet}${trailingGap}`);
}
