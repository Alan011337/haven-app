'use client';

import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { HandHeart, Loader2 } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import RepairSafetyModePanel from '@/components/features/RepairSafetyModePanel';
import { useFeatureFlags } from '@/hooks/queries';
import { useMediationStatusEnabled } from '@/hooks/queries/useMediationStatus';
import { resolveMediationViewState } from '@/features/mediation/view-state';
import { queryKeys } from '@/lib/query-keys';
import {
  completeRepairFlowStep,
  fetchRepairFlowStatus,
  startRepairFlow,
  submitMediationAnswers,
} from '@/services/api-client';
import { logClientError } from '@/lib/safe-error-log';
import { useToast } from '@/hooks/useToast';

const REPAIR_SESSION_STORAGE_KEY = 'haven_repair_flow_session_id_v1';

export default function MediationPageContent() {
  const queryClient = useQueryClient();
  const { data: featureFlags } = useFeatureFlags();
  const repairFlowEnabled = Boolean(featureFlags?.flags?.repair_flow_v1)
    && !Boolean(featureFlags?.kill_switches?.disable_repair_flow_v1);
  const { data: status, isLoading: loading } = useMediationStatusEnabled(!repairFlowEnabled);
  const [repairSessionId, setRepairSessionId] = useState<string | null>(() => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(REPAIR_SESSION_STORAGE_KEY);
  });
  const {
    data: repairStatus,
    isLoading: repairStatusLoading,
    error: repairStatusError,
    refetch: refetchRepairStatus,
  } = useQuery({
    queryKey: ['repairFlowStatus', repairSessionId],
    queryFn: () => fetchRepairFlowStatus(repairSessionId as string),
    enabled: repairFlowEnabled && !!repairSessionId,
    retry: false,
    staleTime: 10_000,
  });

  const [submitting, setSubmitting] = useState(false);
  const [repairStarting, setRepairStarting] = useState(false);
  const [repairSubmitting, setRepairSubmitting] = useState(false);
  const [answers, setAnswers] = useState<[string, string, string]>(['', '', '']);
  const [iFeel, setIFeel] = useState('');
  const [iNeed, setINeed] = useState('');
  const [mirrorText, setMirrorText] = useState('');
  const [sharedCommitment, setSharedCommitment] = useState('');
  const [improvementNote, setImprovementNote] = useState('');
  const { showToast } = useToast();

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!repairFlowEnabled) {
      localStorage.removeItem(REPAIR_SESSION_STORAGE_KEY);
      setRepairSessionId(null);
      return;
    }
    if (repairSessionId) {
      localStorage.setItem(REPAIR_SESSION_STORAGE_KEY, repairSessionId);
      return;
    }
    localStorage.removeItem(REPAIR_SESSION_STORAGE_KEY);
  }, [repairFlowEnabled, repairSessionId]);

  useEffect(() => {
    const statusCode = (repairStatusError as { response?: { status?: number } } | null)?.response?.status;
    if (statusCode === 404) {
      setRepairSessionId(null);
    }
  }, [repairStatusError]);

  const repairStepGuide = useMemo(() => {
    const step = repairStatus?.current_step ?? 1;
    if (step === 1) {
      return {
        title: 'Step 1: 降溫',
        description: '先確認你已完成短暫降溫，避免在情緒高峰時互相傷害。',
      };
    }
    if (step === 2) {
      return {
        title: 'Step 2: 我感受到 / 我需要',
        description: '請用「我訊息」描述感受與需要，不要使用指責語句。',
      };
    }
    if (step === 3) {
      return {
        title: 'Step 3: 鏡像復述',
        description: '只做一次鏡像復述，確認你聽懂伴侶在說什麼。',
      };
    }
    if (step === 4) {
      return {
        title: 'Step 4: 共同承諾',
        description: '選一件 24 小時內可完成的小承諾。',
      };
    }
    return {
      title: 'Step 5: 回顧改善',
      description: '完成後簡短記錄這次修復中真正有改善的一點。',
    };
  }, [repairStatus?.current_step]);

  const viewState = useMemo(
    () =>
      resolveMediationViewState({
        repairFlowEnabled,
        loading,
        status,
        repairSessionId,
        repairStatusLoading,
        repairStatus,
      }),
    [repairFlowEnabled, loading, status, repairSessionId, repairStatusLoading, repairStatus]
  );

  const handleResetRepairFlow = () => {
    setRepairSessionId(null);
    setIFeel('');
    setINeed('');
    setMirrorText('');
    setSharedCommitment('');
    setImprovementNote('');
  };

  const handleStartRepairFlow = async () => {
    setRepairStarting(true);
    try {
      const result = await startRepairFlow({ source: 'web' });
      setRepairSessionId(result.session_id);
      await queryClient.fetchQuery({
        queryKey: ['repairFlowStatus', result.session_id],
        queryFn: () => fetchRepairFlowStatus(result.session_id),
      });
      showToast('已啟動修復流程，先從 Step 2 開始。', 'success');
    } catch (err) {
      logClientError('repair-flow-start-failed', err);
      showToast('啟動修復流程失敗，請稍後再試', 'error');
    } finally {
      setRepairStarting(false);
    }
  };

  const handleCompleteRepairStep = async () => {
    if (!repairStatus || !repairSessionId) return;
    const currentStep = repairStatus.current_step;
    if (currentStep === 2 && (!iFeel.trim() || !iNeed.trim())) {
      showToast('Step 2 需要填寫「我感受到」與「我需要」', 'error');
      return;
    }
    if (currentStep === 3 && !mirrorText.trim()) {
      showToast('Step 3 需要填寫鏡像復述內容', 'error');
      return;
    }
    if (currentStep === 4 && !sharedCommitment.trim()) {
      showToast('Step 4 需要填寫共同承諾', 'error');
      return;
    }
    if (currentStep === 5 && !improvementNote.trim()) {
      showToast('Step 5 需要填寫改善回顧', 'error');
      return;
    }

    setRepairSubmitting(true);
    try {
      const result = await completeRepairFlowStep({
        session_id: repairSessionId,
        step: currentStep,
        source: 'web',
        i_feel: iFeel.trim() || undefined,
        i_need: iNeed.trim() || undefined,
        mirror_text: mirrorText.trim() || undefined,
        shared_commitment: sharedCommitment.trim() || undefined,
        improvement_note: improvementNote.trim() || undefined,
      });
      if (result.safety_mode_active) {
        showToast('已進入安全模式，請先停止刺激性互動。', 'error');
      } else if (result.completed) {
        showToast('修復流程已完成，請在 24 小時內兌現承諾。', 'success');
      } else {
        showToast('已完成本步驟。', 'success');
      }
      setIFeel('');
      setINeed('');
      setMirrorText('');
      setSharedCommitment('');
      setImprovementNote('');
      await refetchRepairStatus();
    } catch (err) {
      logClientError('repair-flow-step-complete-failed', err);
      showToast('提交步驟失敗，請稍後再試', 'error');
    } finally {
      setRepairSubmitting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!status?.session_id || answers.some((a) => !a.trim())) {
      showToast('請填寫三題後再送出', 'error');
      return;
    }
    setSubmitting(true);
    try {
      await submitMediationAnswers(status.session_id, answers);
      await queryClient.invalidateQueries({ queryKey: queryKeys.mediationStatus() });
      showToast('已記錄你的回答', 'success');
    } catch (err) {
      logClientError('mediation-submit-failed', err);
      showToast('送出失敗，請稍後再試', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  if (viewState === 'loading') {
    return (
      <div className="min-h-[40vh] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" aria-hidden />
      </div>
    );
  }

  if (viewState === 'repair_start' || viewState === 'repair_missing_session' || viewState === 'repair_active') {
    return (
      <>
        <h1 className="font-art text-2xl font-bold text-foreground mb-2 flex items-center gap-2.5 animate-slide-up-fade">
          <span className="icon-badge !w-10 !h-10" aria-hidden><HandHeart className="w-5 h-5" /></span>
          修復流程 v1
        </h1>
        <p className="text-body text-muted-foreground mb-8">
          五步驟修復：降溫、我訊息、鏡像復述、共同承諾、改善回顧。
        </p>

        {viewState === 'repair_start' ? (
          <GlassCard className="p-8 text-center">
            <p className="text-body text-foreground font-medium">目前沒有進行中的修復流程。</p>
            <p className="text-caption text-muted-foreground mt-2">
              這個流程設計成可完成的 stepper，你們可以隨時啟動一次修復。
            </p>
            <button
              type="button"
              onClick={handleStartRepairFlow}
              disabled={repairStarting}
              className="mt-6 rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground border-t border-t-white/30 px-6 py-2.5 font-medium shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
            >
              {repairStarting ? <Loader2 className="w-5 h-5 animate-spin inline" aria-hidden /> : '開始修復流程'}
            </button>
          </GlassCard>
        ) : viewState === 'repair_missing_session' ? (
          <GlassCard className="p-8 text-center">
            <p className="text-body text-muted-foreground">找不到這個修復流程，請重新開始。</p>
            <button
              type="button"
              onClick={() => setRepairSessionId(null)}
              className="mt-4 rounded-full border border-input px-5 py-2 text-body text-foreground hover:bg-muted/60 transition-colors"
            >
              清除舊流程
            </button>
          </GlassCard>
        ) : (
          <div className="space-y-6">
            <GlassCard className="p-6">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-art text-lg font-semibold text-card-foreground">
                  {repairStepGuide.title}（步驟 {repairStatus!.current_step}/5）
                </h2>
                <span className="text-caption text-muted-foreground tabular-nums">
                  我的進度：{repairStatus!.my_completed_steps.length}/5
                </span>
              </div>
              <p className="text-body text-muted-foreground mt-2">{repairStepGuide.description}</p>
              <p className="text-caption text-muted-foreground mt-2 tabular-nums">
                伴侶進度：{repairStatus!.partner_completed_steps.length}/5
              </p>
            </GlassCard>

            {repairStatus!.safety_mode_active ? (
              <RepairSafetyModePanel onReset={handleResetRepairFlow} />
            ) : repairStatus!.completed ? (
              <GlassCard className="p-6 border-primary/25">
                <p className="text-body font-medium text-foreground">修復流程已完成</p>
                <p className="text-caption text-muted-foreground mt-2">
                  建議在 24 小時內完成你們的共同承諾，讓修復有具體落地。
                </p>
              </GlassCard>
            ) : (
              <GlassCard className="p-6 space-y-4">
                {repairStatus!.current_step === 2 && (
                  <>
                    <div>
                      <label htmlFor="repair-i-feel" className="block text-body font-medium text-foreground mb-2">
                        我感受到
                      </label>
                      <textarea
                        id="repair-i-feel"
                        value={iFeel}
                        onChange={(e) => setIFeel(e.target.value)}
                        className="w-full rounded-input border border-input bg-background px-3 py-2 text-foreground focus-visible:ring-2 focus-visible:ring-ring min-h-[84px] resize-y"
                        placeholder="例如：我感到被忽略、焦慮…"
                        maxLength={300}
                      />
                    </div>
                    <div>
                      <label htmlFor="repair-i-need" className="block text-body font-medium text-foreground mb-2">
                        我需要
                      </label>
                      <textarea
                        id="repair-i-need"
                        value={iNeed}
                        onChange={(e) => setINeed(e.target.value)}
                        className="w-full rounded-input border border-input bg-background px-3 py-2 text-foreground focus-visible:ring-2 focus-visible:ring-ring min-h-[84px] resize-y"
                        placeholder="例如：我需要你先聽完我的句子…"
                        maxLength={300}
                      />
                    </div>
                  </>
                )}
                {repairStatus!.current_step === 3 && (
                  <div>
                    <label htmlFor="repair-mirror" className="block text-body font-medium text-foreground mb-2">
                      鏡像復述
                    </label>
                    <textarea
                      id="repair-mirror"
                      value={mirrorText}
                      onChange={(e) => setMirrorText(e.target.value)}
                      className="w-full rounded-input border border-input bg-background px-3 py-2 text-foreground focus-visible:ring-2 focus-visible:ring-ring min-h-[84px] resize-y"
                      placeholder="例如：我聽見你其實是在擔心我們的連結…"
                      maxLength={300}
                    />
                  </div>
                )}
                {repairStatus!.current_step === 4 && (
                  <div>
                    <label htmlFor="repair-commitment" className="block text-body font-medium text-foreground mb-2">
                      共同承諾（24 小時內）
                    </label>
                    <textarea
                      id="repair-commitment"
                      value={sharedCommitment}
                      onChange={(e) => setSharedCommitment(e.target.value)}
                      className="w-full rounded-input border border-input bg-background px-3 py-2 text-foreground focus-visible:ring-2 focus-visible:ring-ring min-h-[84px] resize-y"
                      placeholder="例如：今晚散步 10 分鐘，不帶手機。"
                      maxLength={300}
                    />
                  </div>
                )}
                {repairStatus!.current_step === 5 && (
                  <div>
                    <label htmlFor="repair-improvement" className="block text-body font-medium text-foreground mb-2">
                      改善回顧
                    </label>
                    <textarea
                      id="repair-improvement"
                      value={improvementNote}
                      onChange={(e) => setImprovementNote(e.target.value)}
                      className="w-full rounded-input border border-input bg-background px-3 py-2 text-foreground focus-visible:ring-2 focus-visible:ring-ring min-h-[84px] resize-y"
                      placeholder="例如：我們比上次更快停下來，先聽完再回應。"
                      maxLength={300}
                    />
                  </div>
                )}
                <button
                  type="button"
                  onClick={handleCompleteRepairStep}
                  disabled={repairSubmitting}
                  className="rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground border-t border-t-white/30 px-6 py-2.5 font-medium shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
                >
                  {repairSubmitting ? (
                    <Loader2 className="w-5 h-5 animate-spin inline" aria-hidden />
                  ) : (
                    '完成此步驟'
                  )}
                </button>
              </GlassCard>
            )}

            <button
              type="button"
              onClick={handleResetRepairFlow}
              className="rounded-full border border-input px-5 py-2 text-body text-foreground hover:bg-muted/60 transition-colors"
            >
              結束目前流程
            </button>
          </div>
        )}
      </>
    );
  }

  if (!status) return null;

  return (
    <>
      <h1 className="font-art text-2xl font-bold text-foreground mb-2 flex items-center gap-2.5 animate-slide-up-fade">
        <span className="icon-badge !w-10 !h-10" aria-hidden><HandHeart className="w-5 h-5" /></span>
        調解模式
      </h1>
      <p className="text-body text-muted-foreground mb-8">
        換位思考三問，各自填寫後可查看彼此心聲與下次 SOP。
      </p>

      {viewState === 'classic_no_session' ? (
        <GlassCard className="p-8 text-center">
          <p className="text-body text-muted-foreground">目前沒有進行中的調解。</p>
          <p className="text-caption text-muted-foreground mt-2">
            當系統偵測到可能的情緒張力時，會邀請你們進入此流程。
          </p>
        </GlassCard>
      ) : viewState === 'classic_answering' ? (
        <GlassCard className="p-6">
          <h2 className="font-art text-lg font-semibold text-card-foreground mb-4">請回答以下三題</h2>
          <form onSubmit={handleSubmit} className="space-y-6">
            {(status.questions ?? []).map((q, i) => (
              <div key={i}>
                <label htmlFor={`mediation-q-${i}`} className="block text-body font-medium text-foreground mb-2">
                  {i + 1}. {q}
                </label>
                <textarea
                  id={`mediation-q-${i}`}
                  value={answers[i] ?? ''}
                  onChange={(e) => {
                    const next: [string, string, string] = [...answers];
                    next[i] = e.target.value;
                    setAnswers(next);
                  }}
                  placeholder="寫下你的想法..."
                  className="w-full rounded-input border border-input bg-background px-3 py-2 text-foreground focus-visible:ring-2 focus-visible:ring-ring min-h-[80px] resize-y"
                  maxLength={2000}
                />
              </div>
            ))}
            <button
              type="submit"
              disabled={submitting}
              className="rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground border-t border-t-white/30 px-6 py-2.5 font-medium shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
              aria-label="送出調解回答"
            >
              {submitting ? (
                <Loader2 className="w-5 h-5 animate-spin inline" aria-hidden />
              ) : (
                '送出'
              )}
            </button>
          </form>
        </GlassCard>
      ) : viewState === 'classic_waiting_partner' ? (
        <GlassCard className="p-8 text-center">
          <p className="text-body text-foreground font-medium">你已完成填寫</p>
          <p className="text-caption text-muted-foreground mt-2">等待伴侶填寫後即可查看彼此心聲與下次 SOP。</p>
        </GlassCard>
      ) : (
        <div className="space-y-6">
          <GlassCard className="p-6">
            <h2 className="font-art text-lg font-semibold text-card-foreground mb-4">你的回答</h2>
            <ul className="space-y-3">
              {(status.my_answers ?? []).map((ans, i) => (
                <li key={i} className="border-l-2 border-primary/30 pl-3 text-body text-foreground">
                  <span className="text-caption text-muted-foreground">{(status.questions ?? [])[i]}</span>
                  <p className="mt-1">{ans || '—'}</p>
                </li>
              ))}
            </ul>
          </GlassCard>
          <GlassCard className="p-6">
            <h2 className="font-art text-lg font-semibold text-card-foreground mb-4">伴侶的回答</h2>
            <ul className="space-y-3">
              {(status.partner_answers ?? []).map((ans, i) => (
                <li key={i} className="border-l-2 border-border pl-3 text-body text-foreground">
                  <span className="text-caption text-muted-foreground">{(status.questions ?? [])[i]}</span>
                  <p className="mt-1">{ans || '—'}</p>
                </li>
              ))}
            </ul>
          </GlassCard>
          {status.next_sop && (
            <GlassCard className="p-6 border-primary/20">
              <h2 className="font-art text-lg font-semibold text-card-foreground mb-2">下次 SOP</h2>
              <p className="text-body text-foreground">{status.next_sop}</p>
            </GlassCard>
          )}
        </div>
      )}
    </>
  );
}
