import assert from 'node:assert/strict';
import test from 'node:test';
import { buildJournalTranslationStatusPresentation } from '../journal-translation-status.ts';

test('returns null for non-translated visibility modes', () => {
  assert.equal(
    buildJournalTranslationStatusPresentation({
      currentVisibility: 'PRIVATE',
      hasCurrentJournalId: true,
      isDraft: false,
      partnerTranslationStatus: 'NOT_REQUESTED',
      persistedVisibility: 'PRIVATE',
    }),
    null,
  );
});

test('shows not-ready state for translated-only drafts', () => {
  assert.deepEqual(
    buildJournalTranslationStatusPresentation({
      currentVisibility: 'PARTNER_TRANSLATED_ONLY',
      hasCurrentJournalId: true,
      isDraft: true,
      partnerTranslationStatus: 'NOT_REQUESTED',
      persistedVisibility: 'PARTNER_TRANSLATED_ONLY',
    }),
    {
      label: '尚未準備好',
      message: '這一頁設成整理後版本後，保存才會開始準備伴侶可讀的版本。',
      readyAt: null,
      shortLabel: '尚未準備',
      state: 'not-ready',
      tone: 'neutral',
    },
  );
});

test('shows the private unsaved partner message when translated-only is selected locally', () => {
  assert.deepEqual(
    buildJournalTranslationStatusPresentation({
      currentVisibility: 'PARTNER_TRANSLATED_ONLY',
      hasCurrentJournalId: true,
      hasExplicitVisibilitySelection: true,
      isDraft: false,
      partnerTranslationStatus: 'READY',
      persistedVisibility: 'PRIVATE',
    }),
    {
      label: '尚未準備好',
      message: '你還沒保存這次分享設定。保存前，伴侶仍看不到這一頁。',
      readyAt: null,
      shortLabel: '尚未準備',
      state: 'not-ready',
      tone: 'neutral',
    },
  );
});

test('shows the original-share unsaved partner message when translated-only is selected locally', () => {
  assert.deepEqual(
    buildJournalTranslationStatusPresentation({
      currentVisibility: 'PARTNER_TRANSLATED_ONLY',
      hasCurrentJournalId: true,
      hasExplicitVisibilitySelection: true,
      isDraft: false,
      partnerTranslationStatus: 'READY',
      persistedVisibility: 'PARTNER_ORIGINAL',
    }),
    {
      label: '尚未準備好',
      message: '你還沒保存這次分享設定。保存前，伴侶仍看到原文。',
      readyAt: null,
      shortLabel: '尚未準備',
      state: 'not-ready',
      tone: 'neutral',
    },
  );
});

test('shows the pending partner-ready state', () => {
  assert.deepEqual(
    buildJournalTranslationStatusPresentation({
      currentVisibility: 'PARTNER_TRANSLATED_ONLY',
      hasCurrentJournalId: true,
      isDraft: false,
      partnerTranslationStatus: 'PENDING',
      persistedVisibility: 'PARTNER_TRANSLATED_ONLY',
    }),
    {
      label: '正在整理給伴侶看的版本',
      message: 'Haven 正在準備伴侶可讀的版本。整理完成前，伴侶還看不到這段內容。',
      readyAt: null,
      shortLabel: '整理中',
      state: 'pending',
      tone: 'progress',
    },
  );
});

test('shows the ready partner-visible state', () => {
  assert.deepEqual(
    buildJournalTranslationStatusPresentation({
      currentVisibility: 'PARTNER_TRANSLATED_ONLY',
      hasCurrentJournalId: true,
      isDraft: false,
      partnerTranslationStatus: 'READY',
      persistedVisibility: 'PARTNER_TRANSLATED_ONLY',
    }),
    {
      label: '已整理好給伴侶閱讀',
      message: '伴侶現在看到的是 Haven 整理後的版本，不是你的原文或圖片。',
      readyAt: null,
      shortLabel: '伴侶可讀',
      state: 'ready',
      tone: 'success',
    },
  );
});

test('shows the ready state with readyAt timestamp when provided', () => {
  const result = buildJournalTranslationStatusPresentation({
    currentVisibility: 'PARTNER_TRANSLATED_ONLY',
    hasCurrentJournalId: true,
    isDraft: false,
    partnerTranslationReadyAt: '2026-04-04T06:32:00Z',
    partnerTranslationStatus: 'READY',
    persistedVisibility: 'PARTNER_TRANSLATED_ONLY',
  });
  assert.equal(result?.state, 'ready');
  assert.equal(result?.readyAt, '2026-04-04T06:32:00Z');
});

test('shows the ready state with null readyAt when timestamp is not provided', () => {
  const result = buildJournalTranslationStatusPresentation({
    currentVisibility: 'PARTNER_TRANSLATED_ONLY',
    hasCurrentJournalId: true,
    isDraft: false,
    partnerTranslationReadyAt: null,
    partnerTranslationStatus: 'READY',
    persistedVisibility: 'PARTNER_TRANSLATED_ONLY',
  });
  assert.equal(result?.state, 'ready');
  assert.equal(result?.readyAt, null);
});

test('shows the failed state with retry-on-save messaging', () => {
  assert.deepEqual(
    buildJournalTranslationStatusPresentation({
      currentVisibility: 'PARTNER_TRANSLATED_ONLY',
      hasCurrentJournalId: true,
      isDraft: false,
      partnerTranslationStatus: 'FAILED',
      persistedVisibility: 'PARTNER_TRANSLATED_ONLY',
    }),
    {
      label: '暫時沒整理好',
      message: 'Haven 這次還沒整理好伴侶可讀的版本。伴侶目前看不到這段內容；你下次保存這一頁時，Haven 會再試一次。',
      readyAt: null,
      shortLabel: '暫未完成',
      state: 'failed',
      tone: 'error',
    },
  );
});
