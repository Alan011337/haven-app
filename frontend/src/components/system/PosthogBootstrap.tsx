'use client';

import { useEffect } from 'react';

import { initPosthogClient } from '@/lib/posthog';

export default function PosthogBootstrap(): null {
  useEffect(() => {
    void initPosthogClient();
  }, []);

  return null;
}

