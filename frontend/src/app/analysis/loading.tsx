import { AnalysisShell } from '@/app/analysis/AnalysisPrimitives';
import { AnalysisSkeleton } from '@/app/analysis/AnalysisSkeleton';

export default function AnalysisLoading() {
  return (
    <AnalysisShell>
      <AnalysisSkeleton />
    </AnalysisShell>
  );
}
