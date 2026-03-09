// frontend/src/components/ui/TarotCard.tsx
// P2-A: Card flip (MotionProvider + m) + deck-specific card back + unlock glow.
// Motion only in card-ritual; prefers-reduced-motion uses fade/switch (no 3D flip).

'use client';

import { m, useReducedMotion } from 'framer-motion';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { MotionProvider } from '@/components/features/card-ritual/MotionProvider';
import { CardBackVariant } from '@/components/haven/CardBackVariant';
import { getDeckMeta } from '@/lib/deck-meta';
import { useAppearanceStore } from '@/stores/useAppearanceStore';

interface TarotCardProps {
  cardName: string;
  /** Optional deck category for deck-specific card back (8 variants). */
  category?: string | null;
  /** P2-A5: When provided, show prev/next buttons (non-drag alternative for future swipe). */
  onPrev?: () => void;
  onNext?: () => void;
  /** When true, prev button is disabled. */
  hasPrev?: boolean;
  /** When true, next button is disabled. */
  hasNext?: boolean;
}

/** Fallback when no deck; semantic shadow only (ART-DIRECTION). */
const DEFAULT_GLOW = 'shadow-lift';

const FLIP_SPRING = { type: 'spring' as const, stiffness: 120, damping: 16 };

export default function TarotCard({ cardName, category, onPrev, onNext, hasPrev = false, hasNext = false }: TarotCardProps) {
  const [isFlipped, setIsFlipped] = useState(false);
  const reducedMotion = useReducedMotion();
  const cardGlowEnabled = useAppearanceStore((s) => s.cardGlowEnabled);
  const deckMeta = category ? getDeckMeta(category) : null;
  const glowClass = cardGlowEnabled ? (deckMeta?.cardBack?.glowClass ?? DEFAULT_GLOW) : '';

  return (
    <MotionProvider>
      <div className="relative w-full">
      {onPrev != null && (
          <button
            type="button"
            onClick={onPrev}
            disabled={hasPrev}
            className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 min-w-[24px] min-h-[24px] flex items-center justify-center rounded-full bg-card/90 backdrop-blur-sm border border-border shadow-soft text-muted-foreground hover:text-foreground hover:bg-primary/8 hover:shadow-lift disabled:opacity-50 disabled:pointer-events-none transition-all duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background -translate-x-1/2"
            aria-label="上一張"
          >
            <ChevronLeft className="w-5 h-5" aria-hidden />
          </button>
      )}
      {onNext != null && (
          <button
            type="button"
            onClick={onNext}
            disabled={hasNext}
            className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 min-w-[24px] min-h-[24px] flex items-center justify-center rounded-full bg-card/90 backdrop-blur-sm border border-border shadow-soft text-muted-foreground hover:text-foreground hover:bg-primary/8 hover:shadow-lift disabled:opacity-50 disabled:pointer-events-none transition-all duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background translate-x-1/2"
            aria-label="下一張"
          >
            <ChevronRight className="w-5 h-5" aria-hidden />
          </button>
      )}
      <m.div
        className="group w-full h-32 cursor-pointer"
        onClick={() => setIsFlipped(!isFlipped)}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setIsFlipped((f) => !f); } }}
        role="button"
        tabIndex={0}
        aria-label={isFlipped ? 'Hide card' : 'Reveal card'}
        style={{ perspective: reducedMotion ? undefined : '1000px' }}
        whileTap={{ scale: 0.98 }}
        transition={{ duration: 0.22 }}
      >
        <m.div
          className="relative w-full h-full rounded-xl shadow-soft"
          style={{ transformStyle: reducedMotion ? undefined : 'preserve-3d' }}
          animate={reducedMotion ? undefined : { rotateY: isFlipped ? 180 : 0 }}
          transition={reducedMotion ? undefined : FLIP_SPRING}
        >
        {/* Card face (back): CardBackVariant — deck color/pattern/watermark; reduced-motion: crossfade via opacity */}
        <div
          className="absolute inset-0 transition-opacity duration-200 ease-out"
          style={{
            opacity: reducedMotion ? (isFlipped ? 0 : 1) : 1,
            zIndex: reducedMotion && !isFlipped ? 2 : 1,
          }}
          aria-hidden={!!(reducedMotion && isFlipped)}
        >
          <CardBackVariant deck={deckMeta} />
        </div>

        {/* Back face (revealed): unlock glow via shadow */}
        <div
          className={`absolute inset-0 rounded-xl bg-card border-2 border-border flex items-center justify-center overflow-hidden shadow-lift ${glowClass}`}
          style={{
            backfaceVisibility: reducedMotion ? undefined : 'hidden',
            WebkitBackfaceVisibility: reducedMotion ? undefined : 'hidden',
            transform: reducedMotion ? undefined : 'rotateY(180deg)',
            opacity: reducedMotion ? (isFlipped ? 1 : 0) : undefined,
            transition: reducedMotion ? 'opacity 0.2s ease-out' : undefined,
            zIndex: reducedMotion && isFlipped ? 2 : 1,
            pointerEvents: reducedMotion && !isFlipped ? 'none' : undefined,
          }}
          aria-hidden={!!(reducedMotion && !isFlipped)}
        >
          <div className={`absolute top-0 left-0 w-full h-2 ${deckMeta ? `bg-gradient-to-r ${deckMeta.color}` : 'bg-primary'}`} aria-hidden />
          <div className="text-center p-4">
            <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider font-art">Today&apos;s Guidance</p>
            <h3 className="text-lg font-bold text-foreground font-art">{cardName}</h3>
          </div>
          <div className={`absolute bottom-[-10px] right-[-10px] w-12 h-12 rounded-full z-0 ${deckMeta ? deckMeta.badgeClass : 'bg-primary/10'}`} aria-hidden />
        </div>
        </m.div>
      </m.div>
      </div>
    </MotionProvider>
  );
}
