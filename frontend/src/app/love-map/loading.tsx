import LoveMapSkeleton from './LoveMapSkeleton';
import { LoveMapShell } from './LoveMapPrimitives';

export default function Loading() {
  return (
    <LoveMapShell>
      <LoveMapSkeleton />
    </LoveMapShell>
  );
}
