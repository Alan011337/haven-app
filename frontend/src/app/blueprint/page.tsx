'use client';

import dynamic from 'next/dynamic';
import BlueprintSkeleton from './BlueprintSkeleton';
import { BlueprintShell } from './BlueprintPrimitives';

const BlueprintPageContent = dynamic(
  () => import('./BlueprintPageContent').then((m) => m.default),
  {
    loading: () => <BlueprintSkeleton />,
  },
);

export default function BlueprintPage() {
  return (
    <BlueprintShell>
      <BlueprintPageContent />
    </BlueprintShell>
  );
}
