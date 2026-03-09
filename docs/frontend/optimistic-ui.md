# Optimistic UI Guidance (UX-SPEED-01)

## Pattern
- Apply optimistic local state update immediately on mutation.
- Keep previous snapshot for rollback.
- On backend failure: restore snapshot + toast + background retry.

## Recommended Flow
1. `onMutate`: snapshot current state.
2. optimistic patch to UI list/detail.
3. submit network request.
4. `onError`: rollback snapshot + enqueue retry task.
5. `onSettled`: refetch canonical server state.

## Haven-specific Notes
- Journal submit: optimistic append with `status=pending_analysis`.
- Card respond: optimistic response bubble with `status=sending`.
- Partner sync surfaces should show "sync delayed" when fallback mode active.

## Implementation Hook
- Utility module: `frontend/src/lib/optimistic-ui.ts` (`applyOptimisticPatch`, `rollbackOptimisticPatch`)
- Key mutations: journal submit (JournalInput), card draw/respond (DailyCard, useDeckRoom) use local state + retry; shared optimistic wrapper can be applied to additional mutations as needed.
