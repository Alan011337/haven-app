import type { AxiosRequestConfig } from 'axios';
import api from '@/lib/http-client';
import { logClientError } from '../lib/safe-error-log';

export async function apiGet<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await api.get<T>(url, config);
  return response.data;
}

export async function apiPost<T>(
  url: string,
  payload?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const response = await api.post<T>(url, payload, config);
  return response.data;
}

export async function apiPut<T>(
  url: string,
  payload?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const response = await api.put<T>(url, payload, config);
  return response.data;
}

export async function apiDelete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await api.delete<T>(url, config);
  return response.data;
}

export async function getWithFallback<T>({
  action,
  fallbackValue,
  errorTag,
}: {
  action: () => Promise<T>;
  fallbackValue: T;
  errorTag: string;
}): Promise<T> {
  try {
    return await action();
  } catch (error) {
    logClientError(errorTag, error);
    return fallbackValue;
  }
}
