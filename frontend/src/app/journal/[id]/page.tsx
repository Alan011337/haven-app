import JournalPageContent from '@/app/journal/JournalPageContent';
import { JournalShell } from '@/app/journal/JournalPrimitives';

interface JournalDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function JournalDetailPage({ params }: JournalDetailPageProps) {
  const { id } = await params;

  return (
    <JournalShell>
      <JournalPageContent journalId={id} />
    </JournalShell>
  );
}
