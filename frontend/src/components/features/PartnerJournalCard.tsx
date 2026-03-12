import { HeartHandshake, Lightbulb, Lock, ShieldAlert, Sparkles } from 'lucide-react';
import { Journal } from '@/types';
import ActionCard from './ActionCard';
import { getJournalSafetyBand } from '@/lib/safety';
import SafetyTierGate from './SafetyTierGate';

interface Props {
  journal: Journal;
  variant?: 'default' | 'reading-room';
}

export default function PartnerJournalCard({
  journal,
  variant = 'default',
}: Props) {
  const date = new Date(journal.created_at).toLocaleDateString('zh-TW', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  const safetyBand = getJournalSafetyBand(journal);
  const isElevated = safetyBand === 'elevated';
  const isSevere = safetyBand === 'severe';
  const isSafetyConcern = isElevated || isSevere;

  return (
    <SafetyTierGate tier={journal.safety_tier ?? 0}>
      <article
        className={`relative overflow-hidden rounded-[2rem] border p-7 shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift md:p-8
          ${isSevere
            ? 'border-destructive/18 bg-[linear-gradient(180deg,rgba(255,246,246,0.96),rgba(255,250,249,0.92))]'
            : isElevated
              ? 'border-primary/15 bg-[linear-gradient(180deg,rgba(255,250,245,0.96),rgba(255,252,248,0.92))]'
              : variant === 'reading-room'
                ? 'border-[rgba(219,204,187,0.38)] bg-[linear-gradient(180deg,rgba(255,254,251,0.98),rgba(251,247,242,0.95))]'
                : 'border-white/50 bg-[linear-gradient(180deg,rgba(255,252,248,0.94),rgba(250,246,240,0.9))]'}`
        }
      >
        <div className="absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-primary/24 to-transparent" aria-hidden />
        <div className="absolute right-0 top-0 h-56 w-56 translate-x-1/4 -translate-y-1/4 rounded-full bg-primary/8 blur-hero-orb-sm" aria-hidden />

        <div className="relative space-y-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div className="space-y-2">
              <p className="text-[0.68rem] uppercase tracking-[0.28em] text-primary/80">Partner Letter</p>
              <div className="space-y-1">
                <p className="font-art text-[1.55rem] leading-tight text-card-foreground">
                  心情：{journal.mood_label || '平靜'}
                </p>
                <p className="text-xs leading-6 text-muted-foreground">{date}</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {isSafetyConcern ? (
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-[11px] font-bold ${
                    isSevere ? 'border border-destructive/20 bg-destructive/10 text-destructive' : 'border border-primary/20 bg-primary/10 text-primary'
                  }`}
                >
                  <ShieldAlert size={12} aria-hidden />
                  {isSevere ? '安全優先模式' : '需多加關懷'}
                </span>
              ) : null}
              <span className="inline-flex items-center gap-1.5 rounded-full border border-border/80 bg-white/75 px-3 py-1 text-[11px] font-semibold text-muted-foreground shadow-soft">
                <Lock className="h-3 w-3" aria-hidden />
                原文已隱私保護
              </span>
            </div>
          </div>

          <div className={`rounded-[1.7rem] border p-6 shadow-glass-inset ${variant === 'reading-room' ? 'border-[rgba(219,204,187,0.4)] bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(251,247,242,0.94))]' : 'border-white/55 bg-[linear-gradient(180deg,rgba(255,255,255,0.72),rgba(252,248,243,0.72))]'}`}>
            <p className="text-[0.68rem] uppercase tracking-[0.28em] text-primary/80">Inner Need</p>
            <p className="mt-3 font-art text-[1.55rem] leading-[1.65] text-card-foreground italic">
              &quot;{journal.emotional_needs || '希望能被理解與支持'}&quot;
            </p>
          </div>

          {isSevere ? (
            <div className="rounded-[1.5rem] border border-destructive/22 bg-destructive/8 p-5">
              <h4 className="flex items-center gap-2.5 text-sm font-bold text-destructive">
                <span className="icon-badge !w-7 !h-7 !bg-gradient-to-br !from-destructive/12 !to-destructive/4 !border-destructive/8" aria-hidden>
                  <ShieldAlert size={14} />
                </span>
                高風險提醒：先確認安全，再談溝通
              </h4>
              <p className="mt-3 text-sm leading-7 text-destructive/90">
                系統偵測到目前情緒張力偏高。建議先降低刺激、確認彼此安全，暫停深度討論。
              </p>
              {(journal.action_for_partner || journal.advice_for_partner) ? (
                <div className="mt-4 rounded-[1.2rem] border border-border bg-white/72 p-4 shadow-glass-inset">
                  {journal.action_for_partner ? (
                    <p className="text-sm leading-7 text-destructive">
                      <span className="mr-2 font-bold">行動</span>
                      {journal.action_for_partner}
                    </p>
                  ) : null}
                  {journal.advice_for_partner ? (
                    <p className="mt-2 text-sm leading-7 text-destructive">
                      <span className="mr-2 font-bold">建議</span>
                      {journal.advice_for_partner}
                    </p>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : (
            <div className="grid gap-5 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
              {journal.card_recommendation ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.24em] text-primary/80">
                    <Sparkles className="h-4 w-4" aria-hidden />
                    暖心小行動
                  </div>
                  <ActionCard cardKey={journal.card_recommendation} />
                </div>
              ) : null}

              <div className="space-y-4">
                {journal.action_for_partner ? (
                  <div className={`rounded-[1.4rem] border p-4 shadow-soft ${variant === 'reading-room' ? 'border-accent/12 bg-accent/[0.065]' : 'border-accent/16 bg-accent/8'}`}>
                    <h4 className="flex items-center gap-2.5 text-sm font-bold text-accent">
                      <HeartHandshake className="h-4 w-4" aria-hidden />
                      具體做法
                    </h4>
                    <p className="mt-2 text-sm leading-7 text-foreground/90">{journal.action_for_partner}</p>
                  </div>
                ) : null}

                {journal.advice_for_partner ? (
                  <div className={`rounded-[1.4rem] border p-4 shadow-soft ${variant === 'reading-room' ? 'border-primary/10 bg-primary/[0.06]' : 'border-primary/14 bg-primary/8'}`}>
                    <h4 className="flex items-center gap-2.5 text-sm font-bold text-primary">
                      <Lightbulb className="h-4 w-4" aria-hidden />
                      理解視角
                    </h4>
                    <p className="mt-2 text-sm leading-7 text-foreground/90">{journal.advice_for_partner}</p>
                  </div>
                ) : null}
              </div>
            </div>
          )}
        </div>
      </article>
    </SafetyTierGate>
  );
}
