'use client';

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import { fetchBlueprint } from '@/services/api-client';

export function useBlueprint() {
  return useQuery({
    queryKey: queryKeys.blueprint(),
    queryFn: fetchBlueprint,
    staleTime: 60_000,
  });
}
