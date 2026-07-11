import apiClient from "./apiClient";

export interface LoginPayload { email: string; password: string; }
export interface RegisterPayload {
  email: string; password: string;
  first_name: string; last_name: string;
  default_currency?: string;
}
export interface TokenResponse {
  access_token: string; refresh_token: string;
  token_type: string; expires_in: number;
}

export const authService = {
  register: (data: RegisterPayload) => apiClient.post("/auth/register", data),
  login: (data: LoginPayload) => apiClient.post<TokenResponse>("/auth/login", data),
  logout: (refreshToken: string) => apiClient.post("/auth/logout", { refresh_token: refreshToken }),
  getProfile: () => apiClient.get("/users/me"),
  updateProfile: (data: Partial<{ first_name: string; last_name: string; default_currency: string }>) =>
    apiClient.patch("/users/me", data),
  uploadAvatar: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.post("/users/me/avatar", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

export const walletService = {
  listWallets: () => apiClient.get("/wallets"),

  createWallet: (currency: string, label?: string) =>
    apiClient.post("/wallets", { currency, label }),

  credit: (walletId: string, amount: string, description?: string) =>
    apiClient.post(`/wallets/${walletId}/credit`, { amount, description }),

  debit: (walletId: string, amount: string, description?: string) =>
    apiClient.post(`/wallets/${walletId}/debit`, { amount, description }),

  // sender_wallet_id is now required — user picks which wallet to send from
  transfer: (
    senderWalletId: string,
    recipientWalletId: string,
    amount: string,
    note?: string,
    idempotencyKey?: string
  ) =>
    apiClient.post(
      "/wallets/transfer",
      {
        sender_wallet_id: senderWalletId,
        recipient_wallet_id: recipientWalletId,
        amount,
        note,
      },
      idempotencyKey ? { headers: { "Idempotency-Key": idempotencyKey } } : undefined
    ),

  getTransactions: (walletId: string, page = 1, pageSize = 20, transactionType?: string) =>
    apiClient.get(`/wallets/${walletId}/transactions`, {
      params: { page, page_size: pageSize, transaction_type: transactionType },
    }),
};

export const exchangeRateService = {
  getRates: (base = "USD") => apiClient.get("/exchange-rates", { params: { base } }),
  getRate: (base: string, target: string) => apiClient.get(`/exchange-rates/${base}/${target}`),
};
