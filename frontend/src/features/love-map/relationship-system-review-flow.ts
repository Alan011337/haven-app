/**
 * Review-flow view model for the Relationship System pending-review surface.
 *
 * Relationship Compass suggestions and Shared Future suggestions both land in
 * the same page (/love-map), but each lives inside its own domain section.
 * This helper turns the raw pending counts into an ordered, anchor-ready
 * model that the UI can use to:
 *
 *   - show a single "start reviewing" CTA that always points at the right
 *     place even as the user moves through items
 *   - render a calm "completed" state when nothing remains
 *   - render an inline "continue next" panel after a suggestion is handled
 *     and another pending item remains (possibly in a different section)
 *
 * The helper is deliberately tiny: it does not own any state, it does not
 * trigger any mutations, and it never looks at the suggestion bodies. The
 * caller feeds in counts (or empty-defaulted counts) and the helper derives
 * stable anchors + ordering.
 *
 * Ordering rule (per the Relationship System V1 review-flow batch):
 *   1. Relationship Compass suggestions  (section = identity)
 *   2. Shared Future suggestions         (section = future)
 *   3. Shared Future refinements         (section = future)
 *
 * The `firstTarget` is the next unreviewed target in that order. After an
 * accept/dismiss call round-trips and the pending counts update, the first
 * target will naturally advance to whatever kind still has items — no
 * per-suggestion id tracking required.
 */

export type ReviewFlowKind =
  | 'relationship_compass'
  | 'shared_future'
  | 'shared_future_refinement';

export type ReviewFlowSection = 'identity' | 'future';

export interface ReviewFlowInput {
  hasPartner: boolean;
  compassPendingCount: number;
  sharedFuturePendingCount: number;
  sharedFutureRefinementPendingCount: number;
}

export interface ReviewFlowTarget {
  kind: ReviewFlowKind;
  /** Short Traditional Chinese label used inside copy, e.g. "Compass 建議更新". */
  label: string;
  /** Which domain section this target belongs to. */
  section: ReviewFlowSection;
  /** DOM id on the landing element, without the leading '#'. */
  anchorId: string;
  /** Anchor href used by <a href=...> — always '#' + anchorId. */
  href: string;
  /** How many pending items of this kind remain (always >= 1 for a real target). */
  count: number;
}

export interface ReviewFlowModel {
  /** Total pending items across all kinds. */
  totalPending: number;
  /**
   * True when hasPartner is true AND there are zero pending items. A paired
   * couple with nothing to review gets the calm "completed" state; an
   * un-paired visitor never sees "complete" (that would be confusing — they
   * haven't reached the review surface yet).
   */
  isComplete: boolean;
  /** Next review target (first in ordering). Null when nothing is pending. */
  firstTarget: ReviewFlowTarget | null;
  /**
   * Per-kind breakdown in canonical order. Only kinds with count > 0 are
   * included, so the array length matches the number of distinct pending
   * kinds. Useful if the UI ever wants to render "Compass 1 則 · Future 2 則"
   * style detail — not used by the minimum review surface, but kept cheap.
   */
  targets: ReviewFlowTarget[];
}

/**
 * Stable anchor id for the landing wrapper of a given review-flow kind.
 * Exported so the page can set `<div id={buildReviewFlowAnchorId('relationship_compass')}>`
 * on the first pending card of each kind.
 */
export function buildReviewFlowAnchorId(kind: ReviewFlowKind): string {
  if (kind === 'relationship_compass') return 'pending-review-compass';
  if (kind === 'shared_future') return 'pending-review-future';
  // Refinements piggyback on the Future section anchor since they already
  // render inline next to their target wishlist item — adding a third stable
  // anchor would create a confusing third landing spot.
  return 'future';
}

function labelForKind(kind: ReviewFlowKind): string {
  if (kind === 'relationship_compass') return 'Compass 建議更新';
  if (kind === 'shared_future') return 'Shared Future 建議更新';
  return 'Shared Future 補上建議';
}

function sectionForKind(kind: ReviewFlowKind): ReviewFlowSection {
  return kind === 'relationship_compass' ? 'identity' : 'future';
}

function safeCount(value: number): number {
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
}

function buildTarget(kind: ReviewFlowKind, count: number): ReviewFlowTarget {
  const anchorId = buildReviewFlowAnchorId(kind);
  return {
    kind,
    label: labelForKind(kind),
    section: sectionForKind(kind),
    anchorId,
    href: `#${anchorId}`,
    count,
  };
}

/**
 * Build the review-flow view model from raw pending counts.
 *
 * Contract:
 *   - When hasPartner is false, everything is zeroed and isComplete is false
 *     (the un-paired page does not expose a review surface to begin with).
 *   - When hasPartner is true and all counts are zero, isComplete is true.
 *   - When hasPartner is true and any count > 0, totalPending = sum of counts
 *     and firstTarget is the first non-empty kind in canonical order.
 *   - NaN / negative / non-integer counts are floored to 0 (matches the
 *     safety contract already used in relationship-system-home.ts).
 */
export function buildRelationshipSystemReviewFlow(
  input: ReviewFlowInput,
): ReviewFlowModel {
  if (!input.hasPartner) {
    return {
      totalPending: 0,
      isComplete: false,
      firstTarget: null,
      targets: [],
    };
  }

  const compassCount = safeCount(input.compassPendingCount);
  const sharedFutureCount = safeCount(input.sharedFuturePendingCount);
  const refinementCount = safeCount(input.sharedFutureRefinementPendingCount);

  const targets: ReviewFlowTarget[] = [];
  if (compassCount > 0) targets.push(buildTarget('relationship_compass', compassCount));
  if (sharedFutureCount > 0) targets.push(buildTarget('shared_future', sharedFutureCount));
  if (refinementCount > 0) targets.push(buildTarget('shared_future_refinement', refinementCount));

  const totalPending = compassCount + sharedFutureCount + refinementCount;
  return {
    totalPending,
    isComplete: totalPending === 0,
    firstTarget: targets[0] ?? null,
    targets,
  };
}

/**
 * Copy helpers for the review-flow surface. Kept alongside the view model so
 * all the "what users read about review state" text lives in one file and
 * the UI stays a thin renderer.
 */
export interface ReviewFlowPanelCopy {
  title: string;
  description: string;
  ctaLabel?: string;
  ctaHref?: string;
}

export function buildReviewFlowPendingCopy(model: ReviewFlowModel): ReviewFlowPanelCopy {
  const href = model.firstTarget?.href;
  return {
    title: '待審核的 Haven 建議',
    description: `Haven 只會提出建議；接受後才會寫入共同真相。目前有 ${model.totalPending} 則更新等你決定。`,
    ctaLabel: href ? '從第一則開始審核' : undefined,
    ctaHref: href,
  };
}

export function buildReviewFlowCompleteCopy(): ReviewFlowPanelCopy {
  return {
    title: '目前沒有待審核的更新',
    description: '你們已經把目前的 Haven 建議處理完了。之後有足夠清楚的片段時，Haven 會再提出新的建議。',
  };
}

export function buildReviewFlowContinueCopy(model: ReviewFlowModel): ReviewFlowPanelCopy {
  const href = model.firstTarget?.href;
  return {
    title: '繼續審核下一則',
    description: `還有 ${model.totalPending} 則 Haven 建議等你決定。`,
    ctaLabel: href ? '繼續審核下一則' : undefined,
    ctaHref: href,
  };
}

export function buildReviewFlowAllDoneCopy(): ReviewFlowPanelCopy {
  return {
    title: '所有待審核建議都已處理完',
    description: '已保存內容沒有被自動改動，只有接受的建議會寫入。',
  };
}
