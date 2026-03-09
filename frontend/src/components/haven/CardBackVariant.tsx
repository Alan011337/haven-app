/**
 * P2-A1: Deck-specific card back (color/pattern/watermark).
 * Single source: DECK_META_MAP cardBack. No animation.
 * Uses CardBackBase for shared radius/shadow; this component only handles deck variant.
 */

import { CardBackBase } from '@/components/haven/CardBackBase';
import type { DeckMeta } from '@/lib/deck-meta';

interface CardBackVariantProps {
  deck: DeckMeta | null;
  /** Default when deck is null */
  defaultGradient?: string;
  defaultBorderClass?: string;
  /** Inner content (e.g. "Click to Reveal" + icon) */
  children?: React.ReactNode;
}

/** Fallback when deck is null; semantic token only (ART-DIRECTION). */
const DEFAULT_GRADIENT = 'bg-primary';
const DEFAULT_BORDER = 'border-white/30';

export function CardBackVariant({
  deck,
  defaultGradient = DEFAULT_GRADIENT,
  defaultBorderClass = DEFAULT_BORDER,
  children,
}: CardBackVariantProps) {
  const gradient = deck?.cardBack?.gradient ?? defaultGradient;
  const borderClass = deck?.cardBack?.borderClass ?? defaultBorderClass;
  const patternKey = deck?.cardBack?.patternKey ?? undefined;
  const watermarkKey = deck?.cardBack?.watermarkIconKey ?? 'default';
  const Icon = deck?.Icon;
  const showWatermark = watermarkKey === 'default' && Icon;

  return (
    <div
      className="absolute inset-0 z-[2]"
      style={{
        backfaceVisibility: 'hidden',
        WebkitBackfaceVisibility: 'hidden',
        transform: 'rotateY(0deg)',
      }}
    >
      <CardBackBase className="h-full w-full">
        <div
          className={`h-full w-full rounded-card ${gradient} flex items-center justify-center text-white p-4 ${patternKey ?? ''}`}
        >
          <div className={`border-2 ${borderClass} w-full h-full rounded-card flex items-center justify-center border-dashed min-h-0`}>
            {children ?? (
              <div className="text-center">
                {showWatermark ? (
                  <Icon className="w-10 h-10 mx-auto mb-2 opacity-90" strokeWidth={1.8} aria-hidden />
                ) : (
                  <div className="text-2xl mb-1" aria-hidden>🔮</div>
                )}
                <p className="text-xs font-art font-medium tracking-widest uppercase opacity-90">Click to Reveal</p>
              </div>
            )}
          </div>
        </div>
      </CardBackBase>
    </div>
  );
}
