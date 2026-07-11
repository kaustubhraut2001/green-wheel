import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, Link } from "react-router-dom";
import { loginThunk, clearError } from "../store/authSlice";
import type { AppDispatch, RootState } from "../store";

const LoginPage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { isLoading, error } = useSelector((s: RootState) => s.auth);
  const [form, setForm] = useState({ email: "", password: "" });
  const [showPw, setShowPw] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(clearError());
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await dispatch(loginThunk(form));
    if (loginThunk.fulfilled.match(result)) navigate("/dashboard");
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-slate-50">
      {/* ── Left Side: Premium Hero (Hidden on Mobile/Tablet to keep layout compact and focused) ── */}
      <div className="hidden lg:flex lg:w-[48%] xl:w-[45%] flex-col justify-between p-12 relative overflow-hidden"
        style={{ background: "linear-gradient(135deg, #1e1b4b 0%, #312e81 40%, #4338ca 100%)" }}>
        
        {/* Ambient Decorative Orbs */}
        <div className="animate-orb absolute w-[400px] h-[400px] rounded-full pointer-events-none"
          style={{ background: "radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%)", top: "-50px", left: "-50px" }} />
        
        {/* Brand Logo */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center text-xl font-bold text-white shadow-lg"
            style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
            ◈
          </div>
          <span className="text-xl font-bold text-white heading-brand tracking-tight">WalletPro</span>
        </div>

        {/* Floating Credit Card Mockup */}
        <div className="relative z-10 my-auto space-y-8 max-w-sm">
          <div className="animate-float rounded-3xl p-6 shadow-2xl relative overflow-hidden"
            style={{ background: "linear-gradient(135deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.03))", border: "1px solid rgba(255, 255, 255, 0.15)", backdropFilter: "blur(12px)" }}>
            <div className="flex justify-between items-start mb-10">
              <div>
                <p className="text-[10px] text-indigo-200 font-bold uppercase tracking-widest">Total Portfolio</p>
                <p className="text-3xl font-black text-white heading-brand mt-1">$45,190.00</p>
              </div>
              <span className="text-2xl">💳</span>
            </div>
            <div className="flex justify-between items-end">
              <div>
                <p className="text-[9px] text-indigo-200 uppercase tracking-widest font-semibold">Card Holder</p>
                <p className="text-sm font-bold text-white tracking-wide mt-0.5">Alex Mitchell</p>
              </div>
              <div className="flex gap-2">
                <span className="text-xs px-2 py-0.5 rounded bg-white/20 text-white font-bold">USD</span>
                <span className="text-xs px-2 py-0.5 rounded bg-white/10 text-white/80 font-bold">EUR</span>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <h1 className="text-4xl font-extrabold text-white leading-tight heading-brand">
              Manage your wealth globally.
            </h1>
            <p className="text-indigo-100 text-base leading-relaxed">
              Create instant multi-currency wallets, check exchange rates in real-time, and transfer funds seamlessly with zero hassle.
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="relative z-10 text-indigo-300 text-xs">
          © 2026 WalletPro. Enterprise Security Standard.
        </p>
      </div>

      {/* ── Right Side: Login Form (Adaptive for mobile, tablet, and desktops) ── */}
      <div className="flex-1 flex flex-col justify-center items-center p-6 md:p-12">
        <div className="w-full max-w-[420px] bg-white rounded-3xl p-8 md:p-10 border border-slate-200/80 shadow-xl shadow-slate-100/50 animate-fade-in">
          
          {/* Mobile/Tablet Logo (Shown only on smaller screens) */}
          <div className="flex items-center gap-2 mb-8 lg:hidden justify-center">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center text-lg font-bold text-white"
              style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>◈</div>
            <span className="text-lg font-bold text-slate-900 heading-brand">WalletPro</span>
          </div>

          <div className="mb-8 text-center lg:text-left">
            <h2 className="text-3xl font-black text-slate-950 heading-brand tracking-tight mb-2">Welcome back</h2>
            <p className="text-slate-500 text-sm">Sign in to manage your money</p>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="mb-6 p-4 rounded-xl flex items-start gap-3 bg-rose-50 border border-rose-100 animate-slide-up">
              <span className="text-rose-500 font-bold">⚠</span>
              <p className="text-sm text-rose-700 font-medium">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email field */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                Email Address
              </label>
              <input
                name="email" type="email" required value={form.email} onChange={handleChange}
                className="input-base" placeholder="alex@example.com"
                autoComplete="email"
              />
            </div>

            {/* Password field */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500">
                  Password
                </label>
              </div>
              <div className="relative">
                <input
                  name="password" type={showPw ? "text" : "password"} required
                  value={form.password} onChange={handleChange}
                  className="input-base" placeholder="••••••••"
                  style={{ paddingRight: "2.75rem" }}
                  autoComplete="current-password"
                />
                <button type="button" onClick={() => setShowPw(!showPw)} tabIndex={-1}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors text-sm">
                  {showPw ? "🙈" : "👁"}
                </button>
              </div>
            </div>

            {/* Submit button */}
            <div className="pt-2">
              <button type="submit" disabled={isLoading} className="btn-primary w-full">
                <span className="flex items-center justify-center gap-2">
                  {isLoading ? (
                    <><span className="spinner" /> Signing in…</>
                  ) : "Sign In →"}
                </span>
              </button>
            </div>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 h-px bg-slate-200" />
            <span className="text-xs text-slate-400 uppercase tracking-widest font-semibold">or</span>
            <div className="flex-1 h-px bg-slate-200" />
          </div>

          <p className="text-center text-sm text-slate-600">
            New to WalletPro?{" "}
            <Link to="/register" className="font-bold text-indigo-600 hover:text-indigo-500 transition-colors">
              Create an account →
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
