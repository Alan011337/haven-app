'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRight } from 'lucide-react';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
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
import MediationSkeleton from './MediationSkeleton';
import {
  MediationCover,
  MediationOverviewCard,
  MediationQuestionCard,
  MediationResponseCard,
  MediationSafetyPanel,
  MediationSequenceRail,
  MediationStageFrame,
  MediationStatePanel,
  MediationStudioCard,
} from './MediationPrimitives';

const REPAIR_SESSION_STORAGE_KEY = 'haven_repair_flow_session_id_v1';

const REPAIR_STEP_META: Record<
  number,
  {
    railLabel: string;
    railDescription: string;
    title: string;
    description: string;
    studioTitle: string;
    studioDescription: string;
  }
> = {
  1: {
    railLabel: '降溫',
    railDescription: '先讓身體與語氣退回穩定。',
    title: '先確認你們都已從高張力裡退開。',
    description:
      '真正的修復不會在情緒最高點開始。這一步不是拖延，而是先把傷害的速度降下來，讓接下來的內容可以被聽見。',
    studioTitle: '把這一步當作進房前的安頓。',
    studioDescription:
      '如果你們仍在高張力裡，先不要往下。等呼吸、語氣、心跳都稍微穩定，再完成這一步。',
  },
  2: {
    railLabel: '我訊息',
    railDescription: '只說感受與需要，不做指責。',
    title: '先把你的感受與需要說清楚，而不是把對方定罪。',
    description:
      '這一步的目標不是證明自己比較有道理，而是讓對方知道你內在真正發生了什麼，以及你需要什麼。',
    studioTitle: '用「我感受到 / 我需要」把真實說清楚。',
    studioDescription:
      '請盡量避免責備句。把焦點放回你的感受、界線與需要，讓對方有機會聽見真正重要的部分。',
  },
  3: {
    railLabel: '鏡像復述',
    railDescription: '先確認你真的聽懂了。',
    title: '這一步只做一件事: 把對方說的內容準確地還回去。',
    description:
      '鏡像復述不是反駁，也不是自我辯護。它是一個慢下來的動作，先讓對方感受到自己被理解。',
    studioTitle: '先把你聽見的內容安靜地還給對方。',
    studioDescription:
      '用自己的話復述，但不要改寫對方真正的意思。這一步做得越準，後面的防禦就會越少。',
  },
  4: {
    railLabel: '共同承諾',
    railDescription: '找一件 24 小時內能做到的事。',
    title: '讓修復落到一個具體可完成的小承諾上。',
    description:
      '修復如果只停在理解，很容易再次散掉。這一步要把理解落成一件足夠小、足夠可完成的共同動作。',
    studioTitle: '留下你們接下來 24 小時內會真的做到的一件事。',
    studioDescription:
      '承諾不需要宏大，重點是可完成、可感受到，而且真的能讓關係往前一步。',
  },
  5: {
    railLabel: '改善回顧',
    railDescription: '辨認這次真正變好的地方。',
    title: '最後，不是檢討，而是辨認這次有哪裡比以前更好了。',
    description:
      '修復感需要被看見，才會成為下次能夠再次採用的經驗。這一步讓你們知道，改變其實正在發生。',
    studioTitle: '把這次修復裡真正有改善的一點留下來。',
    studioDescription:
      '哪怕只是一個小小的不同，都值得被寫下。這會成為下一次你們更快回到連結的證據。',
  },
};

function getRoomStateCopy(viewState: string, repairFlowEnabled: boolean) {
  if (repairFlowEnabled) {
    switch (viewState) {
      case 'repair_start':
        return {
          stateLabel: '尚未開始',
          nextAction: '啟動一輪新的修復流程',
          pulse: '這個房間會先把節奏放慢，再一步一步陪你們把話說清楚。現在還沒有進行中的修復流程。',
        };
      case 'repair_missing_session':
        return {
          stateLabel: '需要重新對齊',
          nextAction: '清除舊流程或重新啟動',
          pulse: '先前的修復流程沒有被完整帶回來。這一頁會先幫你們把狀態對齊，而不是直接把對話往前推。',
        };
      case 'repair_active':
        return {
          stateLabel: '正在修復',
          nextAction: '一次完成目前這一步',
          pulse: '修復流程進行中。先只處理眼前這一步，不急著把所有問題一次說完。',
        };
      default:
        return {
          stateLabel: '修復房間',
          nextAction: '先把房間安靜下來',
          pulse: '這裡的目標不是贏，而是讓兩個人都有機會在安全的節奏裡被聽見。',
        };
    }
  }

  switch (viewState) {
    case 'classic_no_session':
      return {
        stateLabel: '等待觸發',
        nextAction: '等系統邀請進入',
        pulse: '三問調解目前沒有進行中的 session。當系統偵測到情緒張力時，會邀請你們進入這個較輕量的對話房間。',
      };
    case 'classic_answering':
      return {
        stateLabel: '正在填寫',
        nextAction: '先把三題慢慢寫完',
        pulse: '現在先不用急著解釋自己。把三個問題安靜地寫完，這個房間才會把雙方的版本都展開。',
      };
    case 'classic_waiting_partner':
      return {
        stateLabel: '等待伴侶',
        nextAction: '讓對方在自己的節奏裡完成',
        pulse: '你的回答已經交給這個房間保管了。接下來只需要等伴侶完成，系統就會把兩邊的內容一起展開。',
      };
    case 'classic_completed':
      return {
        stateLabel: '共讀完成',
        nextAction: '一起閱讀答案與 SOP',
        pulse: '雙方回答都已經收進來了。現在的重點不是爭辯，而是一起讀懂彼此真正想被聽見的部分。',
      };
    default:
      return {
        stateLabel: '三問調解',
        nextAction: '先讓心聲被放下',
        pulse: '這個房間會把緊繃的對話拆成更容易被承接的幾個步驟。',
      };
  }
}

export default function MediationPageContent() {
  const queryClient = useQueryClient();
  const { data: featureFlags, isFetched: featureFlagsFetched } = useFeatureFlags();
  const repairFlowEnabled = Boolean(featureFlags?.flags?.repair_flow_v1)
    && !Boolean(featureFlags?.kill_switches?.disable_repair_flow_v1);
  const {
    data: status,
    isLoading: loading,
    error: mediationError,
    refetch: refetchMediationStatus,
  } = useMediationStatusEnabled(!repairFlowEnabled);
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
    if (!featureFlagsFetched) {
      return;
    }
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
  }, [featureFlagsFetched, repairFlowEnabled, repairSessionId]);

  const repairStatusCode = (repairStatusError as { response?: { status?: number } } | null)?.response?.status;

  useEffect(() => {
    if (repairStatusCode === 404) {
      setRepairSessionId(null);
    }
  }, [repairStatusCode]);

  const repairStepGuide = useMemo(() => {
    const step = repairStatus?.current_step ?? 1;
    return REPAIR_STEP_META[step] ?? REPAIR_STEP_META[1];
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
    [repairFlowEnabled, loading, status, repairSessionId, repairStatusLoading, repairStatus],
  );

  const roomStateCopy = getRoomStateCopy(viewState, repairFlowEnabled);

  const sequenceItems = useMemo(() => {
    if (repairFlowEnabled) {
      return [1, 2, 3, 4, 5].map((step) => ({
        label: REPAIR_STEP_META[step].railLabel,
        description: REPAIR_STEP_META[step].railDescription,
        state: repairStatus?.completed || repairStatus?.my_completed_steps.includes(step)
          ? 'complete'
          : repairStatus?.current_step === step
            ? 'active'
            : 'upcoming',
        meta: repairStatus
          ? `你 ${repairStatus.my_completed_steps.includes(step) ? '已完成' : '尚未完成'}`
          : undefined,
      })) as {
        label: string;
        description: string;
        state: 'complete' | 'active' | 'upcoming';
        meta?: string;
      }[];
    }

    const classicState = status?.in_mediation ?? false;
    const myAnswered = status?.my_answered ?? false;
    const partnerAnswered = status?.partner_answered ?? false;

    return [
      {
        label: '進入房間',
        description: '先讓系統幫你們把對話放慢。',
        state: classicState ? 'complete' : 'upcoming',
      },
      {
        label: '寫下三問',
        description: '先各自回答，而不是立刻爭辯。',
        state: myAnswered ? 'complete' : classicState ? 'active' : 'upcoming',
      },
      {
        label: '等待彼此',
        description: '讓兩邊都在自己的節奏裡說完。',
        state: partnerAnswered ? 'complete' : myAnswered ? 'active' : 'upcoming',
      },
      {
        label: '共讀回答',
        description: '把雙方版本放到同一張桌面上。',
        state: partnerAnswered ? 'complete' : 'upcoming',
      },
      {
        label: '留下一次 SOP',
        description: '把下次可用的做法留下來。',
        state: status?.next_sop ? 'complete' : partnerAnswered ? 'active' : 'upcoming',
      },
    ] as {
      label: string;
      description: string;
      state: 'complete' | 'active' | 'upcoming';
      meta?: string;
    }[];
  }, [repairFlowEnabled, repairStatus, status]);

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
      showToast('已啟動修復流程，先從目前這一步開始。', 'success');
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

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!status?.session_id || answers.some((answer) => !answer.trim())) {
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

  if (!repairFlowEnabled && mediationError) {
    return (
      <MediationStatePanel
        eyebrow="Mediation Unavailable"
        title="這個房間暫時還打不開。"
        description="調解狀態載入失敗了。你的資料不會消失，但現在需要重新載入一次，才能把這次對話的狀態帶回來。"
        tone="error"
        action={
          <Button
            variant="secondary"
            onClick={() => {
              void refetchMediationStatus();
            }}
          >
            重新載入
          </Button>
        }
      />
    );
  }

  if (repairFlowEnabled && repairSessionId && repairStatusError && repairStatusCode !== 404) {
    return (
      <MediationStatePanel
        eyebrow="Repair Flow Unavailable"
        title="這次修復流程暫時無法讀取。"
        description="系統暫時取不到目前這輪修復的狀態。你可以先重新載入，或清除這個舊流程後再重新開始。"
        tone="error"
        action={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                void refetchRepairStatus();
              }}
            >
              重新載入
            </Button>
            <Button variant="outline" onClick={handleResetRepairFlow}>
              清除舊流程
            </Button>
          </>
        }
      />
    );
  }

  if (viewState === 'loading') {
    return <MediationSkeleton />;
  }

  const overviewRows = repairFlowEnabled
    ? [
        {
          label: '目前狀態',
          value: roomStateCopy.stateLabel,
          meta: repairStatus ? `Step ${repairStatus.current_step}/5` : '尚未啟動',
        },
        {
          label: '你的節奏',
          value: repairStatus ? `${repairStatus.my_completed_steps.length}/5` : '尚未開始',
          meta: '已完成的步驟數',
        },
        {
          label: '伴侶進度',
          value: repairStatus ? `${repairStatus.partner_completed_steps.length}/5` : '等待同步',
          meta: '對方已完成的步驟數',
        },
      ]
    : [
        {
          label: '目前狀態',
          value: roomStateCopy.stateLabel,
          meta: status?.in_mediation ? 'session 進行中' : '沒有進行中的 session',
        },
        {
          label: '你的進度',
          value: status?.my_answered ? '已完成' : '尚未完成',
          meta: '三題回答是否已送出',
        },
        {
          label: '伴侶進度',
          value: status?.partner_answered ? '已完成' : '等待中',
          meta: '對方是否已完成回答',
        },
      ];

  const primaryAction = viewState === 'repair_start' ? (
    <Button loading={repairStarting} onClick={() => { void handleStartRepairFlow(); }} rightIcon={<ArrowRight className="h-4 w-4" aria-hidden />}>
      開始修復流程
    </Button>
  ) : null;

  const renderRepairContent = () => {
    if (viewState === 'repair_start') {
      return (
        <MediationStageFrame
          eyebrow="Repair Flow"
          title="當你們需要一個更完整、更有節奏的修復流程時，從這裡開始。"
          description="Repair Flow 會把修復拆成五個步驟，降低防禦、保留 dignity，並把真正可落地的承諾留到最後。"
          aside={
            <div className="flex flex-wrap gap-2">
              <Badge variant="metadata" size="md" className="bg-white/72 text-card-foreground">
                5 個步驟
              </Badge>
              <Badge variant="outline" size="md" className="bg-white/66">
                尚未開始
              </Badge>
            </div>
          }
        >
          <MediationStatePanel
            eyebrow="Start Here"
            title="目前沒有進行中的修復流程。"
            description="只有在你們準備好真正慢下來時，才需要啟動這個房間。它不是為了快速結束爭執，而是為了讓修復被好好完成。"
            action={primaryAction}
          />
        </MediationStageFrame>
      );
    }

    if (viewState === 'repair_missing_session') {
      return (
        <MediationStageFrame
          eyebrow="Room Recovery"
          title="先把這個房間重新對齊，再決定要不要繼續。"
          description="先前的流程沒有被完整帶回來。這不代表內容消失了，但現在需要先把房間狀態整理乾淨。"
          aside={
            <div className="flex flex-wrap gap-2">
              <Badge variant="warning" size="md" className="bg-white/72 text-card-foreground">
                需要重新對齊
              </Badge>
            </div>
          }
        >
          <MediationStatePanel
            eyebrow="Session Recovery"
            title="找不到這次修復流程。"
            description="可能是流程已過期、已結束，或目前的 session id 已經失效。你可以先清除舊流程，必要時再重新開始。"
            action={
              <Button variant="secondary" onClick={handleResetRepairFlow}>
                清除舊流程
              </Button>
            }
          />
        </MediationStageFrame>
      );
    }

    if (!repairStatus) {
      return null;
    }

    if (repairStatus.safety_mode_active) {
      return (
        <MediationStageFrame
          eyebrow="Safety First"
          title="現在先處理安全，而不是處理輸贏。"
          description="當高風險語句出現時，系統會先停下修復流程。這一刻最重要的是確認安全、降低刺激，而不是把話講完。"
          aside={
            <div className="flex flex-wrap gap-2">
              <Badge variant="warning" size="md" className="bg-white/72 text-card-foreground">
                安全模式已啟動
              </Badge>
            </div>
          }
        >
          <MediationSafetyPanel onReset={handleResetRepairFlow} />
        </MediationStageFrame>
      );
    }

    if (repairStatus.completed) {
      return (
        <MediationStageFrame
          eyebrow="Repair Complete"
          title="這一輪修復已經有了落點。"
          description="修復流程已完成。接下來最重要的不是再多說，而是讓你們剛剛留下的承諾在現實裡真的發生。"
          aside={
            <div className="flex flex-wrap gap-2">
              <Badge variant="success" size="md" className="bg-white/72 text-card-foreground">
                5/5 已完成
              </Badge>
              <Badge variant="metadata" size="md" className="bg-white/72 text-card-foreground">
                24 小時內兌現承諾
              </Badge>
            </div>
          }
        >
          <MediationStatePanel
            eyebrow="Aftercare"
            title="先把承諾活出來，這次修復才算真正落地。"
            description="如果你們剛剛找到了一件能在 24 小時內完成的小承諾，現在最值得做的，就是安靜地把它做到。"
            tone="success"
            action={
              <div className="flex flex-wrap items-center gap-3">
                {repairStatus.outcome_capture_pending ? (
                  <Link
                    href="/love-map#heart"
                    className="inline-flex h-11 items-center justify-center gap-2 rounded-button border border-transparent bg-gradient-to-b from-primary to-primary/92 px-5 text-sm font-medium text-primary-foreground shadow-satin-button transition-[transform,box-shadow,background-color,border-color,color,opacity] duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
                  >
                    把這次修復帶回關係系統
                    <ArrowRight className="h-4 w-4" aria-hidden />
                  </Link>
                ) : null}
                <Button variant="outline" onClick={handleResetRepairFlow}>
                  結束目前流程
                </Button>
              </div>
            }
          />
        </MediationStageFrame>
      );
    }

    return (
      <MediationStageFrame
        eyebrow={`Step ${repairStatus.current_step} / 5`}
        title={repairStepGuide.title}
        description={repairStepGuide.description}
        aside={
          <div className="flex flex-wrap gap-2">
            <Badge variant="metadata" size="md" className="bg-white/72 text-card-foreground">
              我的進度 {repairStatus.my_completed_steps.length}/5
            </Badge>
            <Badge variant="status" size="md" className="bg-white/72 text-card-foreground">
              伴侶進度 {repairStatus.partner_completed_steps.length}/5
            </Badge>
          </div>
        }
      >
        <MediationStudioCard
          eyebrow={`Repair Studio · ${REPAIR_STEP_META[repairStatus.current_step].railLabel}`}
          title={repairStepGuide.studioTitle}
          description={repairStepGuide.studioDescription}
          footer={
            <>
              <p className="type-caption text-muted-foreground">
                一次只完成這一步。真正的 calm 來自節奏被照顧，而不是速度被追趕。
              </p>
              <Button loading={repairSubmitting} onClick={() => { void handleCompleteRepairStep(); }}>
                {repairStatus.current_step === 1 ? '我已經穩定下來' : '完成此步驟'}
              </Button>
            </>
          }
        >
          {repairStatus.current_step === 1 ? (
            <MediationStatePanel
              eyebrow="Cooldown Check"
              title="在往下之前，先確認刺激性互動已經停止。"
              description="如果你仍然很想立刻解釋、反駁或追著對方要答案，先不要按下完成。修復需要的是一個穩定起點。"
              tone="quiet"
            />
          ) : null}

          {repairStatus.current_step === 2 ? (
            <div className="grid gap-4 md:grid-cols-2">
              <MediationQuestionCard
                eyebrow="Step 2A"
                title="我感受到"
                description="只描述你的感受，不要把對方貼標或定罪。"
                textareaId="repair-i-feel"
                textareaLabel="感受"
                value={iFeel}
                onChange={setIFeel}
                placeholder="例如：我感到被忽略、緊張、害怕關係正在離我遠去..."
                helperText="讓對方先聽見你內在發生了什麼。"
                maxLength={300}
              />
              <MediationQuestionCard
                eyebrow="Step 2B"
                title="我需要"
                description="說清楚你希望被如何對待或靠近。"
                textareaId="repair-i-need"
                textareaLabel="需要"
                value={iNeed}
                onChange={setINeed}
                placeholder="例如：我需要你先聽完，再一起決定怎麼處理..."
                helperText="把需要說清楚，比把委屈放大更有機會被理解。"
                maxLength={300}
              />
            </div>
          ) : null}

          {repairStatus.current_step === 3 ? (
            <MediationQuestionCard
              eyebrow="Step 3"
              title="鏡像復述"
              description="把你真正聽見的內容還給對方，不急著補充自己的版本。"
              textareaId="repair-mirror"
              textareaLabel="鏡像復述"
              value={mirrorText}
              onChange={setMirrorText}
              placeholder="例如：我聽見你其實是在擔心，我們一吵起來就會更遠..."
              helperText="先讓對方知道自己被聽懂了，防禦才有機會下降。"
              maxLength={300}
            />
          ) : null}

          {repairStatus.current_step === 4 ? (
            <MediationQuestionCard
              eyebrow="Step 4"
              title="共同承諾"
              description="找一件 24 小時內真的做得到的小事。"
              textareaId="repair-commitment"
              textareaLabel="共同承諾"
              value={sharedCommitment}
              onChange={setSharedCommitment}
              placeholder="例如：今晚一起散步 10 分鐘，不帶手機。"
              helperText="承諾越具體、越小、越可完成，就越能真的修復關係感。"
              maxLength={300}
            />
          ) : null}

          {repairStatus.current_step === 5 ? (
            <MediationQuestionCard
              eyebrow="Step 5"
              title="改善回顧"
              description="留下這次和以前不一樣的一個小地方。"
              textareaId="repair-improvement"
              textareaLabel="改善回顧"
              value={improvementNote}
              onChange={setImprovementNote}
              placeholder="例如：我們比上次更快停下來，也比較能先聽完再回應。"
              helperText="把微小進步留住，下次你們就更容易再次回到這個修復節奏。"
              maxLength={300}
            />
          ) : null}
        </MediationStudioCard>

        <MediationStatePanel
          eyebrow="Room Exit"
          title="如果這一輪不適合繼續，也可以先把房間關上。"
          description="結束流程不是失敗；在不穩定的時候先停下來，本身也是一種保護關係的能力。"
          tone="quiet"
          action={
            <Button variant="outline" onClick={handleResetRepairFlow}>
              結束目前流程
            </Button>
          }
        />
      </MediationStageFrame>
    );
  };

  const renderClassicContent = () => {
    if (viewState === 'classic_no_session') {
      return (
        <MediationStageFrame
          eyebrow="Classic Mediation"
          title="現在這個房間是安靜的。"
          description="三問調解是較輕量的對話房間。當系統判斷你們適合用較簡單的引導說清楚時，才會邀請進來。"
          aside={
            <div className="flex flex-wrap gap-2">
              <Badge variant="metadata" size="md" className="bg-white/72 text-card-foreground">
                等待觸發
              </Badge>
            </div>
          }
        >
          <MediationStatePanel
            eyebrow="No Active Session"
            title="目前沒有進行中的調解。"
            description="這裡暫時不需要你處理任何內容。當系統偵測到情緒張力時，會邀請你們進入這個較輕量的三問房間。"
          />
        </MediationStageFrame>
      );
    }

    if (viewState === 'classic_waiting_partner') {
      return (
        <MediationStageFrame
          eyebrow="Waiting Room"
          title="你的版本已經被好好放下來了。"
          description="接下來只需要等伴侶完成。這段等待不是停滯，而是讓兩個人的內容都能以同樣被尊重的節奏出現。"
          aside={
            <div className="flex flex-wrap gap-2">
              <Badge variant="success" size="md" className="bg-white/72 text-card-foreground">
                你已完成填寫
              </Badge>
              <Badge variant="metadata" size="md" className="bg-white/72 text-card-foreground">
                等待伴侶
              </Badge>
            </div>
          }
        >
          <MediationStatePanel
            eyebrow="Awaiting Partner"
            title="現在先把空間留給對方。"
            description="等伴侶完成後，系統就會把雙方的內容一起展開，並留下下一次可以使用的 SOP。"
          />
        </MediationStageFrame>
      );
    }

    if (viewState === 'classic_completed' && status) {
      return (
        <MediationStageFrame
          eyebrow="Shared Reading"
          title="現在不是辯論，而是把兩個版本放到同一張桌面上。"
          description="你們都已經把三問寫完了。接下來最重要的是讀懂彼此的版本，然後把下一次遇到類似情況時可以採用的 SOP 留下來。"
          aside={
            <div className="flex flex-wrap gap-2">
              <Badge variant="success" size="md" className="bg-white/72 text-card-foreground">
                雙方都已完成
              </Badge>
              {status.next_sop ? (
                <Badge variant="status" size="md" className="bg-white/72 text-card-foreground">
                  已生成 SOP
                </Badge>
              ) : null}
            </div>
          }
        >
          <div className="grid gap-5 xl:grid-cols-2">
            <MediationStudioCard
              eyebrow="Your Side"
              title="你的回答"
              description="先回看你自己的版本，確認這就是你真正想讓對方聽見的那一層。"
            >
              <div className="space-y-4">
                {(status.my_answers ?? []).map((answer, index) => (
                  <MediationResponseCard
                    key={`mine-${index}`}
                    eyebrow={`Question ${index + 1}`}
                    question={(status.questions ?? [])[index] ?? ''}
                    answer={answer}
                  />
                ))}
              </div>
            </MediationStudioCard>

            <MediationStudioCard
              eyebrow="Partner Side"
              title="伴侶的回答"
              description="現在先把防禦放低一點，讀對方真正想被你聽見的內容。"
            >
              <div className="space-y-4">
                {(status.partner_answers ?? []).map((answer, index) => (
                  <MediationResponseCard
                    key={`partner-${index}`}
                    eyebrow={`Question ${index + 1}`}
                    question={(status.questions ?? [])[index] ?? ''}
                    answer={answer}
                  />
                ))}
              </div>
            </MediationStudioCard>
          </div>

          {status.next_sop ? (
            <MediationStatePanel
              eyebrow="Next Time SOP"
              title="把下一次可以使用的做法留下來。"
              description={status.next_sop}
              tone="success"
            />
          ) : null}
        </MediationStageFrame>
      );
    }

    if (!status) {
      return null;
    }

    return (
      <MediationStageFrame
        eyebrow="Three Questions"
        title="先把每個人的心聲安靜地說清楚，再讓這個房間把兩邊的內容放到一起。"
        description="在三問房間裡，現在不需要搶著回應。先一次一題地把想法寫下來，讓自己的版本被完整收住。"
        aside={
          <div className="flex flex-wrap gap-2">
            <Badge variant="status" size="md" className="bg-white/72 text-card-foreground">
              共 3 題
            </Badge>
            <Badge variant="metadata" size="md" className="bg-white/72 text-card-foreground">
              先完成自己的版本
            </Badge>
          </div>
        }
      >
        <MediationStudioCard
          eyebrow="Your Reflection"
          title="請一次只回答一題，不急著反駁。"
          description="系統會先收下你的版本，等對方也完成後，再一起展開雙方的內容與下次 SOP。"
          footer={
            <>
              <p className="type-caption text-muted-foreground">
                這裡先處理表達，不處理攻防。慢一點，答案通常會更真。
              </p>
              <Button type="submit" form="mediation-answer-form" loading={submitting}>
                送出回答
              </Button>
            </>
          }
        >
          <form id="mediation-answer-form" onSubmit={handleSubmit} className="space-y-4">
            {(status.questions ?? []).map((question, index) => (
              <MediationQuestionCard
                key={`${index}-${question}`}
                eyebrow={`Question ${index + 1}`}
                title={question}
                description="先寫下你的版本，之後才會一起閱讀雙方的內容。"
                textareaId={`mediation-q-${index}`}
                textareaLabel="你的回答"
                value={answers[index] ?? ''}
                onChange={(value) => {
                  setAnswers((current) => {
                    const next = [...current] as [string, string, string];
                    next[index] = value;
                    return next;
                  });
                }}
                placeholder="寫下你的想法..."
                helperText="不需要完美，只需要足夠真實。"
                maxLength={2000}
              />
            ))}
          </form>
        </MediationStudioCard>
      </MediationStageFrame>
    );
  };

  return (
    <div className="space-y-[clamp(1.75rem,3vw,3rem)]">
      <MediationCover
        eyebrow={repairFlowEnabled ? 'Mediation Mode · Repair Flow v1' : 'Mediation Mode · Three-Question Room'}
        title="把最難說清楚的時刻，放進一個足夠溫和的房間。"
        description="Mediation Mode 不該像工單、客服或效率工具。它是一個先降低防禦，再讓兩個人慢慢把真實說清楚的 calm room，讓修復與理解都能保有 dignity。"
        pulse={roomStateCopy.pulse}
        primaryAction={primaryAction}
        highlights={
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-[1.85rem] border border-white/56 bg-white/74 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/78">Current Mode</p>
              <p className="mt-2 font-art text-[1.65rem] leading-tight text-card-foreground">
                {repairFlowEnabled ? 'Repair Flow v1' : 'Three-Question Room'}
              </p>
              <p className="mt-2 type-caption text-muted-foreground">現在使用的調解房間類型。</p>
            </div>

            <div className="rounded-[1.85rem] border border-white/56 bg-white/74 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/78">Current State</p>
              <p className="mt-2 font-art text-[1.65rem] leading-tight text-card-foreground">{roomStateCopy.stateLabel}</p>
              <p className="mt-2 type-caption text-muted-foreground">這個房間此刻真正正在發生的事。</p>
            </div>

            <div className="rounded-[1.85rem] border border-white/56 bg-white/74 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/78">Next Action</p>
              <p className="mt-2 font-art text-[1.65rem] leading-tight text-card-foreground">{roomStateCopy.nextAction}</p>
              <p className="mt-2 type-caption text-muted-foreground">先只做下一步，不把所有問題一次推上來。</p>
            </div>
          </div>
        }
        aside={
          <>
            <MediationOverviewCard
              eyebrow="Current Room State"
              title="這個房間會先保護節奏，才保護結論。"
              description="在敏感時刻裡，最有價值的不是更快，而是更不容易再次傷人。這頁先把順序與節奏照顧好。"
            >
              <div className="space-y-3">
                {overviewRows.map((row) => (
                  <div
                    key={row.label}
                    className="flex items-center justify-between gap-3 rounded-[1.45rem] border border-white/50 bg-white/70 px-4 py-3"
                  >
                    <div className="space-y-1">
                      <p className="type-section-title text-card-foreground">{row.label}</p>
                      <p className="type-caption text-muted-foreground">{row.meta}</p>
                    </div>
                    <Badge variant="metadata" size="sm">
                      {row.value}
                    </Badge>
                  </div>
                ))}
              </div>
            </MediationOverviewCard>

            <MediationOverviewCard
              eyebrow="Room Rules"
              title="這個房間只做修復，不做勝負。"
              description="即使內容困難，這個頁面仍然應該讓人感到被照顧，而不是被流程推著跑。"
            >
              <div className="space-y-3">
                {[
                  '一次只處理眼前這一步，不追求立刻講完所有事情。',
                  '先用「我感受到 / 我需要」取代指責與翻舊帳。',
                  '只要安全模式啟動，就先把對話停下來，安全優先。',
                ].map((rule) => (
                  <div
                    key={rule}
                    className="rounded-[1.45rem] border border-white/50 bg-white/70 px-4 py-3"
                  >
                    <p className="type-caption text-card-foreground">{rule}</p>
                  </div>
                ))}
              </div>
            </MediationOverviewCard>
          </>
        }
      />

      <MediationSequenceRail items={sequenceItems} />

      {repairFlowEnabled ? renderRepairContent() : renderClassicContent()}
    </div>
  );
}
