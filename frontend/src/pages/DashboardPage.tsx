import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import type { AppDispatch, RootState } from "../store";
import {
  fetchWalletsThunk, createWalletThunk, creditWalletThunk, fetchTransactionsThunk,
} from "../store/walletSlice";
import { logout } from "../store/authSlice";
import { walletService } from "../services/api";

const CURRENCIES = ["USD","EUR","GBP","JPY","CAD","AUD","NGN","INR","GHS","ZAR","CHF","CNY","KES"];

const CURRENCY_COLORS: Record<string, string> = {
  USD: "#4f46e5", EUR: "#7c3aed", GBP: "#0891b2", JPY: "#ea580c",
  CAD: "#e11d48", AUD: "#059669", NGN: "#0d9488", INR: "#d97706",
  GHS: "#65a30d", ZAR: "#db2777", CHF: "#8b5cf6", CNY: "#ea580c", KES: "#06b6d4",
};

/* ── Reusable Light Theme Modal ─────────────────────────────────────────── */
const Modal: React.FC<{ title: string; subtitle?: string; onClose: () => void; children: React.ReactNode; accentColor?: string }> = ({
  title, subtitle, onClose, children, accentColor = "#4f46e5",
}) => (
  <div className="fixed inset-0 flex items-center justify-center z-50 p-4"
    style={{ background: "rgba(15, 23, 42, 0.4)", backdropFilter: "blur(4px)" }}>
    <div className="relative w-full max-w-md rounded-3xl overflow-hidden shadow-2xl bg-white border border-slate-200 animate-slide-up">
      {/* Accent top bar */}
      <div className="h-1" style={{ background: `linear-gradient(90deg, ${accentColor}, transparent)` }} />

      <div className="p-6">
        <div className="flex items-start justify-between mb-5">
          <div>
            <h3 className="text-xl font-bold text-slate-900 heading-brand">{title}</h3>
            {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
          </div>
          <button onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-all text-sm font-semibold border border-slate-200">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  </div>
);

/* ── Tx Badge ────────────────────────────────────────────────────────────── */
const TxBadge: React.FC<{ type: string }> = ({ type }) => {
  const styles: Record<string, { bg: string; text: string; icon: string }> = {
    credit:     { bg: "#ecfdf5",  text: "#059669", icon: "↓" },
    debit:      { bg: "#fff1f2",  text: "#e11d48", icon: "↑" },
    transfer:   { bg: "#eef2ff",  text: "#4f46e5", icon: "↗" },
    conversion: { bg: "#fffbeb",  text: "#d97706", icon: "⇄" },
  };
  const s = styles[type] ?? { bg: "#f8fafc", text: "#64748b", icon: "•" };
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wide"
      style={{ backgroundColor: s.bg, color: s.text }}>
      <span className="text-[10px]">{s.icon}</span>{type}
    </span>
  );
};

/* ── Stat Card (Light Theme) ─────────────────────────────────────────────── */
const StatCard: React.FC<{ label: string; value: string; sub?: string; icon: string; color: string }> = ({ label, value, sub, icon, color }) => (
  <div className="rounded-2xl p-5 bg-white border border-slate-200/80 shadow-sm relative overflow-hidden">
    <div className="absolute top-0 right-0 w-20 h-20 rounded-full -translate-y-1/2 translate-x-1/2 opacity-[0.08]"
      style={{ background: `radial-gradient(circle, ${color} 0%, transparent 70%)` }} />
    <div className="flex items-center gap-3 mb-2">
      <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold"
        style={{ backgroundColor: `${color}10`, color: color }}>
        {icon}
      </div>
      <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{label}</p>
    </div>
    <p className="text-2xl font-black text-slate-900 heading-brand leading-none mt-1">{value}</p>
    {sub && <p className="text-[10px] text-slate-400 mt-1.5">{sub}</p>}
  </div>
);

/* ── Main Dashboard ──────────────────────────────────────────────────────── */
const DashboardPage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { user } = useSelector((s: RootState) => s.auth);
  const { wallets, transactions, isLoading, error, transactionPages } =
    useSelector((s: RootState) => s.wallet);

  const [activeNav, setActiveNav] = useState("wallets");
  const [showCreate, setShowCreate]     = useState(false);
  const [showCredit, setShowCredit]     = useState(false);
  const [showDebit, setShowDebit]       = useState(false);
  const [showTransfer, setShowTransfer] = useState(false);

  // Mobile sidebar visibility
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [selectedWallet, setSelectedWallet] = useState<string | null>(null);
  const [newCurrency, setNewCurrency]       = useState("EUR");
  const [creditAmt, setCreditAmt]           = useState("");
  const [debitAmt, setDebitAmt]             = useState("");
  const [txPage, setTxPage]                 = useState(1);
  const [transferForm, setTransferForm]     = useState({ recipient_wallet_id: "", amount: "", note: "" });

  const [actionError, setActionError]     = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  useEffect(() => { dispatch(fetchWalletsThunk()); }, [dispatch]);

  useEffect(() => {
    if (selectedWallet) dispatch(fetchTransactionsThunk({ walletId: selectedWallet, page: txPage }));
  }, [selectedWallet, txPage, dispatch]);

  const flash = (msg: string) => {
    setActionSuccess(msg);
    setTimeout(() => setActionSuccess(null), 3500);
  };

  const handleLogout = () => { dispatch(logout()); navigate("/login"); };

  const handleCreateWallet = async () => {
    setActionError(null);
    const r = await dispatch(createWalletThunk({ currency: newCurrency }));
    if (createWalletThunk.fulfilled.match(r)) { setShowCreate(false); flash(`${newCurrency} wallet created successfully!`); }
    else setActionError(r.payload as string);
  };

  const handleCredit = async () => {
    if (!selectedWallet) return;
    setActionError(null);
    const r = await dispatch(creditWalletThunk({ walletId: selectedWallet, amount: creditAmt }));
    if (creditWalletThunk.fulfilled.match(r)) { setShowCredit(false); setCreditAmt(""); flash("Funds deposited successfully!"); }
    else setActionError(r.payload as string);
  };

  const handleDebit = async () => {
    if (!selectedWallet) return;
    setActionError(null);
    try {
      await walletService.debit(selectedWallet, debitAmt);
      setShowDebit(false); setDebitAmt("");
      dispatch(fetchWalletsThunk()); flash("Funds withdrawn successfully!");
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: { message?: string } } } };
      setActionError(err.response?.data?.error?.message || "Withdrawal failed");
    }
  };

  const handleTransfer = async () => {
    setActionError(null);
    try {
      const key = `transfer-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      await walletService.transfer(transferForm.recipient_wallet_id, transferForm.amount, transferForm.note, key);
      setShowTransfer(false);
      setTransferForm({ recipient_wallet_id: "", amount: "", note: "" });
      dispatch(fetchWalletsThunk()); flash("Transfer completed! ↗");
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: { message?: string } } } };
      setActionError(err.response?.data?.error?.message || "Transfer failed");
    }
  };

  const selectedWalletData = wallets.find((w) => w.id === selectedWallet);
  const totalWallets = wallets.length;
  const totalTx      = transactions.length;
  const initials = `${(user?.first_name?.[0] ?? "").toUpperCase()}${(user?.last_name?.[0] ?? "").toUpperCase()}`;

  return (
    <div className="min-h-screen flex bg-slate-50 relative">

      {/* ══ Sidebar Panel (Desktop only) ═══════════════════════════════════ */}
      <aside className="hidden lg:flex flex-col w-64 flex-shrink-0 sticky top-0 h-screen bg-white border-r border-slate-200">
        
        {/* Brand Header */}
        <div className="flex items-center gap-3 px-6 pt-7 pb-8 border-b border-slate-100">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center text-lg font-bold text-white shadow-md shadow-indigo-200"
            style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}>◈</div>
          <span className="text-lg font-black text-slate-900 heading-brand tracking-tight">WalletPro</span>
        </div>

        {/* Sidebar Nav links */}
        <nav className="flex-1 px-4 py-6 space-y-1">
          {[
            { id: "wallets",      icon: "◈", label: "My Wallets" },
            { id: "transactions", icon: "≡", label: "Transactions" },
          ].map((item) => (
            <button key={item.id} onClick={() => { setActiveNav(item.id); setSelectedWallet(null); }}
              className={`sidebar-link w-full text-left ${activeNav === item.id && !selectedWallet ? "active" : ""}`}>
              <span className="text-base w-5 text-center font-bold">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        {/* Actions panel */}
        <div className="px-4 pb-6 space-y-2 border-t border-slate-100 pt-4">
          <p className="px-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Operations</p>
          <button onClick={() => setShowTransfer(true)}
            className="sidebar-link w-full text-left" style={{ color: "#4f46e5" }}>
            <span>↗</span> Transfer Funds
          </button>
          <button onClick={() => setShowCreate(true)}
            className="sidebar-link w-full text-left" style={{ color: "#4f46e5" }}>
            <span>+</span> New Wallet
          </button>
        </div>

        {/* User Card */}
        <div className="p-4 mx-4 mb-6 rounded-2xl bg-slate-50 border border-slate-200 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold text-white shadow-inner flex-shrink-0"
            style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}>
            {initials || "U"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-slate-800 truncate">{user?.first_name} {user?.last_name}</p>
            <p className="text-[10px] text-slate-500 truncate">{user?.email}</p>
          </div>
          <button onClick={handleLogout} title="Logout"
            className="text-slate-400 hover:text-rose-600 transition-colors text-sm flex-shrink-0">⏻</button>
        </div>
      </aside>

      {/* ══ Mobile Dropdown Overlay (Mobile/Tablet) ═══════════════════════ */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-40 bg-slate-900/20 backdrop-blur-sm lg:hidden" onClick={() => setMobileMenuOpen(false)}>
          <div className="absolute top-16 left-0 right-0 bg-white border-b border-slate-200 p-6 flex flex-col gap-4 animate-slide-up" onClick={(e) => e.stopPropagation()}>
            <button onClick={() => { setActiveNav("wallets"); setSelectedWallet(null); setMobileMenuOpen(false); }} className="w-full text-left py-2 text-slate-700 font-bold border-b border-slate-100 flex items-center gap-2">◈ My Wallets</button>
            <button onClick={() => { setActiveNav("transactions"); setSelectedWallet(null); setMobileMenuOpen(false); }} className="w-full text-left py-2 text-slate-700 font-bold border-b border-slate-100 flex items-center gap-2">≡ Transactions</button>
            <button onClick={() => { setShowTransfer(true); setMobileMenuOpen(false); }} className="w-full text-left py-2 text-indigo-600 font-bold border-b border-slate-100 flex items-center gap-2">↗ Transfer Funds</button>
            <button onClick={() => { setShowCreate(true); setMobileMenuOpen(false); }} className="w-full text-left py-2 text-indigo-600 font-bold border-b border-slate-100 flex items-center gap-2">+ New Wallet</button>
            <button onClick={handleLogout} className="w-full text-left py-2 text-rose-600 font-bold flex items-center gap-2">⏻ Sign Out</button>
          </div>
        </div>
      )}

      {/* ══ Main Section ═══════════════════════════════════════════════════ */}
      <div className="flex-1 flex flex-col min-h-screen overflow-x-hidden">
        
        {/* Mobile Header Bar */}
        <header className="lg:hidden flex items-center justify-between px-6 py-4 bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
          <div className="flex items-center gap-2.5">
            <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="text-xl text-slate-700 mr-1">☰</button>
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-base font-bold text-white shadow-sm"
              style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}>◈</div>
            <span className="text-base font-black text-slate-900 heading-brand">WalletPro</span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setShowCreate(true)}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-indigo-200 bg-indigo-50 text-indigo-600 transition hover:bg-indigo-100">
              + Wallet
            </button>
          </div>
        </header>

        {/* Content Wrapper */}
        <main className="flex-1 p-4 md:p-6 lg:p-8 max-w-6xl w-full mx-auto space-y-6">

          {/* Header Panel */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 animate-fade-in">
            <div>
              <h1 className="text-2xl font-black text-slate-950 heading-brand leading-none">
                Welcome, <span className="gradient-text-blue">{user?.first_name ?? "Alex"}</span> 👋
              </h1>
              <p className="text-xs text-slate-400 mt-2 font-medium">
                {new Date().toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
              </p>
            </div>
            
            <div className="flex gap-2">
              <button onClick={() => setShowTransfer(true)}
                className="flex-1 sm:flex-initial flex items-center justify-center gap-1.5 text-xs font-bold px-4 py-2.5 rounded-xl border border-indigo-100 bg-indigo-50 text-indigo-600 shadow-sm hover:bg-indigo-100 transition">
                ↗ Transfer Funds
              </button>
            </div>
          </div>

          {/* Action Alerts */}
          {actionSuccess && (
            <div className="flex items-center gap-2.5 p-4 rounded-2xl bg-emerald-50 border border-emerald-200 animate-slide-up">
              <span className="text-emerald-600 font-bold">✓</span>
              <p className="text-xs font-semibold text-emerald-800">{actionSuccess}</p>
            </div>
          )}
          {(error || actionError) && (
            <div className="flex items-center gap-2.5 p-4 rounded-2xl bg-rose-50 border border-rose-200 animate-slide-up">
              <span className="text-rose-600 font-bold">⚠</span>
              <p className="text-xs font-semibold text-rose-800">{error || actionError}</p>
            </div>
          )}

          {/* Stats Bar */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-fade-in">
            <StatCard label="Total Accounts"    value={String(totalWallets)}     icon="◈" color="#4f46e5" sub="active digital wallets" />
            <StatCard label="Recent Ledger"    value={String(totalTx)}          icon="⏚" color="#7c3aed" sub="transactions loaded" />
            <StatCard label="Home Currency"    value={user?.default_currency ?? "USD"} icon="💱" color="#0891b2" sub="profile base currency" />
            <StatCard label="Security Node"    value="Secure"                   icon="✓" color="#059669" sub="256-bit monitoring active" />
          </div>

          {/* Wallets Deck */}
          {activeNav === "wallets" && (
            <section className="animate-fade-in space-y-5">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-lg font-bold text-slate-900 heading-brand">Your Wallets</h2>
                  <p className="text-xs text-slate-400 mt-0.5">Holdings in global digital currencies</p>
                </div>
                <button onClick={() => setShowCreate(true)}
                  className="flex items-center gap-1.5 text-xs font-bold px-4 py-2.5 rounded-xl text-white shadow-sm hover:opacity-90 transition"
                  style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}>
                  + New Wallet
                </button>
              </div>

              {isLoading && wallets.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 gap-3 bg-white rounded-3xl border border-slate-200">
                  <div className="spinner-lg" />
                  <p className="text-xs text-slate-400">Fetching wallets…</p>
                </div>
              ) : wallets.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 bg-white rounded-3xl border border-dashed border-slate-200/80 gap-3 text-center p-6">
                  <span className="text-4xl text-slate-300">💳</span>
                  <div>
                    <p className="font-bold text-slate-800 text-sm">No wallets created yet</p>
                    <p className="text-xs text-slate-400 mt-0.5">Open a wallet to start depositing cash</p>
                  </div>
                  <button onClick={() => setShowCreate(true)}
                    className="text-xs font-bold px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition border border-slate-200 mt-2">
                    + Add Wallet
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
                  {wallets.map((w, idx) => {
                    const accent = CURRENCY_COLORS[w.currency] ?? "#4f46e5";
                    const isSelected = selectedWallet === w.id;
                    return (
                      <div key={w.id}
                        onClick={() => { setSelectedWallet(w.id); setTxPage(1); }}
                        className="rounded-3xl p-6 cursor-pointer border transition-all duration-200 relative overflow-hidden hover:shadow-md"
                        style={{
                          backgroundColor: "#ffffff",
                          borderColor: isSelected ? accent : "#e2e8f0",
                          boxShadow: isSelected ? `0 10px 25px -5px ${accent}15` : "none",
                          transform: isSelected ? "scale(1.01)" : "none",
                        }}>
                        
                        {/* Currency Identifier */}
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-xl flex items-center justify-center text-xs font-bold shadow-sm"
                              style={{ backgroundColor: `${accent}10`, color: accent }}>
                              {w.currency}
                            </div>
                            <div>
                              <p className="text-sm font-bold text-slate-900 heading-brand">{w.currency}</p>
                              {w.label && <p className="text-[10px] text-slate-400">{w.label}</p>}
                            </div>
                          </div>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                            style={{
                              backgroundColor: w.status === "active" ? "#ecfdf5" : "#fff1f2",
                              color: w.status === "active" ? "#059669" : "#e11d48",
                            }}>
                            {w.status}
                          </span>
                        </div>

                        {/* Balance value */}
                        <div className="mb-4">
                          <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Available Balance</p>
                          <p className="text-2xl font-black text-slate-950 heading-brand mt-1 tabular-nums">
                            {parseFloat(w.balance).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </p>
                        </div>

                        {/* Wallet ID & Copy Trigger */}
                        <div className="flex items-center justify-between gap-2 mt-2 pt-2 border-t border-slate-100 relative z-10" onClick={(e) => e.stopPropagation()}>
                          <span className="text-[10px] font-mono text-slate-400 select-all truncate" title={w.id}>
                            ID: {w.id}
                          </span>
                          <button
                            onClick={() => handleCopyId(w.id)}
                            className="flex-shrink-0 flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-lg border transition-colors duration-150"
                            style={{
                              backgroundColor: copiedId === w.id ? "#ecfdf5" : "#f1f5f9",
                              borderColor: copiedId === w.id ? "#a7f3d0" : "#e2e8f0",
                              color: copiedId === w.id ? "#059669" : "#475569",
                            }}
                          >
                            {copiedId === w.id ? "✓ Copied" : "Copy 📋"}
                          </button>
                        </div>

                        {/* Slide-out card action controls */}
                        {isSelected && (
                          <div className="flex gap-2 mt-5 animate-slide-up">
                            <button onClick={(e) => { e.stopPropagation(); setShowCredit(true); }}
                              className="flex-1 py-2 text-center text-xs font-bold rounded-xl border border-emerald-200 bg-emerald-50 text-emerald-700 transition hover:bg-emerald-100">
                              + Deposit
                            </button>
                            <button onClick={(e) => { e.stopPropagation(); setShowDebit(true); }}
                              className="flex-1 py-2 text-center text-xs font-bold rounded-xl border border-rose-200 bg-rose-50 text-rose-700 transition hover:bg-rose-100">
                              − Withdraw
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          )}

          {/* Transactions Ledger Panel */}
          {(activeNav === "transactions" || selectedWallet) && (
            <section className="animate-fade-in space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-slate-900 heading-brand">Transaction History</h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {selectedWallet ? `Viewing Ledger: ${selectedWalletData?.currency} (${selectedWalletData?.id.slice(0, 8)}…)` : "Viewing all ledger instances"}
                  </p>
                </div>
                {selectedWallet && (
                  <button onClick={() => setSelectedWallet(null)}
                    className="text-xs px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 transition">
                    ✕ Clear Filter
                  </button>
                )}
              </div>

              {!selectedWallet && wallets.length > 0 && (
                <div className="p-6 text-center bg-white rounded-3xl border border-slate-200/80 text-slate-400 text-xs">
                  👉 Select a wallet card above to fetch details, deposit funds, or view recent transactions.
                </div>
              )}

              {selectedWallet && (
                isLoading ? (
                  <div className="flex justify-center py-12"><div className="spinner-lg" /></div>
                ) : transactions.length === 0 ? (
                  <div className="p-12 text-center bg-white rounded-3xl border border-slate-200/80 text-slate-400 text-xs">
                    No transactions found for this wallet.
                  </div>
                ) : (
                  <div className="bg-white rounded-3xl border border-slate-200/80 overflow-hidden shadow-sm">
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left">
                        <thead>
                          <tr className="bg-slate-50 border-b border-slate-200 text-slate-400 font-bold">
                            <th className="px-5 py-4">Type</th>
                            <th className="px-5 py-4 text-right">Amount</th>
                            <th className="px-5 py-4 text-right">Balance After</th>
                            <th className="px-5 py-4 hidden md:table-cell">Note</th>
                            <th className="px-5 py-4">Date</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 text-slate-700">
                          {transactions.map((tx) => (
                            <tr key={tx.id} className="hover:bg-slate-50/50 transition">
                              <td className="px-5 py-3.5"><TxBadge type={tx.transaction_type} /></td>
                              <td className="px-5 py-3.5 text-right font-bold tabular-nums">
                                <span style={{ color: tx.transaction_type === "debit" ? "#e11d48" : "#059669" }}>
                                  {tx.transaction_type === "debit" ? "−" : "+"}{parseFloat(tx.amount).toFixed(2)}
                                </span>
                                {" "}<span className="font-semibold text-slate-400">{tx.currency}</span>
                              </td>
                              <td className="px-5 py-3.5 text-right tabular-nums text-slate-500 font-medium">{parseFloat(tx.balance_after).toFixed(2)}</td>
                              <td className="px-5 py-3.5 hidden md:table-cell text-slate-400 max-w-xs truncate">{tx.description || "—"}</td>
                              <td className="px-5 py-3.5 text-slate-400">{new Date(tx.created_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {transactionPages > 1 && (
                      <div className="flex justify-center gap-1.5 p-4 border-t border-slate-100 bg-slate-50/50">
                        {Array.from({ length: transactionPages }, (_, i) => i + 1).map((p) => (
                          <button key={p} onClick={() => setTxPage(p)}
                            className="w-8 h-8 rounded-lg text-xs font-bold transition border"
                            style={{
                              backgroundColor: p === txPage ? "#4f46e5" : "#ffffff",
                              color: p === txPage ? "#ffffff" : "#475569",
                              borderColor: p === txPage ? "#4f46e5" : "#e2e8f0",
                            }}>
                            {p}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )
              )}
            </section>
          )}
        </main>
      </div>

      {/* ══ Action Modals ══════════════════════════════════════════════════ */}

      {showCreate && (
        <Modal title="Create Wallet" subtitle="Support multi-currency assets instantly" onClose={() => { setShowCreate(false); setActionError(null); }} accentColor="#4f46e5">
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Currency Type</label>
              <select value={newCurrency} onChange={(e) => setNewCurrency(e.target.value)} className="input-base" style={{ cursor: "pointer" }}>
                {CURRENCIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            {actionError && <p className="text-xs p-3 bg-rose-50 text-rose-700 border border-rose-100 rounded-xl">{actionError}</p>}
            <button onClick={handleCreateWallet} className="btn-primary w-full">
              <span>Open {newCurrency} Wallet</span>
            </button>
          </div>
        </Modal>
      )}

      {showCredit && (
        <Modal title="Deposit Funds" subtitle={`Deposit into wallet: ${selectedWalletData?.currency}`} onClose={() => { setShowCredit(false); setActionError(null); }} accentColor="#059669">
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Amount</label>
              <input type="number" step="0.01" min="0.01" value={creditAmt}
                onChange={(e) => setCreditAmt(e.target.value)} placeholder="0.00"
                className="input-base" />
            </div>
            {actionError && <p className="text-xs p-3 bg-rose-50 text-rose-700 border border-rose-100 rounded-xl">{actionError}</p>}
            <button onClick={handleCredit} className="btn-primary w-full" style={{ background: "linear-gradient(135deg, #059669, #047857)" }}>
              <span>Confirm Deposit</span>
            </button>
          </div>
        </Modal>
      )}

      {showDebit && (
        <Modal title="Withdraw Funds" subtitle={`Withdraw from wallet: ${selectedWalletData?.currency}`} onClose={() => { setShowDebit(false); setActionError(null); }} accentColor="#e11d48">
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Amount</label>
              <input type="number" step="0.01" min="0.01" value={debitAmt}
                onChange={(e) => setDebitAmt(e.target.value)} placeholder="0.00"
                className="input-base" />
            </div>
            {actionError && <p className="text-xs p-3 bg-rose-50 text-rose-700 border border-rose-100 rounded-xl">{actionError}</p>}
            <button onClick={handleDebit} className="btn-primary w-full" style={{ background: "linear-gradient(135deg, #e11d48, #be123c)" }}>
              <span>Confirm Withdrawal</span>
            </button>
          </div>
        </Modal>
      )}

      {showTransfer && (
        <Modal title="Transfer Funds" subtitle="Move money securely to another user wallet" onClose={() => { setShowTransfer(false); setActionError(null); }} accentColor="#7c3aed">
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Recipient Wallet ID</label>
              <input value={transferForm.recipient_wallet_id}
                onChange={(e) => setTransferForm({ ...transferForm, recipient_wallet_id: e.target.value })}
                className="input-base" placeholder="Paste destination UUID address" />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Amount to Send</label>
              <input type="number" step="0.01" value={transferForm.amount}
                onChange={(e) => setTransferForm({ ...transferForm, amount: e.target.value })}
                className="input-base" placeholder="0.00" />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Note (optional)</label>
              <input value={transferForm.note}
                onChange={(e) => setTransferForm({ ...transferForm, note: e.target.value })}
                className="input-base" placeholder="e.g. Gift, Invoice #12" />
            </div>
            {actionError && <p className="text-xs p-3 bg-rose-50 text-rose-700 border border-rose-100 rounded-xl">{actionError}</p>}
            <button onClick={handleTransfer} className="btn-primary w-full" style={{ background: "linear-gradient(135deg, #7c3aed, #6d28d9)" }}>
              <span>Confirm Transfer</span>
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default DashboardPage;
