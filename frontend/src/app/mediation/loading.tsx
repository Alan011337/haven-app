import MediationSkeleton from './MediationSkeleton';
import { MediationShell } from './MediationPrimitives';

export default function Loading() {
  return (
    <MediationShell>
      <MediationSkeleton />
    </MediationShell>
  );
}
