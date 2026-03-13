'use client';

import { useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/use-auth';
import {
  readDailySyncStatusSnapshot,
  writeDailySyncStatusSnapshot,
} from '@/lib/home-fast-snapshot';
import { HOME_OPTIONAL_DATA_TIMEOUT_MS } from '@/lib/home-performance';
import { queryKeys } from '@/lib/query-keys';
import { fetchDailySyncStatus } from '@/services/api-client';

export function useDailySyncStatus(enabled = true) {
  const { user, isLoading } = useAuth();
  const userId = user?.id ? String(user.id) : null;
  const placeholderData = useMemo(() => {
    if (!userId) return undefined;
    return readDailySyncStatusSnapshot(userId) ?? undefined;
  }, [userId]);

  const query = useQuery({
    queryKey: queryKeys.dailySyncStatus(),
    queryFn: () => fetchDailySyncStatus({ timeout: HOME_OPTIONAL_DATA_TIMEOUT_MS }),
    enabled: enabled && !isLoading && !!user,
    placeholderData,
    retry: false,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!userId || !query.data || query.isPlaceholderData) return;
    writeDailySyncStatusSnapshot(userId, query.data);
  }, [userId, query.data, query.isPlaceholderData]);

  return query;
}
