import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildMemoryDayRevealModel,
  getMemoryDayRevealArtifactKey,
} from '../memory-day-reveal.ts';
import type { TimelineItem } from '@/services/memoryService';

const JOURNAL: TimelineItem = {
  type: 'journal',
  id: 'journal-1',
  created_at: '2026-04-20T10:00:00Z',
  user_id: 'alice',
  mood_label: '安心',
  content_preview: '今天我們一起去散步，聊到最近真正需要被理解的地方。',
  is_own: true,
  attachment_count: 0,
  attachments: [],
};

const CARD: TimelineItem = {
  type: 'card',
  session_id: 'card-1',
  revealed_at: '2026-04-20T11:00:00Z',
  card_title: '慢慢說出來',
  card_question: '今天最想讓對方理解的是什麼？',
  category: 'connection',
  my_answer: '我想先被聽完。',
  partner_answer: '我想知道你還在。',
  is_own: true,
};

const APPRECIATION: TimelineItem = {
  type: 'appreciation',
  id: '12',
  created_at: '2026-04-20T12:00:00Z',
  user_id: 'alice',
  partner_id: 'bob',
  body_text: '謝謝你今天願意把語氣放慢。',
  is_mine: true,
};

const PHOTO: TimelineItem = {
  type: 'photo',
  id: 'photo-1',
  created_at: '2026-04-20T13:00:00Z',
  user_id: 'bob',
  caption: '河邊散步的照片',
  is_own: false,
};

test('buildMemoryDayRevealModel returns a calm empty model', () => {
  const model = buildMemoryDayRevealModel({ date: '2026-04-20', items: [] });

  assert.equal(model.mode, 'empty');
  assert.equal(model.counts.total, 0);
  assert.match(model.summaryLabel, /暫時沒有/);
});

test('buildMemoryDayRevealModel derives a single journal reveal', () => {
  const model = buildMemoryDayRevealModel({ date: '2026-04-20', items: [JOURNAL] });

  assert.equal(model.mode, 'single');
  assert.equal(model.counts.journal, 1);
  assert.equal(model.artifacts[0].key, 'journal:journal-1');
  assert.equal(model.artifacts[0].contextLabel, '我寫下');
  assert.equal(model.artifacts[0].actionLabel, '打開完整日記');
  assert.match(model.artifacts[0].excerpt, /散步/);
});

test('buildMemoryDayRevealModel derives a single card reveal', () => {
  const model = buildMemoryDayRevealModel({ date: '2026-04-20', items: [CARD] });

  assert.equal(model.mode, 'single');
  assert.equal(model.counts.card, 1);
  assert.equal(model.artifacts[0].key, 'card:card-1');
  assert.equal(model.artifacts[0].contextLabel, '雙方都回答了');
  assert.equal(model.artifacts[0].actionLabel, '打開完整卡片對話');
});

test('buildMemoryDayRevealModel derives a single appreciation reveal', () => {
  const model = buildMemoryDayRevealModel({ date: '2026-04-20', items: [APPRECIATION] });

  assert.equal(model.mode, 'single');
  assert.equal(model.counts.appreciation, 1);
  assert.equal(model.artifacts[0].key, 'appreciation:12');
  assert.equal(model.artifacts[0].contextLabel, '我寫給伴侶');
  assert.equal(model.artifacts[0].actionLabel, '打開完整感謝');
});

test('buildMemoryDayRevealModel keeps multi-artifact counts and stable keys', () => {
  const model = buildMemoryDayRevealModel({
    date: '2026-04-20',
    items: [JOURNAL, CARD, APPRECIATION, PHOTO],
  });

  assert.equal(model.mode, 'multi');
  assert.equal(model.counts.total, 4);
  assert.deepEqual(
    model.artifacts.map((artifact) => artifact.key),
    ['journal:journal-1', 'card:card-1', 'appreciation:12', 'photo:photo-1'],
  );
  assert.match(model.summaryLabel, /4 個真實片段/);
});

test('buildMemoryDayRevealModel degrades malformed blank text without throwing', () => {
  const blankJournal: TimelineItem = {
    ...JOURNAL,
    content_preview: '   ',
    mood_label: '',
    attachments: [
      {
        id: 'attachment-1',
        file_name: 'memory.jpg',
        mime_type: 'image/jpeg',
        caption: '  ',
      },
    ],
  };

  const model = buildMemoryDayRevealModel({ date: 'bad-date', items: [blankJournal] });

  assert.equal(model.date, 'bad-date');
  assert.equal(model.artifacts[0].title, '一頁被留下的日記');
  assert.match(model.artifacts[0].excerpt, /1 張圖片/);
});

test('getMemoryDayRevealArtifactKey uses card session ids and item ids consistently', () => {
  assert.equal(getMemoryDayRevealArtifactKey(CARD), 'card:card-1');
  assert.equal(getMemoryDayRevealArtifactKey(JOURNAL), 'journal:journal-1');
  assert.equal(getMemoryDayRevealArtifactKey(APPRECIATION), 'appreciation:12');
});
