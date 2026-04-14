import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildCreateJournalPayload,
  buildUpdateJournalPayload,
  hasJournalDraftContent,
  hasJournalSubstantiveContent,
  normalizeJournalDraftContent,
  normalizeJournalDraftTitle,
  resolveJournalDraftContent,
} from '../journal-draft-payload.ts';

test('resolveJournalDraftContent prefers the live editor markdown and normalizes line endings', () => {
  assert.equal(
    resolveJournalDraftContent({
      editorMarkdown: '第一段\r\n\r\n第二段',
      fallbackContent: 'fallback',
    }),
    '第一段\n\n第二段',
  );
});

test('resolveJournalDraftContent falls back to React state when the editor is not ready', () => {
  assert.equal(
    resolveJournalDraftContent({
      editorMarkdown: null,
      fallbackContent: '畫面上的內容',
    }),
    '畫面上的內容',
  );
});

test('resolveJournalDraftContent falls back to the hydrated state when the editor is still blank', () => {
  assert.equal(
    resolveJournalDraftContent({
      editorMarkdown: '',
      fallbackContent: '從後端回來的內容',
    }),
    '從後端回來的內容',
  );
});

test('normalizeJournalDraftTitle converts blank titles to null', () => {
  assert.equal(normalizeJournalDraftTitle('   '), null);
  assert.equal(normalizeJournalDraftTitle('  夜裡想留下的一頁  '), '夜裡想留下的一頁');
});

test('hasJournalDraftContent only accepts meaningful content', () => {
  assert.equal(hasJournalDraftContent('   \n  '), false);
  assert.equal(hasJournalDraftContent('留下這句話'), true);
});

test('hasJournalSubstantiveContent ignores attachment-only markdown', () => {
  assert.equal(hasJournalSubstantiveContent('![window light](attachment:one)'), false);
  assert.equal(
    hasJournalSubstantiveContent(['![window light](attachment:one)', '留下一句正文'].join('\n\n')),
    true,
  );
});

test('buildCreateJournalPayload emits only the backend-supported create fields', () => {
  assert.deepEqual(
    buildCreateJournalPayload({
      content: '第一段\r\n\r\n第二段',
      isDraft: true,
      title: '  測試標題  ',
      visibility: 'PARTNER_TRANSLATED_ONLY',
    }),
    {
      content: '第一段\n\n第二段',
      content_format: 'markdown',
      is_draft: true,
      title: '測試標題',
      visibility: 'PARTNER_TRANSLATED_ONLY',
    },
  );
});

test('buildUpdateJournalPayload emits only the backend-supported update fields', () => {
  assert.deepEqual(
    buildUpdateJournalPayload({
      content: normalizeJournalDraftContent('更新後內容'),
      isDraft: false,
      title: '   ',
      visibility: 'PRIVATE',
    }),
    {
      content: '更新後內容',
      is_draft: false,
      request_analysis: false,
      title: null,
      visibility: 'PRIVATE',
    },
  );
});
