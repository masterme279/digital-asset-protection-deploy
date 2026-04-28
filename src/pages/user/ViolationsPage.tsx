import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { SentinelSidebar } from '../../components/shared/SentinelSidebar';
import { 
  AlertTriangle, Globe, Search, Filter, ShieldAlert, 
  ChevronRight, FileText, CheckCircle2, XCircle, Clock, Zap, Download
} from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell
} from 'recharts';
import { cn } from '../../lib/utils';
import { showToast } from '../../components/shared/GlobalToast';
import { downloadSentinelPdf } from '../../lib/downloadPdf';
import { useAuth } from '../../context/AuthContext';
import { apiGet } from '../../lib/api';

export function ViolationsPage() {
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
   const [violations, setViolations] = useState<{ p: string; a: string; sim: string; time: string; sev: string; status: string }[]>([]);
   const chartData = violations.map((item, index) => ({ name: `${index + 1}`, hits: 1 }));
   const parseDate = (value: unknown) => {
      if (!value) return null;
      const date = new Date(String(value));
      return Number.isNaN(date.getTime()) ? null : date;
   };
   const tenMinutesAgo = Date.now() - 10 * 60 * 1000;
   const recentHits = violations.filter((item) => {
      const date = parseDate(item.time);
      return date ? date.getTime() >= tenMinutesAgo : false;
   }).length;
   const resolvedCount = violations.filter((item) => {
      const status = String(item.status || '').toLowerCase();
      return status.includes('complied') || status.includes('resolved') || status.includes('closed');
   }).length;
   const autoCount = violations.filter((item: any) => item.auto === true).length;
   const manualCount = violations.filter((item: any) => item.auto === false).length;
   const unresolvedCount = violations.length - resolvedCount;
   const successRate = violations.length ? Math.round((resolvedCount / violations.length) * 100) : 0;
   const resolveTxHash = (item?: any) => item?.txHash || item?.hash || 'N/A';

   useEffect(() => {
      const loadViolations = async () => {
         try {
            const response = await apiGet<{ violations: any[] }>('/api/signals/violations/');
            if (response.violations?.length) {
               setViolations(response.violations);
            }
         } catch {
            showToast('Unable to fetch violations from backend', 'error');
         }
      };
      loadViolations();
   }, []);

  const handleTakedown = (asset: string) => {
    showToast(`Takedown request initiated for ${asset}`, 'success');
  };

   const handleExportIpReport = () => {
      const sample = violations[0];
      try {
         downloadSentinelPdf({
            type: 'dmca',
            title: 'IP Enforcement Summary Report',
            refId: `IPR-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}`,
            assetName: 'Global Interdiction Feed Summary',
            orgName: user?.orgName || 'Your Organization',
            ...issuer,
            txHash: resolveTxHash(sample),
            similarity: sample?.sim || 'N/A',
            date: new Date().toISOString().split('T')[0],
         });
         showToast('IP report downloaded', 'success');
      } catch {
         showToast('IP report download failed on this device', 'error');
      }
   };

   const handleDownloadViolationReport = (assetName: string, platform: string, similarity: string, txHash?: string) => {
      try {
         downloadSentinelPdf({
            type: 'dmca',
            title: 'Technical Intel Report',
            refId: `INTEL-${Math.floor(Math.random() * 9000 + 1000)}`,
            assetName,
            platform,
            similarity,
            orgName: user?.orgName || 'Your Organization',
            ...issuer,
            txHash: txHash || 'N/A',
            date: new Date().toISOString().split('T')[0],
         });
         showToast(`Technical report downloaded for ${assetName}`, 'success');
      } catch {
         showToast('Download failed on this device', 'error');
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
              <div className="w-2 h-2 rounded-full bg-brand-danger animate-pulse" />
              <p className="text-xl font-bold text-white tracking-tight">Signal Intelligence Feed</p>
            </div>
          </div>
          <div className="flex gap-3">
             <button className="ghost-button" onClick={handleExportIpReport}>
                <FileText size={16} />
                Export IP Report
             </button>
             <button className="primary-button bg-brand-danger" onClick={() => showToast("Initializing global mass-interdiction sequence...", "warning")}>
                <Zap size={16} />
                Mass Takedown
             </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
           <div className="lg:col-span-3 glass-card p-6 bg-brand-danger/[0.02] border-brand-danger/10">
              <div className="flex items-center justify-between mb-8">
                 <h3 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
                    <ShieldAlert className="text-brand-danger w-4 h-4" />
                    Detection Surge Monitor
                 </h3>
                 <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                       <div className="w-1.5 h-1.5 rounded-full bg-brand-danger animate-pulse" />
                       <span className="text-[10px] font-mono text-brand-danger font-bold">{recentHits} NEW HITS (LAST 10M)</span>
                    </div>
                 </div>
              </div>
              <div className="h-[280px] w-full">
                 <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                       <defs>
                          <linearGradient id="colorLevel" x1="0" y1="0" x2="0" y2="1">
                             <stop offset="5%" stopColor="#EF4444" stopOpacity={0.2}/>
                             <stop offset="95%" stopColor="#EF4444" stopOpacity={0}/>
                          </linearGradient>
                       </defs>
                       <XAxis dataKey="name" stroke="#4A6080" fontSize={10} tickLine={false} axisLine={false} />
                       <YAxis stroke="#4A6080" fontSize={10} tickLine={false} axisLine={false} />
                       <Tooltip 
                          contentStyle={{ backgroundColor: '#05080F', border: '1px solid rgba(239,68,68,0.2)', borderRadius: '12px' }}
                          itemStyle={{ color: '#C8D8EA', fontSize: '11px' }}
                       />
                       <Area type="monotone" dataKey="hits" stroke="#EF4444" strokeWidth={2} fillOpacity={1} fill="url(#colorLevel)" />
                    </AreaChart>
                 </ResponsiveContainer>
              </div>
           </div>

           <div className="glass-card p-6 flex flex-col justify-between">
              <div>
                 <h4 className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest mb-6">Enforcement Rate</h4>
                 <div className="flex flex-col items-center mb-8">
                    <div className="relative w-32 h-32">
                       <svg className="w-full h-full transform -rotate-90">
                          <circle cx="64" cy="64" r="58" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-white/5" />
                          <circle cx="64" cy="64" r="58" stroke="currentColor" strokeWidth="8" fill="transparent" strokeDasharray={364} strokeDashoffset={364 - (364 * (successRate / 100))} className="text-brand-accent3 transition-all duration-1000" />
                       </svg>
                       <div className="absolute inset-0 flex flex-col items-center justify-center">
                          <span className="text-2xl font-bold text-white">{successRate}%</span>
                          <span className="text-[9px] text-brand-muted uppercase font-mono">Success</span>
                       </div>
                    </div>
                 </div>
              </div>
              <div className="space-y-3">
                 <div className="flex justify-between text-xs">
                    <span className="text-brand-muted uppercase font-mono text-[9px] tracking-wider">Automated</span>
                    <span className="text-white font-bold">{autoCount}</span>
                 </div>
                 <div className="flex justify-between text-xs">
                    <span className="text-brand-muted uppercase font-mono text-[9px] tracking-wider">Manual Review</span>
                    <span className="text-white font-bold">{manualCount}</span>
                 </div>
                 <div className="pt-3 border-t border-white/5">
                    <div className="flex justify-between text-xs">
                       <span className="text-brand-danger font-bold italic">Unresolved</span>
                       <span className="text-brand-danger font-bold uppercase font-mono">{unresolvedCount} Critical</span>
                    </div>
                 </div>
              </div>
           </div>
        </div>

        <div className="glass-card overflow-hidden">
           <div className="p-6 border-b border-brand-border flex items-center justify-between bg-white/[0.02]">
              <div className="flex items-center gap-6">
                 <h2 className="text-lg font-bold text-white">Global Interdiction Feed</h2>
                 <div className="flex items-center gap-3">
                    <div className="px-3 py-1 bg-brand-danger/10 text-brand-danger border border-brand-danger/30 rounded-lg text-[10px] font-bold font-mono tracking-widest uppercase animate-pulse">Critical Alert State</div>
                 </div>
              </div>
              <div className="flex items-center gap-4">
                 <div className="flex items-center gap-2 bg-black/20 rounded-lg px-3 py-1.5 border border-white/5">
                    <Search className="w-4 h-4 text-brand-muted" />
                    <input type="text" placeholder="Filter violations..." className="bg-transparent text-sm text-white outline-none w-48 font-mono" />
                 </div>
                 <button 
                   onClick={() => showToast("Applying advanced detection filters...", "info")}
                   className="ghost-button h-9 px-4 text-xs font-bold uppercase tracking-wider"
                 >
                    <Filter size={14} /> Refine Feed
                 </button>
              </div>
           </div>
           
           <div className="overflow-x-auto">
              <table className="w-full text-left">
                 <thead>
                    <tr className="border-b border-brand-border bg-white/[0.01] uppercase font-mono text-[10px] tracking-widest text-brand-muted">
                       <th className="px-6 py-4 font-bold">Severity</th>
                       <th className="px-6 py-4 font-bold">Involved Asset</th>
                       <th className="px-6 py-4 font-bold">Platform / Origin</th>
                       <th className="px-6 py-4 font-bold">Similarity DNA</th>
                       <th className="px-6 py-4 font-bold">Sync Info</th>
                       <th className="px-6 py-4 font-bold">Enforcement</th>
                       <th className="px-6 py-4 font-bold text-right pr-8">Actions</th>
                    </tr>
                 </thead>
                         <tbody className="divide-y divide-brand-border">
                              {violations.length === 0 ? (
                                 <tr>
                                    <td className="px-6 py-8 text-sm text-brand-muted" colSpan={7}>
                                       No violations detected yet.
                                    </td>
                                 </tr>
                              ) : violations.map((v, i) => (
                      <tr key={i} className="hover:bg-white/[0.02] transition-colors group">
                         <td className="px-6 py-4">
                            <div className={cn(
                               "w-2 h-2 rounded-full ring-4",
                               v.sev === 'high' ? 'bg-brand-danger ring-brand-danger/20 shadow-[0_0_12px_rgba(239,68,68,0.6)]' :
                               v.sev === 'med' ? 'bg-brand-warn ring-brand-warn/20' : 'bg-brand-accent3 ring-brand-accent3/20'
                            )} />
                         </td>
                         <td className="px-6 py-4">
                            <p className="text-sm font-bold text-white mb-0.5">{v.a}</p>
                            <p className="text-[10px] text-brand-muted uppercase font-mono tracking-tighter">FINGERPRINT MATCH ENABLED</p>
                         </td>
                         <td className="px-6 py-4">
                            <div className="flex items-center gap-2">
                               <div className="w-6 h-6 rounded-md bg-white/5 flex items-center justify-center">
                                  <Globe size={12} className="text-brand-muted" />
                               </div>
                               <span className="text-xs font-mono font-bold text-brand-muted uppercase">{v.p}</span>
                            </div>
                         </td>
                         <td className="px-6 py-4">
                            <span className={cn(
                              "text-[10px] font-mono px-2 py-0.5 rounded font-black",
                              v.sev === 'high' ? 'bg-brand-danger/20 text-brand-danger' : 
                              v.sev === 'med' ? 'bg-brand-warn/20 text-brand-warn' : 'bg-brand-accent3/20 text-brand-accent3'
                            )}>
                               {v.sim} DNA
                            </span>
                         </td>
                         <td className="px-6 py-4">
                            <div className="flex flex-col gap-1">
                               <p className="text-[10px] text-white flex items-center gap-1 font-mono">
                                  <Clock size={10} className="text-brand-muted" />
                                  {v.time}
                               </p>
                               <span className="text-[9px] text-brand-muted uppercase font-mono">Sector: EMEA-4</span>
                            </div>
                         </td>
                         <td className="px-6 py-4">
                            <div className="flex items-center gap-2">
                               {v.status === 'Blocked' ? <XCircle size={14} className="text-brand-danger" /> : 
                                v.status === 'Sent' ? <CheckCircle2 size={14} className="text-brand-accent3" /> :
                                <Clock size={14} className="text-brand-warn" />}
                               <span className={cn(
                                 "text-[10px] font-bold font-mono uppercase tracking-widest",
                                 v.status === 'Blocked' ? 'text-brand-danger' : 
                                 v.status === 'Sent' ? 'text-brand-accent3' : 
                                 'text-brand-muted'
                               )}>{v.status}</span>
                            </div>
                         </td>
                         <td className="px-6 py-4">
                                          <div className="flex justify-end gap-2 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-all pr-4">
                               <button 
                                                onClick={() => handleDownloadViolationReport(v.a, v.p, v.sim, (v as any).txHash || (v as any).hash)}
                                 className="p-2 text-brand-accent hover:bg-brand-accent/10 rounded-lg transition-colors border border-transparent hover:border-brand-accent/20"
                               >
                                  <Download size={14}/>
                               </button>
                               <button onClick={() => handleTakedown(v.a)} className="p-2 text-brand-danger hover:bg-brand-danger/10 rounded-lg transition-colors border border-transparent hover:border-brand-danger/20">
                                  <ShieldAlert size={14}/>
                               </button>
                               <button 
                                 onClick={() => showToast(`Opening deep-analysis for ${v.a}...`, "info")}
                                 className="p-2 text-brand-accent hover:bg-brand-accent/10 rounded-lg transition-colors"
                               >
                                  <ChevronRight size={16}/>
                               </button>
                            </div>
                         </td>
                      </tr>
                    ))}
                 </tbody>
              </table>
           </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pb-12">
           <div className="glass-card p-6 bg-brand-danger/[0.03] border border-brand-danger/20 flex gap-6 items-start">
              <div className="p-3 rounded-2xl bg-brand-danger/10 text-brand-danger border border-brand-danger/20">
                 <AlertTriangle className="w-8 h-8" />
              </div>
              <div>
                 <h4 className="text-lg font-bold text-white mb-2">High-Velocity Cluster Detected</h4>
                 <p className="text-xs text-brand-muted leading-relaxed mb-4">
                    AI models have identified a coordinated leak network across 42 Telegram channels originating from Sector: SEA-9. 
                    Immediate "Aggressive Suppression" mode recommended.
                 </p>
                 <button onClick={() => showToast("Suppression protocol authorized", "warning")} className="primary-button bg-brand-danger border-none h-9 text-xs">Authorize Suppression Protocol</button>
              </div>
           </div>
           <div className="glass-card p-6 border border-brand-accent/20 flex gap-6 items-start">
              <div className="p-3 rounded-2xl bg-brand-accent/10 text-brand-accent border border-brand-accent/20">
                 <Globe className="w-8 h-8" />
              </div>
              <div>
                 <h4 className="text-lg font-bold text-white mb-2">Global IP Blocking Active</h4>
                 <p className="text-xs text-brand-muted leading-relaxed mb-4">
                    Current defensive mesh has successfully sinkholed 8,204 pirate stream IPs in the last hour. 
                    Syncing with 4 ISPs for hardware-level DNS blocking.
                 </p>
                 <button onClick={() => showToast("Opening topology graph...", "info")} className="ghost-button border-brand-accent text-brand-accent h-9 text-xs">View Network Graph</button>
              </div>
           </div>
        </div>
      </main>
    </div>
  );
}
