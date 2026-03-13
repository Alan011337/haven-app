"use client";

import Link from "next/link";
import {
  ArrowLeft,
  BookHeart,
  CheckCircle2,
  ChevronRight,
  HeartHandshake,
  NotebookPen,
  ScrollText,
  Sparkles,
  Star,
  type LucideIcon,
} from "lucide-react";
import { GlassCard } from "@/components/haven/GlassCard";
import OnboardingConsentCard from "@/components/features/OnboardingConsentCard";
import Skeleton from "@/components/ui/Skeleton";
import Badge from "@/components/ui/Badge";
import { useOnboardingQuest } from "@/hooks/queries";
import { routeLinkCtaClasses } from "@/features/decks/ui/routeStyleHelpers";
import {
  resolveHomeOnboardingStepHref,
  resolveOnboardingStepActionLabel,
} from "@/lib/home-fast-snapshot";
import type { OnboardingQuestStep, OnboardingQuestStepKey } from "@/services/api-client.types";

const STEP_META: Record<
  OnboardingQuestStepKey,
  {
    icon: LucideIcon;
    eyebrow: string;
    helper: string;
  }
> = {
  ACCEPT_TERMS: {
    icon: ScrollText,
    eyebrow: "Day 1",
    helper: "先把安全感、通知與 AI 介入方式定下來，後面的互動才會舒服。",
  },
  BIND_PARTNER: {
    icon: HeartHandshake,
    eyebrow: "Day 2",
    helper: "連結伴侶之後，首頁、來信與每日儀式才會真的開始成形。",
  },
  CREATE_FIRST_JOURNAL: {
    icon: NotebookPen,
    eyebrow: "Day 3",
    helper: "寫下第一篇日記，讓 Haven 開始理解你今天真正的狀態。",
  },
  RESPOND_FIRST_CARD: {
    icon: Sparkles,
    eyebrow: "Day 4",
    helper: "完成第一張卡片，讓日常互動開始帶有一點儀式感。",
  },
  PARTNER_FIRST_JOURNAL: {
    icon: BookHeart,
    eyebrow: "Day 5",
    helper: "去看伴侶的來信，讓首頁不只是在寫，也開始閱讀彼此。",
  },
  PAIR_CARD_EXCHANGE: {
    icon: Star,
    eyebrow: "Day 6",
    helper: "完成雙向卡片交換，讓互動從單向回應變成真正來回。",
  },
  PAIR_STREAK_2_DAYS: {
    icon: CheckCircle2,
    eyebrow: "Day 7",
    helper: "只要再穩穩互動幾次，你們的 onboarding 就會進入常態節奏。",
  },
};

function StepRow({
  step,
  isCurrent,
}: {
  step: OnboardingQuestStep;
  isCurrent: boolean;
}) {
  const meta = STEP_META[step.key];
  const Icon = meta.icon;

  return (
    <div
      className={`rounded-[1.5rem] border px-4 py-4 transition-all duration-haven ease-haven ${
        step.completed
          ? "border-primary/16 bg-primary/6"
          : isCurrent
            ? "border-white/60 bg-white/80 shadow-soft"
            : "border-white/40 bg-white/52"
      }`}
    >
      <div className="flex items-start gap-3">
        <span
          className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border ${
            step.completed
              ? "border-primary/20 bg-primary/12 text-primary"
              : isCurrent
                ? "border-card-foreground/10 bg-card/90 text-card-foreground"
                : "border-white/50 bg-white/60 text-muted-foreground"
          }`}
          aria-hidden
        >
          {step.completed ? <CheckCircle2 className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
        </span>
        <div className="stack-block">
          <p className="type-micro uppercase text-primary/70">{meta.eyebrow}</p>
          <h3 className="type-section-title text-card-foreground">{step.title}</h3>
          <p className="type-caption text-muted-foreground">{step.description}</p>
        </div>
      </div>
    </div>
  );
}

function CurrentStepPanel({ step }: { step: OnboardingQuestStep | undefined }) {
  if (!step) {
    return (
      <GlassCard className="p-6 md:p-7">
        <p className="type-micro uppercase text-primary/70">Complete</p>
        <h2 className="mt-3 type-h3 text-card-foreground">新手引導已完成。</h2>
        <p className="mt-3 max-w-2xl type-body-muted text-muted-foreground">
          你們已經跨過首頁最開始的幾個節點。接下來就回到首頁，讓 Haven 回到日常陪伴的節奏。
        </p>
        <Link
          href="/"
          className={`mt-6 ${routeLinkCtaClasses.primary}`}
        >
          回首頁
          <ChevronRight className="h-4 w-4" aria-hidden />
        </Link>
      </GlassCard>
    );
  }

  if (step.key === "ACCEPT_TERMS") {
    return (
      <div className="space-y-4">
        <GlassCard className="p-6 md:p-7">
          <p className="type-micro uppercase text-primary/70">Current Step</p>
          <h2 className="mt-3 type-h3 text-card-foreground">{step.title}</h2>
          <p className="mt-3 max-w-2xl type-body-muted text-muted-foreground">
            帳號建立時，Haven 已記錄最小法遵同意流程。這一頁會把隱私範圍、資料使用摘要、通知節奏與 AI 介入偏好整理清楚，讓你在正式開始前先知道產品會如何陪你們運作。
          </p>
          <p className="mt-3 max-w-2xl type-body-muted text-muted-foreground">
            如果你要看完整法律文件，這裡也會直接提供服務條款與隱私權政策入口；不需要回到其他頁面再自己找。
          </p>
        </GlassCard>
        <OnboardingConsentCard mode="onboarding" />
      </div>
    );
  }

  const actionHref = resolveHomeOnboardingStepHref(step.key);
  const actionLabel = resolveOnboardingStepActionLabel(step.key);

  return (
    <GlassCard className="p-6 md:p-7">
      <p className="type-micro uppercase text-primary/70">Current Step</p>
      <h2 className="mt-3 type-h3 text-card-foreground">{step.title}</h2>
      <p className="mt-3 max-w-2xl type-body-muted text-muted-foreground">
        {STEP_META[step.key].helper}
      </p>
      <Link
        href={actionHref}
        className={`mt-6 ${routeLinkCtaClasses.primary}`}
      >
        {actionLabel}
        <ChevronRight className="h-4 w-4" aria-hidden />
      </Link>
    </GlassCard>
  );
}

export default function OnboardingPage() {
  const onboardingQuery = useOnboardingQuest(true);
  const onboardingQuest = onboardingQuery.data;
  const nextStep = onboardingQuest?.steps.find((step) => !step.completed);

  if (onboardingQuery.isLoading && !onboardingQuest) {
    return (
      <div className="min-h-screen bg-auth-gradient px-4 py-10 md:px-6">
        <div className="mx-auto max-w-6xl stack-page">
          <Skeleton className="h-32 w-full rounded-[2rem]" variant="shimmer" aria-hidden />
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_380px]">
            <Skeleton className="h-[340px] w-full rounded-[2rem]" variant="shimmer" aria-hidden />
            <Skeleton className="h-[340px] w-full rounded-[2rem]" variant="shimmer" aria-hidden />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-auth-gradient px-4 py-10 md:px-6">
      <div className="mx-auto max-w-6xl stack-page">
        <div className="flex items-center justify-between gap-4">
          <Link
            href="/"
            className="inline-flex items-center gap-[var(--space-inline)] rounded-button border border-white/55 bg-white/72 px-4 py-2.5 type-label text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            回首頁
          </Link>
          {onboardingQuest ? (
            <Badge variant="metadata" size="md" className="bg-white/72 px-4 py-2 text-muted-foreground shadow-soft">
              進度 {onboardingQuest.completed_steps}/{onboardingQuest.total_steps}
            </Badge>
          ) : null}
        </div>

        <GlassCard className="overflow-hidden p-6 md:p-8">
          <p className="type-micro uppercase text-primary/75">Onboarding</p>
          <h1 className="mt-3 max-w-4xl type-h1 text-card-foreground">
            把開始的幾步走清楚，之後 Haven 才會真的像在陪你們。
          </h1>
          <p className="mt-4 max-w-3xl type-body-muted text-muted-foreground">
            這一頁就是新手引導，不是一般設定頁。首頁只負責提醒下一步；真正的 onboarding 會在這裡把目前進度、下一步與完成入口整理清楚。
          </p>
        </GlassCard>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_380px] xl:items-start">
          <CurrentStepPanel step={nextStep} />

          <div className="space-y-4">
            <GlassCard className="p-5">
              <p className="type-micro uppercase text-primary/70">Journey</p>
              <div className="mt-4 space-y-3">
                {onboardingQuest?.steps.map((step) => (
                  <StepRow
                    key={step.key}
                    step={step}
                    isCurrent={Boolean(nextStep && nextStep.key === step.key)}
                  />
                ))}
              </div>
            </GlassCard>
          </div>
        </div>
      </div>
    </div>
  );
}
