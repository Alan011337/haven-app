import type { AxiosRequestConfig } from 'axios';
import { apiGet, apiPost } from '@/services/api-transport';
import { logClientError } from '@/lib/safe-error-log';

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

export const fetchAppreciationById = async (id: number, config?: AxiosRequestConfig): Promise<AppreciationPublic> => {
  try {
    return await apiGet<AppreciationPublic>(`/appreciations/${id}`, config);
  } catch (error) {
    logClientError('fetch-appreciation-detail-failed', error);
    throw error;
  }
};

export const createAppreciation = async (bodyText: string): Promise<AppreciationPublic> => {
  return apiPost<AppreciationPublic>('/appreciations', { body_text: bodyText });
};
