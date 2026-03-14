'use client';

import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Button from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Input';
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

const REPAIR_STEPS = [
  { num: 1, label: '降溫' },
  { num: 2, label: '我訊息' },
  { num: 3, label: '鏡像復述' },
  { num: 4, label: '承諾' },
  { num: 5, label: '回顧' },
] as const;

/* ──────────────────────────────────────────────── */

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

  /* ── Session persistence ── */

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

  /* ── Step guide ── */

  const repairStepGuide = useMemo(() => {
    const step = repairStatus?.current_step ?? 1;
    if (step === 1) {
      return {
        title: '降溫',
        description: '先確認你已完成短暫降溫，避免在情緒高峰時互相傷害。',
      };
    }
    if (step === 2) {
      return {
        title: '我感受到 / 我需要',
        description: '用「我訊息」描述感受與需要，不要使用指責語句。',
      };
    }
    if (step === 3) {
      return {
        title: '鏡像復述',
        description: '只做一次鏡像復述，確認你聽懂伴侶在說什麼。',
      };
    }
    if (step === 4) {
      return {
        title: '共同承諾',
        description: '選一件 24 小時內可完成的小承諾。',
      };
    }
    return {
      title: '回顧改善',
      description: '完成後簡短記錄這次修復中真正有改善的一點。',
    };
  }, [repairStatus?.current_step]);

  /* ── View state ── */

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

  /* ── Handlers ── */

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

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ RENDER ━━ */

  /* ── Loading ── */

  if (viewState === 'loading') {
    return (
      <div className="flex min-h-[40vh] items-center justify-center" role="status">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary/20 border-t-primary" />
        <span className="sr-only">載入中</span>
      </div>
    );
  }

  /* ── Repair flow ── */

  if (viewState === 'repair_start' || viewState === 'repair_missing_session' || viewState === 'repair_active') {
    return (
      <div className="space-y-8 md:space-y-10">
        {/* Page identity */}
        <div className="space-y-3 animate-slide-up-fade">
          <h1 className="font-art text-[2rem] leading-[1.05] tracking-tight text-gradient-gold md:text-[2.8rem]">
            修復流程
          </h1>
          <p className="text-sm leading-relaxed text-muted-foreground">
            五步驟引導修復：降溫、我訊息、鏡像復述、共同承諾、改善回顧。
          </p>
        </div>

        {viewState === 'repair_start' ? (
          <section className="animate-slide-up-fade-1 rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(248,244,238,0.78))] p-8 shadow-soft md:p-10">
            <div className="space-y-6 text-center">
              <div className="space-y-2">
                <h2 className="font-art text-xl text-card-foreground">
                  目前沒有進行中的修復
                </h2>
                <p className="text-sm text-muted-foreground">
                  這個流程引導你們完成五個修復步驟，隨時可以啟動。
                </p>
              </div>
              <Button
                variant="primary"
                size="lg"
                loading={repairStarting}
                onClick={handleStartRepairFlow}
              >
                開始修復流程
              </Button>
            </div>
          </section>
        ) : viewState === 'repair_missing_session' ? (
          <section className="animate-slide-up-fade-1 rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(248,244,238,0.78))] p-8 shadow-soft md:p-10">
            <div className="space-y-5 text-center">
              <p className="text-sm text-muted-foreground">
                找不到這個修復流程，請重新開始。
              </p>
              <Button
                variant="secondary"
                size="md"
                onClick={() => setRepairSessionId(null)}
              >
                清除舊流程
              </Button>
            </div>
          </section>
        ) : (
          <div className="space-y-8 md:space-y-10">
            {/* Step progress indicator */}
            <nav
              className="animate-slide-up-fade-1 flex items-center justify-between gap-1 px-1 sm:px-4"
              aria-label="修復流程進度"
            >
              {REPAIR_STEPS.map((s, idx) => {
                const myCompleted = repairStatus!.my_completed_steps ?? [];
                const done = myCompleted.includes(s.num);
                const active = s.num === repairStatus!.current_step;
                return (
                  <div key={s.num} className="flex flex-1 items-center gap-1">
                    <div className="flex flex-col items-center gap-1.5">
                      <div
                        className={[
                          'flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium transition-all duration-haven',
                          done
                            ? 'bg-primary text-primary-foreground shadow-soft'
                            : active
                              ? 'border-2 border-primary bg-white text-primary shadow-soft'
                              : 'border border-white/60 bg-white/50 text-muted-foreground',
                        ].join(' ')}
                        aria-current={active ? 'step' : undefined}
                      >
                        {s.num}
                      </div>
                      <span
                        className={[
                          'text-[10px] leading-tight sm:text-[11px]',
                          active ? 'font-medium text-card-foreground' : 'text-muted-foreground',
                        ].join(' ')}
                      >
                        {s.label}
                      </span>
                    </div>
                    {idx < REPAIR_STEPS.length - 1 && (
                      <div
                        className={[
                          'mb-5 h-px flex-1 transition-colors duration-haven',
                          done ? 'bg-primary/40' : 'bg-white/60',
                        ].join(' ')}
                        aria-hidden
                      />
                    )}
                  </div>
                );
              })}
            </nav>

            {/* Current step card */}
            <section className="animate-slide-up-fade-2 rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(248,252,250,0.90),rgba(241,247,244,0.82))] p-6 shadow-soft md:p-8">
              <div className="space-y-6">
                {/* Step header */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-3">
                    <h2 className="font-art text-xl text-card-foreground">
                      {repairStepGuide.title}
                    </h2>
                    <span className="text-xs tabular-nums text-muted-foreground">
                      步驟 {repairStatus!.current_step}/5
                    </span>
                  </div>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {repairStepGuide.description}
                  </p>
                  <p className="text-xs tabular-nums text-muted-foreground">
                    伴侶進度：{repairStatus!.partner_completed_steps.length}/5
                  </p>
                </div>

                {/* Step content */}
                {repairStatus!.safety_mode_active ? (
                  <RepairSafetyModePanel onReset={handleResetRepairFlow} />
                ) : repairStatus!.completed ? (
                  <div className="rounded-[1.5rem] border border-primary/15 bg-primary/5 p-5 md:p-6">
                    <p className="font-art text-base font-medium text-card-foreground">
                      修復流程已完成
                    </p>
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                      建議在 24 小時內完成你們的共同承諾，讓修復有具體落地。
                    </p>
                  </div>
                ) : (
                  <div className="space-y-5">
                    {repairStatus!.current_step === 1 && (
                      <div className="rounded-[1.5rem] bg-white/50 p-5 backdrop-blur-sm md:p-6">
                        <div className="flex items-start gap-3">
                          <span className="relative mt-0.5 flex h-3 w-3 shrink-0" aria-hidden>
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/30" />
                            <span className="relative inline-flex h-3 w-3 rounded-full bg-primary/50" />
                          </span>
                          <div className="space-y-2">
                            <p className="text-sm font-medium leading-relaxed text-card-foreground">
                              先讓自己慢下來
                            </p>
                            <p className="text-xs leading-relaxed text-muted-foreground">
                              深呼吸幾次，確認情緒已從高峰回落。準備好後，按下方按鈕進入下一步。
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                    {repairStatus!.current_step === 2 && (
                      <>
                        <Textarea
                          id="repair-i-feel"
                          label="我感受到"
                          value={iFeel}
                          onChange={(e) => setIFeel(e.target.value)}
                          placeholder="例如：我感到被忽略、焦慮…"
                          maxLength={300}
                          className="min-h-[84px]"
                        />
                        <Textarea
                          id="repair-i-need"
                          label="我需要"
                          value={iNeed}
                          onChange={(e) => setINeed(e.target.value)}
                          placeholder="例如：我需要你先聽完我的句子…"
                          maxLength={300}
                          className="min-h-[84px]"
                        />
                      </>
                    )}
                    {repairStatus!.current_step === 3 && (
                      <Textarea
                        id="repair-mirror"
                        label="鏡像復述"
                        value={mirrorText}
                        onChange={(e) => setMirrorText(e.target.value)}
                        placeholder="例如：我聽見你其實是在擔心我們的連結…"
                        maxLength={300}
                        className="min-h-[84px]"
                      />
                    )}
                    {repairStatus!.current_step === 4 && (
                      <Textarea
                        id="repair-commitment"
                        label="共同承諾（24 小時內）"
                        value={sharedCommitment}
                        onChange={(e) => setSharedCommitment(e.target.value)}
                        placeholder="例如：今晚散步 10 分鐘，不帶手機。"
                        maxLength={300}
                        className="min-h-[84px]"
                      />
                    )}
                    {repairStatus!.current_step === 5 && (
                      <Textarea
                        id="repair-improvement"
                        label="改善回顧"
                        value={improvementNote}
                        onChange={(e) => setImprovementNote(e.target.value)}
                        placeholder="例如：我們比上次更快停下來，先聽完再回應。"
                        maxLength={300}
                        className="min-h-[84px]"
                      />
                    )}
                    <div className="flex justify-end">
                      <Button
                        variant="primary"
                        size="md"
                        loading={repairSubmitting}
                        onClick={handleCompleteRepairStep}
                      >
                        完成此步驟
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </section>

            {/* End flow action */}
            <div className="flex justify-center">
              <Button variant="ghost" size="sm" onClick={handleResetRepairFlow}>
                結束目前流程
              </Button>
            </div>
          </div>
        )}
      </div>
    );
  }

  /* ── Classic mediation ── */

  if (!status) return null;

  return (
    <div className="space-y-8 md:space-y-10">
      {/* Page identity */}
      <div className="space-y-3 animate-slide-up-fade">
        <h1 className="font-art text-[2rem] leading-[1.05] tracking-tight text-gradient-gold md:text-[2.8rem]">
          調解模式
        </h1>
        <p className="text-sm leading-relaxed text-muted-foreground">
          換位思考三問，各自填寫後查看彼此心聲。
        </p>
      </div>

      {viewState === 'classic_no_session' ? (
        <section className="animate-slide-up-fade-1 rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(248,244,238,0.78))] p-8 shadow-soft md:p-10">
          <div className="space-y-2 text-center">
            <p className="font-art text-base text-card-foreground">
              目前沒有進行中的調解。
            </p>
            <p className="text-xs text-muted-foreground/70">
              當系統偵測到可能的情緒張力時，會邀請你們進入此流程。
            </p>
          </div>
        </section>
      ) : viewState === 'classic_answering' ? (
        <section className="animate-slide-up-fade-1 rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(248,252,250,0.90),rgba(241,247,244,0.82))] p-6 shadow-soft md:p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <h2 className="font-art text-xl text-card-foreground">請回答以下三題</h2>
            {(status.questions ?? []).map((q, i) => (
              <Textarea
                key={i}
                id={`mediation-q-${i}`}
                label={`${i + 1}. ${q}`}
                value={answers[i] ?? ''}
                onChange={(e) => {
                  const next: [string, string, string] = [...answers];
                  next[i] = e.target.value;
                  setAnswers(next);
                }}
                placeholder="寫下你的想法…"
                maxLength={2000}
                className="min-h-[80px]"
              />
            ))}
            <div className="flex justify-end">
              <Button
                type="submit"
                variant="primary"
                size="lg"
                loading={submitting}
                aria-label="送出調解回答"
              >
                送出
              </Button>
            </div>
          </form>
        </section>
      ) : viewState === 'classic_waiting_partner' ? (
        <section className="animate-slide-up-fade-1 rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(248,244,238,0.78))] p-8 shadow-soft md:p-10">
          <div className="space-y-2 text-center">
            <p className="font-art text-base font-medium text-card-foreground">
              你已完成填寫
            </p>
            <p className="text-sm text-muted-foreground">
              等待伴侶填寫後即可查看彼此心聲與下次 SOP。
            </p>
          </div>
        </section>
      ) : (
        <div className="space-y-6 animate-slide-up-fade-1">
          {/* My answers */}
          <section className="rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(248,252,250,0.90),rgba(241,247,244,0.82))] p-6 shadow-soft md:p-8">
            <h2 className="mb-4 font-art text-xl text-card-foreground">你的回答</h2>
            <div className="space-y-3">
              {(status.my_answers ?? []).map((ans, i) => (
                <div
                  key={i}
                  className="rounded-[1.2rem] border-l-[3px] border-l-primary/30 bg-white/55 px-4 py-3 backdrop-blur-sm"
                >
                  <p className="text-xs text-muted-foreground">
                    {(status.questions ?? [])[i]}
                  </p>
                  <p className="mt-1.5 text-sm leading-relaxed text-card-foreground">
                    {ans || '—'}
                  </p>
                </div>
              ))}
            </div>
          </section>

          {/* Partner answers */}
          <section className="rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,252,248,0.90),rgba(248,244,238,0.82))] p-6 shadow-soft md:p-8">
            <h2 className="mb-4 font-art text-xl text-card-foreground">伴侶的回答</h2>
            <div className="space-y-3">
              {(status.partner_answers ?? []).map((ans, i) => (
                <div
                  key={i}
                  className="rounded-[1.2rem] border-l-[3px] border-l-primary/15 bg-white/55 px-4 py-3 backdrop-blur-sm"
                >
                  <p className="text-xs text-muted-foreground">
                    {(status.questions ?? [])[i]}
                  </p>
                  <p className="mt-1.5 text-sm leading-relaxed text-card-foreground">
                    {ans || '—'}
                  </p>
                </div>
              ))}
            </div>
          </section>

          {/* Next SOP */}
          {status.next_sop && (
            <section className="rounded-[2rem] border border-primary/12 bg-[linear-gradient(180deg,rgba(255,250,247,0.90),rgba(250,243,234,0.82))] p-6 shadow-soft md:p-8">
              <h2 className="mb-2 font-art text-xl text-card-foreground">下次 SOP</h2>
              <p className="text-sm leading-relaxed text-card-foreground">
                {status.next_sop}
              </p>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
