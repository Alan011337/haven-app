import JournalPageContent from '@/app/journal/JournalPageContent';
import { JournalShell } from '@/app/journal/JournalPrimitives';

export default function JournalPage() {
  return (
    <JournalShell>
      <JournalPageContent />
    </JournalShell>
  );
}
