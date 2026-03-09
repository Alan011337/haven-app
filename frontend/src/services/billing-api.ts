import { apiPost } from '@/services/api-transport';

export interface CreateCheckoutSessionRequest {
  price_id?: string;
  success_url?: string;
  cancel_url?: string;
}

export interface CreateCheckoutSessionResult {
  url: string;
}

export const createCheckoutSession = async (
  payload?: CreateCheckoutSessionRequest
): Promise<CreateCheckoutSessionResult> => {
  return apiPost<CreateCheckoutSessionResult>('/billing/create-checkout-session', payload ?? {});
};
