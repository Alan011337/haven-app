import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildAnalysisEvidencePreviewMap,
  type BuildAnalysisEvidencePreviewMapInput,
} from '../analysis-v2-evidence-preview.ts';

function baseInput(
  overrides: Partial<BuildAnalysisEvidencePreviewMapInput> = {},
): BuildAnalysisEvidencePreviewMapInput {
  return {
    maxItems: 2,
    lenses: [
      {
        id: 'tension',
        eyebrow: 'Repair Evidence',
        title: '最近需要先照顧安全感的地方',
        summary: '把高張力時刻拆回實際痕跡。',
        stats: [
          {
            label: '高張力片段',
            value: '2',
            hint: '近兩週被標成需要放慢的紀錄',
          },
        ],
        entries: [
          {
            id: 'journal-1',
            eyebrow: '你',
            title: '你最近更常從「疲憊」進入',
            description: '我需要先被理解，而不是立刻被糾正。',
            meta: '3/15 10:00',
            badges: ['疲憊', '高張力'],
            action: {
              label: '打開完整日記',
              href: '/journal/journal-1?from=analysis&date=2026-03-15',
            },
          },
          {
            id: 'journal-2',
            eyebrow: '伴侶',
            title: '伴侶留下了一則關鍵痕跡',
            description: '我需要安全感和更慢一點的回應。',
            meta: '3/15 18:00',
            badges: ['不安'],
          },
        ],
      },
    ],
    artifacts: [
      {
        key: '/love-map#identity',
        source: 'Relationship Compass',
        title: '先靠近你們自己寫下的未來方向',
        excerpt: '接下來一起靠近更穩定的週末節奏。',
        meta: '更新於 3/15',
        href: '/love-map#identity',
      },
    ],
    ...overrides,
  };
}

test('buildAnalysisEvidencePreviewMap turns lens entries into compact preview rows', () => {
  const map = buildAnalysisEvidencePreviewMap(baseInput());
  const preview = map.tension;

  assert.equal(preview.action.evidenceId, 'tension');
  assert.equal(preview.action.label, '展開完整依據');
  assert.equal(preview.items.length, 2);
  assert.equal(preview.items[0].source, '你');
  assert.match(preview.items[0].excerpt, /先被理解/);
  assert.ok(preview.items[0].badges.includes('高張力'));
  assert.equal(preview.items[0].action?.label, '打開完整日記');
  assert.equal(preview.items[0].action?.href, '/journal/journal-1?from=analysis&date=2026-03-15');
});

test('buildAnalysisEvidencePreviewMap uses stats when entries are missing', () => {
  const map = buildAnalysisEvidencePreviewMap(
    baseInput({
      lenses: [
        {
          id: 'sync',
          eyebrow: 'Rhythm Evidence',
          title: '你們的節拍最近比較容易斷掉',
          entries: [],
          stats: [
            {
              label: '本週同步',
              value: '43%',
              hint: '3/7 天留下了回答',
            },
          ],
        },
      ],
      artifacts: [],
    }),
  );

  assert.equal(map.sync.items.length, 1);
  assert.match(map.sync.items[0].title, /本週同步/);
  assert.match(map.sync.items[0].excerpt, /3\/7 天/);
  assert.ok(map.sync.items[0].badges.includes('數據定位'));
});

test('buildAnalysisEvidencePreviewMap returns calm fallback for empty lenses', () => {
  const map = buildAnalysisEvidencePreviewMap(
    baseInput({
      lenses: [
        {
          id: 'patterns',
          eyebrow: 'Pattern Read',
          title: '雙方模式還在慢慢浮出來',
          entries: [],
          stats: [],
          emptyMessage: '等情緒語氣與需要更清楚後，這裡會顯示更完整的雙方模式。',
        },
      ],
      artifacts: [],
    }),
  );

  assert.equal(map.patterns.items.length, 1);
  assert.match(map.patterns.items[0].excerpt, /等情緒語氣/);
  assert.ok(map.patterns.items[0].badges.includes('保守讀法'));
});

test('buildAnalysisEvidencePreviewMap includes artifact pointers for href actions', () => {
  const map = buildAnalysisEvidencePreviewMap(baseInput());
  const preview = map['/love-map#identity'];

  assert.equal(preview.action.href, '/love-map#identity');
  assert.equal(preview.action.label, '打開原始位置');
  assert.equal(preview.items[0].source, 'Relationship Compass');
  assert.match(preview.items[0].excerpt, /週末節奏/);
  assert.equal(preview.items[0].action?.label, '打開來源');
  assert.equal(preview.items[0].action?.href, '/love-map#identity');
});

test('buildAnalysisEvidencePreviewMap drops malformed row actions', () => {
  const map = buildAnalysisEvidencePreviewMap(
    baseInput({
      lenses: [
        {
          id: 'tension',
          entries: [
            {
              id: 'journal-with-bad-action',
              eyebrow: '你',
              title: '有內容但沒有安全連結',
              description: '這個片段可以展示，但不應該有 row action。',
              action: {
                label: ' ',
                href: '/journal/journal-with-bad-action',
              },
            },
          ],
        },
      ],
      artifacts: [
        {
          key: '/love-map#heart',
          source: 'Repair Agreements',
          title: '有來源',
          excerpt: '但覆寫 action 不完整時要回到安全預設。',
          href: '/love-map#heart',
          action: {
            label: ' ',
          },
        },
      ],
    }),
  );

  assert.equal(map.tension.items[0].action, undefined);
  assert.equal(map['/love-map#heart'].items[0].action?.label, '打開來源');
  assert.equal(map['/love-map#heart'].items[0].action?.href, '/love-map#heart');
});

test('buildAnalysisEvidencePreviewMap truncates long preview text', () => {
  const map = buildAnalysisEvidencePreviewMap(
    baseInput({
      lenses: [
        {
          id: 'appreciation',
          eyebrow: 'Appreciation Evidence',
          entries: [
            {
              id: 'long-entry',
              eyebrow: 'Appreciation',
              title: '一段非常長的感謝標題'.repeat(8),
              description: '一段非常長的感謝內容'.repeat(16),
            },
          ],
        },
      ],
      artifacts: [],
    }),
  );

  assert.ok(map.appreciation.items[0].title.length <= 74);
  assert.ok(map.appreciation.items[0].excerpt.length <= 118);
  assert.match(map.appreciation.items[0].excerpt, /…$/);
});

test('buildAnalysisEvidencePreviewMap skips unusable artifacts without throwing', () => {
  const map = buildAnalysisEvidencePreviewMap(
    baseInput({
      lenses: [
        {
          id: 'bad-lens',
          entries: [{ id: 'empty-entry' }],
          stats: [{ label: '', value: '', hint: '' }],
        },
      ],
      artifacts: [
        {
          key: '/empty',
          source: 'Relationship System',
          title: ' ',
          excerpt: ' ',
          href: '/empty',
        },
      ],
    }),
  );

  assert.equal(map['/empty'], undefined);
  assert.equal(map['bad-lens'].items.length, 1);
});
