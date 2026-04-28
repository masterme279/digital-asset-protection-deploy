import React, { useState } from 'react';
import { motion } from 'motion/react';
import { SentinelSidebar } from '../../components/shared/SentinelSidebar';
import { 
  User, Mail, Shield, Key, History, Smartphone, 
  MapPin, Globe, Camera, Edit2, LogOut, CheckCircle
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { showToast } from '../../components/shared/GlobalToast';
import { useAuth } from '../../context/AuthContext';
import { apiPut } from '../../lib/api';

export function ProfilePage() {
   const { user, setUser, logout } = useAuth();
   const [fullName, setFullName] = useState(user.name);
   const [email, setEmail] = useState(user.email);
   const [region, setRegion] = useState(user.bioRegion || 'Europe (West)');
   const [country, setCountry] = useState(user.country || 'India');
   const [legalEntityName, setLegalEntityName] = useState(user.legalEntityName || user.orgName);
   const [legalAddress, setLegalAddress] = useState(user.legalAddress || '');
   const [postalCode, setPostalCode] = useState(user.postalCode || '');
   const [registrationId, setRegistrationId] = useState(user.registrationId || '');
   const [taxId, setTaxId] = useState(user.taxId || '');
   const [noticeEmail, setNoticeEmail] = useState(user.noticeEmail || user.email);
   const [contactPhone, setContactPhone] = useState(user.contactPhone || '');

   const signature = user.signature || `SNT-${user.name.replace(/[^a-zA-Z0-9]/g, '').slice(0, 8).toUpperCase() || 'USER'}`;
   const avatarUrl = `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name)}&background=0f172a&color=e2e8f0&bold=true`;

   const handleUpdate = async () => {
      setUser({
         ...user,
         name: fullName.trim() || user.name,
         email: email.trim() || user.email,
         bioRegion: region,
         country,
         legalEntityName: legalEntityName.trim() || user.orgName,
         legalAddress: legalAddress.trim(),
         postalCode: postalCode.trim(),
         registrationId: registrationId.trim(),
         taxId: taxId.trim(),
         noticeEmail: noticeEmail.trim() || email.trim() || user.email,
         contactPhone: contactPhone.trim(),
         signature,
      });

      try {
         await apiPut('/api/auth/profile/', {
            full_name: fullName.trim() || user.name,
            contact_no: contactPhone.trim() || 'N/A',
         });
         showToast('Profile identity updated', 'success');
      } catch {
         showToast('Profile update failed on backend', 'error');
      }
   };

  return (
    <div className="flex bg-brand-bg min-h-screen">
      <SentinelSidebar role="user" />
      <main className="flex-1 p-8 space-y-8 overflow-x-hidden">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white mb-1">Identity & Profile</h1>
            <p className="text-xs font-mono text-brand-muted uppercase tracking-widest">Manage your personal sentinel credentials and security</p>
          </div>
          <button onClick={handleUpdate} className="primary-button">
            <CheckCircle size={16} />
            Commit Changes
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
           <div className="lg:col-span-1 space-y-8">
              <div className="glass-card p-8 flex flex-col items-center text-center relative overflow-hidden group">
                 <div className="absolute top-0 inset-x-0 h-24 bg-gradient-to-b from-brand-accent/10 to-transparent group-hover:from-brand-accent/20 transition-all" />
                 <div className="relative mb-6">
                    <div className="w-32 h-32 rounded-full border-4 border-brand-accent/20 overflow-hidden bg-brand-surface relative group/avatar">
                       <img 
                                     src={avatarUrl}
                         alt="Avatar" 
                         className="w-full h-full object-cover transition-transform group-hover/avatar:scale-110"
                       />
                       <button className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover/avatar:opacity-100 transition-opacity">
                          <Camera className="text-white w-6 h-6" />
                       </button>
                    </div>
                    <div className="absolute bottom-1 right-1 w-6 h-6 bg-brand-accent rounded-full border-2 border-brand-bg flex items-center justify-center">
                       <CheckCircle className="text-white w-3 h-3" />
                    </div>
                 </div>
                 <h2 className="text-xl font-bold text-white mb-1">{user.name}</h2>
                 <p className="text-xs font-mono text-brand-muted uppercase tracking-[0.2em] mb-6">{user.role === 'admin' ? 'Administrator' : 'Operator'} • {user.orgName}</p>
                 <div className="flex gap-2 w-full">
                    <button className="flex-1 ghost-button h-9 text-xs">Edit Bio</button>
                    <button onClick={logout} className="flex-1 ghost-button h-9 text-xs border-brand-danger/30 text-brand-danger hover:bg-brand-danger/10"><LogOut size={14} /></button>
                 </div>
              </div>

              <div className="glass-card p-6">
                 <h3 className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest mb-6 border-l-2 border-brand-accent pl-3">Account Security Strength</h3>
                 <div className="space-y-6">
                    <div className="flex items-center justify-between text-xs">
                       <span className="text-white">Multifactor Auth</span>
                       <span className="text-brand-accent3 font-bold font-mono">ENABLED</span>
                    </div>
                    <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                       <div className="h-full bg-brand-accent3" style={{ width: '92%' }} />
                    </div>
                    <div className="space-y-3">
                       <div className="flex items-center gap-2 text-xs text-brand-muted">
                          <CheckCircle className="w-3 h-3 text-brand-accent3" />
                          <span>Encrypted Backup Active</span>
                       </div>
                       <div className="flex items-center gap-2 text-xs text-brand-muted">
                          <CheckCircle className="w-3 h-3 text-brand-accent3" />
                          <span>Email Verified ({user.email})</span>
                       </div>
                    </div>
                 </div>
              </div>
           </div>

           <div className="lg:col-span-2 space-y-8">
              <div className="glass-card p-8">
                 <h3 className="text-sm font-bold text-white uppercase tracking-widest mb-8 flex items-center gap-2">
                    <User className="text-brand-accent w-4 h-4" />
                    Identity Details
                 </h3>
                 <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="space-y-2">
                       <label className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest">Full Legal Name</label>
                       <div className="flex items-center gap-3 bg-black/20 rounded-xl px-4 py-3 border border-white/5 focus-within:border-brand-accent/40 transition-all">
                          <User size={16} className="text-brand-muted" />
                          <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} className="bg-transparent text-sm text-white w-full outline-none" />
                       </div>
                    </div>
                    <div className="space-y-2">
                       <label className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest">Primary Workspace Email</label>
                       <div className="flex items-center gap-3 bg-black/20 rounded-xl px-4 py-3 border border-white/5 focus-within:border-brand-accent/40 transition-all">
                          <Mail size={16} className="text-brand-muted" />
                          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="bg-transparent text-sm text-white w-full outline-none" />
                       </div>
                    </div>
                    <div className="space-y-2">
                       <label className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest">Digital Avatar Signature</label>
                       <div className="flex items-center gap-3 bg-black/20 rounded-xl px-4 py-3 border border-white/5 focus-within:border-brand-accent/40 transition-all">
                          <Shield size={16} className="text-brand-muted" />
                          <input type="text" value={signature} readOnly className="bg-transparent text-sm text-brand-muted w-full outline-none cursor-default" />
                       </div>
                    </div>
                    <div className="space-y-2">
                       <label className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest">Preferred Sentinel Bio-Region</label>
                       <div className="flex items-center gap-3 bg-black/20 rounded-xl px-4 py-3 border border-white/5 focus-within:border-brand-accent/40 transition-all">
                          <Globe size={16} className="text-brand-muted" />
                          <select value={region} onChange={(e) => setRegion(e.target.value)} className="bg-transparent text-sm text-white w-full outline-none border-none focus:ring-0">
                             <option className="bg-brand-bg">Europe (West)</option>
                             <option className="bg-brand-bg">North America</option>
                             <option className="bg-brand-bg">Asia Pacific</option>
                             <option className="bg-brand-bg">Middle East</option>
                             <option className="bg-brand-bg">Latin America</option>
                             <option className="bg-brand-bg">Africa</option>
                          </select>
                       </div>
                    </div>
                    <div className="space-y-2">
                       <label className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest">Country / Jurisdiction</label>
                       <div className="flex items-center gap-3 bg-black/20 rounded-xl px-4 py-3 border border-white/5 focus-within:border-brand-accent/40 transition-all">
                          <Globe size={16} className="text-brand-muted" />
                          <select value={country} onChange={(e) => setCountry(e.target.value)} className="bg-transparent text-sm text-white w-full outline-none border-none focus:ring-0">
                             <option className="bg-brand-bg">India</option>
                             <option className="bg-brand-bg">United States</option>
                             <option className="bg-brand-bg">United Kingdom</option>
                             <option className="bg-brand-bg">European Union</option>
                             <option className="bg-brand-bg">Canada</option>
                             <option className="bg-brand-bg">Australia</option>
                             <option className="bg-brand-bg">Singapore</option>
                             <option className="bg-brand-bg">United Arab Emirates</option>
                             <option className="bg-brand-bg">Other</option>
                          </select>
                       </div>
                    </div>
                 </div>
              </div>

              <div className="glass-card p-8">
                 <h3 className="text-sm font-bold text-white uppercase tracking-widest mb-8 flex items-center gap-2">
                    <Shield className="text-brand-accent w-4 h-4" />
                    Official Compliance Details
                 </h3>
                 <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="space-y-2">
                       <label className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest">Legal Entity Name</label>
                       <div className="flex items-center gap-3 bg-black/20 rounded-xl px-4 py-3 border border-white/5 focus-within:border-brand-accent/40 transition-all">
                          <User size={16} className="text-brand-muted" />
                          <input type="text" value={legalEntityName} onChange={(e) => setLegalEntityName(e.target.value)} className="bg-transparent text-sm text-white w-full outline-none" placeholder="Your Organization Pvt Ltd" />
                       </div>
                    </div>
                    <div className="space-y-2">
                       <label className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest">Legal Notice Email</label>
                       <div className="flex items-center gap-3 bg-black/20 rounded-xl px-4 py-3 border border-white/5 focus-within:border-brand-accent/40 transition-all">
                          <Mail size={16} className="text-brand-muted" />
                          <input type="email" value={noticeEmail} onChange={(e) => setNoticeEmail(e.target.value)} className="bg-transparent text-sm text-white w-full outline-none" placeholder="legal@company.com" />
                       </div>
                    </div>
                    <div className="space-y-2 md:col-span-2">
                       <label className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest">Registered Office Address</label>
                       <div className="flex items-center gap-3 bg-black/20 rounded-xl px-4 py-3 border border-white/5 focus-within:border-brand-accent/40 transition-all">
                          <Globe size={16} className="text-brand-muted" />
                          <input type="text" value={legalAddress} onChange={(e) => setLegalAddress(e.target.value)} className="bg-transparent text-sm text-white w-full outline-none" placeholder="Street, City, State / Province" />
                       </div>
                    </div>
                    <div className="space-y-2">
                       <label className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest">Postal / ZIP Code</label>
                       <div className="flex items-center gap-3 bg-black/20 rounded-xl px-4 py-3 border border-white/5 focus-within:border-brand-accent/40 transition-all">
                          <Globe size={16} className="text-brand-muted" />
                          <input type="text" value={postalCode} onChange={(e) => setPostalCode(e.target.value)} className="bg-transparent text-sm text-white w-full outline-none" placeholder="Postal code" />
                       </div>
                    </div>
                    <div className="space-y-2">
                       <label className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest">Official Contact Number</label>
                       <div className="flex items-center gap-3 bg-black/20 rounded-xl px-4 py-3 border border-white/5 focus-within:border-brand-accent/40 transition-all">
                          <Smartphone size={16} className="text-brand-muted" />
                          <input type="text" value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} className="bg-transparent text-sm text-white w-full outline-none" placeholder="+00 0000 000000" />
                       </div>
                    </div>
                    <div className="space-y-2">
                       <label className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest">Company Registration ID</label>
                       <div className="flex items-center gap-3 bg-black/20 rounded-xl px-4 py-3 border border-white/5 focus-within:border-brand-accent/40 transition-all">
                          <Shield size={16} className="text-brand-muted" />
                          <input type="text" value={registrationId} onChange={(e) => setRegistrationId(e.target.value)} className="bg-transparent text-sm text-white w-full outline-none" placeholder="CIN / Incorporation Number" />
                       </div>
                    </div>
                    <div className="space-y-2">
                       <label className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest">Tax Registration ID</label>
                       <div className="flex items-center gap-3 bg-black/20 rounded-xl px-4 py-3 border border-white/5 focus-within:border-brand-accent/40 transition-all">
                          <Shield size={16} className="text-brand-muted" />
                          <input type="text" value={taxId} onChange={(e) => setTaxId(e.target.value)} className="bg-transparent text-sm text-white w-full outline-none" placeholder="GST / VAT / Tax ID" />
                       </div>
                    </div>
                 </div>
              </div>

              <div className="glass-card p-6">
                 <div className="flex items-center justify-between mb-8">
                    <h3 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
                       <History className="text-brand-accent w-4 h-4" />
                       Recent Sentinel Access Logs
                    </h3>
                    <button className="text-[10px] font-mono text-brand-accent hover:underline uppercase">Terminate All Sessions</button>
                 </div>
                 <div className="space-y-4">
                    {[
                      { d: 'MacBook Pro 16"', l: 'Barcelona, Spain', t: 'Just Now', i: '192.168.1.42', s: 'Current' },
                      { d: 'iPhone 15 Pro', l: 'Manchester, UK', t: '2 hours ago', i: '92.14.88.211', s: 'Syncing' },
                      { d: 'Sentinel Terminal V3', l: 'Doha, Qatar', t: 'Yesterday', i: '202.44.11.2', s: 'Inactive' },
                    ].map((log, i) => (
                      <div key={i} className="flex items-center justify-between p-4 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] transition-colors">
                         <div className="flex items-center gap-4">
                            <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-brand-muted">
                               {log.d.includes('iPhone') ? <Smartphone size={18} /> : <Globe size={18} />}
                            </div>
                            <div>
                               <p className="text-sm font-medium text-white">{log.d}</p>
                               <p className="text-[10px] text-brand-muted font-mono">{log.l} • {log.i}</p>
                            </div>
                         </div>
                         <div className="text-right">
                            <p className={cn("text-[9px] font-black font-mono uppercase mb-1", log.s === 'Current' ? 'text-brand-accent3' : 'text-brand-muted')}>{log.s}</p>
                            <p className="text-[10px] text-brand-muted font-mono">{log.t}</p>
                         </div>
                      </div>
                    ))}
                 </div>
              </div>
           </div>
        </div>
      </main>
    </div>
  );
}
