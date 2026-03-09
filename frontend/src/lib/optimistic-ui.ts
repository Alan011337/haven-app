export interface OptimisticPatchResult<TState> {
  nextState: TState;
  rollbackState: TState;
}

/**
 * Minimal optimistic patch helper for local state stores.
 * Callers should persist rollbackState and restore on mutation failure.
 */
export function applyOptimisticPatch<TState>(
  currentState: TState,
  patcher: (state: TState) => TState,
): OptimisticPatchResult<TState> {
  return {
    nextState: patcher(currentState),
    rollbackState: currentState,
  };
}

export function rollbackOptimisticPatch<TState>(snapshot: TState): TState {
  return snapshot;
}
