import { JournalShell, JournalStatePanel } from '@/app/journal/JournalPrimitives';

export default function JournalLoading() {
  return (
    <JournalShell>
      <JournalStatePanel
        eyebrow="書房載入中"
        title="正在把這一頁攤開"
        description="Journal 書房正在載入你的頁面、草稿與可分享設定。"
      />
    </JournalShell>
  );
}
