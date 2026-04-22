import assert from 'node:assert/strict';
import test from 'node:test';
import { buildJournalSharingDeliveryPresentation } from '../journal-sharing-delivery.ts';

test('shows private saved state as partner-invisible', () => {
  const result = buildJournalSharingDeliveryPresentation({
    currentVisibility: 'PRIVATE',
    hasCurrentJournalId: true,
    isDraft: false,
    persistedVisibility: 'PRIVATE',
  });

  assert.equal(result.partnerNowLabel, '伴侶現在看不到這一頁');
  assert.equal(result.nextSaveLabel, '保存後伴侶仍看不到');
  assert.equal(result.lifecycleLabel, '不在交付中');
  assert.equal(result.lifecycleState, 'not-shared');
  assert.equal(result.tone, 'private');
});

test('shows draft translated-only state as not visible until saved', () => {
  const result = buildJournalSharingDeliveryPresentation({
    currentVisibility: 'PARTNER_TRANSLATED_ONLY',
    hasCurrentJournalId: true,
    isDraft: true,
    persistedVisibility: 'PARTNER_TRANSLATED_ONLY',
  });

  assert.equal(result.partnerNowLabel, '伴侶現在看不到這一頁');
  assert.match(result.partnerNowDescription, /草稿/);
  assert.equal(result.nextSaveLabel, '保存後會準備伴侶版本');
  assert.equal(result.lifecycleLabel, '尚未進入交付流程');
  assert.equal(result.lifecycleState, 'not-shared');
});

test('shows original saved state with attachment count', () => {
  const result = buildJournalSharingDeliveryPresentation({
    attachmentsCount: 2,
    currentVisibility: 'PARTNER_ORIGINAL',
    hasCurrentJournalId: true,
    isDraft: false,
    persistedVisibility: 'PARTNER_ORIGINAL',
  });

  assert.equal(result.partnerNowLabel, '伴侶現在看到上一次保存的原文');
  assert.match(result.partnerNowDescription, /2 張圖片/);
  assert.equal(result.nextSaveLabel, '保存後伴侶會看到原文');
  assert.equal(result.lifecycleLabel, '原文分享已保存');
  assert.equal(result.lifecycleState, 'original');
  assert.equal(result.tone, 'original');
});

test('shows original dirty state as last saved original until save', () => {
  const result = buildJournalSharingDeliveryPresentation({
    attachmentsCount: 1,
    currentVisibility: 'PARTNER_ORIGINAL',
    hasCurrentJournalId: true,
    hasUnsavedChanges: true,
    isDraft: false,
    persistedVisibility: 'PARTNER_ORIGINAL',
    saveState: 'dirty',
  });

  assert.match(result.partnerNowDescription, /上一次保存的原文/);
  assert.match(result.partnerNowDescription, /你剛改的內容還沒送出/);
  assert.equal(result.lifecycleLabel, '原文分享等待保存');
  assert.match(result.lifecycleDescription, /上一次保存的原文與圖片/);
  assert.equal(result.tone, 'dirty');
});

test('shows translated-only not-ready state as partner-invisible', () => {
  const result = buildJournalSharingDeliveryPresentation({
    currentVisibility: 'PARTNER_TRANSLATED_ONLY',
    hasCurrentJournalId: true,
    isDraft: false,
    partnerTranslationStatus: 'NOT_REQUESTED',
    persistedVisibility: 'PARTNER_TRANSLATED_ONLY',
  });

  assert.equal(result.partnerNowLabel, '伴侶現在看不到這一頁');
  assert.match(result.partnerNowDescription, /沒有可交付給伴侶/);
  assert.equal(result.lifecycleLabel, '尚未開始準備伴侶版本');
  assert.equal(result.lifecycleState, 'waiting');
  assert.equal(result.tone, 'translated-waiting');
});

test('shows translated-only pending state as partner-invisible while preparing', () => {
  const result = buildJournalSharingDeliveryPresentation({
    currentVisibility: 'PARTNER_TRANSLATED_ONLY',
    hasCurrentJournalId: true,
    isDraft: false,
    partnerTranslationStatus: 'PENDING',
    persistedVisibility: 'PARTNER_TRANSLATED_ONLY',
  });

  assert.equal(result.partnerNowLabel, '伴侶現在看不到這一頁');
  assert.match(result.partnerNowDescription, /整理完成前/);
  assert.equal(result.lifecycleLabel, '正在等待伴侶版本');
  assert.equal(result.lifecycleState, 'waiting');
  assert.equal(result.tone, 'translated-waiting');
});

test('shows translated-only ready state without exposing partner text', () => {
  const result = buildJournalSharingDeliveryPresentation({
    currentVisibility: 'PARTNER_TRANSLATED_ONLY',
    hasCurrentJournalId: true,
    isDraft: false,
    partnerTranslationReadyAt: '2026-04-04T06:32:00Z',
    partnerTranslationStatus: 'READY',
    persistedVisibility: 'PARTNER_TRANSLATED_ONLY',
  });

  assert.equal(result.partnerNowLabel, '伴侶現在看到整理後版本');
  assert.match(result.partnerNowDescription, /不是你的原文或圖片/);
  assert.equal(result.boundaryLabel, '整理後版本只給伴侶閱讀；你仍只會看到自己的原文與準備狀態。');
  assert.equal(result.lifecycleLabel, '整理後版本已交付');
  assert.equal(result.lifecycleMetaLabel, '上次成功準備');
  assert.equal(result.lifecycleReadyAt, '2026-04-04T06:32:00Z');
  assert.equal(result.lifecycleState, 'current');
  assert.equal(result.tone, 'translated-ready');
});

test('shows translated-only failed state as partner-invisible', () => {
  const result = buildJournalSharingDeliveryPresentation({
    currentVisibility: 'PARTNER_TRANSLATED_ONLY',
    hasCurrentJournalId: true,
    isDraft: false,
    partnerTranslationStatus: 'FAILED',
    persistedVisibility: 'PARTNER_TRANSLATED_ONLY',
  });

  assert.equal(result.partnerNowLabel, '伴侶現在看不到這一頁');
  assert.match(result.partnerNowDescription, /沒有可交付給伴侶/);
  assert.equal(result.nextSaveLabel, '保存後會準備伴侶版本');
  assert.equal(result.lifecycleLabel, '這次準備沒有完成');
  assert.equal(result.lifecycleState, 'failed');
});

test('shows unsaved switch from original to translated-only with current original still visible', () => {
  const result = buildJournalSharingDeliveryPresentation({
    currentVisibility: 'PARTNER_TRANSLATED_ONLY',
    hasCurrentJournalId: true,
    hasExplicitVisibilitySelection: true,
    hasUnsavedChanges: true,
    isDraft: false,
    partnerTranslationStatus: 'READY',
    persistedVisibility: 'PARTNER_ORIGINAL',
    saveState: 'dirty',
  });

  assert.equal(result.partnerNowLabel, '伴侶現在看到上一次保存的原文');
  assert.equal(result.nextSaveLabel, '保存後會準備伴侶版本');
  assert.equal(result.lifecycleLabel, '等待保存後開始準備');
  assert.equal(result.lifecycleState, 'waiting');
  assert.equal(result.tone, 'dirty');
});

test('shows dirty translated-only ready state as last ready version until save', () => {
  const result = buildJournalSharingDeliveryPresentation({
    currentVisibility: 'PARTNER_TRANSLATED_ONLY',
    hasCurrentJournalId: true,
    hasUnsavedChanges: true,
    isDraft: false,
    partnerTranslationReadyAt: '2026-04-04T06:32:00Z',
    partnerTranslationStatus: 'READY',
    persistedVisibility: 'PARTNER_TRANSLATED_ONLY',
    saveState: 'dirty',
  });

  assert.equal(result.partnerNowLabel, '伴侶現在看到整理後版本');
  assert.match(result.partnerNowDescription, /上一次已整理好的版本/);
  assert.match(result.nextSaveDescription, /刷新伴侶可讀的整理後版本/);
  assert.equal(result.lifecycleLabel, '上次整理版仍在使用中');
  assert.equal(result.lifecycleReadyAt, '2026-04-04T06:32:00Z');
  assert.equal(result.lifecycleState, 'stale-until-save');
  assert.equal(result.tone, 'dirty');
});

test('shows translated-only saving state as refreshing lifecycle', () => {
  const result = buildJournalSharingDeliveryPresentation({
    currentVisibility: 'PARTNER_TRANSLATED_ONLY',
    hasCurrentJournalId: true,
    hasUnsavedChanges: true,
    isDraft: false,
    partnerTranslationReadyAt: '2026-04-04T06:32:00Z',
    partnerTranslationStatus: 'READY',
    persistedVisibility: 'PARTNER_TRANSLATED_ONLY',
    saveState: 'saving',
  });

  assert.equal(result.lifecycleLabel, '正在刷新伴侶版本');
  assert.match(result.lifecycleDescription, /伺服器確認的狀態/);
  assert.equal(result.lifecycleReadyAt, '2026-04-04T06:32:00Z');
  assert.equal(result.lifecycleState, 'refreshing');
});
