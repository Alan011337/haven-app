import { SettingsShell } from '@/app/settings/SettingsPrimitives';
import { SettingsSkeleton } from '@/app/settings/SettingsSkeleton';

export default function SettingsLoading() {
  return (
    <SettingsShell>
      <SettingsSkeleton />
    </SettingsShell>
  );
}
