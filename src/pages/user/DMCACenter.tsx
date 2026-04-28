import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { SentinelSidebar } from '../../components/shared/SentinelSidebar';
import { FileText, Send, Clock, CheckCircle, AlertTriangle, Search, Filter, Mail, Globe, Download } from 'lucide-react';
import { cn } from '../../lib/utils';
import { showToast } from '../../components/shared/GlobalToast';
import { downloadSentinelPdf } from '../../lib/downloadPdf';
import { useAuth } from '../../context/AuthContext';
import { apiGet, apiPost } from '../../lib/api';

export function DMCACenter() {
  const { user } = useAuth();
   const issuer = {
      country: user?.country || 'Global',
      legalEntityName: user?.legalEntityName || user?.orgName,
      legalAddress: user?.legalAddress,
      postalCode: user?.postalCode,
      registrationId: user?.registrationId,
      taxId: user?.taxId,
      noticeEmail: user?.noticeEmail || user?.email,
      contactPhone: user?.contactPhone,
   };
   const [notices, setNotices] = useState<any[]>([]);
   const [chainMode, setChainMode] = useState<string>('demo');
   const [isSubmitting, setIsSubmitting] = useState(false);
   const [formState, setFormState] = useState({
      asset: '',
      platform: 'YouTube',
      url: '',
      similarity: '',
      status: 'Sent',
      notes: '',
   });
   const totalTakedowns = notices.length;
   const compliedCount = notices.filter((notice) => String(notice.status || '').toLowerCase() === 'complied').length;
   const complianceRate = totalTakedowns ? Math.round((compliedCount / totalTakedowns) * 1000) / 10 : 0;
   const takedownHours = notices
      .map((notice) => Number(notice.takedown_hours ?? notice.takedownHours ?? notice.hours ?? notice.avg_hours))
      .filter((value) => Number.isFinite(value));
   const avgTakedownHours = takedownHours.length
      ? Math.round((takedownHours.reduce((sum, value) => sum + value, 0) / takedownHours.length) * 10) / 10
      : null;

   useEffect(() => {
      const loadNotices = async () => {
         try {
            const response = await apiGet<{ notices: any[] }>('/api/signals/dmca/');
            if (response.notices?.length) {
               setNotices(response.notices);
            }
         } catch {
            showToast('Unable to fetch DMCA notices', 'error');
         }
      };
      loadNotices();
   }, []);

   useEffect(() => {
      const loadMode = async () => {
         try {
            const response = await apiGet<{ mode?: string }>('/api/signals/blockchain/mode/');
            if (response.mode) {
               setChainMode(String(response.mode).toLowerCase());
            }
         } catch {
            setChainMode('demo');
         }
      };
      loadMode();
   }, []);

  const handleManualNotice = () => {
    showToast("Generating DMCA notice...", "info");
      downloadSentinelPdf({
         type: 'dmca',
         title: 'DMCA Enforcement Notice',
         refId: 'DMCA-' + Math.floor(Math.random() * 900 + 100),
         assetName: 'Manual Filing - Asset Unspecified',
         orgName: user?.orgName || 'Your Organization',
         ...issuer,
         txHash: 'DEMO-MANUAL-NOTICE',
         date: new Date().toISOString().split('T')[0],
      });
      showToast(`DMCA notice generated · Reference: SENT-${Math.floor(Math.random() * 900000 + 100000)}`, 'success');
  };

   const handleFormChange = (key: keyof typeof formState, value: string) => {
      setFormState((prev) => ({ ...prev, [key]: value }));
   };

   const submitNotice = async () => {
      if (!formState.asset.trim() || !formState.platform.trim() || !formState.url.trim()) {
         showToast('Asset, platform, and URL are required', 'error');
         return;
      }
      setIsSubmitting(true);
      try {
         const response = await apiPost<{ notice?: any }>('/api/signals/dmca/', {
            asset: formState.asset.trim(),
            platform: formState.platform.trim(),
            url: formState.url.trim(),
            similarity: formState.similarity.trim(),
            status: formState.status,
            notes: formState.notes.trim(),
         });
         if (response.notice) {
            setNotices((prev) => [response.notice, ...prev]);
            setFormState({
               asset: '',
               platform: 'YouTube',
               url: '',
               similarity: '',
               status: 'Sent',
               notes: '',
            });
            showToast('DMCA notice saved', 'success');
         } else {
            showToast('Notice saved, but response was empty', 'info');
         }
      } catch {
         showToast('Failed to save DMCA notice', 'error');
      } finally {
         setIsSubmitting(false);
      }
   };

  return (
    <div className="flex bg-brand-bg min-h-screen">
      <SentinelSidebar role="user" />
      <main className="flex-1 p-8 space-y-8 overflow-x-hidden">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="mission-control-header !text-brand-accent mb-2">Authenticated: {user?.orgName || 'Your Organization'}</h1>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-brand-accent animate-pulse" />
              <p className="text-xl font-bold text-white tracking-tight">Legal Enforcement Terminal</p>
            </div>
                  {chainMode === 'demo' ? (
                     <div className="mt-3 inline-flex items-center gap-2 rounded-lg border border-brand-warn/30 bg-brand-warn/10 px-3 py-1.5 text-[11px]">
                         <span className="font-bold text-brand-warn uppercase tracking-wide">Demo Chain Mode</span>
                         <span className="text-brand-muted">Simulated Output for Prototype</span>
                     </div>
                  ) : null}
          </div>
          <button onClick={handleManualNotice} className="primary-button bg-brand-danger hover:shadow-[0_0_20px_rgba(239,68,68,0.3)]">
            <Send className="w-4 h-4" />
            File Manual Notice
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
           {[
             { label: 'Total Takedowns', val: totalTakedowns, icon: CheckCircle, color: 'text-brand-accent3' },
             { label: 'Compliance Rate', val: `${complianceRate}%`, icon: Globe, color: 'text-brand-accent' },
             { label: 'Avg Takedown Time', val: avgTakedownHours === null ? 'N/A' : `${avgTakedownHours}h`, icon: Clock, color: 'text-brand-accent' },
           ].map((stat) => (
             <div key={stat.label} className="glass-card p-6">
                <div className="flex items-center gap-4">
                   <div className={cn("p-3 rounded-xl bg-current/10", stat.color)}>
                      <stat.icon size={24} />
                   </div>
                   <div>
                      <div className="text-2xl font-bold text-white">{stat.val}</div>
                      <div className="text-xs text-brand-muted uppercase tracking-tight">{stat.label}</div>
                   </div>
                </div>
             </div>
           ))}
        </div>

        <div className="glass-card p-6 border-brand-danger/30">
           <div className="flex items-center justify-between mb-6">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                 <AlertTriangle className="w-4 h-4 text-brand-danger" />
                 Create DMCA Notice
              </h3>
              <span className="text-[10px] text-brand-muted uppercase font-mono">Critical enforcement intake</span>
           </div>
           <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                 <label className="text-[10px] text-brand-muted uppercase tracking-widest">Infringed Asset</label>
                 <input
                    value={formState.asset}
                    onChange={(e) => handleFormChange('asset', e.target.value)}
                    placeholder="Asset name or ID"
                    className="mt-2 w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-accent"
                 />
              </div>
              <div>
                 <label className="text-[10px] text-brand-muted uppercase tracking-widest">Platform</label>
                 <select
                    value={formState.platform}
                    onChange={(e) => handleFormChange('platform', e.target.value)}
                    className="mt-2 w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-accent"
                 >
                    {['YouTube', 'Instagram', 'Reddit', 'Facebook', 'X', 'Other'].map((platform) => (
                       <option key={platform} value={platform} className="bg-[#0B111C]">
                          {platform}
                       </option>
                    ))}
                 </select>
              </div>
              <div className="md:col-span-2">
                 <label className="text-[10px] text-brand-muted uppercase tracking-widest">Infringing URL</label>
                 <input
                    value={formState.url}
                    onChange={(e) => handleFormChange('url', e.target.value)}
                    placeholder="https://"
                    className="mt-2 w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-accent"
                 />
              </div>
              <div>
                 <label className="text-[10px] text-brand-muted uppercase tracking-widest">Similarity Match</label>
                 <input
                    value={formState.similarity}
                    onChange={(e) => handleFormChange('similarity', e.target.value)}
                    placeholder="94.2%"
                    className="mt-2 w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-accent"
                 />
              </div>
              <div>
                 <label className="text-[10px] text-brand-muted uppercase tracking-widest">Status</label>
                 <select
                    value={formState.status}
                    onChange={(e) => handleFormChange('status', e.target.value)}
                    className="mt-2 w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-accent"
                 >
                    {['Sent', 'Review', 'Complied'].map((status) => (
                       <option key={status} value={status} className="bg-[#0B111C]">
                          {status}
                       </option>
                    ))}
                 </select>
              </div>
              <div className="md:col-span-2">
                 <label className="text-[10px] text-brand-muted uppercase tracking-widest">Notes</label>
                 <textarea
                    value={formState.notes}
                    onChange={(e) => handleFormChange('notes', e.target.value)}
                    placeholder="Evidence details or escalation notes"
                    rows={3}
                    className="mt-2 w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-accent"
                 />
              </div>
           </div>
           <div className="mt-6 flex justify-end">
              <button
                 onClick={submitNotice}
                 disabled={isSubmitting}
                 className="primary-button bg-brand-danger disabled:opacity-60 disabled:cursor-not-allowed"
              >
                 <Send className="w-4 h-4" />
                 {isSubmitting ? 'Saving...' : 'Save Notice'}
              </button>
           </div>
        </div>

        <div className="glass-card p-6">
           <div className="flex items-center justify-between mb-8">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                 <FileText className="w-4 h-4 text-brand-accent" />
                 Recent Enforcement History
              </h3>
              <div className="flex gap-2">
                 <button className="ghost-button h-8 px-3 text-xs border-white/5"><Filter size={14}/></button>
                 <button className="ghost-button h-8 px-3 text-xs border-white/5"><Search size={14}/></button>
              </div>
           </div>

           <div className="overflow-x-auto">
              <table className="w-full text-left">
                 <thead>
                    <tr className="border-b border-brand-border text-[10px] font-mono text-brand-muted uppercase tracking-widest">
                       <th className="pb-4 px-2">Notice ID</th>
                       <th className="pb-4 px-2">Infringed Asset</th>
                       <th className="pb-4 px-2">Platform</th>
                       <th className="pb-4 px-2">Status</th>
                       <th className="pb-4 px-2">Mode</th>
                       <th className="pb-4 px-2 text-right">Actions</th>
                    </tr>
                 </thead>
                         <tbody className="divide-y divide-brand-border/50">
                              {notices.length === 0 ? (
                                 <tr>
                                    <td className="py-6 px-2 text-sm text-brand-muted" colSpan={6}>
                                       No enforcement notices yet.
                                    </td>
                                 </tr>
                              ) : notices.map((notice) => (
                      <tr key={notice.id} className="text-sm hover:bg-white/5 transition-colors group">
                         <td className="py-4 px-2 font-mono text-brand-muted text-xs">{notice.id}</td>
                         <td className="py-4 px-2 text-white font-medium">{notice.asset}</td>
                         <td className="py-4 px-2 text-brand-muted">{notice.platform}</td>
                         <td className="py-4 px-2">
                            <span className={cn(
                              "px-2 py-0.5 rounded text-[10px] font-bold uppercase",
                              notice.status === 'Complied' ? "bg-brand-accent3/20 text-brand-accent3" :
                              notice.status === 'Sent' ? "bg-brand-accent/20 text-brand-accent" : "bg-brand-warn/20 text-brand-warn"
                            )}>
                               {notice.status}
                            </span>
                         </td>
                         <td className="py-4 px-2 font-mono text-[10px] text-brand-muted uppercase">
                            {notice.auto ? 'System Auto' : 'Manual File'}
                         </td>
                                     <td className="py-4 px-2 text-right flex justify-end gap-3 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                            <button 
                              onClick={() => {
                                                try {
                                                   downloadSentinelPdf({
                                                      type: 'dmca',
                                                      title: 'DMCA Enforcement Notice',
                                                      refId: notice.id,
                                                      assetName: notice.asset,
                                                      platform: notice.platform,
                                                      txHash: notice.txHash || notice.hash || 'N/A',
                                                      orgName: user?.orgName || 'Your Organization',
                                                      ...issuer,
                                                      similarity: notice.similarity || 'N/A',
                                                      date: notice.date || new Date().toISOString().split('T')[0],
                                                   });
                                                   showToast(`DMCA notice downloaded · Reference: ${notice.id}`, 'success');
                                                } catch {
                                                   showToast('Download failed on this device', 'error');
                                                }
                              }}
                              className="text-brand-accent hover:text-white transition-colors cursor-pointer"
                            >
                               <Download size={14} />
                            </button>
                            <button className="text-brand-muted hover:text-white transition-colors">
                               <Mail size={14} />
                            </button>
                         </td>
                      </tr>
                    ))}
                 </tbody>
              </table>
           </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
           <div className="glass-card p-6 border-brand-accent/20">
              <h4 className="text-white font-bold mb-4 flex items-center gap-2">
                 <AlertTriangle className="w-4 h-4 text-brand-warn" />
                 Legal Sandbox
              </h4>
              <p className="text-xs text-brand-muted mb-6">Test your DMCA notices against platform-specific filters before sending. Prevents false positive strikes.</p>
              <button className="ghost-button w-full border-brand-border text-brand-text">Open Sandbox Studio</button>
           </div>
           <div className="glass-card p-6 border-brand-accent3/20">
              <h4 className="text-white font-bold mb-4 flex items-center gap-2">
                 <CheckCircle className="w-4 h-4 text-brand-accent3" />
                 Platform Whitelist
              </h4>
              <p className="text-xs text-brand-muted mb-6">Manage approved creators and official partner channels to prevent accidental automated takedowns.</p>
              <button className="ghost-button w-full border-brand-border text-brand-text">Manage Global Whitelist</button>
           </div>
        </div>
      </main>
    </div>
  );
}
