'use client';

import Link from 'next/link';
import { ShieldCheck } from 'lucide-react';
import PartnerSettings from '@/components/features/PartnerSettings';
import OnboardingConsentCard from '@/components/features/OnboardingConsentCard';
import RelationshipRadarCard from '@/components/features/RelationshipRadarCard';
import CooldownSOSCard from '@/components/features/CooldownSOSCard';
import WeeklyReportCard from '@/components/features/WeeklyReportCard';

export default function SettingsPageBody() {
  return (
    <>
      <OnboardingConsentCard />
      <RelationshipRadarCard />
      <CooldownSOSCard />
      <WeeklyReportCard />
      <div className="flex-1 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <PartnerSettings />
      </div>
      <div className="max-w-4xl mx-auto w-full mt-8 space-y-3 animate-page-enter-delay-2">
        <div className="section-divider mb-4" />
        <p className="text-caption text-muted-foreground/80 leading-relaxed">
          您可隨時匯出或刪除自己的資料；若需伴侶一併刪除，請伴侶登入後於設定中執行刪除。
        </p>
        <Link
          href="/admin/moderation"
          className="inline-flex items-center gap-2 text-caption text-muted-foreground hover:text-primary transition-colors duration-haven ease-haven"
        >
          <span className="icon-badge !w-6 !h-6" aria-hidden><ShieldCheck className="w-3 h-3" /></span>
          內容審核（管理員）
        </Link>
      </div>
    </>
  );
}
