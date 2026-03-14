import MemorySkeleton from './MemorySkeleton';
import { MemoryShell } from './MemoryPrimitives';

export default function MemoryLoading() {
  return (
    <MemoryShell>
      <MemorySkeleton />
    </MemoryShell>
  );
}
