import { motion } from 'motion/react';
import { Eye, EyeOff, LayoutDashboard, Database, AlertCircle, Map, CheckCircle } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import React, { useState, useEffect, FormEvent } from 'react';
import { cn } from '../../lib/utils';
import { useAuth } from '../../context/AuthContext';
import { apiPost } from '../../lib/api';
import { showToast } from '../../components/shared/GlobalToast';
import { SentinelLogo } from '../../components/shared/SentinelLogo';

export function LoginPage() {
  useEffect(() => {
    document.title = "SENTINEL · Portal Access";
  }, []);

  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();
  const { setUser, setTokens } = useAuth();

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await apiPost<{ access: string; refresh: string; user: { full_name: string; email: string } }>(
        '/api/auth/login/',
        { email, password }
      );

      setTokens({ access: response.access, refresh: response.refresh });

      const localName = response.user.full_name || email.split('@')[0] || 'Sentinel User';
      const displayName = localName
        .split(' ')
        .filter(Boolean)
        .map((part) => part[0].toUpperCase() + part.slice(1))
        .join(' ');
      const domain = email.split('@')[1] || 'organization.local';
      const orgName = domain.split('.')[0]
        ? domain.split('.')[0][0].toUpperCase() + domain.split('.')[0].slice(1)
        : 'Your Organization';

      setUser({
        name: displayName,
        email: response.user.email,
        orgName,
        role: 'user',
        plan: 'Pro',
        bioRegion: 'Europe (West)',
        signature: `SNT-${Math.random().toString(36).slice(2, 8).toUpperCase()}`,
        country: 'India',
        legalEntityName: orgName,
        legalAddress: '',
        postalCode: '',
        registrationId: '',
        taxId: '',
        noticeEmail: response.user.email,
        contactPhone: '',
      });
      navigate('/dashboard');
    } catch {
      showToast('Login failed. Check your email or password.', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-brand-bg flex relative overflow-hidden">
      {/* Background Orbs */}
      <div className="absolute top-1/4 -left-32 w-80 h-80 bg-brand-accent rounded-full blur-[120px] opacity-10 float-animation" />
      <div className="absolute bottom-1/4 -right-32 w-64 h-64 bg-brand-accent2 rounded-full blur-[120px] opacity-10 float-animation" />

      {/* Left Panel - Branding */}
      <div className="hidden lg:flex w-1/2 flex-col justify-center items-center p-12 relative z-10 border-r border-brand-border bg-brand-surface/20">
        <div className="max-w-md">
          <Link to="/" className="flex items-center gap-4 mb-12">
            <SentinelLogo iconClassName="w-16 h-16" textClassName="[&_span:first-child]:text-4xl" />
          </Link>
          <h2 className="text-5xl font-bold text-white mb-6 font-serif leading-tight">Protect What's <span className="text-brand-accent">Yours.</span></h2>
          <div className="space-y-6">
            {[
              "AI Fingerprinting",
              "Blockchain Provenance",
              "Real-Time Detection"
            ].map((feature) => (
              <div key={feature} className="flex items-center gap-4 text-brand-muted">
                <CheckCircle className="w-5 h-5 text-brand-accent" />
                <span className="text-lg">{feature}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right Panel - Form */}
      <div className="w-full lg:w-1/2 flex flex-col justify-center items-center p-6 relative z-10">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card w-full max-w-[400px] p-10"
        >
          <div className="mb-10 text-center lg:text-left">
             <h3 className="mission-control-header !text-brand-accent mb-2">Authenticated System Access</h3>
             <p className="text-white text-3xl font-bold font-sans tracking-tight mb-2">Welcome Back</p>
             <p className="text-brand-muted text-xs font-mono uppercase tracking-widest">Sign in to your SENTINEL account.</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            <div className="space-y-2">
              <label className="text-xs font-mono font-bold text-brand-muted uppercase tracking-widest px-1">Email Address</label>
              <input 
                type="email" 
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full h-12 bg-brand-surface border border-brand-border rounded-lg px-4 text-white placeholder-brand-muted focus:outline-none focus:border-brand-accent focus:ring-1 focus:ring-brand-accent/30 transition-all font-sans"
                placeholder="email@organization.com"
              />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <label className="text-xs font-mono font-bold text-brand-muted uppercase tracking-widest px-1">Password</label>
                <button type="button" className="text-[11px] text-brand-accent hover:underline font-medium">Forgot password?</button>
              </div>
              <div className="relative">
                <input 
                  type={showPassword ? "text" : "password"} 
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full h-12 bg-brand-surface border border-brand-border rounded-lg px-4 text-white placeholder-brand-muted focus:outline-none focus:border-brand-accent focus:ring-1 focus:ring-brand-accent/30 transition-all font-sans"
                  placeholder="••••••••"
                />
                <button 
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-brand-muted hover:text-white"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button 
              disabled={loading}
              className="primary-button w-full h-12 relative overflow-hidden"
            >
              {loading ? (
                <div className="flex items-center gap-3">
                   <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                   <span>Authenticating...</span>
                </div>
              ) : "Sign In"}
            </button>
          </form>

          <div className="mt-8 text-center">
             <div className="relative mb-8">
                <div className="absolute inset-0 flex items-center">
                   <div className="w-full border-t border-brand-border"></div>
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                   <span className="bg-[#0D1421] px-4 text-brand-muted font-mono tracking-widest">or continue with</span>
                </div>
             </div>

             <button className="ghost-button w-full h-12 border-brand-border text-white hover:bg-white/5 flex gap-3">
                <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24">
                   <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                   <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                   <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                   <path d="M12 5.38c1.62 0 3.06.56 4.21 1.66l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                </svg>
                Google SSO
             </button>

             <p className="mt-8 text-sm text-brand-muted">
                Don't have an account? <Link to="/register" className="text-brand-accent hover:underline">Register →</Link>
             </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
