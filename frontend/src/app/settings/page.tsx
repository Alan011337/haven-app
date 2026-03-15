'use client';

import dynamic from 'next/dynamic';
import { SettingsShell } from '@/app/settings/SettingsPrimitives';
import { SettingsSkeleton } from '@/app/settings/SettingsSkeleton';

const SettingsPageBody = dynamic(
  () => import('./SettingsPageBody'),
  {
    ssr: false,
    loading: () => <SettingsSkeleton />,
  },
);

export default function SettingsPage() {
  return (
    <SettingsShell>
      <SettingsPageBody />
    </SettingsShell>
  );
}
