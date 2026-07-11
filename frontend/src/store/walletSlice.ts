import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { walletService } from "../services/api";

interface Wallet {
  id: string;
  currency: string;
  balance: string;
  status: string;
  label: string | null;
  created_at: string;
}

interface Transaction {
  id: string;
  transaction_type: string;
  amount: string;
  currency: string;
  balance_before: string;
  balance_after: string;
  description: string | null;
  created_at: string;
}

interface WalletState {
  wallets: Wallet[];
  transactions: Transaction[];
  transactionTotal: number;
  transactionPage: number;
  transactionPages: number;
  isLoading: boolean;
  error: string | null;
}

const initialState: WalletState = {
  wallets: [],
  transactions: [],
  transactionTotal: 0,
  transactionPage: 1,
  transactionPages: 1,
  isLoading: false,
  error: null,
};

export const fetchWalletsThunk = createAsyncThunk(
  "wallet/fetchAll",
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await walletService.listWallets();
      return data;
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: { message?: string } } } };
      return rejectWithValue(error.response?.data?.error?.message || "Failed to load wallets");
    }
  }
);

export const createWalletThunk = createAsyncThunk(
  "wallet/create",
  async ({ currency, label }: { currency: string; label?: string }, { rejectWithValue }) => {
    try {
      const { data } = await walletService.createWallet(currency, label);
      return data;
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: { message?: string } } } };
      return rejectWithValue(error.response?.data?.error?.message || "Failed to create wallet");
    }
  }
);

export const creditWalletThunk = createAsyncThunk(
  "wallet/credit",
  async (
    { walletId, amount, description }: { walletId: string; amount: string; description?: string },
    { rejectWithValue }
  ) => {
    try {
      const { data } = await walletService.credit(walletId, amount, description);
      return data;
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: { message?: string } } } };
      return rejectWithValue(error.response?.data?.error?.message || "Credit failed");
    }
  }
);

export const fetchTransactionsThunk = createAsyncThunk(
  "wallet/fetchTransactions",
  async (
    { walletId, page, pageSize }: { walletId: string; page?: number; pageSize?: number },
    { rejectWithValue }
  ) => {
    try {
      const { data } = await walletService.getTransactions(walletId, page, pageSize);
      return data;
    } catch {
      return rejectWithValue("Failed to load transactions");
    }
  }
);

const walletSlice = createSlice({
  name: "wallet",
  initialState,
  reducers: {
    clearWalletError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchWalletsThunk.pending, (state) => { state.isLoading = true; })
      .addCase(fetchWalletsThunk.fulfilled, (state, action) => {
        state.isLoading = false;
        state.wallets = action.payload;
      })
      .addCase(fetchWalletsThunk.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      .addCase(createWalletThunk.fulfilled, (state, action) => {
        state.wallets.push(action.payload);
      })
      .addCase(createWalletThunk.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      .addCase(creditWalletThunk.fulfilled, (state, action) => {
        const idx = state.wallets.findIndex((w) => w.id === action.payload.id);
        if (idx !== -1) state.wallets[idx] = action.payload;
      })
      .addCase(creditWalletThunk.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      .addCase(fetchTransactionsThunk.pending, (state) => { state.isLoading = true; })
      .addCase(fetchTransactionsThunk.fulfilled, (state, action) => {
        state.isLoading = false;
        state.transactions = action.payload.items;
        state.transactionTotal = action.payload.total;
        state.transactionPage = action.payload.page;
        state.transactionPages = action.payload.pages;
      })
      .addCase(fetchTransactionsThunk.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });
  },
});

export const { clearWalletError } = walletSlice.actions;
export default walletSlice.reducer;
