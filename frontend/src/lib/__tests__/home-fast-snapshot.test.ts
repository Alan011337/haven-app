import test from 'node:test';
import assert from 'node:assert/strict';
import {
  resolveHomeOnboardingStepHref,
  resolveOnboardingStepActionLabel,
  sanitizeDailySyncStatusForSnapshot,
} from '../home-fast-snapshot.ts';

test('daily sync snapshot removes answer text and question ids', () => {
  assert.deepEqual(
    sanitizeDailySyncStatusForSnapshot({
      today: '2026-03-13',
      my_filled: true,
      partner_filled: true,
      unlocked: true,
      my_mood_score: 4,
      my_question_id: 'q4',
      my_answer_text: 'hello',
      partner_mood_score: 5,
      partner_question_id: 'q4',
      partner_answer_text: 'world',
      today_question_id: 'q4',
      today_question_label: '明天想一起做的一件小事？',
    }),
    {
      today: '2026-03-13',
      my_filled: true,
      partner_filled: true,
      unlocked: true,
      my_mood_score: 4,
      my_question_id: null,
      my_answer_text: null,
      partner_mood_score: 5,
      partner_question_id: null,
      partner_answer_text: null,
      today_question_id: 'q4',
      today_question_label: '明天想一起做的一件小事？',
    },
  );
});

test('onboarding href routes each next step to the correct home or settings entry', () => {
  assert.equal(resolveHomeOnboardingStepHref('ACCEPT_TERMS'), '/settings#onboarding-consent-card');
  assert.equal(resolveHomeOnboardingStepHref('BIND_PARTNER'), '/settings');
  assert.equal(resolveHomeOnboardingStepHref('RESPOND_FIRST_CARD'), '/?tab=card');
  assert.equal(resolveHomeOnboardingStepHref('PARTNER_FIRST_JOURNAL'), '/?tab=partner');
  assert.equal(resolveHomeOnboardingStepHref('CREATE_FIRST_JOURNAL'), '/');
});

test('onboarding action labels describe the next step in plain language', () => {
  assert.equal(resolveOnboardingStepActionLabel('ACCEPT_TERMS'), '在這裡完成條款與隱私設定');
  assert.equal(resolveOnboardingStepActionLabel('BIND_PARTNER'), '前往連結伴侶');
  assert.equal(resolveOnboardingStepActionLabel('RESPOND_FIRST_CARD'), '前往完成第一張卡片');
});
