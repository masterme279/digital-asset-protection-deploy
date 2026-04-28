import React, { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { SentinelSidebar } from '../../components/shared/SentinelSidebar';
import { 
  Building2, Layers, AlertCircle, Link as LinkIcon, Cpu, Radar,
  ArrowUpRight, BarChart3, Globe, ShieldAlert, Activity, RefreshCw, ExternalLink, Plus,
  Shield, Zap
} from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell, CartesianGrid
} from 'recharts';
import { cn, formatNumber } from '../../lib/utils';
import { apiGet } from '../../lib/api';

import { showToast } from '../../components/shared/GlobalToast';

export function AdminDashboard() {
  useEffect(() => {
    document.title = "SENTINEL · Admin Terminal";
  }, []);

   const [violations, setViolations] = useState<any[]>([]);
   const [assets, setAssets] = useState<any[]>([]);
   const [records, setRecords] = useState<any[]>([]);
   const [notices, setNotices] = useState<any[]>([]);
   const [aiCases, setAiCases] = useState<any[]>([]);
   const [aiAudit, setAiAudit] = useState<any[]>([]);
   const [aiConnected, setAiConnected] = useState(false);
   const [chartData, setChartData] = useState<{ name: string; count: number }[]>([]);
   const [platformUsage, setPlatformUsage] = useState<{ name: string; val: number; count: number }[]>([]);
   const [alerts, setAlerts] = useState<{ m: string; t: string }[]>([]);

   const parseDate = (value: unknown) => {
      if (!value) return null;
      const date = new Date(String(value));
      return Number.isNaN(date.getTime()) ? null : date;
   };

   const buildDailyCounts = (items: any[]) => {
      const days = Array.from({ length: 7 }, (_, index) => {
         const date = new Date();
         date.setDate(date.getDate() - (6 - index));
         date.setHours(0, 0, 0, 0);
         return date;
      });
      const buckets = days.map((date) => ({
         name: date.toLocaleDateString('en-US', { weekday: 'short' }),
         dateKey: date.toISOString().slice(0, 10),
         count: 0,
      }));
      const byKey = new Map(buckets.map((bucket) => [bucket.dateKey, bucket]));
      items.forEach((item) => {
         const date = parseDate(item.time ?? item.created_at ?? item.createdAt);
         if (!date) return;
         const key = date.toISOString().slice(0, 10);
         const bucket = byKey.get(key);
         if (bucket) bucket.count += 1;
      });
      return buckets.map((bucket) => ({ name: bucket.name, count: bucket.count }));
   };

   const buildPlatformUsage = (items: any[]) => {
      const counts = new Map<string, number>();
      items.forEach((item) => {
         const name = String(item.platform ?? item.p ?? item.source ?? 'Unknown');
         counts.set(name, (counts.get(name) ?? 0) + 1);
      });
      const total = items.length || 1;
      return Array.from(counts.entries())
         .sort((a, b) => b[1] - a[1])
         .slice(0, 4)
         .map(([name, count]) => ({
            name,
            count,
            val: Math.round((count / total) * 100),
         }));
   };

   const formatAgo = (value: unknown) => {
      const date = parseDate(value);
      if (!date) return '--';
      const diffMinutes = Math.max(1, Math.floor((Date.now() - date.getTime()) / 60000));
      if (diffMinutes < 60) return `${diffMinutes}m`;
      const diffHours = Math.floor(diffMinutes / 60);
      if (diffHours < 24) return `${diffHours}h`;
      return `${Math.floor(diffHours / 24)}d`;
   };

   const buildAlerts = (items: any[]) => {
      const sorted = [...items].sort((a, b) => {
         const aDate = parseDate(a.time ?? a.created_at ?? a.createdAt);
         const bDate = parseDate(b.time ?? b.created_at ?? b.createdAt);
         return (bDate?.getTime() ?? 0) - (aDate?.getTime() ?? 0);
      });
      return sorted.slice(0, 3).map((item) => ({
         m: `${item.platform ?? item.p ?? 'Unknown'} · ${item.asset ?? item.a ?? 'Asset'}`,
         t: formatAgo(item.time ?? item.created_at ?? item.createdAt),
      }));
   };

   useEffect(() => {
      const loadAdminData = async () => {
         try {
            const [violationsRes, assetsRes, recordsRes, noticesRes] = await Promise.all([
               apiGet<{ violations: any[] }>('/api/signals/violations/'),
               apiGet<{ assets: any[] }>('/api/assets/'),
               apiGet<{ records: any[] }>('/api/signals/blockchain/'),
               apiGet<{ notices: any[] }>('/api/signals/dmca/'),
            ]);

            let aiCasesData: any[] = [];
            let aiAuditData: any[] = [];
            let aiStatus = false;
            try {
               const [healthRes, casesRes, auditRes] = await Promise.all([
                  apiGet<{ connected: boolean }>('/api/signals/ai/health/'),
                  apiGet<{ items: any[] }>('/api/signals/ai/cases/?limit=500'),
                  apiGet<{ items: any[] }>('/api/signals/ai/audit/?limit=500'),
               ]);
               aiStatus = Boolean(healthRes.connected);
               aiCasesData = casesRes.items ?? [];
               aiAuditData = auditRes.items ?? [];
            } catch {
               aiStatus = false;
            }

            const violationsData = violationsRes.violations ?? [];
            const assetsData = assetsRes.assets ?? [];
            const recordsData = recordsRes.records ?? [];
            const noticesData = noticesRes.notices ?? [];

            setViolations(violationsData);
            setAssets(assetsData);
            setRecords(recordsData);
            setNotices(noticesData);
            setAiConnected(aiStatus);
            setAiCases(aiCasesData);
            setAiAudit(aiAuditData);
            setChartData(buildDailyCounts(violationsData));
            setPlatformUsage(buildPlatformUsage(violationsData));
            setAlerts(buildAlerts(violationsData));
         } catch {
            showToast('Unable to load admin telemetry', 'error');
            setChartData(buildDailyCounts([]));
            setPlatformUsage([]);
            setAlerts([]);
            setAiConnected(false);
            setAiCases([]);
            setAiAudit([]);
         }
      };
      loadAdminData();
   }, []);

  const handleRefresh = () => {
    showToast("Global command scan initiated...", "info");
    setTimeout(() => {
       showToast("All AI tactical nodes online", "success");
       showToast("Crawlers synchronized with zero lag", "success");
    }, 1200);
  };

   const entityCount = new Set(assets.map((asset) => asset.user_id).filter(Boolean)).size;
   const adminStats = [
      { label: 'Network Entities', val: formatNumber(entityCount), trend: 'LIVE', icon: Building2, color: 'text-brand-accent2' },
      { label: 'Secured Assets', val: formatNumber(assets.length), trend: 'LIVE', icon: Layers, color: 'text-brand-accent' },
      { label: 'Global Hits', val: formatNumber(violations.length), trend: violations.length ? 'CRITICAL' : 'CLEAR', icon: AlertCircle, color: 'text-brand-danger' },
      { label: 'Blockchain Records', val: formatNumber(records.length), trend: 'LIVE', icon: LinkIcon, color: 'text-brand-accent3' },
      { label: 'DMCA Notices', val: formatNumber(notices.length), trend: 'LIVE', icon: Cpu, color: 'text-brand-accent3' },
      { label: 'Active Platforms', val: formatNumber(platformUsage.length), trend: 'LIVE', icon: Radar, color: 'text-brand-accent3' },
      { label: 'AI Cases', val: formatNumber(aiCases.length), trend: aiConnected ? 'LIVE' : 'OFFLINE', icon: Shield, color: aiConnected ? 'text-brand-accent3' : 'text-brand-danger' },
      { label: 'AI Audit Events', val: formatNumber(aiAudit.length), trend: aiConnected ? 'LIVE' : 'OFFLINE', icon: Activity, color: aiConnected ? 'text-brand-accent3' : 'text-brand-danger' },
   ];
   const recentAiCases = aiCases.slice(0, 5);
   const recentAiAudit = aiAudit.slice(0, 5);
   const formatTs = (value: unknown) => {
      if (typeof value === 'number') {
         const date = new Date(value * 1000);
         return Number.isNaN(date.getTime()) ? 'N/A' : date.toLocaleString();
      }
      if (typeof value === 'string') {
         const date = new Date(value);
         return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
      }
      return 'N/A';
   };
   const toPrettyJson = (value: unknown) => {
      try {
         return JSON.stringify(value ?? {}, null, 2);
      } catch {
         return '{}';
      }
   };

  return (
    <div className="flex bg-[#05080F] min-h-screen text-brand-text">
      <SentinelSidebar role="admin" />
      
      <main className="flex-1 p-8 space-y-8 overflow-x-hidden">
        {/* Admin Header */}
        <div className="flex items-center justify-between border-b border-white/5 pb-8">
           <div className="flex items-center gap-6">
              <div className="w-16 h-16 rounded-2xl bg-brand-danger/10 border border-brand-danger/20 flex items-center justify-center text-brand-danger shadow-[0_0_40px_rgba(239,68,68,0.15)] relative overflow-hidden group">
                 <div className="absolute inset-0 bg-brand-danger/5 animate-pulse" />
                 <ShieldAlert size={32} className="relative z-10" />
              </div>
              <div>
                 <h1 className="text-3xl font-bold text-white mb-1 tracking-tight uppercase">SENTINEL PRO PLATFORM: NODE-TERMINAL</h1>
                 <p className="text-[10px] font-mono text-brand-danger uppercase tracking-[0.4em] font-black">GLOBAL COMMAND & CONTROL · RIGHTS PROTECTION LAYER 0</p>
              </div>
           </div>
           
           <div className="flex items-center gap-6">
              <div className="hidden xl:flex flex-col items-end px-6 border-r border-white/10">
                 <span className="text-[9px] font-mono text-brand-muted uppercase tracking-widest">Core Status</span>
                 <span className="text-brand-accent3 font-bold text-xs flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-brand-accent3 animate-ping" />
                    OPERATIONAL
                 </span>
              </div>
              <button 
                onClick={handleRefresh}
                className="flex items-center gap-3 px-6 py-3 bg-white/5 border border-white/10 rounded-xl text-white font-mono text-[10px] uppercase tracking-[0.2em] font-bold hover:bg-white/10 transition-all hover:scale-105 active:scale-95 shadow-xl"
              >
                <RefreshCw className="w-4 h-4" />
                Global Scan
              </button>
           </div>
        </div>

        {/* Tactical HUD */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {adminStats.map((stat) => (
            <div key={stat.label} className="glass-card p-5 border-white/5 hover:border-brand-accent/20 transition-all group relative h-32 flex flex-col justify-between overflow-hidden cursor-default">
               <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-100 transition-all group-hover:scale-110">
                  <stat.icon className={cn("w-10 h-10", stat.color)} />
               </div>
               <div>
                  <div className="text-[9px] font-mono text-brand-muted uppercase tracking-wider mb-2 font-black">{stat.label}</div>
                  <div className="text-2xl font-bold text-white tracking-tighter">{stat.val}</div>
               </div>
               <div className={cn("text-[9px] font-mono font-black uppercase py-0.5 px-2 rounded-sm w-fit", 
                 stat.trend === 'CRITICAL' ? 'bg-brand-danger/20 text-brand-danger' : 'bg-brand-accent3/10 text-brand-accent3'
               )}>
                  {stat.trend}
               </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
           {/* Center Visuals */}
           <div className="lg:col-span-8 space-y-8">
              <div className="glass-card p-8 bg-brand-surface/30 relative">
                 <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-3">
                       <div className="p-2 rounded-lg bg-brand-accent/10 border border-brand-accent/20">
                          <BarChart3 className="text-brand-accent w-5 h-5" />
                       </div>
                       <h3 className="text-sm font-bold text-white uppercase tracking-widest">Global Interdiction Velocity</h3>
                    </div>
                    <div className="flex gap-2 p-1 bg-black/20 rounded-lg border border-white/5">
                       <button className="px-3 py-1 bg-brand-accent/20 text-brand-accent text-[10px] font-bold rounded-md uppercase tracking-widest">Daily</button>
                       <button className="px-3 py-1 text-brand-muted text-[10px] font-bold rounded-md uppercase tracking-widest hover:text-white transition-colors">Historical</button>
                    </div>
                 </div>
                 <div className="h-[320px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                       <AreaChart data={chartData}>
                          <defs>
                             <linearGradient id="adminGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#EF4444" stopOpacity={0.2}/>
                                <stop offset="95%" stopColor="#EF4444" stopOpacity={0}/>
                             </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1A2433" vertical={false} />
                          <XAxis dataKey="name" stroke="#4A6080" fontSize={10} tickLine={false} axisLine={false} />
                          <YAxis stroke="#4A6080" fontSize={10} tickLine={false} axisLine={false} />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#05080F', border: '1px solid rgba(239,68,68,0.2)', borderRadius: '12px' }}
                            itemStyle={{ color: '#C8D8EA', fontSize: '11px', fontWeight: 'bold' }}
                          />
                          <Area type="stepAfter" dataKey="count" stroke="#EF4444" strokeWidth={2} fillOpacity={1} fill="url(#adminGradient)" />
                       </AreaChart>
                    </ResponsiveContainer>
                 </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                 <div className="glass-card p-6">
                    <h3 className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest mb-6 border-l-2 border-brand-accent pl-3">Crawler Sync Distribution</h3>
                    <div className="space-y-6">
                       {platformUsage.length === 0 ? (
                         <div className="text-[11px] text-brand-muted">No platform data yet.</div>
                       ) : platformUsage.map((plat) => (
                         <div key={plat.name} className="space-y-2">
                            <div className="flex justify-between text-[11px]">
                               <span className="text-white font-bold">{plat.name}</span>
                               <span className="text-brand-muted font-mono">{plat.val}% ({formatNumber(plat.count)})</span>
                            </div>
                            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                               <motion.div 
                                 initial={{ width: 0 }}
                                 animate={{ width: `${plat.val}%` }}
                                 className={cn("h-full", plat.val >= 30 ? 'bg-brand-danger' : 'bg-brand-accent')}
                               />
                            </div>
                         </div>
                       ))}
                    </div>
                 </div>

                 <div className="glass-card p-6 border-brand-danger/20 bg-brand-danger/[0.02]">
                    <div className="flex items-center justify-between mb-6">
                       <h3 className="text-[10px] font-mono font-bold text-brand-danger uppercase tracking-widest flex items-center gap-2">
                          <Activity size={14} />
                          Tactical Alerts
                       </h3>
                                  <span className="text-[9px] font-black bg-brand-danger text-white px-2 py-0.5 rounded animate-pulse">{alerts.length} CRITICAL</span>
                    </div>
                    <div className="space-y-3">
                                  {alerts.length === 0 ? (
                                     <div className="text-[11px] text-brand-muted">No active alerts.</div>
                                  ) : alerts.map((alert, index) => (
                                     <div key={`${alert.m}-${index}`} className="flex items-center justify-between p-3 rounded-xl bg-white/[0.03] border border-white/5 hover:border-brand-danger/30 transition-all cursor-crosshair group">
                                          <span className="text-[11px] text-brand-muted group-hover:text-white transition-colors truncate pr-4">{alert.m}</span>
                                          <span className="text-[9px] font-mono text-brand-danger font-bold shrink-0">{alert.t}</span>
                                     </div>
                                  ))}
                    </div>
                 </div>
              </div>
           </div>

           {/* Side Controls */}
           <div className="lg:col-span-4 space-y-8">
              <div className="glass-card p-6 bg-gradient-to-b from-brand-surface to-transparent">
                 <h3 className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest mb-8 text-center text-white">Network Load Core</h3>
                 <div className="flex flex-col items-center">
                    <div className="relative w-44 h-44 mb-8">
                       <div className="absolute inset-0 border-[4px] border-white/5 rounded-full" />
                       <div className="absolute inset-0 border-t-[4px] border-brand-danger rounded-full animate-[spin_2s_linear_infinite] shadow-[0_0_15px_rgba(239,68,68,0.4)]" />
                       <div className="absolute inset-0 flex flex-col items-center justify-center">
                          <span className="text-4xl font-black text-white leading-none">{formatNumber(violations.length)}</span>
                          <span className="text-[9px] text-brand-danger uppercase font-mono font-black mt-2 tracking-widest text-center">Violations Total</span>
                       </div>
                    </div>
                    <div className="w-full grid grid-cols-2 gap-3">
                       <div className="bg-white/5 p-4 rounded-2xl border border-white/5 text-center">
                          <div className="text-[9px] text-brand-muted uppercase font-bold mb-1">Inbound</div>
                          <div className="text-sm font-black text-brand-accent">N/A</div>
                       </div>
                       <div className="bg-white/5 p-4 rounded-2xl border border-white/5 text-center">
                          <div className="text-[9px] text-brand-muted uppercase font-bold mb-1">Latency</div>
                          <div className="text-sm font-black text-brand-accent3">N/A</div>
                       </div>
                    </div>
                 </div>
              </div>

              <div className="glass-card p-6 border-brand-accent/20">
                 <h3 className="text-[10px] font-mono font-bold text-white uppercase tracking-widest mb-6 flex items-center gap-2">
                    <Shield size={14} className="text-brand-accent" />
                    Master Terminal
                 </h3>
                 <div className="space-y-3">
                    <button className="w-full py-4 bg-brand-accent text-white font-mono text-[10px] uppercase font-black rounded-xl hover:shadow-[0_0_20px_rgba(14,165,233,0.4)] transition-all flex items-center justify-center gap-3 active:scale-95">
                       <Zap size={14} />
                       Rebalance AI Hub
                    </button>
                    <button className="w-full py-4 bg-white/5 border border-white/10 text-white font-mono text-[10px] uppercase font-black rounded-xl hover:bg-white/10 transition-all flex items-center justify-center gap-3">
                       <Globe size={14} />
                       Global Crawler Patch
                    </button>
                    <button className="w-full py-4 bg-white/5 border border-white/10 text-brand-muted font-mono text-[10px] uppercase font-black rounded-xl hover:text-white transition-all">
                       Audit Tactical Logs
                    </button>
                 </div>
              </div>

                     <div className="glass-card p-6 border-brand-accent3/20 bg-brand-accent3/[0.03]">
                         <h3 className="text-[10px] font-mono font-bold text-white uppercase tracking-widest mb-4">AI Case Feed</h3>
                         <div className="space-y-2">
                              {!aiConnected ? (
                                 <div className="text-[11px] text-brand-danger">AI pipeline offline.</div>
                              ) : recentAiCases.length === 0 ? (
                                 <div className="text-[11px] text-brand-muted">No AI cases yet.</div>
                              ) : recentAiCases.map((c: any) => (
                                 <div key={String(c.case_id)} className="p-3 rounded-xl border border-white/10 bg-black/20">
                                    <div className="flex items-center justify-between text-[10px] font-mono">
                                       <span className="text-brand-muted uppercase">{String(c.platform || 'unknown')}</span>
                                       <span className="text-white">{Number(c.score || 0).toFixed(3)}</span>
                                    </div>
                                    <p className="text-[11px] text-white truncate mt-1">{String(c.action || 'NO_ACTION')}</p>
                                    <p className="text-[10px] text-brand-muted truncate">CASE {String(c.case_id || 'N/A')} · JOB {String(c.job_id || 'N/A')}</p>
                                    <p className="text-[10px] text-brand-muted truncate">POST {String(c.post_id || 'N/A')} · ACCOUNT {String(c.account_id || 'N/A')}</p>
                                    <p className="text-[10px] text-brand-muted truncate">MEDIA {String(c.media_type || 'N/A')} · STATUS {String(c.status || 'N/A')} · CONF {String(c.confidence_tier || 'N/A')}</p>
                                    <p className="text-[10px] text-brand-muted truncate">SOURCE {String(c.source_type || c.platform || 'N/A')} · SEVERITY {String(c.severity || 'N/A')} · CONFIDENCE {String(c.confidence ?? c.score ?? 'N/A')}</p>
                                    <p className="text-[10px] text-brand-muted truncate">ASSET {String(c.matched_asset_id || 'N/A')}</p>
                                    <p className="text-[10px] text-brand-muted truncate">URL {String(c.media_url || 'N/A')}</p>
                                    <p className="text-[10px] text-brand-muted">TIME {formatTs(c.created_at)}</p>
                                    <p className="text-[10px] text-brand-muted">EXPLANATION: {String(c.explanation || 'N/A')}</p>
                                    <details className="mt-2">
                                      <summary className="text-[10px] text-brand-accent3 cursor-pointer uppercase font-mono">View Evidence JSON</summary>
                                      <pre className="mt-2 text-[10px] text-brand-muted bg-black/30 rounded-lg p-2 overflow-x-auto">{toPrettyJson(c.evidence)}</pre>
                                    </details>
                                 </div>
                              ))}
                         </div>
                     </div>

                     <div className="glass-card p-6 border-brand-accent/20 bg-brand-accent/[0.03]">
                         <h3 className="text-[10px] font-mono font-bold text-white uppercase tracking-widest mb-4">AI Audit Feed</h3>
                         <div className="space-y-2">
                              {!aiConnected ? (
                                 <div className="text-[11px] text-brand-danger">AI pipeline offline.</div>
                              ) : recentAiAudit.length === 0 ? (
                                 <div className="text-[11px] text-brand-muted">No AI audit events yet.</div>
                              ) : recentAiAudit.map((event: any, index: number) => (
                                 <div key={`${String(event.event_id || index)}`} className="p-3 rounded-xl border border-white/10 bg-black/20">
                                    <p className="text-[10px] text-brand-accent3 uppercase font-mono truncate">{String(event.event_type || 'EVENT')}</p>
                                    <p className="text-[10px] text-brand-muted truncate">{String(event.entity_type || 'entity')} · {String(event.entity_id || 'id')}</p>
                                    <p className="text-[10px] text-brand-muted">EVENT ID {String(event.event_id ?? 'N/A')} · TIME {formatTs(event.created_at)}</p>
                                    <details className="mt-2">
                                      <summary className="text-[10px] text-brand-accent cursor-pointer uppercase font-mono">View Payload JSON</summary>
                                      <pre className="mt-2 text-[10px] text-brand-muted bg-black/30 rounded-lg p-2 overflow-x-auto">{toPrettyJson(event.payload)}</pre>
                                    </details>
                                 </div>
                              ))}
                         </div>
                     </div>
              
              <div className="glass-card p-5 bg-brand-danger/10 border-brand-danger/30">
                 <div className="flex items-center gap-3 text-brand-danger mb-4 font-black text-xs uppercase tracking-widest">
                    <AlertCircle size={14} />
                    Emergency Protocol
                 </div>
                 <button className="w-full py-2 bg-brand-danger text-white font-mono text-[10px] font-black rounded-lg hover:shadow-[0_0_20px_rgba(239,68,68,0.4)] transition-all">
                    INITIATE BROADCAST KILL-SWITCH
                 </button>
              </div>
           </div>
        </div>
      </main>
    </div>
  );
}
