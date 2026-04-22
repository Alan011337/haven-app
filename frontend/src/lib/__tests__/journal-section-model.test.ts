import assert from 'node:assert/strict';
import test from 'node:test';
import { buildJournalOutline } from '../journal-outline.ts';
import { buildJournalSectionModel } from '../journal-section-model.ts';

test('buildJournalSectionModel returns a safe starter section for empty drafts', () => {
  assert.deepEqual(
    buildJournalSectionModel({
      content: '',
      outlineEntries: [],
      title: '',
    }),
    [
      {
        characterCount: 0,
        depth: 0,
        excerpt: '',
        id: 'journal-draft',
        isEmpty: true,
        isLight: false,
        kind: 'title',
        label: '未命名的一頁',
        paragraphCount: 0,
      },
    ],
  );
});

test('buildJournalSectionModel derives title intro and h1/h2 body sections', () => {
  const content = [
    '先把還沒有標題的開場放在這裡。',
    '',
    '# Opening Scene',
    '',
    '第一段。',
    '',
    '第二段。',
    '',
    '## What I Need',
    '',
    '最後把真正想留下的需要寫清楚。',
  ].join('\n');
  const outlineEntries = buildJournalOutline({ content, title: 'Night Notes' });
  const sections = buildJournalSectionModel({ content, outlineEntries, title: 'Night Notes' });

  assert.equal(sections.length, 3);
  assert.equal(sections[0]?.id, 'night-notes');
  assert.equal(sections[0]?.excerpt, '先把還沒有標題的開場放在這裡。');
  assert.equal(sections[1]?.id, 'opening-scene');
  assert.equal(sections[1]?.paragraphCount, 2);
  assert.equal(sections[2]?.id, 'what-i-need');
  assert.equal(sections[2]?.isLight, true);
});

test('buildJournalSectionModel strips images and markdown decorations from excerpts', () => {
  const content = [
    '# Images',
    '',
    '![window](attachment:image-1)',
    '',
    '這裡有 **真正要讀的文字**，也有 [連結](https://haven.app)。',
  ].join('\n');
  const outlineEntries = buildJournalOutline({ content, title: 'Media Note' });
  const sections = buildJournalSectionModel({ content, outlineEntries, title: 'Media Note' });

  assert.equal(sections[1]?.excerpt, '這裡有 真正要讀的文字 ，也有 連結。');
  assert.equal(sections[1]?.paragraphCount, 1);
});

test('buildJournalSectionModel preserves duplicate heading ids from the outline', () => {
  const content = ['# Repeated', '', '第一次。', '', '## Repeated', '', '第二次。'].join('\n');
  const outlineEntries = buildJournalOutline({ content, title: 'Repeated' });
  const sections = buildJournalSectionModel({ content, outlineEntries, title: 'Repeated' });

  assert.deepEqual(
    sections.map((section) => section.id),
    ['repeated', 'repeated-2', 'repeated-3'],
  );
});

test('buildJournalSectionModel marks empty heading sections without throwing on malformed text', () => {
  const content = ['```', '# not a heading', '', '# Real', '', '```', '', '# Real'].join('\n');
  const outlineEntries = buildJournalOutline({ content, title: null });
  const sections = buildJournalSectionModel({ content, outlineEntries, title: null });

  assert.equal(sections.at(-1)?.id, 'real');
  assert.equal(sections.at(-1)?.isEmpty, true);
  assert.equal(sections.at(-1)?.paragraphCount, 0);
});
