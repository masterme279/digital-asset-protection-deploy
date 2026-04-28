import { motion } from 'motion/react';
import { CheckCircle } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import React, { useState, useEffect, FormEvent } from 'react';
import { cn } from '../../lib/utils';
import { useAuth } from '../../context/AuthContext';
import { apiPost, ApiError } from '../../lib/api';
import { showToast } from '../../components/shared/GlobalToast';
import { SentinelLogo } from '../../components/shared/SentinelLogo';

export function RegisterPage() {
  useEffect(() => {
    document.title = "SENTINEL · Organization Registration";
  }, []);

  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(0);
  const [orgType, setOrgType] = useState('Sports League');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [contactNo, setContactNo] = useState('');
  const [organizationName, setOrganizationName] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [roleSelection, setRoleSelection] = useState('Admin');
  const navigate = useNavigate();
  const { setUser, setTokens } = useAuth();

  const getErrorMessage = (err: unknown) => {
    const defaultMessage = 'Registration failed. Check details and try again.';
    const apiError = err as ApiError | null;
    if (apiError?.data && typeof apiError.data === 'object') {
      const data = apiError.data as Record<string, unknown>;
      const preferredKeys = ['detail', 'non_field_errors', 'email', 'password', 'password_confirm', 'contact_no'];
      for (const key of preferredKeys) {
        const value = data[key];
        if (Array.isArray(value) && value[0]) return String(value[0]);
        if (typeof value === 'string') return value;
      }
      const values = Object.values(data);
      const first = values[0];
      if (Array.isArray(first) && first[0]) return String(first[0]);
      if (typeof first === 'string') return first;
    }
    if (err instanceof Error && err.message) return err.message;
    return defaultMessage;
  };

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const stepsList = [
      "Creating account...",
      "Setting up workspace...",
      "Registering on blockchain...",
      "Welcome to SENTINEL ✓"
    ];
    let stepIndex = 0;
    const stepTimer = window.setInterval(() => {
      stepIndex += 1;
      setStep(Math.min(stepIndex, stepsList.length));
      if (stepIndex >= stepsList.length) {
        window.clearInterval(stepTimer);
      }
    }, 700);

    try {
      await apiPost('/api/auth/register/', {
        full_name: fullName,
        email,
        contact_no: contactNo,
        password,
        password_confirm: passwordConfirm,
      });

      const loginResponse = await apiPost<{ access: string; refresh: string; user: { full_name: string; email: string } }>(
        '/api/auth/login/',
        { email, password }
      );

      setTokens({ access: loginResponse.access, refresh: loginResponse.refresh });
      setUser({
        name: fullName,
        email: loginResponse.user.email,
        orgName: organizationName,
        role: roleSelection === 'Admin' ? 'admin' : 'user',
        plan: 'Pro',
        bioRegion: 'Europe (West)',
        signature: `SNT-${organizationName.replace(/[^a-zA-Z0-9]/g, '').slice(0, 6).toUpperCase() || 'ORG'}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`,
        country: 'India',
        legalEntityName: organizationName,
        legalAddress: '',
        postalCode: '',
        registrationId: '',
        taxId: '',
        noticeEmail: loginResponse.user.email,
        contactPhone: contactNo,
      });
      navigate('/dashboard');
    } catch (err) {
      showToast(getErrorMessage(err), 'error');
      setLoading(false);
      setStep(0);
      window.clearInterval(stepTimer);
      return;
    }
  };

  const stepsLabels = [
    "Creating account...",
    "Setting up workspace...",
    "Registering on blockchain...",
    "Welcome to SENTINEL ✓"
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-brand-bg flex items-center justify-center p-6 flex-col">
        <div className="w-full max-w-sm space-y-4">
           {stepsLabels.map((s, i) => (
             <motion.div 
               key={s}
               initial={{ opacity: 0, x: -10 }}
               animate={step > i ? { opacity: 1, x: 0 } : { opacity: 0.3 }}
               className="flex items-center gap-3 p-4 glass-card bg-brand-surface border-brand-border"
             >
               <div className={cn(
                 "w-5 h-5 rounded-full flex items-center justify-center text-xs",
                 step > i ? "bg-brand-accent3 text-white" : "bg-white/10 text-white/50"
               )}>
                 {step > i ? <CheckCircle size={14} /> : i + 1}
               </div>
               <span className={cn("text-sm font-medium", step > i ? "text-white" : "text-brand-muted")}>
                 {s}
               </span>
             </motion.div>
           ))}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-brand-bg flex relative overflow-hidden">
      <div className="absolute top-1/4 -left-32 w-80 h-80 bg-brand-accent rounded-full blur-[120px] opacity-10 float-animation" />
      <div className="absolute bottom-1/4 -right-32 w-64 h-64 bg-brand-accent2 rounded-full blur-[120px] opacity-10 float-animation" />

      <div className="hidden lg:flex w-1/3 flex-col justify-center items-center p-12 relative z-10 border-r border-brand-border bg-brand-surface/20">
        <div className="max-w-md">
          <Link to="/" className="flex items-center gap-4 mb-12">
            <SentinelLogo iconClassName="w-16 h-16" textClassName="[&_span:first-child]:text-4xl" />
          </Link>
          <h2 className="text-5xl font-bold text-white mb-6 font-serif leading-tight">Secure Your <span className="text-brand-accent">Media DNA.</span></h2>
        </div>
      </div>

      <div className="w-full lg:w-2/3 flex flex-col justify-center items-center p-6 relative z-10 overflow-y-auto">
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="glass-card w-full max-w-[560px] p-10 my-8"
        >
          <h3 className="mission-control-header !text-brand-accent mb-2">Initialize Organization Protocol</h3>
          <p className="text-white text-3xl font-bold font-sans tracking-tight mb-8">Create Workspace</p>
          <form onSubmit={handleRegister} className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="col-span-2 md:col-span-1 border-b border-white/5 pb-2">
              <label className="text-[10px] font-mono font-bold text-brand-muted uppercase">Full Name</label>
              <input type="text" required value={fullName} onChange={(e) => setFullName(e.target.value)} className="w-full bg-transparent p-2 text-white outline-none" placeholder="John Doe" />
            </div>
            <div className="col-span-2 md:col-span-1 border-b border-white/5 pb-2">
              <label className="text-[10px] font-mono font-bold text-brand-muted uppercase">Email Address</label>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full bg-transparent p-2 text-white outline-none" placeholder="jd@fcb.com" />
            </div>
            <div className="col-span-2 md:col-span-1 border-b border-white/5 pb-2">
              <label className="text-[10px] font-mono font-bold text-brand-muted uppercase">Contact Number</label>
              <input type="text" required value={contactNo} onChange={(e) => setContactNo(e.target.value)} className="w-full bg-transparent p-2 text-white outline-none" placeholder="9876543210" />
            </div>
            <div className="col-span-2 md:col-span-1 border-b border-white/5 pb-2">
              <label className="text-[10px] font-mono font-bold text-brand-muted uppercase">Organization Type</label>
              <select 
                value={orgType}
                onChange={(e) => setOrgType(e.target.value)}
                className="w-full h-12 bg-brand-surface p-2 text-white outline-none border border-brand-border focus:border-brand-accent font-sans mt-1"
              >
                <option>Sports League</option>
                <option>Club</option>
                <option>Broadcaster</option>
                <option>Media House</option>
              </select>
            </div>
            <div className="col-span-2 md:col-span-1 border-b border-white/5 pb-2">
              <label className="text-[10px] font-mono font-bold text-brand-muted uppercase">Organization Name</label>
              <input type="text" required value={organizationName} onChange={(e) => setOrganizationName(e.target.value)} className="w-full bg-transparent p-2 text-white outline-none" placeholder="FC Barcelona" />
            </div>
            <div className="col-span-2 md:col-span-1 border-b border-white/5 pb-2">
              <label className="text-[10px] font-mono font-bold text-brand-muted uppercase">Password</label>
              <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="w-full bg-transparent p-2 text-white outline-none" placeholder="••••••••" />
            </div>
            <div className="col-span-2 md:col-span-1 border-b border-white/5 pb-2">
              <label className="text-[10px] font-mono font-bold text-brand-muted uppercase">Confirm Password</label>
              <input type="password" required value={passwordConfirm} onChange={(e) => setPasswordConfirm(e.target.value)} className="w-full bg-transparent p-2 text-white outline-none" placeholder="••••••••" />
            </div>
            <div className="col-span-2 md:col-span-1 border-b border-white/5 pb-2">
              <label className="text-[10px] font-mono font-bold text-brand-muted uppercase">Role</label>
              <select value={roleSelection} onChange={(e) => setRoleSelection(e.target.value)} className="w-full bg-brand-surface p-2 text-white outline-none">
                <option>Admin</option>
                <option>Legal</option>
                <option>Analyst</option>
              </select>
            </div>
            <button className="primary-button col-span-2 w-full mt-4 shadow-[0_0_24px_rgba(14,165,233,0.3)]">Create Account</button>
          </form>
          <p className="mt-8 text-sm text-brand-muted text-center">
            Already have an account? <Link to="/login" className="text-brand-accent hover:underline font-bold">Sign in →</Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
