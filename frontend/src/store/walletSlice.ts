import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import { walletService } from "../services/api";

export interface Wallet {
  id: string;
  currency: string;
  balance: string;
  status: string;
  label: string | null;
  created_at: string;
}

export interface Transaction {
  id: string;
  wallet_id: string;
  transaction_type: string;
  amount: string;
  currency: string;
  balance_before: string;
  balance_after: string;
  description: string | null;
  created_at: string;
  // live-injected (SSE) transactions won't have all fields so make them optional
  reference?: string | null;
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

// ── Async thunks ───────────────────────────────────────────────────────────────

export const fetchWalletsThunk = createAsyncThunk(
  "wallet/fetchAll",
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await walletService.listWallets();
      return data as Wallet[];
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      return rejectWithValue(e.response?.data?.error?.message || "Failed to load wallets");
    }
  }
);

export const createWalletThunk = createAsyncThunk(
  "wallet/create",
  async ({ currency, label }: { currency: string; label?: string }, { rejectWithValue }) => {
    try {
      const { data } = await walletService.createWallet(currency, label);
      return data as Wallet;
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      return rejectWithValue(e.response?.data?.error?.message || "Failed to create wallet");
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
      return data as Wallet;
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      return rejectWithValue(e.response?.data?.error?.message || "Credit failed");
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

// ── Slice ──────────────────────────────────────────────────────────────────────

const walletSlice = createSlice({
  name: "wallet",
  initialState,
  reducers: {
    clearWalletError(state) {
      state.error = null;
    },

    /**
     * Called by SSE hook when a wallet_update event arrives.
     * Instantly updates the balance shown on the wallet card — no API call needed.
     */
    updateWalletBalance(
      state,
      action: PayloadAction<{ walletId: string; newBalance: string }>
    ) {
      const wallet = state.wallets.find((w) => w.id === action.payload.walletId);
      if (wallet) {
        wallet.balance = action.payload.newBalance;
      }
    },

    /**
     * Called by SSE hook to add a new transaction row at the TOP of the table
     * instantly when an operation completes — no page reload needed.
     */
    prependTransaction(
      state,
      action: PayloadAction<{
        wallet_id: string;
        transaction_type: string;
        amount: string;
        currency: string;
        new_balance: string;
        event_type: string;
        note: string | null;
      }>
    ) {
      const { wallet_id, transaction_type, amount, currency, new_balance, note } = action.payload;

      // Build a synthetic transaction row
      const syntheticTx: Transaction = {
        id: `live-${Date.now()}`,
        wallet_id,
        transaction_type,
        amount,
        currency,
        balance_before: "—",
        balance_after: new_balance,
        description: note,
        created_at: new Date().toISOString(),
      };

      // Only prepend if this wallet's transactions are currently visible
      const isCurrentWallet = state.transactions.some(
        (t) => t.wallet_id === wallet_id
      ) || state.transactions.length === 0;

      if (isCurrentWallet && wallet_id === state.transactions[0]?.wallet_id) {
        state.transactions = [syntheticTx, ...state.transactions];
        state.transactionTotal += 1;
      }
    },
  },

  extraReducers: (builder) => {
    builder
      // fetchWallets
      .addCase(fetchWalletsThunk.pending, (state) => { state.isLoading = true; state.error = null; })
      .addCase(fetchWalletsThunk.fulfilled, (state, action) => {
        state.isLoading = false;
        state.wallets = action.payload;
      })
      .addCase(fetchWalletsThunk.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })

      // createWallet
      .addCase(createWalletThunk.fulfilled, (state, action) => {
        state.wallets.push(action.payload);
      })
      .addCase(createWalletThunk.rejected, (state, action) => {
        state.error = action.payload as string;
      })

      // creditWallet — API response has the updated wallet, so sync it
      .addCase(creditWalletThunk.fulfilled, (state, action) => {
        const idx = state.wallets.findIndex((w) => w.id === action.payload.id);
        if (idx !== -1) state.wallets[idx] = action.payload;
      })
      .addCase(creditWalletThunk.rejected, (state, action) => {
        state.error = action.payload as string;
      })

      // fetchTransactions
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

export const { clearWalletError, updateWalletBalance, prependTransaction } = walletSlice.actions;
export default walletSlice.reducer;
