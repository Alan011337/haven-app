'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { isAxiosError } from 'axios';
import {
  BellRing,
  Check,
  Clock3,
  Copy,
  HeartHandshake,
  Link2,
  PauseCircle,
  RefreshCw,
  Shield,
  ShieldCheck,
  Sparkles,
  Target,
  Wind,
} from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Input, { Textarea } from '@/components/ui/Input';
import { useToast } from '@/hooks/useToast';
import { useCooldownStatus } from '@/hooks/queries/useCooldownStatus';
import { queryKeys } from '@/lib/query-keys';
import {
  buildReferralInviteUrl,
  createReferralCoupleInviteEventId,
  normalizeInviteCode,
} from '@/lib/referral';
import { logClientError } from '@/lib/safe-error-log';
import {
  fetchWeeklyReport,
  rewriteMessage,
  startCooldown,
  trackReferralCoupleInvite,
  type WeeklyReportPublic,
} from '@/services/api-client';
import {
  fetchBaseline,
  fetchCoupleGoal,
  type BaselineSummaryPublic,
  type CoupleGoalPublic,
} from '@/services/relationship-api';
import {
  fetchOnboardingConsent,
  fetchUserMe,
  generateInviteCode,
  pairWithPartner,
  upsertOnboardingConsent,
  type OnboardingConsentCreate,
  type OnboardingConsentPublic,
  type UserMeResponse,
} from '@/services/user';
import { useAppearanceStore } from '@/stores/useAppearanceStore';
import {
  SettingsChoiceGrid,
  type SettingsChoiceOption,
  SettingsCover,
  SettingsFieldRow,
  SettingsFooterNote,
  SettingsSection,
  SettingsSectionRail,
  type SettingsSectionRailItem,
  SettingsSnapshotCard,
  SettingsStatePanel,
  SettingsSwitch,
} from '@/app/settings/SettingsPrimitives';

type NotifFreq = OnboardingConsentCreate['notification_frequency'];
type AIIntensity = OnboardingConsentCreate['ai_intensity'];

type RelationshipSettingsData = {
  baseline: BaselineSummaryPublic;
  goal: CoupleGoalPublic | null;
};

const SECTION_ITEMS: SettingsSectionRailItem[] = [
  { id: 'settings-trust', label: 'Trust & Boundaries', description: '隱私、通知與 AI 介入的邊界。' },
  { id: 'settings-relationship', label: 'Relationship Direction', description: '伴侶連結、雷達與共同目標。' },
  { id: 'settings-support', label: 'Support Rhythm', description: '每週節奏與需要暫停時的支持。' },
  { id: 'settings-device', label: 'Device Feel', description: '卡片、音效與觸覺的陪伴感。' },
];

const NOTIFICATION_OPTIONS: SettingsChoiceOption[] = [
  { value: 'low', label: '較少', description: '只留下關鍵提醒，讓 Haven 更安靜。', eyebrow: 'Quiet' },
  { value: 'normal', label: '一般', description: '保持穩定節奏，適合大多數情況。', eyebrow: 'Balanced' },
  { value: 'high', label: '較多', description: '更主動提醒你們回到互動與儀式。', eyebrow: 'Guided' },
  { value: 'off', label: '關閉 Email 備援', description: '只保留產品內的主要互動訊號。', eyebrow: 'Minimal' },
];

const AI_OPTIONS: SettingsChoiceOption[] = [
  { value: 'gentle', label: '溫和引導', description: '更像柔和陪伴與留白提示。', eyebrow: 'Soft' },
  { value: 'direct', label: '直接提醒', description: '更快指出問題與下一步。', eyebrow: 'Clear' },
];

const GOAL_OPTIONS: SettingsChoiceOption[] = [
  { value: 'reduce_argument', label: '減少爭吵', description: '把情緒升高前的修復做得更早。', eyebrow: 'Repair' },
  { value: 'increase_intimacy', label: '提升親密感', description: '把溫柔、靠近與分享重新變得容易。', eyebrow: 'Closeness' },
  { value: 'better_communication', label: '更好溝通', description: '讓彼此更懂得怎麼說、怎麼聽。', eyebrow: 'Dialogue' },
  { value: 'more_trust', label: '更多信任', description: '讓安全感與可依靠感慢慢累積。', eyebrow: 'Trust' },
  { value: 'other', label: '其他', description: '先定一個方向，之後再慢慢細化。', eyebrow: 'Flexible' },
];

const HAPTIC_OPTIONS: SettingsChoiceOption[] = [
  { value: 'light', label: '輕', description: '只是輕輕碰一下，不打擾。', eyebrow: 'Soft' },
  { value: 'medium', label: '中', description: '保留更明確的回饋感。', eyebrow: 'Present' },
];

function scrollToSection(id: string) {
  if (typeof document === 'undefined') return;
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function formatShortDate(iso?: string | null) {
  if (!iso) return '還沒有紀錄';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '還沒有紀錄';
  return new Intl.DateTimeFormat('zh-TW', {
    month: 'numeric',
    day: 'numeric',
  }).format(date);
}

function formatDateTime(iso?: string | null) {
  if (!iso) return '還沒有紀錄';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '還沒有紀錄';
  return new Intl.DateTimeFormat('zh-TW', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function formatRemaining(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remain = seconds % 60;
  return `${minutes}:${remain.toString().padStart(2, '0')}`;
}

function getNotificationLabel(value: NotifFreq) {
  return NOTIFICATION_OPTIONS.find((option) => option.value === value)?.label ?? '一般';
}

function getAIIntensityLabel(value: AIIntensity) {
  return AI_OPTIONS.find((option) => option.value === value)?.label ?? '溫和引導';
}

function getGoalLabel(value?: string | null) {
  return GOAL_OPTIONS.find((option) => option.value === value)?.label ?? '還在思考方向';
}

function getInitial(value?: string | null) {
  if (!value) return 'H';
  return value.charAt(0).toUpperCase();
}

function getPairErrorMessage(error: unknown) {
  if (isAxiosError(error) && error.response?.status === 409) {
    return error.response.data?.detail || '目前連結狀態有衝突，請稍後再試一次。';
  }
  if (isAxiosError(error) && error.response?.status === 400) {
    return '這組邀請碼已過期或不存在，請伴侶重新產生一組。';
  }
  return '連結沒有成功，請確認代碼是否正確，或稍後再試一次。';
}

export default function SettingsPageBody() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const cardGlowEnabled = useAppearanceStore((state) => state.cardGlowEnabled);
  const setCardGlowEnabled = useAppearanceStore((state) => state.setCardGlowEnabled);
  const hapticsEnabled = useAppearanceStore((state) => state.hapticsEnabled);
  const setHapticsEnabled = useAppearanceStore((state) => state.setHapticsEnabled);
  const hapticStrength = useAppearanceStore((state) => state.hapticStrength);
  const setHapticStrength = useAppearanceStore((state) => state.setHapticStrength);
  const soundEnabled = useAppearanceStore((state) => state.soundEnabled);
  const setSoundEnabled = useAppearanceStore((state) => state.setSoundEnabled);

  const consentQuery = useQuery({
    queryKey: ['settings', 'consent'],
    queryFn: fetchOnboardingConsent,
    staleTime: 60_000,
  });

  const partnerQuery = useQuery({
    queryKey: ['settings', 'me'],
    queryFn: fetchUserMe,
    staleTime: 60_000,
  });

  const relationshipQuery = useQuery<RelationshipSettingsData>({
    queryKey: ['settings', 'relationship'],
    queryFn: async () => {
      const [baseline, goal] = await Promise.all([fetchBaseline(), fetchCoupleGoal()]);
      return { baseline, goal };
    },
    staleTime: 60_000,
  });

  const weeklyReportQuery = useQuery({
    queryKey: ['settings', 'weekly-report'],
    queryFn: fetchWeeklyReport,
    staleTime: 60_000,
    retry: 1,
  });

  const cooldownQuery = useCooldownStatus();
  const cooldownData = cooldownQuery.data;
  const cooldownLoading = cooldownQuery.isLoading;
  const cooldownError = cooldownQuery.isError;
  const refetchCooldown = cooldownQuery.refetch;

  const [trustDraft, setTrustDraft] = useState<{
    privacyScope?: boolean;
    notificationFrequency?: NotifFreq;
    aiIntensity?: AIIntensity;
  }>({});
  const [generatedInviteCode, setGeneratedInviteCode] = useState<string | null>(null);
  const [inputCode, setInputCode] = useState('');
  const [copied, setCopied] = useState(false);
  const [rewriteDraft, setRewriteDraft] = useState('');
  const [rewritten, setRewritten] = useState<string | null>(null);
  const [tickNow, setTickNow] = useState(0);

  useEffect(() => {
    if (!cooldownData?.in_cooldown || !cooldownData.ends_at_iso) return;
    const interval = setInterval(() => setTickNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, [cooldownData?.ends_at_iso, cooldownData?.in_cooldown]);

  const displaySeconds =
    cooldownData?.in_cooldown && cooldownData.ends_at_iso
      ? Math.max(0, Math.floor((new Date(cooldownData.ends_at_iso).getTime() - tickNow) / 1000))
      : 0;

  useEffect(() => {
    if (cooldownData?.in_cooldown && displaySeconds <= 0) {
      void refetchCooldown();
    }
  }, [cooldownData?.in_cooldown, displaySeconds, refetchCooldown]);

  const saveConsentMutation = useMutation({
    mutationFn: (payload: OnboardingConsentCreate) => upsertOnboardingConsent(payload),
    onSuccess: async (updated) => {
      queryClient.setQueryData(['settings', 'consent'], updated);
      setTrustDraft({});
      await queryClient.invalidateQueries({ queryKey: queryKeys.onboardingQuest() });
      showToast('安全感與通知設定已收好。', 'success');
    },
    onError: (error) => {
      logClientError('onboarding-consent-save-failed', error);
      showToast('這次沒有順利收好設定，稍後再試一次。', 'error');
    },
  });

  const generateInviteMutation = useMutation({
    mutationFn: generateInviteCode,
    onSuccess: (result) => {
      setGeneratedInviteCode(result.code);
      queryClient.setQueryData<UserMeResponse | undefined>(['settings', 'me'], (current) =>
        current ? { ...current, invite_code: result.code } : current,
      );
      showToast('新的邀請連結已準備好，可以傳給對方了。', 'success');
    },
    onError: (error) => {
      logClientError('partner-settings-generate-invite-failed', error);
      showToast('邀請連結這次沒有順利準備好，稍後再試一次。', 'error');
    },
  });

  const pairMutation = useMutation({
    mutationFn: (code: string) => pairWithPartner(code),
    onSuccess: async () => {
      await Promise.all([
        partnerQuery.refetch(),
        relationshipQuery.refetch(),
        queryClient.invalidateQueries({ queryKey: queryKeys.partnerStatus() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.partnerJournals() }),
      ]);
      setGeneratedInviteCode(null);
      setInputCode('');
      showToast('你們已經連上了。', 'success');
    },
    onError: (error) => {
      logClientError('partner-settings-bind-failed', error);
      showToast(getPairErrorMessage(error), 'error');
    },
  });

  const startCooldownMutation = useMutation({
    mutationFn: (durationMinutes: number) => startCooldown(durationMinutes),
    onSuccess: async () => {
      setTickNow(Date.now());
      await queryClient.invalidateQueries({ queryKey: queryKeys.cooldownStatus() });
      showToast('冷卻時間已啟動，伴侶會收到提醒。', 'success');
    },
    onError: (error) => {
      logClientError('cooldown-start-failed', error);
      showToast('這次沒有順利啟動冷卻時間，稍後再試一次。', 'error');
    },
  });

  const rewriteMutation = useMutation({
    mutationFn: (message: string) => rewriteMessage(message),
    onMutate: () => {
      setRewritten(null);
    },
    onSuccess: (result) => {
      setRewritten(result.rewritten);
      showToast('已整理成更適合說出口的版本。', 'success');
    },
    onError: (error) => {
      logClientError('cooldown-rewrite-failed', error);
      showToast('這次沒有順利整理這段話，稍後再試一次。', 'error');
    },
  });

  const partner = partnerQuery.data;
  const report = weeklyReportQuery.data as WeeklyReportPublic | undefined;
  const consent = consentQuery.data as OnboardingConsentPublic | null | undefined;
  const privacyScope = trustDraft.privacyScope ?? consent?.privacy_scope_accepted ?? true;
  const notificationFrequency =
    trustDraft.notificationFrequency ?? (consent?.notification_frequency as NotifFreq | undefined) ?? 'normal';
  const aiIntensity =
    trustDraft.aiIntensity ?? (consent?.ai_intensity as AIIntensity | undefined) ?? 'gentle';
  const inviteCode = generatedInviteCode ?? partner?.invite_code ?? '';
  const isPartnerLinked = Boolean(partner?.partner_id);
  const trustLooksIncomplete = !consent || !consent.privacy_scope_accepted;
  const weeklyCompletionRate = report ? Math.round(report.daily_sync_completion_rate * 100) : null;

  const primaryAction = !isPartnerLinked
    ? { label: '連結伴侶', target: 'settings-relationship' }
    : trustLooksIncomplete
      ? { label: '確認信任設定', target: 'settings-trust' }
      : { label: '調整支持節奏', target: 'settings-support' };

  const pulseCopy = !isPartnerLinked
    ? '先把伴侶連結好，Haven 才能真的把提醒、修復與回顧調成屬於你們的節奏。'
    : trustLooksIncomplete
      ? '你們已經開始建立共同空間，現在最值得確認的是通知密度、AI 介入方式，以及你想保留的界線。'
      : cooldownData?.in_cooldown
        ? '現在的設定正把 Haven 變成一個更穩定的緩衝區：一邊保留提醒節奏，一邊替情緒留出安全距離。'
        : '目前的設定正在把 Haven 變成一個更貼近你們日常的陪伴系統：知道何時提醒、何時收斂、何時保護關係。';

  const featuredTitle = !isPartnerLinked
    ? '先完成伴侶連結，這裡才會真正長成你們的設定中心'
    : `你們的 Haven 節奏，正在圍繞 ${partner?.partner_name || '這段關係'} 慢慢成形`;

  const featuredDescription = !isPartnerLinked
    ? '連結完成後，提醒節奏、關係週報、冷卻支持與共同目標才會從個人偏好升級成你們之間的默契。'
    : `目前的北極星目標是「${getGoalLabel(relationshipQuery.data?.goal?.goal_slug)}」，而通知與 AI 介入方式則決定 Haven 會用多直接、多頻繁的方式陪你們。`;

  const deviceFeelSummary = [
    cardGlowEnabled ? '保留卡片發光' : '已關閉發光',
    hapticsEnabled ? `觸覺 ${hapticStrength === 'light' ? '偏輕' : '偏明顯'}` : '關閉觸覺',
    soundEnabled ? '保留音效' : '音效關閉',
  ].join(' · ');

  async function handleCopyInvite() {
    if (!inviteCode) return;
    const inviteUrl = buildReferralInviteUrl(
      inviteCode,
      typeof window !== 'undefined' ? window.location.origin : null,
    );

    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      showToast('邀請連結已複製，可以直接傳給對方。', 'info');
      window.setTimeout(() => setCopied(false), 2000);

      try {
        await trackReferralCoupleInvite({
          invite_code: inviteCode,
          event_id: createReferralCoupleInviteEventId(),
          source: 'partner_settings',
          share_channel: 'link_copy',
          landing_path: '/register',
        });
      } catch (trackingError) {
        logClientError('referral-couple-invite-track-failed', trackingError);
      }
    } catch (error) {
      logClientError('partner-settings-copy-invite-failed', error);
      showToast('這次沒有順利複製邀請連結，稍後再試一次。', 'error');
    }
  }

  function handleSaveConsent() {
    void saveConsentMutation.mutateAsync({
      privacy_scope_accepted: privacyScope,
      notification_frequency: notificationFrequency,
      ai_intensity: aiIntensity,
    });
  }

  function handlePair() {
    const normalized = normalizeInviteCode(inputCode);
    if (!normalized) {
      showToast('先輸入有效的邀請碼。', 'error');
      return;
    }
    void pairMutation.mutateAsync(normalized);
  }

  function handleRewrite() {
    const text = rewriteDraft.trim();
    if (!text) {
      showToast('先寫下你現在想說的話。', 'error');
      return;
    }
    void rewriteMutation.mutateAsync(text);
  }

  return (
    <div className="space-y-[clamp(1.5rem,3vw,2.75rem)]">
      <SettingsCover
        eyebrow="Settings"
        title="用更安靜、更可信的方式，決定 Haven 要怎麼陪你們"
        description="這裡不是一張功能清單，而是你們設定產品節奏、提醒密度、信任邊界與支持方式的地方。每一個選項都在決定 Haven 會怎麼靠近你們。"
        pulse={pulseCopy}
        highlights={
          <div className="flex flex-wrap gap-2">
            <Badge variant={isPartnerLinked ? 'success' : 'warning'} size="md" className="border-white/56 bg-white/76">
              {isPartnerLinked ? '已連結伴侶' : '等待伴侶連結'}
            </Badge>
            <Badge variant={trustLooksIncomplete ? 'warning' : 'metadata'} size="md" className="border-white/56 bg-white/76">
              信任設定：{trustLooksIncomplete ? '仍待確認' : '已確認'}
            </Badge>
            <Badge variant="metadata" size="md" className="border-white/56 bg-white/76">
              裝置節奏：{hapticsEnabled || soundEnabled || cardGlowEnabled ? '已客製化' : '極簡'}
            </Badge>
          </div>
        }
        actions={
          <>
            <Button
              onClick={() => scrollToSection(primaryAction.target)}
              rightIcon={<RefreshCw className="h-4 w-4" aria-hidden />}
            >
              {primaryAction.label}
            </Button>
            <Button
              variant="secondary"
              onClick={() => scrollToSection('settings-trust')}
            >
              查看信任與界線
            </Button>
          </>
        }
        featured={
          <GlassCard className="overflow-hidden rounded-[2.8rem] border-white/56 bg-[linear-gradient(165deg,rgba(255,253,249,0.96),rgba(243,237,228,0.92))] p-6 shadow-lift backdrop-blur-xl md:p-8">
            <div className="space-y-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-3">
                  <Badge variant="metadata" size="sm" className="border-white/54 bg-white/74">
                    Current Relationship Read
                  </Badge>
                  <div className="space-y-2">
                    <h2 className="type-h2 text-card-foreground">{featuredTitle}</h2>
                    <p className="max-w-3xl type-body-muted text-card-foreground/84">{featuredDescription}</p>
                  </div>
                </div>
                <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-[1.65rem] border border-white/60 bg-white/78 text-primary shadow-soft">
                  <HeartHandshake className="h-5 w-5" aria-hidden />
                </span>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-[1.8rem] border border-white/58 bg-white/74 p-4 shadow-soft">
                  <p className="type-micro uppercase text-primary/78">Relationship State</p>
                  <p className="mt-2 type-h3 text-card-foreground">
                    {isPartnerLinked ? `已與 ${partner?.partner_name || '伴侶'} 連結` : '還沒有連結伴侶'}
                  </p>
                  <p className="mt-2 type-caption text-muted-foreground">
                    {isPartnerLinked
                      ? 'Haven 已能把提醒、週報與支持節奏建立在你們共同的關係脈絡上。'
                      : '完成連結後，關係週報、伴侶提醒與修復支持才會真正進入雙人模式。'}
                  </p>
                </div>
                <div className="rounded-[1.8rem] border border-white/58 bg-white/74 p-4 shadow-soft">
                  <p className="type-micro uppercase text-primary/78">North Star</p>
                  <p className="mt-2 type-h3 text-card-foreground">
                    {getGoalLabel(relationshipQuery.data?.goal?.goal_slug)}
                  </p>
                  <p className="mt-2 type-caption text-muted-foreground">
                    {relationshipQuery.data?.goal
                      ? `最近一次更新：${formatShortDate(relationshipQuery.data.goal.chosen_at)}`
                      : '先選一個你們現在最想一起靠近的方向。'}
                  </p>
                </div>
              </div>

              <div className="rounded-[2rem] border border-white/58 bg-white/74 p-4 shadow-soft">
                <p className="type-section-title text-card-foreground">現在的 Haven 會怎麼出手</p>
                <p className="mt-2 type-caption text-muted-foreground">
                  {trustLooksIncomplete
                    ? `目前的通知節奏預設為「${getNotificationLabel(notificationFrequency)}」，AI 介入方式是「${getAIIntensityLabel(aiIntensity)}」。先把這兩件事講清楚，會讓之後所有提醒都更像支持，而不是打擾。`
                    : `目前的通知節奏是「${getNotificationLabel(notificationFrequency)}」，AI 介入方式是「${getAIIntensityLabel(aiIntensity)}」。${weeklyCompletionRate !== null ? `本週同步完成率約 ${weeklyCompletionRate}%。` : '每週節奏摘要仍在整理中。'}`}
                </p>
              </div>
            </div>
          </GlassCard>
        }
        aside={
          <>
            <SettingsSnapshotCard
              eyebrow="Trust"
              title={`${getNotificationLabel(notificationFrequency)} · ${getAIIntensityLabel(aiIntensity)}`}
              description={
                consentQuery.isLoading
                  ? '正在整理隱私、通知與 AI 介入偏好。'
                  : trustLooksIncomplete
                    ? '你的信任設定還沒完全確認，現在是最值得回來看一次的時候。'
                    : `隱私範圍已確認，最近更新於 ${formatDateTime(consent?.updated_at)}。`
              }
              tone={trustLooksIncomplete ? 'error' : 'default'}
              icon={<Shield className="h-4 w-4" aria-hidden />}
            />
            <SettingsSnapshotCard
              eyebrow="Support Rhythm"
              title={
                weeklyCompletionRate !== null
                  ? `${weeklyCompletionRate}% 每週同步完成率`
                  : '正在整理每週節奏'
              }
              description={
                report
                  ? `本週完成 ${report.daily_sync_days_filled}/7 天，同時累積 ${report.appreciation_count} 則感謝。`
                  : cooldownData?.in_cooldown
                    ? '冷卻支持正在進行中，Haven 會先替你們留出一段呼吸距離。'
                    : '週報還在讀取；支援節奏與冷卻保護仍然可用。'
              }
              tone={cooldownData?.in_cooldown ? 'quiet' : 'default'}
              icon={<Clock3 className="h-4 w-4" aria-hidden />}
            />
            <SettingsSnapshotCard
              eyebrow="Device Feel"
              title="你的裝置陪伴感"
              description={deviceFeelSummary}
              icon={<Sparkles className="h-4 w-4" aria-hidden />}
            />
          </>
        }
      />

      <SettingsSectionRail
        items={SECTION_ITEMS}
        onNavigate={scrollToSection}
      />

      <SettingsSection
        id="settings-trust"
        eyebrow="Trust & Boundaries"
        title="先把界線說清楚，之後的陪伴才會舒服"
        description="這裡決定 Haven 要多主動、AI 要多直接，以及你希望產品在資料與提醒上靠近到什麼程度。"
        aside={
          <>
            <SettingsSnapshotCard
              eyebrow="Your Control"
              title="你保留隨時調整的控制權"
              description="通知節奏、AI 介入方式與資料範圍都不是一次性決定。當關係進入不同階段，這裡也應該跟著更新。"
              icon={<ShieldCheck className="h-4 w-4" aria-hidden />}
              footer={
                <div className="flex flex-wrap gap-3">
                  <Link
                    href="/legal/privacy"
                    className="inline-flex items-center gap-2 rounded-full border border-white/56 bg-white/78 px-3 py-2 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
                  >
                    隱私權政策
                  </Link>
                  <Link
                    href="/legal/terms"
                    className="inline-flex items-center gap-2 rounded-full border border-white/56 bg-white/78 px-3 py-2 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
                  >
                    服務條款
                  </Link>
                </div>
              }
            />
            <SettingsSnapshotCard
              eyebrow="Last Confirmation"
              title={trustLooksIncomplete ? '尚待確認' : formatDateTime(consent?.updated_at)}
              description={
                trustLooksIncomplete
                  ? '如果 Haven 的提醒方式讓你覺得太靠近，先從這一區重新調整。'
                  : '最近一次信任設定更新時間。當節奏不再舒服時，這裡就是最先回來的地方。'
              }
              tone={trustLooksIncomplete ? 'error' : 'success'}
              icon={<BellRing className="h-4 w-4" aria-hidden />}
            />
          </>
        }
      >
        {consentQuery.isLoading ? (
          <SettingsStatePanel
            tone="quiet"
            eyebrow="正在讀取信任設定"
            title="正在整理隱私與提醒偏好"
            description="我們正在讀取你目前的通知節奏、AI 介入方式與隱私確認狀態。"
          />
        ) : consentQuery.isError ? (
          <SettingsStatePanel
            tone="error"
            eyebrow="信任設定離線中"
            title="信任設定暫時沒有順利讀取"
            description="這一區應該讓你安穩地理解 Haven 會怎麼靠近你們，而不是留下不確定。重新讀取後，我們會把設定帶回來。"
            actions={
              <Button
                variant="secondary"
                leftIcon={<RefreshCw className="h-4 w-4" aria-hidden />}
                onClick={() => void consentQuery.refetch()}
              >
                重新讀取
              </Button>
            }
          />
        ) : (
          <div className="space-y-4">
            <SettingsFieldRow
              label="資料與界線確認"
              description="這是你對目前資料範圍與使用方式的確認。設定之後仍可回來調整。"
              control={
                <label className="inline-flex items-center gap-3 rounded-full border border-white/58 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft">
                  <input
                    type="checkbox"
                    checked={privacyScope}
                    onChange={(event) =>
                      setTrustDraft((current) => ({
                        ...current,
                        privacyScope: event.target.checked,
                      }))
                    }
                    className="h-4 w-4 rounded border-border text-primary focus-visible:ring-2 focus-visible:ring-ring"
                  />
                  我同意目前的隱私範圍
                </label>
              }
            />

            <div className="rounded-[2rem] border border-white/58 bg-white/74 p-4 shadow-soft md:p-5">
              <SettingsChoiceGrid
                legend="通知節奏"
                name="settings-notification-frequency"
                value={notificationFrequency}
                onChange={(next) =>
                  setTrustDraft((current) => ({
                    ...current,
                    notificationFrequency: next as NotifFreq,
                  }))
                }
                options={NOTIFICATION_OPTIONS}
                columns={2}
              />
            </div>

            <div className="rounded-[2rem] border border-white/58 bg-white/74 p-4 shadow-soft md:p-5">
              <SettingsChoiceGrid
                legend="AI 介入方式"
                name="settings-ai-intensity"
                value={aiIntensity}
                onChange={(next) =>
                  setTrustDraft((current) => ({
                    ...current,
                    aiIntensity: next as AIIntensity,
                  }))
                }
                options={AI_OPTIONS}
                columns={2}
              />
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Button
                loading={saveConsentMutation.isPending}
                onClick={handleSaveConsent}
              >
                儲存信任設定
              </Button>
              <p className="type-caption text-muted-foreground">
                {trustLooksIncomplete
                  ? '如果你想讓 Haven 更安靜或更直接，先從這兩個選項開始。'
                  : `最近一次更新於 ${formatDateTime(consent?.updated_at)}。`}
              </p>
            </div>

            {saveConsentMutation.isError ? (
              <p className="type-caption text-destructive" role="alert">
                儲存失敗，請稍後再試。
              </p>
            ) : null}
          </div>
        )}
      </SettingsSection>

      <SettingsSection
        id="settings-relationship"
        eyebrow="Relationship Direction"
        title="把 Haven 從個人偏好，調成你們的共同方向"
        description="連結伴侶後，關係雷達、週報與支持節奏才會真正建立在同一段關係上。"
        aside={
          <SettingsSnapshotCard
            eyebrow="Shared Direction"
            title={getGoalLabel(relationshipQuery.data?.goal?.goal_slug)}
            description={
              relationshipQuery.data?.goal
                ? `你們目前把重心放在「${getGoalLabel(relationshipQuery.data.goal.goal_slug)}」。`
                : '還沒選定共同目標也沒關係，先連結伴侶與填完五維雷達，就能看出目前最值得優先照顧的方向。'
            }
            tone={relationshipQuery.data?.goal ? 'success' : 'quiet'}
            icon={<Target className="h-4 w-4" aria-hidden />}
          />
        }
      >
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
          {partnerQuery.isLoading ? (
            <SettingsStatePanel
              tone="quiet"
              eyebrow="Relationship Linking"
              title="正在整理伴侶連結狀態"
              description="我們正在確認目前是否已經連結伴侶，以及是否有可分享的邀請連結。"
            />
          ) : partnerQuery.isError ? (
            <SettingsStatePanel
              tone="error"
              eyebrow="Relationship Linking"
              title="伴侶連結狀態沒有順利讀取"
              description="這裡應該清楚地告訴你們是否已經在同一個 Haven 空間裡。重新讀取後，我們會把這一區帶回來。"
              actions={
                <Button
                  variant="secondary"
                  leftIcon={<RefreshCw className="h-4 w-4" aria-hidden />}
                  onClick={() => void partnerQuery.refetch()}
                >
                  重新讀取
                </Button>
              }
            />
          ) : (
            <GlassCard className="overflow-hidden rounded-[2.2rem] border-white/56 bg-white/76 p-5 md:p-6">
              {isPartnerLinked ? (
                <div className="space-y-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-2">
                      <Badge variant="success" size="sm" className="border-white/56 bg-white/78">
                        Relationship Linked
                      </Badge>
                      <h3 className="type-h3 text-card-foreground">
                        已與 {partner?.partner_name || '伴侶'} 連結
                      </h3>
                      <p className="type-body-muted text-muted-foreground">
                        Haven 現在能把提醒、週報與修復支持建立在你們共同的互動裡，而不是只看單邊資料。
                      </p>
                    </div>
                    <div className="flex h-14 w-14 items-center justify-center rounded-[1.5rem] border border-white/60 bg-white/78 text-primary shadow-soft">
                      <span className="text-2xl font-semibold text-primary">
                        {getInitial(partner?.partner_name || partner?.email)}
                      </span>
                    </div>
                  </div>

                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="rounded-[1.6rem] border border-white/58 bg-white/78 p-4 shadow-soft">
                      <p className="type-micro uppercase text-primary/78">Current Goal</p>
                      <p className="mt-2 type-section-title text-card-foreground">
                        {getGoalLabel(relationshipQuery.data?.goal?.goal_slug)}
                      </p>
                      <p className="mt-2 type-caption text-muted-foreground">
                        共同目標會幫後續的週報與回顧更聚焦。
                      </p>
                    </div>
                    <div className="rounded-[1.6rem] border border-white/58 bg-white/78 p-4 shadow-soft">
                      <p className="type-micro uppercase text-primary/78">Weekly Rhythm</p>
                      <p className="mt-2 type-section-title text-card-foreground">
                        {weeklyCompletionRate !== null ? `${weeklyCompletionRate}% 完成率` : '正在整理中'}
                      </p>
                      <p className="mt-2 type-caption text-muted-foreground">
                        完成率愈穩定，Haven 的提醒就愈能跟上你們真正的節奏。
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <Link
                      href="/?tab=partner"
                      className="inline-flex items-center gap-2 rounded-full border border-white/58 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
                    >
                      去看看伴侶頁
                    </Link>
                    <p className="type-caption text-muted-foreground">
                      伴侶頁會更直接反映當下的雙人互動狀態。
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-5">
                  <div className="space-y-2">
                    <Badge variant="warning" size="sm" className="border-white/56 bg-white/78">
                      Relationship Setup
                    </Badge>
                    <h3 className="type-h3 text-card-foreground">先完成伴侶連結</h3>
                    <p className="type-body-muted text-muted-foreground">
                      這一步會把 Haven 從單人偏好頁，變成能理解你們關係節奏的共同空間。
                    </p>
                  </div>

                  <div className="rounded-[1.9rem] border border-white/58 bg-white/78 p-4 shadow-soft md:p-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="space-y-1">
                        <p className="type-section-title text-card-foreground">你的邀請連結</p>
                        <p className="type-caption text-muted-foreground">
                          先產生邀請碼，再把連結傳給對方。
                        </p>
                      </div>
                      <Button
                        variant="secondary"
                        loading={generateInviteMutation.isPending}
                        leftIcon={<Link2 className="h-4 w-4" aria-hidden />}
                        onClick={() => void generateInviteMutation.mutateAsync()}
                      >
                        {inviteCode ? '重新產生' : '產生邀請碼'}
                      </Button>
                    </div>

                    <div className="mt-4 flex flex-col gap-3 lg:flex-row">
                      <code className="flex min-h-[3.25rem] flex-1 items-center justify-center rounded-[1.3rem] border border-white/60 bg-background/76 px-4 text-lg font-semibold tracking-[0.22em] text-card-foreground shadow-glass-inset">
                        {inviteCode || '------'}
                      </code>
                      <Button
                        variant="outline"
                        disabled={!inviteCode}
                        leftIcon={copied ? <Check className="h-4 w-4" aria-hidden /> : <Copy className="h-4 w-4" aria-hidden />}
                        onClick={handleCopyInvite}
                      >
                        {copied ? '已複製' : '複製邀請連結'}
                      </Button>
                    </div>
                  </div>

                  <div className="rounded-[1.9rem] border border-white/58 bg-white/78 p-4 shadow-soft md:p-5">
                    <Input
                      label="輸入對方邀請碼"
                      value={inputCode}
                      onChange={(event) => setInputCode(event.target.value.toUpperCase())}
                      placeholder="例如 ABC123"
                      helperText="若對方已經把邀請連結傳給你，只要貼上代碼即可。"
                    />
                    <div className="mt-4 flex flex-wrap items-center gap-3">
                      <Button
                        loading={pairMutation.isPending}
                        disabled={!normalizeInviteCode(inputCode)}
                        onClick={handlePair}
                      >
                        完成連結
                      </Button>
                      <p className="type-caption text-muted-foreground">
                        連結完成後，週報與提醒才會真正進入雙人模式。
                      </p>
                    </div>
                    {pairMutation.isError ? (
                      <p className="mt-3 type-caption text-destructive" role="alert">
                        {getPairErrorMessage(pairMutation.error)}
                      </p>
                    ) : null}
                  </div>
                </div>
              )}
            </GlassCard>
          )}

          {relationshipQuery.isLoading ? (
            <SettingsStatePanel
              tone="quiet"
              eyebrow="Relationship System"
              title="正在整理你們目前的關係知識"
              description="Relationship System 會接手承載關係脈動、共同方向與 Shared Future。"
            />
          ) : relationshipQuery.isError ? (
            <SettingsStatePanel
              tone="error"
              eyebrow="Relationship System"
              title="Relationship System 摘要暫時沒有順利載入"
              description="Settings 不再是關係知識的主要編輯面；重新讀取後，我們會把目前的摘要帶回來。"
              actions={
                <Button
                  variant="secondary"
                  leftIcon={<RefreshCw className="h-4 w-4" aria-hidden />}
                  onClick={() => void relationshipQuery.refetch()}
                >
                  重新讀取
                </Button>
              }
            />
          ) : (
            <GlassCard className="overflow-hidden rounded-[2.2rem] border-white/56 bg-white/76 p-5 md:p-6">
              <div className="space-y-5">
                <div className="space-y-2">
                  <Badge variant="metadata" size="sm" className="border-white/56 bg-white/78">
                    Relationship System
                  </Badge>
                  <h3 className="type-h3 text-card-foreground">Relationship System 現在是這塊知識的主場</h3>
                  <p className="type-body-muted text-muted-foreground">
                    Settings 只保留摘要與配對狀態；真正的關係脈動、內在地圖與共同未來，現在都應該回到 Relationship System 裡被一起理解。
                  </p>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-[1.7rem] border border-white/58 bg-white/78 p-4 shadow-soft">
                    <p className="type-micro uppercase text-primary/78">Relationship Pulse</p>
                    <p className="mt-2 type-section-title text-card-foreground">
                      {relationshipQuery.data?.baseline.mine ? '已建立個人脈動' : '尚未建立'}
                    </p>
                    <p className="mt-2 type-caption text-muted-foreground">
                      {relationshipQuery.data?.baseline.partner
                        ? '伴侶最近也留下了自己的脈動。'
                        : '伴侶端脈動還沒完整建立。'}
                    </p>
                  </div>
                  <div className="rounded-[1.7rem] border border-white/58 bg-white/78 p-4 shadow-soft">
                    <p className="type-micro uppercase text-primary/78">North Star</p>
                    <p className="mt-2 type-section-title text-card-foreground">
                      {getGoalLabel(relationshipQuery.data?.goal?.goal_slug)}
                    </p>
                    <p className="mt-2 type-caption text-muted-foreground">
                      {relationshipQuery.data?.goal
                        ? `最近更新於 ${formatShortDate(relationshipQuery.data.goal.chosen_at)}。`
                        : '共同方向還沒被正式寫下。'}
                    </p>
                  </div>
                </div>

                <div className="rounded-[1.9rem] border border-white/58 bg-white/78 p-4 shadow-soft md:p-5">
                  <p className="type-section-title text-card-foreground">這塊現在怎麼運作</p>
                  <p className="mt-2 type-caption text-muted-foreground">
                    Relationship System 會把關係脈動、你的內在地圖與 Shared Future 放回同一張頁面。Settings 只留下摘要，避免你們在兩個地方維護同一份 relationship truth。
                  </p>
                  <div className="mt-4 flex flex-wrap items-center gap-3">
                    <Link
                      href="/love-map"
                      className="inline-flex items-center gap-2 rounded-full border border-white/58 bg-white/82 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
                    >
                      前往 Relationship System
                    </Link>
                    <p className="type-caption text-muted-foreground">
                      之後所有這類更新，應該都從 Relationship System 進行。
                    </p>
                  </div>
                </div>
              </div>
            </GlassCard>
          )}
        </div>
      </SettingsSection>

      <SettingsSection
        id="settings-support"
        eyebrow="Support Rhythm"
        title="讓提醒、週報與冷卻支持更像你們需要的陪伴"
        description="這一區不是在管理事件，而是在決定 Haven 什麼時候該提醒、什麼時候該退一步、什麼時候該幫你把話說得更溫和。"
      >
        <div className="grid gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
          {weeklyReportQuery.isLoading ? (
            <SettingsStatePanel
              tone="quiet"
              eyebrow="Weekly Report"
              title="正在整理本週節奏"
              description="同步完成率、感謝次數與本週洞察很快就會出現在這裡。"
            />
          ) : weeklyReportQuery.isError ? (
            <SettingsStatePanel
              tone="error"
              eyebrow="Weekly Report"
              title="本週節奏摘要暫時沒有順利載入"
              description="這不影響其他設定，但你暫時看不到本週的同步與感謝脈絡。"
              actions={
                <Button
                  variant="secondary"
                  leftIcon={<RefreshCw className="h-4 w-4" aria-hidden />}
                  onClick={() => void weeklyReportQuery.refetch()}
                >
                  重新讀取
                </Button>
              }
            />
          ) : report ? (
            <GlassCard className="overflow-hidden rounded-[2.2rem] border-white/56 bg-white/76 p-5 md:p-6">
              <div className="space-y-5">
                <div className="space-y-2">
                  <Badge variant="metadata" size="sm" className="border-white/56 bg-white/78">
                    Weekly Rhythm
                  </Badge>
                  <h3 className="type-h3 text-card-foreground">
                    {formatShortDate(report.period_start)} 至 {formatShortDate(report.period_end)}
                  </h3>
                  <p className="type-body-muted text-muted-foreground">
                    這裡不是用來評分你們，而是幫你看出現在的節奏是偏穩、偏鬆，還是需要更溫柔的提醒。
                  </p>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-[1.6rem] border border-white/58 bg-white/78 p-4 shadow-soft">
                    <p className="type-micro uppercase text-primary/78">Daily Sync</p>
                    <p className="mt-2 text-[2rem] font-semibold tracking-tight text-card-foreground tabular-nums">
                      {weeklyCompletionRate ?? '—'}%
                    </p>
                    <p className="mt-1 type-caption text-muted-foreground">
                      {report.daily_sync_days_filled}/7 天完成
                    </p>
                  </div>
                  <div className="rounded-[1.6rem] border border-white/58 bg-white/78 p-4 shadow-soft">
                    <p className="type-micro uppercase text-primary/78">Appreciation</p>
                    <p className="mt-2 text-[2rem] font-semibold tracking-tight text-card-foreground tabular-nums">
                      {report.appreciation_count}
                    </p>
                    <p className="mt-1 type-caption text-muted-foreground">
                      這週感謝與被感謝的次數
                    </p>
                  </div>
                </div>

                <div className="rounded-[1.9rem] border border-white/58 bg-white/78 p-4 shadow-soft">
                  <p className="type-section-title text-card-foreground">本週讀後感</p>
                  <p className="mt-2 type-caption leading-relaxed text-muted-foreground">
                    {report.insight || '這週的洞察還不夠明確，但同步與感謝仍然會慢慢累積出你們的節奏。'}
                  </p>
                </div>
              </div>
            </GlassCard>
          ) : (
            <SettingsStatePanel
              tone="quiet"
              eyebrow="Weekly Report"
              title="本週還沒有足夠的節奏摘要"
              description="當同步與互動再多一些，這裡就會開始告訴你們哪些支持方式最有感。"
            />
          )}

          {cooldownLoading ? (
            <SettingsStatePanel
              tone="quiet"
              eyebrow="Cooldown Support"
              title="正在確認冷卻狀態"
              description="如果你們目前正在冷卻期，這裡會顯示剩餘時間與溫和改寫工具。"
            />
          ) : cooldownError || !cooldownData ? (
            <SettingsStatePanel
              tone="error"
              eyebrow="Cooldown Support"
              title="冷卻支持暫時沒有順利載入"
              description="這會影響你們需要暫停時的保護節奏，但不會影響其他設定。"
              actions={
                <Button
                  variant="secondary"
                  leftIcon={<RefreshCw className="h-4 w-4" aria-hidden />}
                  onClick={() => void refetchCooldown()}
                >
                  重新讀取
                </Button>
              }
            />
          ) : (
            <GlassCard className="overflow-hidden rounded-[2.2rem] border-white/56 bg-white/76 p-5 md:p-6">
              <div className="space-y-5">
                <div className="space-y-2">
                  <Badge
                    variant={cooldownData.in_cooldown ? 'warning' : 'metadata'}
                    size="sm"
                    className="border-white/56 bg-white/78"
                  >
                    Cooldown Support
                  </Badge>
                  <h3 className="type-h3 text-card-foreground">
                    {cooldownData.in_cooldown ? '冷卻模式進行中' : '需要時，先幫你們留出空氣'}
                  </h3>
                  <p className="type-body-muted text-muted-foreground">
                    當情緒開始太快時，這裡負責替你們拉開一段更安全的距離，而不是把衝突推得更近。
                  </p>
                </div>

                {cooldownData.in_cooldown ? (
                  <div className="space-y-4">
                    <div className="rounded-[1.8rem] border border-white/58 bg-white/78 p-4 shadow-soft">
                      <div className="flex items-center gap-3">
                        <span className="flex h-11 w-11 items-center justify-center rounded-[1rem] border border-white/60 bg-white/80 text-primary shadow-soft">
                          <PauseCircle className="h-4 w-4" aria-hidden />
                        </span>
                        <div>
                          <p className="type-section-title text-card-foreground">
                            {cooldownData.started_by_me ? '你已啟動冷卻' : '伴侶已啟動冷卻'}
                          </p>
                          <p className="mt-1 text-2xl font-semibold tracking-tight text-card-foreground tabular-nums">
                            {formatRemaining(displaySeconds)}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="rounded-[1.8rem] border border-white/58 bg-white/78 p-4 shadow-soft">
                      <Textarea
                        label="寫給對方（改寫成我訊息）"
                        value={rewriteDraft}
                        onChange={(event) => setRewriteDraft(event.target.value)}
                        placeholder="輸入想說的話，Haven 會先幫你把語氣放慢一點。"
                        helperText="改寫只會生成建議，不會自動送出。"
                        maxLength={2000}
                      />
                      <div className="mt-4 flex flex-wrap items-center gap-3">
                        <Button
                          loading={rewriteMutation.isPending}
                          onClick={handleRewrite}
                        >
                          改寫預覽
                        </Button>
                        <a
                          href="https://www.nhs.uk/mental-health/self-help/guides/breathing-exercises/"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 rounded-full border border-white/56 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
                        >
                          <Wind className="h-4 w-4" aria-hidden />
                          深呼吸練習
                        </a>
                      </div>
                      {rewriteMutation.isError ? (
                        <p className="mt-3 type-caption text-destructive" role="alert">
                          改寫失敗，請稍後再試。
                        </p>
                      ) : null}
                      {rewritten ? (
                        <div className="mt-4 rounded-[1.45rem] border border-white/58 bg-background/76 p-4 shadow-glass-inset">
                          <p className="type-section-title text-card-foreground">改寫建議</p>
                          <p className="mt-2 type-caption leading-relaxed text-muted-foreground">{rewritten}</p>
                        </div>
                      ) : null}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="rounded-[1.8rem] border border-white/58 bg-white/78 p-4 shadow-soft">
                      <p className="type-section-title text-card-foreground">選擇一段冷卻時間</p>
                      <p className="mt-2 type-caption text-muted-foreground">
                        當你知道現在繼續說只會更傷時，先讓 Haven 幫你們把節奏慢下來。
                      </p>
                      <div className="mt-4 flex flex-wrap gap-2">
                        {[20, 30, 45, 60].map((minutes) => (
                          <Button
                            key={minutes}
                            variant="outline"
                            size="sm"
                            loading={startCooldownMutation.isPending}
                            disabled={startCooldownMutation.isPending}
                            onClick={() => void startCooldownMutation.mutateAsync(minutes)}
                          >
                            {minutes} 分鐘
                          </Button>
                        ))}
                      </div>
                      {startCooldownMutation.isError ? (
                        <p className="mt-3 type-caption text-destructive" role="alert">
                          啟動失敗，請稍後再試。
                        </p>
                      ) : null}
                    </div>
                  </div>
                )}
              </div>
            </GlassCard>
          )}
        </div>
      </SettingsSection>

      <SettingsSection
        id="settings-device"
        eyebrow="Device Feel"
        title="把裝置回饋調成剛剛好的陪伴感"
        description="這些不是華麗特效，而是 Haven 在最細微的地方要不要更像在陪你，而不是打擾你。"
        aside={
          <SettingsSnapshotCard
            eyebrow="Current Feel"
            title="現在的裝置節奏"
            description={deviceFeelSummary}
            icon={<Sparkles className="h-4 w-4" aria-hidden />}
          />
        }
      >
        <div className="space-y-4">
          <SettingsFieldRow
            label="卡片解鎖發光效果"
            description="保留抽卡與解鎖時那種被溫柔照亮一下的感覺。"
            control={
              <SettingsSwitch
                checked={cardGlowEnabled}
                onChange={setCardGlowEnabled}
                label="卡片解鎖發光效果"
              />
            }
          />
          <SettingsFieldRow
            label="觸覺回饋"
            description="用更身體感的方式告訴你：這裡有一個值得注意的小瞬間。"
            control={
              <div className="flex items-center gap-3">
                {hapticsEnabled ? (
                  <Badge variant="metadata" size="md" className="border-white/56 bg-white/78">
                    {hapticStrength === 'light' ? '輕' : '中'}
                  </Badge>
                ) : null}
                <SettingsSwitch
                  checked={hapticsEnabled}
                  onChange={setHapticsEnabled}
                  label="觸覺回饋"
                />
              </div>
            }
          />
          {hapticsEnabled ? (
            <div className="rounded-[2rem] border border-white/58 bg-white/74 p-4 shadow-soft md:p-5">
              <SettingsChoiceGrid
                legend="觸覺強度"
                name="settings-haptic-strength"
                value={hapticStrength}
                onChange={(next) => setHapticStrength(next as 'light' | 'medium')}
                options={HAPTIC_OPTIONS}
                columns={2}
              />
            </div>
          ) : null}
          <SettingsFieldRow
            label="音效"
            description="保留抽卡、解鎖與小提示出現時的聲音回饋。"
            control={
              <SettingsSwitch
                checked={soundEnabled}
                onChange={setSoundEnabled}
                label="音效"
              />
            }
          />
        </div>
      </SettingsSection>

      <SettingsFooterNote
        title="資料權利與額外入口"
        description="你可以隨時匯出或刪除自己的資料；若需伴侶一併刪除，請伴侶登入後在自己的設定中執行。"
        actions={
          <>
            <Link
              href="/legal/privacy"
              className="inline-flex items-center gap-2 rounded-full border border-white/56 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
            >
              <Shield className="h-4 w-4" aria-hidden />
              隱私權政策
            </Link>
            <Link
              href="/admin/moderation"
              className="inline-flex items-center gap-2 rounded-full border border-white/56 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
            >
              <ShieldCheck className="h-4 w-4" aria-hidden />
              內容審核（管理員）
            </Link>
          </>
        }
      />
    </div>
  );
}
