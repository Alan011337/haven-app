import type { AxiosRequestConfig } from 'axios';
import { apiGet, apiPost } from '@/services/api-transport';

export interface AppreciationPublic {
  id: number;
  body_text: string;
  created_at: string;
  is_mine: boolean;
}

export const fetchAppreciations = async (params?: {
  limit?: number;
  offset?: number;
  from_date?: string;
  to_date?: string;
}, config?: AxiosRequestConfig): Promise<AppreciationPublic[]> => {
  return apiGet<AppreciationPublic[]>('/appreciations', { ...config, params });
};

export const createAppreciation = async (bodyText: string): Promise<AppreciationPublic> => {
  return apiPost<AppreciationPublic>('/appreciations', { body_text: bodyText });
};
