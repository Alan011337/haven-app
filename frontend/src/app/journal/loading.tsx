import { JournalShell, JournalStatePanel } from '@/app/journal/JournalPrimitives';

export default function JournalLoading() {
  return (
    <JournalShell>
      <JournalStatePanel
        eyebrow="Journal Route"
        title="正在把這一頁攤開"
        description="Journal Studio 正在載入你的書房、草稿與可分享設定。"
      />
    </JournalShell>
  );
}
