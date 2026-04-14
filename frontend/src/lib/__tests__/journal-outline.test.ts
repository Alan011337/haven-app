import assert from 'node:assert/strict';
import test from 'node:test';
import { buildJournalOutline } from '../journal-outline.ts';

test('buildJournalOutline includes the title plus h1 and h2 headings in order', () => {
  assert.deepEqual(
    buildJournalOutline({
      title: 'Night Notes',
      content: ['# Opening Scene', '', 'Body copy', '', '## What I Need', '', 'Closing thoughts'].join('\n'),
    }),
    [
      { depth: 0, id: 'night-notes', kind: 'title', label: 'Night Notes' },
      { depth: 1, id: 'opening-scene', kind: 'heading', label: 'Opening Scene' },
      { depth: 2, id: 'what-i-need', kind: 'heading', label: 'What I Need' },
    ],
  );
});

test('buildJournalOutline ignores headings inside fenced code blocks', () => {
  assert.deepEqual(
    buildJournalOutline({
      title: 'Code Fence Check',
      content: ['```', '# not a heading', '## also not a heading', '```', '', '# Real Heading'].join('\n'),
    }),
    [
      { depth: 0, id: 'code-fence-check', kind: 'title', label: 'Code Fence Check' },
      { depth: 1, id: 'real-heading', kind: 'heading', label: 'Real Heading' },
    ],
  );
});

test('buildJournalOutline generates stable suffixes for duplicate labels', () => {
  assert.deepEqual(
    buildJournalOutline({
      title: 'Repeated',
      content: ['# Repeated', '', '## Repeated', '', '# Repeated'].join('\n'),
    }).map((entry) => entry.id),
    ['repeated', 'repeated-2', 'repeated-3', 'repeated-4'],
  );
});

test('buildJournalOutline ignores image-only title and non-structural markdown', () => {
  assert.deepEqual(
    buildJournalOutline({
      title: '![cover](attachment:hero)',
      content: ['![cover](attachment:hero)', '', '## A Quiet Section'].join('\n'),
    }),
    [{ depth: 2, id: 'a-quiet-section', kind: 'heading', label: 'A Quiet Section' }],
  );
});
