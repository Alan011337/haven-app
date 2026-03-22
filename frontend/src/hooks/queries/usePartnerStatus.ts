'use client';

import { useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/use-auth';
import { readPartnerStatusSnapshot, writePartnerStatusSnapshot } from '@/lib/home-fast-snapshot';
import { HOME_STATUS_TIMEOUT_MS } from '@/lib/home-performance';
import { queryKeys } from '@/lib/query-keys';
import { DEFAULT_PARTNER_STATUS, fetchPartnerStatus } from '@/services/api-client';

export function usePartnerStatus(enabled = true) {
  const { user, isLoading } = useAuth();
  const userId = user?.id ? String(user.id) : null;
  const placeholderData = useMemo(() => {
    if (!userId) return DEFAULT_PARTNER_STATUS;
    return readPartnerStatusSnapshot(userId) ?? DEFAULT_PARTNER_STATUS;
  }, [userId]);

  const query = useQuery({
    queryKey: queryKeys.partnerStatus(),
    queryFn: () => fetchPartnerStatus({ timeout: HOME_STATUS_TIMEOUT_MS }),
    enabled: !isLoading && !!user && enabled,
    staleTime: 30_000,
    placeholderData,
    retry: false,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (!userId || !query.data || query.isPlaceholderData) return;
    if (
      query.data.has_partner ||
      query.data.latest_journal_at !== null ||
      query.data.current_score !== 0 ||
      query.data.unread_notification_count !== 0
    ) {
      writePartnerStatusSnapshot(userId, query.data);
    }
  }, [userId, query.data, query.isPlaceholderData]);

  return query;
}
