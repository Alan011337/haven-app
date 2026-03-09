/**
 * P2-F: Detect network/offline failure (so we can enqueue for replay).
 */

import { isAxiosError } from 'axios';

export function isNetworkError(error: unknown): boolean {
  if (isAxiosError(error)) {
    if (!error.response) return true;
    const status = error.response.status;
    if (status >= 500 && status < 600) return true;
  }
  if (error instanceof TypeError && error.message === 'Failed to fetch') return true;
  return false;
}
