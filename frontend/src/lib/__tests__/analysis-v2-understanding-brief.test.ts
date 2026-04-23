import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildAnalysisV2UnderstandingBrief,
  type AnalysisUnderstandingBriefInput,
} from '../analysis-v2-understanding-brief.ts';

function baseInput(overrides: Partial<AnalysisUnderstandingBriefInput> = {}): AnalysisUnderstandingBriefInput {
  return {
    hasPartner: true,
    pulseScore: 58,
    syncCompletionPct: 43,
    alignmentPct: 29,
    journalCount14: 4,
    myJournalCount14: 2,
    partnerJournalCount14: 2,
    highTensionCount14: 1,
    appreciationCount: 2,
    topTopics: ['修復', '安全感'],
    currentRead: '這週的連結還在，但更需要被刻意照顧。',
    patternTitle: '你最近更常從「疲憊」進入，伴侶更常從「不安」進入',
    monthlyTrendSummary: '最近你們其實都有想靠近的動機。',
    healthSuggestion: '先從一段低壓力對話開始。',
    todaySyncState: '今天還差你的同步。',
    relationshipCompass: {
      identity_statement: '我們是在忙裡仍願意回來對話的伴侶。',
      story_anchor: '想一起記得那些有走回彼此的時刻。',
      future_direction: '接下來一起靠近更穩定的週末節奏。',
    },
    repairAgreements: {
      protect_what_matters: '先保護安全感。',
      avoid_in_conflict: '避免翻舊帳。',
      repair_reentry: '24 小時內回來。',
    },
    hasHeartCare: true,
    weeklyTask: {
      task_label: '一起完成一個小照顧。',
      completed: false,
    },
    storyMomentCount: 2,
    wishlistCount: 3,
    loveMapAvailable: true,
    ...overrides,
  };
}

test('buildAnalysisV2UnderstandingBrief returns four stable relationship questions', () => {
  const model = buildAnalysisV2UnderstandingBrief(baseInput());

  assert.equal(model.title, '這週的關係讀法');
  assert.deepEqual(model.cards.map((card) => card.question), [
    '我們最近怎麼樣',
    '什麼正在撐住我們',
    '哪裡需要先照顧',
    '下一步往哪裡靠近',
  ]);
});

test('full data grounds strength and direction in Relationship Compass', () => {
  const model = buildAnalysisV2UnderstandingBrief(baseInput());
  const strength = model.cards.find((card) => card.key === 'strength');
  const direction = model.cards.find((card) => card.key === 'direction');

  assert.ok(strength?.sources.includes('Relationship Compass'));
  assert.match(strength?.description ?? '', /走回彼此/);
  assert.ok(direction?.sources.includes('Relationship Compass'));
  assert.match(direction?.description ?? '', /更穩定的週末節奏/);
  assert.equal(direction?.action.href, '/love-map#identity');
});

test('high tension attention card keeps Repair Agreements visible as grounding', () => {
  const model = buildAnalysisV2UnderstandingBrief(baseInput());
  const attention = model.cards.find((card) => card.key === 'attention');

  assert.equal(attention?.tone, 'attention');
  assert.ok(attention?.sources.includes('Repair Agreements'));
  assert.match(attention?.description ?? '', /3\/3 個 Repair Agreements/);
  assert.equal(attention?.action.evidenceId, 'tension');
});

test('low sync without high tension points attention to rhythm evidence', () => {
  const model = buildAnalysisV2UnderstandingBrief(baseInput({ highTensionCount14: 0 }));
  const attention = model.cards.find((card) => card.key === 'attention');

  assert.equal(attention?.tone, 'attention');
  assert.equal(attention?.action.evidenceId, 'sync');
  assert.ok(attention?.sources.includes('Daily Sync'));
});

test('partial data without Love Map still returns a conservative brief', () => {
  const model = buildAnalysisV2UnderstandingBrief(
    baseInput({
      relationshipCompass: null,
      repairAgreements: null,
      hasHeartCare: false,
      weeklyTask: null,
      loveMapAvailable: false,
      appreciationCount: 0,
      storyMomentCount: 0,
      wishlistCount: 0,
      highTensionCount14: 0,
    }),
  );

  assert.equal(model.cards.length, 4);
  assert.match(model.sourceNote, /Relationship System 暫時沒有回來/);
  assert.ok(model.cards.every((card) => card.description.trim().length > 0));
});

test('unpaired state avoids over-claiming pair insight', () => {
  const model = buildAnalysisV2UnderstandingBrief(
    baseInput({
      hasPartner: false,
      pulseScore: null,
      partnerJournalCount14: 0,
      relationshipCompass: null,
      repairAgreements: null,
      loveMapAvailable: false,
    }),
  );
  const current = model.cards.find((card) => card.key === 'current');

  assert.equal(current?.tone, 'quiet');
  assert.match(current?.title ?? '', /自己的節奏/);
});

test('no data still produces useful starter actions instead of pseudo-insight', () => {
  const model = buildAnalysisV2UnderstandingBrief(
    baseInput({
      hasPartner: true,
      pulseScore: null,
      syncCompletionPct: 0,
      alignmentPct: 0,
      journalCount14: 0,
      myJournalCount14: 0,
      partnerJournalCount14: 0,
      highTensionCount14: 0,
      appreciationCount: 0,
      topTopics: [],
      currentRead: null,
      patternTitle: null,
      monthlyTrendSummary: null,
      healthSuggestion: null,
      todaySyncState: null,
      relationshipCompass: null,
      repairAgreements: null,
      hasHeartCare: false,
      weeklyTask: null,
      storyMomentCount: 0,
      wishlistCount: 0,
      loveMapAvailable: false,
    }),
  );
  const direction = model.cards.find((card) => card.key === 'direction');

  assert.equal(model.cards.length, 4);
  assert.match(direction?.title ?? '', /共同方向/);
  assert.equal(direction?.action.href, '/love-map#identity');
});
