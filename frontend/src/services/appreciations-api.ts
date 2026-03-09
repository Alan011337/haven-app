import { apiGet, apiPost } from '@/services/api-transport';

export interface AppreciationPublic {
  id: number;
  body_text: string;
  created_at: string;
}

export const fetchAppreciations = async (params?: {
  limit?: number;
  offset?: number;
  from_date?: string;
  to_date?: string;
}): Promise<AppreciationPublic[]> => {
  return apiGet<AppreciationPublic[]>('/appreciations', { params });
};

export const createAppreciation = async (bodyText: string): Promise<AppreciationPublic> => {
  return apiPost<AppreciationPublic>('/appreciations', { body_text: bodyText });
};
