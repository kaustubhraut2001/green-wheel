import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { authService } from "../services/api";

const CURRENCIES = [
  { code: "USD", name: "US Dollar",         flag: "🇺🇸" },
  { code: "EUR", name: "Euro",              flag: "🇪🇺" },
  { code: "GBP", name: "British Pound",     flag: "🇬🇧" },
  { code: "JPY", name: "Japanese Yen",      flag: "🇯🇵" },
  { code: "CAD", name: "Canadian Dollar",   flag: "🇨🇦" },
  { code: "AUD", name: "Australian Dollar", flag: "🇦🇺" },
  { code: "NGN", name: "Nigerian Naira",    flag: "🇳🇬" },
  { code: "INR", name: "Indian Rupee",      flag: "🇮🇳" },
  { code: "GHS", name: "Ghanaian Cedi",     flag: "🇬🇭" },
  { code: "ZAR", name: "South African Rand",flag: "🇿🇦" },
];

interface FieldError { field: string; message: string; }

function passwordStrength(pw: string): { label: string; color: string; pct: number } {
  if (!pw) return { label: "", color: "transparent", pct: 0 };
  let score = 0;
  if (pw.length >= 8)  score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw))  score++;
  if (/[0-9]/.test(pw))  score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score <= 1) return { label: "Weak",   color: "#ef4444", pct: 20 };
  if (score <= 2) return { label: "Fair",   color: "#f97316", pct: 45 };
  if (score <= 3) return { label: "Good",   color: "#eab308", pct: 65 };
  if (score <= 4) return { label: "Strong", color: "#22c55e", pct: 85 };
  return { label: "Very strong", color: "#10b981", pct: 100 };
}

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: "", password: "", first_name: "", last_name: "", default_currency: "USD",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setError(null);
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setFieldErrors({});
    try {
      await authService.register(form);
      navigate("/login", { state: { registered: true } });
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: { message?: string; details?: FieldError[] } } } };
      const errData = e.response?.data?.error;
      if (errData?.details) {
        const fe: Record<string, string> = {};
        errData.details.forEach((d) => { fe[d.field] = d.message; });
        setFieldErrors(fe);
      } else {
        setError(errData?.message || "Registration failed. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const strength = passwordStrength(form.password);

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-slate-50">
      {/* ── Left Side: Hero (Hidden on Mobile/Tablet) ── */}
      <div className="hidden lg:flex lg:w-[48%] xl:w-[45%] flex-col justify-between p-12 relative overflow-hidden"
        style={{ background: "linear-gradient(135deg, #1e1b4b 0%, #312e81 40%, #4338ca 100%)" }}>

        <div className="animate-orb absolute w-[400px] h-[400px] rounded-full pointer-events-none"
          style={{ background: "radial-gradient(circle, rgba(124, 58, 237, 0.15) 0%, transparent 70%)", top: "-50px", right: "-50px" }} />

        {/* Logo */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center text-xl font-bold text-white shadow-lg"
            style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>◈</div>
          <span className="text-xl font-bold text-white heading-brand tracking-tight">WalletPro</span>
        </div>

        {/* Info Cards */}
        <div className="relative z-10 my-auto space-y-6 max-w-md">
          <h1 className="text-4xl font-extrabold text-white leading-tight heading-brand">
            Get started with WalletPro
          </h1>
          <p className="text-indigo-100 text-base">
            Create an account in less than a minute and experience global finance built for the modern era.
          </p>

          <div className="space-y-4 pt-4">
            {[
              { emoji: "⚡", title: "Instant Verification", desc: "No complex paperwork required" },
              { emoji: "🌍", title: "Multi-Currency support", desc: "Access 10+ currencies anytime" },
              { emoji: "💳", title: "Secure Digital Wallets", desc: "Monitored 24/7 with banking security" },
            ].map((item, idx) => (
              <div key={idx} className="flex gap-4 items-start p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
                <span className="text-2xl">{item.emoji}</span>
                <div>
                  <p className="text-sm font-bold text-white">{item.title}</p>
                  <p className="text-xs text-indigo-200 mt-0.5">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="relative z-10 text-indigo-300 text-xs">
          © 2026 WalletPro. Standardized AES Encryption.
        </p>
      </div>

      {/* ── Right Side: Register Form (Responsive layout) ── */}
      <div className="flex-1 flex flex-col justify-center items-center p-6 md:p-12">
        <div className="w-full max-w-[460px] bg-white rounded-3xl p-8 md:p-10 border border-slate-200/80 shadow-xl shadow-slate-100/50 animate-fade-in">
          
          {/* Mobile Logo */}
          <div className="flex items-center gap-2 mb-6 lg:hidden justify-center">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center text-lg font-bold text-white"
              style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>◈</div>
            <span className="text-lg font-bold text-slate-900 heading-brand">WalletPro</span>
          </div>

          <div className="mb-6 text-center lg:text-left">
            <h2 className="text-3xl font-black text-slate-950 heading-brand tracking-tight mb-2">Create your account</h2>
            <p className="text-slate-500 text-sm">Hold, send, and exchange currencies</p>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="mb-5 p-4 rounded-xl flex items-start gap-3 bg-rose-50 border border-rose-100 animate-slide-up">
              <span className="text-rose-500 font-bold">⚠</span>
              <p className="text-sm text-rose-700 font-medium">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Names row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {(["first_name", "last_name"] as const).map((field) => (
                <div key={field}>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                    {field === "first_name" ? "First Name" : "Last Name"}
                  </label>
                  <input
                    name={field} required value={form[field]} onChange={handleChange}
                    className="input-base" placeholder={field === "first_name" ? "Alex" : "Mitchell"}
                  />
                  {fieldErrors[field] && <p className="text-xs text-rose-500 mt-1">{fieldErrors[field]}</p>}
                </div>
              ))}
            </div>

            {/* Email Address */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                Email Address
              </label>
              <input
                name="email" type="email" required value={form.email} onChange={handleChange}
                className="input-base" placeholder="you@example.com"
                autoComplete="email"
              />
              {fieldErrors["email"] && <p className="text-xs text-rose-500 mt-1">{fieldErrors["email"]}</p>}
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  name="password" type={showPw ? "text" : "password"} required
                  value={form.password} onChange={handleChange}
                  className="input-base" placeholder="At least 8 characters"
                  style={{ paddingRight: "2.75rem" }}
                  autoComplete="new-password"
                />
                <button type="button" onClick={() => setShowPw(!showPw)} tabIndex={-1}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors text-sm">
                  {showPw ? "🙈" : "👁"}
                </button>
              </div>

              {/* Password Strength Indicator */}
              {form.password && (
                <div className="mt-2 space-y-1">
                  <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full transition-all duration-300"
                      style={{ width: `${strength.pct}%`, backgroundColor: strength.color }} />
                  </div>
                  <span className="text-xs font-semibold" style={{ color: strength.color }}>{strength.label} password</span>
                </div>
              )}
              {fieldErrors["body -> password"] && <p className="text-xs text-rose-500 mt-1">{fieldErrors["body -> password"]}</p>}
            </div>

            {/* Home Currency */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                Preferred Default Currency
              </label>
              <select
                name="default_currency" value={form.default_currency} onChange={handleChange}
                className="input-base" style={{ cursor: "pointer" }}>
                {CURRENCIES.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.flag} {c.code} — {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="pt-2">
              <button type="submit" disabled={isLoading} className="btn-primary w-full">
                <span className="flex items-center justify-center gap-2">
                  {isLoading ? (
                    <><span className="spinner" /> Creating Account…</>
                  ) : "Create Account →"}
                </span>
              </button>
            </div>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px bg-slate-200" />
            <span className="text-xs text-slate-400 uppercase tracking-widest font-semibold">or</span>
            <div className="flex-1 h-px bg-slate-200" />
          </div>

          <p className="text-center text-sm text-slate-600">
            Already have an account?{" "}
            <Link to="/login" className="font-bold text-indigo-600 hover:text-indigo-500 transition-colors">
              Sign in →
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
