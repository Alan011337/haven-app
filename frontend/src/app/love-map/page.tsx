'use client';

import dynamic from 'next/dynamic';
import { LoveMapShell } from './LoveMapPrimitives';
import LoveMapSkeleton from './LoveMapSkeleton';

const LoveMapPageContent = dynamic(
  () => import('./LoveMapPageContent').then((m) => m.default),
  {
    loading: () => <LoveMapSkeleton />,
  },
);

export default function LoveMapPage() {
  return (
    <LoveMapShell>
      <LoveMapPageContent />
    </LoveMapShell>
  );
}
