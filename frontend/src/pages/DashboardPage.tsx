import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import type { AppDispatch, RootState } from "../store";
import {
  fetchWalletsThunk, createWalletThunk, creditWalletThunk, fetchTransactionsThunk,
} from "../store/walletSlice";
import { logout } from "../store/authSlice";
import { walletService } from "../services/api";
import { useWalletSSE } from "../hooks/useWalletSSE";

const CURRENCIES = ["USD","EUR","GBP","CAD","AUD","NGN","INR","GHS","ZAR","CHF","CNY","KES","JPY"];

/* ── Copy to clipboard button ────────────────────────────────────────────── */
const CopyButton: React.FC<{ text: string }> = ({ text }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation(); // don't trigger wallet card selection
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback for older browsers
      const el = document.createElement("textarea");
      el.value = text;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <button
      onClick={handleCopy}
      title="Copy wallet ID"
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium transition-all ${
        copied
          ? "bg-green-100 text-green-700"
          : "bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700"
      }`}
    >
      {copied ? (
        <>
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          Copied!
        </>
      ) : (
        <>
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
          </svg>
          Copy ID
        </>
      )}
    </button>
  );
};

/* ── Modal ───────────────────────────────────────────────────────────────── */
const Modal: React.FC<{ title: string; onClose: () => void; children: React.ReactNode }> = ({
  title, onClose, children,
}) => (
  <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
    <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-semibold text-lg text-gray-900">{title}</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
      </div>
      {children}
    </div>
  </div>
);

/* ── Share Wallet ID modal ────────────────────────────────────────────────── */
const ShareModal: React.FC<{ wallet: { id: string; currency: string; label: string | null }; onClose: () => void }> = ({
  wallet, onClose,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(wallet.id);
    } catch {
      const el = document.createElement("textarea");
      el.value = wallet.id;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <Modal title={`Share ${wallet.currency} Wallet`} onClose={onClose}>
      <div className="space-y-4">
        <p className="text-sm text-gray-500">
          Share this wallet ID with anyone who wants to send you money.
          They'll paste it into the <strong>To Wallet ID</strong> field when transferring.
        </p>

        {/* Big wallet ID display */}
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-2 font-medium">
            {wallet.currency} Wallet ID {wallet.label ? `· ${wallet.label}` : ""}
          </p>
          <p className="font-mono text-sm text-gray-800 break-all leading-relaxed select-all">
            {wallet.id}
          </p>
        </div>

        {/* Copy button — large, prominent */}
        <button
          onClick={handleCopy}
          className={`w-full flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm transition-all ${
            copied
              ? "bg-green-500 text-white"
              : "bg-blue-600 hover:bg-blue-700 text-white"
          }`}
        >
          {copied ? (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Copied to clipboard!
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
              </svg>
              Copy Wallet ID
            </>
          )}
        </button>

        <p className="text-xs text-center text-gray-400">
          Tip: tap and hold the ID above to select and share it manually
        </p>
      </div>
    </Modal>
  );
};

/* ── Transaction badge ───────────────────────────────────────────────────── */
const TxBadge: React.FC<{ type: string }> = ({ type }) => {
  const map: Record<string, string> = {
    credit: "bg-green-100 text-green-700",
    debit: "bg-red-100 text-red-700",
    transfer: "bg-blue-100 text-blue-700",
    conversion: "bg-purple-100 text-purple-700",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${map[type] ?? "bg-gray-100 text-gray-600"}`}>
      {type}
    </span>
  );
};

/* ── Live dot ────────────────────────────────────────────────────────────── */
const LiveDot: React.FC = () => (
  <span className="inline-flex items-center gap-1.5 text-xs text-green-600 font-medium">
    <span className="relative flex h-2 w-2">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
      <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
    </span>
    Live
  </span>
);

/* ═══════════════════════════════════════════════════════════════════════════ */
const DashboardPage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { user } = useSelector((s: RootState) => s.auth);
  const { wallets, transactions, isLoading, error, transactionPages } =
    useSelector((s: RootState) => s.wallet);

  useWalletSSE();

  const [selectedWallet, setSelectedWallet] = useState<string | null>(null);
  const [txPage, setTxPage]                 = useState(1);
  const [showCreate, setShowCreate]         = useState(false);
  const [showCredit, setShowCredit]         = useState(false);
  const [showDebit, setShowDebit]           = useState(false);
  const [showTransfer, setShowTransfer]     = useState(false);
  const [shareWallet, setShareWallet]       = useState<{ id: string; currency: string; label: string | null } | null>(null);
  const [newCurrency, setNewCurrency]       = useState("EUR");
  const [creditAmt, setCreditAmt]           = useState("");
  const [debitAmt, setDebitAmt]             = useState("");
  const [transferForm, setTransferForm]     = useState({
    sender_wallet_id: "", recipient_wallet_id: "", amount: "", note: "",
  });
  const [actionError, setActionError]       = useState<string | null>(null);
  const [actionSuccess, setActionSuccess]   = useState<string | null>(null);

  useEffect(() => { dispatch(fetchWalletsThunk()); }, [dispatch]);

  useEffect(() => {
    if (selectedWallet) {
      dispatch(fetchTransactionsThunk({ walletId: selectedWallet, page: txPage }));
    }
  }, [selectedWallet, txPage, dispatch]);

  useEffect(() => {
    if (showTransfer && selectedWallet) {
      setTransferForm(f => ({ ...f, sender_wallet_id: f.sender_wallet_id || selectedWallet }));
    }
  }, [showTransfer, selectedWallet]);

  const flash = (msg: string) => { setActionSuccess(msg); setTimeout(() => setActionSuccess(null), 3000); };
  const clearErr = () => setActionError(null);
  const handleLogout = () => { dispatch(logout()); navigate("/login"); };

  const handleCreateWallet = async () => {
    clearErr();
    const r = await dispatch(createWalletThunk({ currency: newCurrency }));
    if (createWalletThunk.fulfilled.match(r)) { setShowCreate(false); flash(`${newCurrency} wallet created!`); }
    else setActionError(r.payload as string);
  };

  const handleCredit = async () => {
    if (!selectedWallet || !creditAmt) return;
    clearErr();
    const r = await dispatch(creditWalletThunk({ walletId: selectedWallet, amount: creditAmt }));
    if (creditWalletThunk.fulfilled.match(r)) { setShowCredit(false); setCreditAmt(""); flash("Funds added!"); }
    else setActionError(r.payload as string);
  };

  const handleDebit = async () => {
    if (!selectedWallet || !debitAmt) return;
    clearErr();
    try {
      await walletService.debit(selectedWallet, debitAmt);
      setShowDebit(false); setDebitAmt("");
      dispatch(fetchTransactionsThunk({ walletId: selectedWallet, page: txPage }));
      flash("Funds withdrawn!");
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: { message?: string } } } };
      setActionError(err.response?.data?.error?.message || "Debit failed");
    }
  };

  const handleTransfer = async () => {
    clearErr();
    const { sender_wallet_id, recipient_wallet_id, amount, note } = transferForm;
    if (!sender_wallet_id || !recipient_wallet_id || !amount) {
      setActionError("Please fill in all required fields."); return;
    }
    try {
      const key = `tx-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      await walletService.transfer(sender_wallet_id, recipient_wallet_id, amount, note, key);
      setShowTransfer(false);
      setTransferForm({ sender_wallet_id: "", recipient_wallet_id: "", amount: "", note: "" });
      if (selectedWallet === sender_wallet_id) {
        dispatch(fetchTransactionsThunk({ walletId: selectedWallet, page: txPage }));
      }
      flash("Transfer completed! Balance updated.");
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: { message?: string } } } };
      setActionError(err.response?.data?.error?.message || "Transfer failed");
    }
  };

  const selectedWalletData = wallets.find(w => w.id === selectedWallet);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between sticky top-0 z-10 shadow-sm">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-blue-600">💳 WalletPro</h1>
          <LiveDot />
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600 hidden sm:block">{user?.first_name} {user?.last_name}</span>
          <button onClick={handleLogout} className="text-sm text-red-500 hover:text-red-600 font-medium">Sign out</button>
        </div>
      </header>

      <div className="max-w-5xl mx-auto p-4 md:p-6 space-y-6">

        {/* Alerts */}
        {actionSuccess && (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">✅ {actionSuccess}</div>
        )}
        {(error || actionError) && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">❌ {error || actionError}</div>
        )}

        {/* Wallets */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-gray-800">My Wallets</h2>
              <span className="text-xs text-gray-400 hidden sm:inline">(balances update live)</span>
            </div>
            <div className="flex gap-2">
              <button onClick={() => { clearErr(); setShowTransfer(true); }}
                className="bg-purple-600 text-white px-3 py-2 rounded-lg text-sm hover:bg-purple-700 transition">
                ↗ Transfer
              </button>
              <button onClick={() => { clearErr(); setShowCreate(true); }}
                className="bg-blue-600 text-white px-3 py-2 rounded-lg text-sm hover:bg-blue-700 transition">
                + New Wallet
              </button>
            </div>
          </div>

          {isLoading && wallets.length === 0 ? (
            <div className="text-center py-16 text-gray-400">Loading wallets…</div>
          ) : wallets.length === 0 ? (
            <div className="bg-white rounded-xl border-2 border-dashed border-gray-200 p-12 text-center text-gray-400">
              No wallets yet. Click <strong>+ New Wallet</strong> to get started.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {wallets.map((w) => (
                <div key={w.id}
                  onClick={() => { setSelectedWallet(w.id); setTxPage(1); }}
                  className={`bg-white rounded-xl p-5 border-2 cursor-pointer transition select-none ${
                    selectedWallet === w.id ? "border-blue-500 shadow-md" : "border-gray-100 hover:border-gray-300"
                  }`}
                >
                  {/* Currency + status */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-gray-700 text-lg">{w.currency}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      w.status === "active" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                    }`}>{w.status}</span>
                  </div>

                  {/* Balance — live via SSE */}
                  <p className="text-2xl font-bold text-gray-900 tabular-nums">
                    {parseFloat(w.balance).toLocaleString(undefined, {
                      minimumFractionDigits: 2, maximumFractionDigits: 2,
                    })}
                  </p>
                  {w.label && <p className="text-xs text-gray-400 mt-1">{w.label}</p>}

                  {/* ── Wallet ID row — always visible ── */}
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-xs text-gray-400 mb-0.5">Wallet ID</p>
                        <p className="font-mono text-xs text-gray-600 truncate" title={w.id}>
                          {w.id.slice(0, 8)}…{w.id.slice(-8)}
                        </p>
                      </div>
                      <div className="flex gap-1.5 flex-shrink-0">
                        {/* Quick copy button */}
                        <CopyButton text={w.id} />
                        {/* Share / view full ID button */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setShareWallet({ id: w.id, currency: w.currency, label: w.label });
                          }}
                          title="Share wallet ID"
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-600 hover:bg-blue-100 transition"
                        >
                          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                          </svg>
                          Share
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Action buttons when selected */}
                  {selectedWallet === w.id && (
                    <div className="mt-3 flex gap-2">
                      <button onClick={(e) => { e.stopPropagation(); clearErr(); setShowCredit(true); }}
                        className="flex-1 bg-green-50 text-green-700 py-1.5 rounded-lg text-sm hover:bg-green-100 font-medium">
                        + Add
                      </button>
                      <button onClick={(e) => { e.stopPropagation(); clearErr(); setShowDebit(true); }}
                        className="flex-1 bg-red-50 text-red-700 py-1.5 rounded-lg text-sm hover:bg-red-100 font-medium">
                        − Withdraw
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Transaction History */}
        {selectedWallet && (
          <section>
            <div className="flex items-center gap-2 mb-4">
              <h2 className="text-lg font-semibold text-gray-800">
                Transactions — {selectedWalletData?.currency}
              </h2>
              <LiveDot />
            </div>

            {isLoading ? (
              <div className="text-center py-8 text-gray-400">Loading…</div>
            ) : transactions.length === 0 ? (
              <div className="bg-white rounded-xl p-8 text-center text-gray-400 border border-gray-100">
                No transactions yet for this wallet.
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
                      <tr>
                        <th className="px-4 py-3 text-left">Type</th>
                        <th className="px-4 py-3 text-right">Amount</th>
                        <th className="px-4 py-3 text-right">Balance After</th>
                        <th className="px-4 py-3 text-left hidden md:table-cell">Note</th>
                        <th className="px-4 py-3 text-left">Time</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {transactions.map((tx) => {
                        const isNew = tx.id.startsWith("live-");
                        return (
                          <tr key={tx.id}
                            className={`transition-colors duration-500 ${isNew ? "bg-blue-50" : "hover:bg-gray-50"}`}>
                            <td className="px-4 py-3">
                              <TxBadge type={tx.transaction_type} />
                              {isNew && <span className="ml-1.5 text-xs text-blue-500 font-medium">● new</span>}
                            </td>
                            <td className="px-4 py-3 text-right font-medium tabular-nums">
                              <span className={tx.transaction_type === "debit" ? "text-red-600" : "text-green-600"}>
                                {tx.transaction_type === "debit" ? "−" : "+"}
                                {parseFloat(tx.amount).toFixed(2)}
                              </span>{" "}{tx.currency}
                            </td>
                            <td className="px-4 py-3 text-right text-gray-500 tabular-nums">
                              {tx.balance_after === "—" ? "—" : parseFloat(tx.balance_after).toFixed(2)}
                            </td>
                            <td className="px-4 py-3 text-gray-500 hidden md:table-cell">
                              {tx.description || "—"}
                            </td>
                            <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">
                              {new Date(tx.created_at).toLocaleTimeString([], {
                                hour: "2-digit", minute: "2-digit", second: "2-digit"
                              })}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {transactionPages > 1 && (
                  <div className="flex justify-center gap-1 p-4 border-t border-gray-50">
                    {Array.from({ length: transactionPages }, (_, i) => i + 1).map((p) => (
                      <button key={p} onClick={() => setTxPage(p)}
                        className={`w-8 h-8 rounded text-sm ${p === txPage ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
                        {p}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </section>
        )}
      </div>

      {/* ── Share Wallet ID Modal ── */}
      {shareWallet && (
        <ShareModal wallet={shareWallet} onClose={() => setShareWallet(null)} />
      )}

      {/* ── Create Wallet Modal ── */}
      {showCreate && (
        <Modal title="Create New Wallet" onClose={() => setShowCreate(false)}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Currency</label>
              <select value={newCurrency} onChange={e => setNewCurrency(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 focus:ring-2 focus:ring-blue-500 outline-none">
                {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            {actionError && <p className="text-red-600 text-sm">❌ {actionError}</p>}
            <button onClick={handleCreateWallet}
              className="w-full bg-blue-600 text-white py-2.5 rounded-lg hover:bg-blue-700 font-medium">
              Create Wallet
            </button>
          </div>
        </Modal>
      )}

      {/* ── Credit Modal ── */}
      {showCredit && (
        <Modal title={`Add Funds — ${selectedWalletData?.currency}`} onClose={() => setShowCredit(false)}>
          <div className="space-y-4">
            <p className="text-sm text-gray-500">
              Current balance: <strong>{parseFloat(selectedWalletData?.balance || "0").toFixed(2)} {selectedWalletData?.currency}</strong>
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Amount</label>
              <input type="number" step="0.01" min="0.01" value={creditAmt}
                onChange={e => setCreditAmt(e.target.value)} placeholder="0.00" autoFocus
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 focus:ring-2 focus:ring-green-500 outline-none" />
            </div>
            {actionError && <p className="text-red-600 text-sm">❌ {actionError}</p>}
            <button onClick={handleCredit}
              className="w-full bg-green-600 text-white py-2.5 rounded-lg hover:bg-green-700 font-medium">
              Add Funds
            </button>
          </div>
        </Modal>
      )}

      {/* ── Debit Modal ── */}
      {showDebit && (
        <Modal title={`Withdraw — ${selectedWalletData?.currency}`} onClose={() => setShowDebit(false)}>
          <div className="space-y-4">
            <p className="text-sm text-gray-500">
              Available: <strong>{parseFloat(selectedWalletData?.balance || "0").toFixed(2)} {selectedWalletData?.currency}</strong>
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Amount</label>
              <input type="number" step="0.01" min="0.01" value={debitAmt}
                onChange={e => setDebitAmt(e.target.value)} placeholder="0.00" autoFocus
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 focus:ring-2 focus:ring-red-500 outline-none" />
            </div>
            {actionError && <p className="text-red-600 text-sm">❌ {actionError}</p>}
            <button onClick={handleDebit}
              className="w-full bg-red-600 text-white py-2.5 rounded-lg hover:bg-red-700 font-medium">
              Withdraw
            </button>
          </div>
        </Modal>
      )}

      {/* ── Transfer Modal ── */}
      {showTransfer && (
        <Modal title="Transfer Funds" onClose={() => { setShowTransfer(false); clearErr(); }}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">From Wallet</label>
              <select value={transferForm.sender_wallet_id}
                onChange={e => setTransferForm({ ...transferForm, sender_wallet_id: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 focus:ring-2 focus:ring-purple-500 outline-none">
                <option value="">— Select your wallet —</option>
                {wallets.filter(w => w.status === "active").map(w => (
                  <option key={w.id} value={w.id}>
                    {w.currency} · {parseFloat(w.balance).toFixed(2)} {w.label ? `(${w.label})` : ""}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">To Wallet ID</label>
              <input value={transferForm.recipient_wallet_id}
                onChange={e => setTransferForm({ ...transferForm, recipient_wallet_id: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 font-mono text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                placeholder="Paste recipient wallet UUID" />
              <p className="text-xs text-gray-400 mt-1">
                Ask recipient to click <strong>Share</strong> on their wallet card and paste the ID here.
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Amount</label>
              <input type="number" step="0.01" min="0.01" value={transferForm.amount}
                onChange={e => setTransferForm({ ...transferForm, amount: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 focus:ring-2 focus:ring-purple-500 outline-none"
                placeholder="0.00" />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Note (optional)</label>
              <input value={transferForm.note}
                onChange={e => setTransferForm({ ...transferForm, note: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 focus:ring-2 focus:ring-purple-500 outline-none"
                placeholder="e.g. Invoice #123, Rent" />
            </div>

            {actionError && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-sm">❌ {actionError}</div>
            )}
            <button onClick={handleTransfer}
              className="w-full bg-purple-600 text-white py-2.5 rounded-lg hover:bg-purple-700 font-medium">
              Send Transfer
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default DashboardPage;
