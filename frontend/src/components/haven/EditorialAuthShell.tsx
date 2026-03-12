import type { ReactNode } from 'react';
import { Heart, Sparkles } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';

type AuthHighlight = {
  value: string;
  label: string;
  description: string;
};

interface EditorialAuthShellProps {
  panelHeadingId: string;
  panelEyebrow: string;
  panelTitle: string;
  panelSubtitle: string;
  storyEyebrow: string;
  storyTitle: string;
  storyBody: string;
  storyQuote: string;
  storyCredit: string;
  highlights: AuthHighlight[];
  children: ReactNode;
  callout?: ReactNode;
  footer?: ReactNode;
}

export function EditorialAuthShell({
  panelHeadingId,
  panelEyebrow,
  panelTitle,
  panelSubtitle,
  storyEyebrow,
  storyTitle,
  storyBody,
  storyQuote,
  storyCredit,
  highlights,
  children,
  callout,
  footer,
}: EditorialAuthShellProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-auth-gradient">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(214,168,124,0.14),transparent_28%),radial-gradient(circle_at_82%_18%,rgba(137,154,141,0.16),transparent_22%),linear-gradient(135deg,rgba(255,255,255,0.46),transparent_42%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-y-0 left-0 hidden w-[46%] bg-[linear-gradient(180deg,rgba(255,255,255,0.34),rgba(255,255,255,0.08))] lg:block"
        aria-hidden
      />
      <div className="pointer-events-none absolute left-[8%] top-20 h-72 w-72 rounded-full bg-primary/10 blur-hero-orb animate-float" aria-hidden />
      <div className="pointer-events-none absolute bottom-16 right-[10%] h-56 w-56 rounded-full bg-accent/12 blur-hero-orb-sm animate-float-delayed" aria-hidden />
      <div className="pointer-events-none absolute left-[55%] top-[28%] h-36 w-36 rounded-full bg-primary/7 blur-hero-orb-sm animate-float-slow" aria-hidden />

      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-7xl items-center px-4 py-8 sm:px-6 lg:px-10">
        <div className="grid w-full gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(420px,520px)] xl:gap-10">
          <section className="relative overflow-hidden rounded-[2rem] border border-white/45 bg-[linear-gradient(135deg,rgba(255,252,248,0.9)_0%,rgba(250,243,234,0.78)_52%,rgba(230,237,232,0.74)_100%)] p-7 shadow-lift lg:p-10 xl:p-12">
            <div className="absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" aria-hidden />
            <div className="absolute bottom-0 right-0 h-48 w-48 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.45),transparent_70%)]" aria-hidden />

            <div className="flex h-full flex-col justify-between gap-8">
              <div className="space-y-6">
                <div className="inline-flex items-center gap-3 rounded-full border border-primary/12 bg-white/70 px-4 py-2 shadow-soft backdrop-blur-md">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-satin-button">
                    <Heart className="h-4 w-4 fill-current" aria-hidden />
                  </div>
                  <div>
                    <p className="font-art text-lg tracking-[0.16em] text-foreground">Haven</p>
                    <p className="text-[0.68rem] uppercase tracking-[0.28em] text-muted-foreground">Couple Journal</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <p className="text-[0.72rem] uppercase tracking-[0.34em] text-primary/80">{storyEyebrow}</p>
                  <h1 className="max-w-xl font-art text-4xl leading-[1.05] text-foreground sm:text-5xl xl:text-[4rem]">
                    {storyTitle}
                  </h1>
                  <p className="max-w-lg text-base leading-8 text-muted-foreground sm:text-lg">
                    {storyBody}
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  {highlights.map((highlight) => (
                    <div
                      key={highlight.label}
                      className="rounded-[1.4rem] border border-white/50 bg-white/72 p-4 shadow-soft backdrop-blur-md"
                    >
                      <p className="font-art text-2xl text-foreground">{highlight.value}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.28em] text-primary/75">{highlight.label}</p>
                      <p className="mt-3 text-sm leading-6 text-muted-foreground">{highlight.description}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-[1.7rem] border border-primary/12 bg-[linear-gradient(135deg,rgba(255,255,255,0.62),rgba(255,255,255,0.32))] p-5 shadow-soft backdrop-blur-lg">
                <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-[0.68rem] uppercase tracking-[0.28em] text-primary/85">
                  <Sparkles className="h-3.5 w-3.5" aria-hidden />
                  Quiet Luxury Ritual
                </div>
                <blockquote className="font-art text-2xl leading-9 text-foreground">
                  “{storyQuote}”
                </blockquote>
                <p className="mt-4 text-sm tracking-[0.18em] text-muted-foreground uppercase">{storyCredit}</p>
              </div>
            </div>
          </section>

          <div className="flex items-center lg:justify-end">
            <GlassCard className="w-full max-w-xl p-7 md:p-8 lg:p-10">
              <div className="space-y-6">
                <div className="space-y-3">
                  <p className="text-[0.72rem] uppercase tracking-[0.34em] text-primary/80">{panelEyebrow}</p>
                  <div className="space-y-2">
                    <h2 id={panelHeadingId} className="font-art text-3xl leading-tight text-foreground sm:text-[2.15rem]">
                      {panelTitle}
                    </h2>
                    <p className="text-sm leading-7 text-muted-foreground sm:text-base">{panelSubtitle}</p>
                  </div>
                </div>

                {callout}

                {children}

                {footer ? (
                  <div className="pt-2 text-sm text-muted-foreground">
                    <div className="section-divider mb-5" />
                    {footer}
                  </div>
                ) : null}
              </div>
            </GlassCard>
          </div>
        </div>
      </div>
    </div>
  );
}
