'use client';

import dynamic from 'next/dynamic';
import MediationSkeleton from './MediationSkeleton';
import { MediationShell } from './MediationPrimitives';

const MediationPageContent = dynamic(
  () => import('./MediationPageContent').then((m) => m.default),
  {
    loading: () => <MediationSkeleton />,
  },
);

export default function MediationPage() {
  return (
    <MediationShell>
      <MediationPageContent />
    </MediationShell>
  );
}
