import type { MediationStatusPublic, RepairFlowStatusPublic } from '@/services/api-client';

export type MediationViewState =
  | 'loading'
  | 'repair_start'
  | 'repair_missing_session'
  | 'repair_active'
  | 'classic_no_session'
  | 'classic_answering'
  | 'classic_waiting_partner'
  | 'classic_completed';

export function resolveMediationViewState(params: {
  repairFlowEnabled: boolean;
  loading: boolean;
  status: MediationStatusPublic | null | undefined;
  repairSessionId: string | null;
  repairStatusLoading: boolean;
  repairStatus: RepairFlowStatusPublic | null | undefined;
}): MediationViewState {
  const {
    repairFlowEnabled,
    loading,
    status,
    repairSessionId,
    repairStatusLoading,
    repairStatus,
  } = params;

  if ((repairFlowEnabled && repairStatusLoading) || (!repairFlowEnabled && (loading || !status))) {
    return 'loading';
  }

  if (repairFlowEnabled) {
    if (!repairSessionId) return 'repair_start';
    if (!repairStatus) return 'repair_missing_session';
    return 'repair_active';
  }

  if (!status?.in_mediation) return 'classic_no_session';
  if (!status.my_answered) return 'classic_answering';
  if (!status.partner_answered) return 'classic_waiting_partner';
  return 'classic_completed';
}

