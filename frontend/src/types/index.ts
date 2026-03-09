/**
 * Re-export shared domain types from haven-shared (P2-G).
 * Keeps @/types imports working; single source of truth in packages/haven-shared.
 */
export type { Journal, User, Card } from 'haven-shared';
export { CardCategory } from 'haven-shared';
