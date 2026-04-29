import { api } from './client';

export interface MarketplaceListing {
  id: number;
  title: string;
  description: string | null;
  category: string | null;
  price_brl: number;
  preview_image_url: string | null;
  metrics: Record<string, unknown> | null;
  total_sales: number;
  rating_avg: number | null;
  rating_count: number;
  node_count: number;
}

export interface MarketplaceReview {
  id: number;
  rating: number;
  comment: string | null;
  created_at: string;
}

export interface MarketplaceListingDetail extends MarketplaceListing {
  blueprint_json: Record<string, unknown>;
  agent_json: Record<string, unknown> | null;
  already_bought: boolean;
  reviews: MarketplaceReview[];
}

export interface MyListing {
  id: number;
  title: string;
  category: string | null;
  price_brl: number;
  status: string;
  rejection_reason: string | null;
  total_sales: number;
  total_revenue_brl: number;
  rating_avg: number | null;
  rating_count: number;
  approved_at: string | null;
  created_at: string;
}

export interface BuyResult {
  ok: boolean;
  purchase_id: number;
  qr_code_image_url?: string;
  qr_code_text?: string;
  expires_at?: string;
  amount_brl?: number;
  already_purchased?: boolean;
  applied_blueprint_id?: number | null;
}

export interface ApplyResult {
  ok: boolean;
  blueprint_id?: number;
  slug?: string;
  redirect?: string;
  already_applied?: boolean;
}

export interface SaleRow {
  id: number;
  listing_id: number;
  amount_brl: number;
  fee_brl: number;
  payout_brl: number;
  purchased_at: string;
}

export interface SalesResponse {
  sales: SaleRow[];
  summary: {
    total_sales?: number;
    total_revenue_brl?: number;
  };
}

export interface CreateListingPayload {
  title: string;
  description: string;
  category?: string | null;
  price_brl: number;
  blueprint_json: Record<string, unknown>;
  agent_json?: Record<string, unknown> | null;
}

export const marketplaceApi = {
  list: (params?: { category?: string; price_max?: number; sort?: string }) => {
    const qs = new URLSearchParams();
    if (params?.category) qs.set('category', params.category);
    if (params?.price_max) qs.set('price_max', String(params.price_max));
    if (params?.sort) qs.set('sort', params.sort);
    const suffix = qs.toString() ? `?${qs}` : '';
    return api.get<{ listings: MarketplaceListing[] }>(`/saas/marketplace${suffix}`);
  },

  get: (id: number) =>
    api.get<MarketplaceListingDetail>(`/saas/marketplace/${id}`),

  buy: (id: number, provider: 'pix' | 'stripe' = 'pix') =>
    api.post<BuyResult>(`/saas/marketplace/${id}/buy`, { payment_provider: provider }),

  apply: (purchaseId: number) =>
    api.post<ApplyResult>(`/saas/marketplace/purchases/${purchaseId}/apply`, {}),

  review: (id: number, rating: number, comment?: string) =>
    api.post<{ ok: boolean }>(`/saas/marketplace/${id}/review`, { rating, comment }),

  myListings: () =>
    api.get<{ listings: MyListing[] }>(`/saas/marketplace/my/listings`),

  createListing: (payload: CreateListingPayload) =>
    api.post<{ ok: boolean; id: number; status: string; message: string }>(
      `/saas/marketplace/listings`,
      payload,
    ),

  mySales: () => api.get<SalesResponse>(`/saas/marketplace/my/sales`),
};
