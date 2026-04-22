import assert from 'node:assert/strict';
import test from 'node:test';
import { buildJournalOutline } from '../journal-outline.ts';
import { buildJournalRereadGuide } from '../journal-reread-guide.ts';
import { buildJournalSectionModel } from '../journal-section-model.ts';

function buildSections(content: string, title = 'Night Notes') {
  const outlineEntries = buildJournalOutline({ content, title });
  return buildJournalSectionModel({ content, outlineEntries, title });
}

test('buildJournalRereadGuide selects opener, strongest middle, and closing anchors for long-form entries', () => {
  const content = [
    '# Opening Scene',
    '',
    '第一段。',
    '',
    '第二段。',
    '',
    '## Thin Bridge',
    '',
    '短短一段。',
    '',
    '## Deep Middle',
    '',
    '這是比較長的中段，讓重讀路線可以找到真正展開的地方。',
    '',
    '這裡還有第二段，讓它比其他中段更適合成為深入入口。',
    '',
    '## Closing Note',
    '',
    '最後把真正想留下的需要寫清楚。',
  ].join('\n');
  const guide = buildJournalRereadGuide({
    content,
    imageCount: 2,
    sections: buildSections(content),
  });

  assert.equal(guide.sectionCount, 5);
  assert.equal(guide.paragraphCount, 6);
  assert.equal(guide.imageCount, 2);
  assert.equal(guide.emptyOrShort, false);
  assert.deepEqual(
    guide.pathItems.map((item) => [item.slot, item.sectionLabel]),
    [
      ['opener', 'Opening Scene'],
      ['middle', 'Deep Middle'],
      ['closing', 'Closing Note'],
    ],
  );
  assert.match(guide.summary, /5 個段落、6 段正文、2 張圖片/);
});

test('buildJournalRereadGuide returns a calm short-entry fallback', () => {
  const content = '只先留下一句。';
  const guide = buildJournalRereadGuide({
    content,
    imageCount: 0,
    sections: buildSections(content, ''),
  });

  assert.equal(guide.emptyOrShort, true);
  assert.equal(guide.paragraphCount, 1);
  assert.equal(guide.pathItems.length, 1);
  assert.equal(guide.pathItems[0]?.slot, 'opener');
  assert.equal(guide.pathItems[0]?.excerpt, '只先留下一句。');
});

test('buildJournalRereadGuide counts empty and light sections without dropping anchors', () => {
  const content = ['# Empty', '', '## Light', '', '短句。'].join('\n');
  const guide = buildJournalRereadGuide({
    content,
    imageCount: 1,
    sections: buildSections(content, ''),
  });

  assert.equal(guide.lightSectionCount, 2);
  assert.equal(guide.imageCount, 1);
  assert.equal(guide.pathItems[0]?.sectionLabel, 'Light');
  assert.match(guide.summary, /其中 2 段還很輕/);
});

test('buildJournalRereadGuide preserves duplicate section ids from the section model', () => {
  const content = ['# Repeated', '', '第一次。', '', '## Repeated', '', '第二次。'].join('\n');
  const guide = buildJournalRereadGuide({
    content,
    imageCount: 0,
    sections: buildSections(content, 'Repeated'),
  });

  assert.deepEqual(
    guide.pathItems.map((item) => item.sectionId),
    ['repeated-2', 'repeated-3'],
  );
});

test('buildJournalRereadGuide never throws on malformed or empty markdown', () => {
  const content = ['```', '# not a heading', '', '![image](attachment:one)', '```'].join('\n');
  const guide = buildJournalRereadGuide({
    content,
    imageCount: -2,
    sections: buildSections(content, ''),
  });

  assert.equal(guide.imageCount, 0);
  assert.equal(guide.emptyOrShort, true);
  assert.ok(guide.summary.length > 0);
});
