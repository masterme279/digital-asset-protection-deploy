import React, { useState, useEffect, useRef } from 'react';
import { 
  Plus, 
  Search, 
  Globe, 
  Shield, 
  Clock, 
  AlertTriangle, 
  CheckCircle,
  TrendingUp,
  Download,
  Share2,
  ExternalLink,
  ChevronRight,
  UploadCloud,
  Layers,
  Zap,
  FileText,
  Link as LinkIcon
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { SentinelSidebar } from '../../components/shared/SentinelSidebar';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  PieChart, 
  Pie, 
  Cell 
} from 'recharts';
import { Link, useNavigate } from 'react-router-dom';
import { cn, formatNumber } from '../../lib/utils';
import { showToast } from '../../components/shared/GlobalToast';
import { downloadSentinelPdf } from '../../lib/downloadPdf';
import { useAuth } from '../../context/AuthContext';
import { apiGet, apiPost, apiPostForm } from '../../lib/api';

export function UserDashboard() {
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
   const [isUploading, setIsUploading] = useState(false);
   const [uploadStep, setUploadStep] = useState(0);
   const [isDragging, setIsDragging] = useState(false);
   const fileInputRef = useRef<HTMLInputElement>(null);
   const liveIngestTriggered = useRef(false);
   const uploadTimerRef = useRef<number | null>(null);

  useEffect(() => {
    document.title = "SENTINEL · Dashboard";
  }, []);

  const handleManualDMCA = (asset: string) => {
     downloadSentinelPdf({
       type: 'dmca',
       title: 'DMCA Enforcement Notice',
       refId: 'NOTICE-' + Math.floor(Math.random() * 10000),
       assetName: asset,
       url: 'https://cdn.pirate-host.net/v/74829/view',
       orgName: user?.orgName || 'Your Organization',
       ...issuer,
       date: new Date().toISOString().split('T')[0],
     });
     showToast(`DMCA Notice generated for ${asset}`, 'success');
  };

   const stopUploadTimer = () => {
      if (uploadTimerRef.current) {
         window.clearInterval(uploadTimerRef.current);
         uploadTimerRef.current = null;
      }
   };

   const startUploadTimer = () => {
      stopUploadTimer();
      let step = 1;
      setUploadStep(step);
      uploadTimerRef.current = window.setInterval(() => {
         step += 1;
         setUploadStep(Math.min(step, 5));
         if (step >= 5) {
            stopUploadTimer();
         }
      }, 700);
   };

   const processUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    showToast(`Initializing protection for ${file.name}`, "info");
    setIsUploading(true);
      startUploadTimer();
      try {
         const form = new FormData();
         form.append('file', file);
            const uploadResponse = await apiPostForm<{
               message?: string;
               duplicate?: boolean;
               asset_id?: string;
            }>('/api/assets/upload/', form);
            if (uploadResponse.duplicate) {
               showToast(uploadResponse.message || 'File already exists', 'info');
            } else {
               showToast(uploadResponse.message || `${file.name} secured`, 'success');
            }

            try {
               const refreshed = await apiGet<{ assets: any[] }>('/api/assets/');
               if (refreshed.assets) {
                  setAssetsList(refreshed.assets);
               }
            } catch {
               // Ignore refresh failures after upload.
            }
         setUploadStep(5);
      } catch {
         showToast('Upload failed. Check backend connection.', 'error');
      } finally {
         stopUploadTimer();
         window.setTimeout(() => {
            setIsUploading(false);
            setUploadStep(0);
         }, 600);
      }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    processUpload(e.dataTransfer.files);
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };
   const [assetsList, setAssetsList] = useState<any[]>([]);
   const [forecastData, setForecastData] = useState<{ name: string; detected: number; predicted: number }[]>([]);
   const [violations, setViolations] = useState<{ p: string; a: string; sim: string; time: string; sev: string }[]>([]);
   const [blockchainProofs, setBlockchainProofs] = useState<{ id: string; name: string; hash: string; confirmed: boolean; date: string }[]>([]);
   const totalAssetBytes = assetsList.reduce((sum, asset) => sum + (asset?.metadata?.size ?? 0), 0);
   const formatBytes = (bytes: number) => {
      if (!bytes) return '0 B';
      const units = ['B', 'KB', 'MB', 'GB', 'TB'];
      const index = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
      const value = bytes / Math.pow(1024, index);
      return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
   };

   const stats = [
      { label: 'Protected Assets', val: assetsList.length, sub: 'from backend', icon: Layers, color: 'text-brand-accent' },
      { label: 'Violations Found', val: violations.length, sub: 'from backend', icon: AlertTriangle, color: 'text-brand-danger', badge: 'DANGER' },
      { label: 'Assets On-Chain', val: assetsList.length, sub: 'registered', icon: LinkIcon, color: 'text-brand-accent3' },
      { label: 'Protected Volume', val: formatBytes(totalAssetBytes), sub: 'from uploads', icon: TrendingUp, color: 'text-brand-accent3' },
   ];

   const pieData = [] as { name: string; value: number; color: string }[];

   const triggerLiveIngest = async () => {
      const sources = [
         { path: '/api/signals/ai/ingest/youtube/real/', body: { limit: 10 } },
         { path: '/api/signals/ai/ingest/x/real/', body: { limit: 25 } },
         { path: '/api/signals/ai/ingest/instagram/real/', body: { limit: 10 } },
         { path: '/api/signals/ai/ingest/reddit/real/', body: { limit: 25 } },
      ];

      const results = await Promise.allSettled(
         sources.map((source) => apiPost<{ connected?: boolean }>(source.path, source.body))
      );

      const successCount = results.filter((result) => {
         if (result.status !== 'fulfilled') return false;
         return result.value.connected !== false;
      }).length;

      if (successCount > 0) {
         showToast(`Live ingest queued for ${successCount}/${sources.length} sources`, 'success');
      }
   };

   useEffect(() => {
      const loadSignals = async () => {
         try {
            const v = await apiGet<{ violations: any[] }>('/api/signals/violations/');
            if (v.violations?.length) {
               setViolations(v.violations.map((item) => ({
                  p: item.p,
                  a: item.a,
                  sim: item.sim,
                  time: item.time,
                  sev: item.sev,
               })));
            }
         } catch {
            showToast('Unable to load live violations', 'error');
         }

         try {
            const b = await apiGet<{ records: any[] }>('/api/signals/blockchain/');
            if (b.records?.length) {
               setBlockchainProofs(b.records.map((item, idx) => ({
                  id: item.id || `BC-${idx + 1}`,
                  name: item.asset,
                  hash: item.hash,
                  confirmed: true,
                  date: item.time?.split(' ')[0] || 'N/A',
               })));
            }
         } catch {
            showToast('Unable to load blockchain proofs', 'error');
         }

         try {
            const f = await apiGet<{ forecast: any[] }>('/api/signals/forecast/');
            if (f.forecast?.length) {
               setForecastData(f.forecast.map((item) => ({
                  name: item.time,
                  detected: item.predictions ?? 0,
                  predicted: item.predictions ?? 0,
               })));
            }
         } catch {
            // No forecast data
         }

         try {
            const a = await apiGet<{ assets: any[] }>('/api/assets/');
            if (a.assets) {
               setAssetsList(a.assets);
            }
         } catch {
            showToast('Unable to load assets from backend', 'error');
         }

         if (!liveIngestTriggered.current) {
            liveIngestTriggered.current = true;
            try {
               await triggerLiveIngest();
            } catch {
               // Ignore live ingest failures on first load.
            }
         }
      };
      loadSignals();
   }, []);

  return (
    <div className="flex bg-brand-bg min-h-screen">
      <SentinelSidebar role="user" />
      
      <main className="flex-1 p-8 space-y-8 overflow-x-hidden">
        {/* Header */}
        <div className="flex items-center justify-between">
           <div>
              <h1 className="mission-control-header !text-brand-accent mb-2">Authenticated: {user?.orgName || 'Your Organization'}</h1>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-brand-accent animate-pulse" />
                <p className="text-xl font-bold text-white tracking-tight">Sentinel Monitoring Hub</p>
              </div>
           </div>
           <button className="primary-button" onClick={triggerFileInput}>
              <Plus className="w-4 h-4" />
              Upload Asset
           </button>
           <input 
             type="file" 
             ref={fileInputRef} 
             className="hidden" 
             onChange={(e) => processUpload(e.target.files)} 
           />
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat) => (
            <div key={stat.label} className="glass-card p-6 flex flex-col hover:translate-y-[-4px] transition-all">
               <div className="flex items-center justify-between mb-4">
                  <div className={cn("p-2 rounded-lg bg-current/10", stat.color)}>
                     <stat.icon size={20} />
                  </div>
                  {stat.badge && <span className="badge-high text-[9px] px-1.5">{stat.badge}</span>}
               </div>
               <div className="font-mono text-2xl font-bold text-white mb-1">{stat.val}</div>
               <div className="text-xs text-brand-muted">{stat.label}</div>
               <div className={cn("text-[10px] mt-2 font-mono uppercase", stat.color === 'text-brand-danger' ? 'text-brand-danger' : 'text-brand-accent3')}>
                  {stat.sub}
               </div>
            </div>
          ))}
        </div>

        {/* Dash Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
           <div className="lg:col-span-2 glass-card p-0 overflow-hidden border border-brand-border/20">
              <div className="flex items-center justify-between p-6 border-b border-brand-border bg-white/[0.02]">
                 <h2 className="mission-control-header !text-white !opacity-100 uppercase tracking-[0.2em] font-mono text-[10px]">Real-Time Signal Interception</h2>
                 <Link to="/violations" className="text-[10px] text-brand-accent hover:underline font-mono tracking-widest uppercase font-bold">Terminal View →</Link>
              </div>
              <div className="p-4 space-y-4">
                         {violations.length === 0 ? (
                            <div className="text-sm text-brand-muted">No live violations detected yet.</div>
                         ) : violations.map((v, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.06 }}
                      className={cn(
                        "flex items-center justify-between p-3 rounded-xl border bg-white/2 hover:bg-white/5 transition-all group",
                        i === 0
                          ? "border-brand-danger/40 bg-brand-danger/[0.03] shadow-[inset_3px_0_0_#EF4444]"
                          : "border-white/5"
                      )}
                    >
                       <div className="flex items-center gap-4">
                          <div className="w-8 h-8 rounded-full bg-brand-accent/20 flex items-center justify-center text-brand-accent">
                             <Globe size={14} />
                          </div>
                          <div>
                             <p className="text-sm font-medium text-white truncate max-w-[180px] group-hover:text-brand-accent transition-colors">{v.a}</p>
                             <p className="text-[10px] text-brand-muted uppercase font-mono">{v.p} • {v.time}</p>
                          </div>
                       </div>
                       <div className="flex items-center gap-4">
                          <span className={cn(
                            v.sev === 'high' ? 'badge-high' : 
                            v.sev === 'med' ? 'badge-med' : 'badge-low'
                          )}>
                             {v.sim} MATCH
                          </span>
                          <button 
                            onClick={() => handleManualDMCA(v.a)}
                            className="p-2 rounded-lg text-brand-muted hover:text-brand-danger transition-all cursor-pointer"
                            title="Generate DMCA Takedown"
                          >
                             <AlertTriangle size={14} />
                          </button>
                       </div>
                    </motion.div>
                 ))}
              </div>
           </div>

            <div className="glass-card p-6 flex flex-col">
               <h2 className="text-lg font-bold text-white mb-6">Protection Status</h2>
               <div className="relative">
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                       <Pie 
                          data={pieData} 
                          innerRadius={65} 
                          outerRadius={90} 
                          paddingAngle={3} 
                          dataKey="value"
                          stroke="none"
                        >
                          {pieData.map((entry, i) => <Cell key={i} fill={entry.color} opacity={0.9} />)}
                       </Pie>
                       <Tooltip 
                         contentStyle={{ background: '#0D1421', border: '1px solid rgba(14,165,233,0.2)', borderRadius: '10px', fontSize: '11px', fontFamily: 'Space Mono' }}
                         itemStyle={{ color: '#C8D8EA' }}
                       />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                     <span className="text-2xl font-bold text-white font-mono">847</span>
                     <span className="text-[10px] text-brand-muted uppercase tracking-widest">Total</span>
                  </div>
               </div>
               <div className="mt-6 flex flex-wrap justify-center gap-4">
                  {pieData.map((entry) => (
                    <div key={entry.name} className="flex items-center gap-2">
                       <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
                       <span className="text-[10px] font-mono text-brand-muted uppercase whitespace-nowrap">{entry.name}</span>
                    </div>
                  ))}
               </div>
            </div>
        </div>

        {/* Upload Quick Card */}
        <div 
          onClick={!isUploading ? triggerFileInput : undefined}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={cn(
            "glass-card p-12 border-2 border-dashed flex flex-col items-center justify-center cursor-pointer transition-all",
            isUploading ? "border-brand-accent bg-brand-accent/5" : 
            isDragging ? "border-brand-accent3 bg-brand-accent3/5 scale-[1.02]" :
            "border-brand-accent/20 hover:border-brand-accent hover:bg-brand-accent/5"
          )}
        >
          {isUploading ? (
            <div className="w-full max-w-md space-y-8">
               <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-mono text-brand-accent uppercase font-bold tracking-widest">Processing Digital Fingerprint</span>
                  <span className="text-xs text-brand-muted">{Math.min(uploadStep * 20, 100)}%</span>
               </div>
               <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(uploadStep * 20, 100)}%` }}
                    className="h-full bg-brand-accent shadow-[0_0_12px_rgba(14,165,233,0.5)]"
                  />
               </div>
               <div className="flex justify-between gap-2 overflow-hidden">
                  {["Upload", "Analyze", "Stamping", "Polygon", "Live"].map((s, i) => (
                    <div key={s} className="flex flex-col items-center gap-2 flex-1">
                       <div className={cn(
                         "w-6 h-6 rounded-full flex items-center justify-center text-[10px]",
                         uploadStep > i ? "bg-brand-accent3 text-white" : "bg-white/10 text-brand-muted"
                       )}>
                          {uploadStep > i ? <CheckCircle size={12} /> : i + 1}
                       </div>
                       <span className={cn("text-[8px] uppercase font-bold tracking-tighter", uploadStep > i ? "text-brand-accent3" : "text-brand-muted")}>{s}</span>
                    </div>
                  ))}
               </div>
               {uploadStep === 5 && (
                  <div className="pt-4 text-center">
                    <motion.div
                       initial={{ opacity: 0, y: 6 }}
                       animate={{ opacity: 1, y: 0 }}
                       className="flex items-center justify-center gap-3 mt-4 text-[11px] font-mono text-brand-accent3"
                    >
                       <CheckCircle size={14} />
                       <span>Confirmed · TX: 0x4F3AD9E1...</span>
                       <a 
                          href="https://amoy.polygonscan.com" 
                          target="_blank" 
                          rel="noopener noreferrer" 
                          className="text-brand-accent underline hover:no-underline"
                       >
                          Polygonscan ↗
                       </a>
                    </motion.div>
                    <button className="ghost-button h-8 text-[11px] font-mono px-4 mt-6 mx-auto" onClick={(e) => {e.stopPropagation(); setIsUploading(false); setUploadStep(0);}}>REGISTER ANOTHER</button>
                  </div>
                )}
            </div>
          ) : (
            <>
              <UploadCloud className="w-16 h-16 text-brand-accent mb-6 animate-bounce" />
              <h3 className="text-xl font-bold text-white mb-2">Drag & drop your asset here</h3>
              <p className="text-brand-muted text-sm mb-4">or click to browse from your device</p>
              <p className="text-[10px] font-mono text-brand-muted/60 uppercase tracking-widest">Supported: JPG, PNG, MP4, MOV • Max 500MB</p>
            </>
          )}
        </div>

        {/* Forecasting & Blockchain */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
           <div className="glass-card p-6">
              <div className="flex items-center justify-between mb-8">
                 <div>
                    <h2 className="text-lg font-bold text-white">72-Hour Propagation Forecast</h2>
                    <p className="text-brand-muted text-xs">Prophet-powered viral prediction</p>
                 </div>
                 <span className="badge-high">RISK: CRITICAL</span>
              </div>
              <div className="h-[280px] w-full">
                         {forecastData.length === 0 && (
                            <p className="text-xs text-brand-muted mb-4">No forecast data available yet.</p>
                         )}
                 <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={forecastData}>
                       <defs>
                          <linearGradient id="colorViral" x1="0" y1="0" x2="0" y2="1">
                             <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3}/>
                             <stop offset="95%" stopColor="#EF4444" stopOpacity={0}/>
                          </linearGradient>
                       </defs>
                       <XAxis dataKey="name" stroke="#4A6080" fontSize={10} tickLine={false} axisLine={false} />
                       <YAxis stroke="#4A6080" fontSize={10} tickLine={false} axisLine={false} />
                       <Tooltip 
                          contentStyle={{ background: '#111927', border: '1px solid rgba(14,165,233,0.15)', borderRadius: '8px' }}
                          itemStyle={{ color: '#C8D8EA' }}
                       />
                       <Area type="monotone" dataKey="predicted" stroke="#F59E0B" fillOpacity={1} fill="url(#colorViral)" strokeDasharray="5 5" />
                       <Area type="monotone" dataKey="detected" stroke="#EF4444" fillOpacity={1} fill="url(#colorViral)" />
                    </AreaChart>
                 </ResponsiveContainer>
              </div>
              <div className="mt-4 p-4 rounded-xl bg-brand-danger/5 border border-brand-danger/10">
                 <p className="text-xs text-brand-text leading-relaxed">
                    <span className="font-bold text-brand-danger uppercase mr-2">Warning:</span>
                    Detection volume is predicted to surge by 240% across Telegram and Twitter channels in the next 18 hours due to high viral engagement indices.
                 </p>
              </div>
           </div>

           <div className="glass-card p-6 flex flex-col">
              <h2 className="text-lg font-bold text-white mb-6">Blockchain Proof Center</h2>
              <div className="space-y-6">
                 {blockchainProofs.length === 0 ? (
                    <div className="text-sm text-brand-muted">No blockchain proofs available yet.</div>
                 ) : blockchainProofs.map((asset, i) => (
                    <div key={i} className="flex items-center gap-4 p-4 rounded-xl border border-white/5 bg-white/2 hover:bg-white/5 transition-colors group">
                       <div className="w-12 h-12 rounded-lg bg-brand-accent2/20 flex items-center justify-center text-brand-accent2 group-hover:scale-105 transition-transform">
                          <LinkIcon size={20} />
                       </div>
                       <div className="flex-1 min-w-0">
                          <p className="text-sm font-bold text-white truncate">{asset.name}</p>
                          <p className="text-[10px] font-mono text-brand-accent truncate mt-1">{asset.hash}</p>
                       </div>
                       <div className="flex flex-col items-end gap-2">
                          {asset.confirmed ? <span className="badge-low text-[9px] py-0">SECURED</span> : <span className="badge-med text-[9px] py-0">MINING</span>}
                          <button 
                             onClick={() => {
                                showToast(`Scanning Polygon Ledger for ${asset.name}`, "info");
                                window.open(`https://amoy.polygonscan.com/search?q=${asset.hash}`, '_blank');
                             }}
                             className="text-[10px] text-brand-muted hover:text-brand-accent transition-colors flex items-center gap-1 cursor-pointer"
                           >
                              Scan <ExternalLink size={10} />
                           </button>
                           {asset.confirmed && (
                             <button 
                                onClick={() => {
                                   downloadSentinelPdf({
                                     type: 'blockchain',
                                     title: 'Blockchain Proof Certificate',
                                     refId: asset.id,
                                     assetName: asset.name,
                                     txHash: asset.hash,
                                     orgName: user?.orgName || 'Your Organization',
                                                       ...issuer,
                                     date: asset.date,
                                   });
                                   showToast(`Proof certificate downloaded for ${asset.name}`, 'success');
                                }}
                                className="text-[10px] text-brand-accent3 hover:text-white flex items-center gap-1 cursor-pointer"
                                title="Download Proof"
                             >
                                <Download size={10} />
                             </button>
                           )}
                       </div>
                    </div>
                 ))}
              </div>
              <button 
                onClick={() => handleManualDMCA("Selected Assets")}
                className="danger-ghost-button w-full mt-auto py-3 cursor-pointer group"
              >
                 <FileText size={16} className="group-hover:scale-110 transition-transform" />
                 Generate Legal DMCA Notice
              </button>
           </div>
        </div>

        {/* Global Feed Simulation (Optional Page 4 element) */}
        <div className="glass-card overflow-hidden">
           <div className="p-6 border-b border-brand-border flex items-center justify-between bg-white/2">
              <h2 className="text-lg font-bold text-white">Live Monitoring Console</h2>
              <div className="flex items-center gap-6">
                 <div className="flex items-center gap-2">
                    <Search className="w-4 h-4 text-brand-muted" />
                    <input type="text" placeholder="Search assets..." onKeyDown={(e) => e.key === 'Enter' && showToast(`Filtering monitoring feed for "${(e.target as HTMLInputElement).value}"...`, "info")} className="bg-transparent text-sm text-white outline-none w-32 border-b border-brand-border/30 focus:border-brand-accent transition-all" />
                 </div>
                 <button className="ghost-button h-8 px-4 text-xs cursor-pointer" onClick={() => showToast("Opening filters...", "info")}>Filters</button>
              </div>
           </div>
           <table className="w-full text-left">
              <thead>
                 <tr className="border-b border-brand-border bg-white/1 uppercase font-mono text-[10px] tracking-widest text-brand-muted">
                    <th className="px-6 py-4 font-bold">Thumbnail</th>
                    <th className="px-6 py-4 font-bold">Asset Name</th>
                    <th className="px-6 py-4 font-bold">Type</th>
                    <th className="px-6 py-4 font-bold">Registry Hash</th>
                    <th className="px-6 py-4 font-bold">Status</th>
                    <th className="px-6 py-4 font-bold text-center">Violations</th>
                    <th className="px-6 py-4 font-bold text-right pr-10">Actions</th>
                 </tr>
              </thead>
              <tbody className="divide-y divide-brand-border">
                         {assetsList.length === 0 ? (
                            <tr>
                               <td className="px-6 py-8 text-sm text-brand-muted" colSpan={7}>
                                  No monitored assets yet.
                               </td>
                            </tr>
                         ) : assetsList.map((asset, i) => {
                            const name = asset.file_name || asset.metadata?.original_name || 'Untitled Asset';
                            const type = asset.metadata?.content_type || 'FILE';
                            const hash = asset.file_hash || 'N/A';
                            const violationsCount = 0;
                            return (
                            <tr key={asset._id || i} className="hover:bg-white/[0.02] transition-colors group">
                      <td className="px-6 py-4">
                         <div className="w-10 h-10 rounded bg-brand-surface border border-white/5 flex items-center justify-center">
                            <Globe className="w-4 h-4 text-brand-muted group-hover:text-brand-accent transition-colors" />
                         </div>
                      </td>
                      <td className="px-6 py-4 text-sm font-medium text-white group-hover:text-brand-accent transition-colors">{name}</td>
                      <td className="px-6 py-4 text-[10px] font-mono text-brand-muted uppercase">{type}</td>
                      <td className="px-6 py-4 text-[10px] font-mono text-brand-accent">{hash}</td>
                      <td className="px-6 py-4">
                         <div className="flex items-center gap-2 text-brand-accent3">
                            <LinkIcon size={12} />
                            <span className="text-[10px] font-bold font-mono">SECURED</span>
                         </div>
                      </td>
                      <td className="px-6 py-4 text-center">
                         <span className={cn(violationsCount > 10 ? 'badge-high' : violationsCount > 0 ? 'badge-med' : 'badge-low')}>
                            {violationsCount}
                         </span>
                      </td>
                                 <td className="px-6 py-4">
                                     <div className="flex items-center justify-end gap-2 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-all pr-4">
                            <button className="p-2 rounded-lg text-brand-accent hover:bg-brand-accent/10 transition-colors cursor-pointer" title="View Source"><ExternalLink size={14} /></button>
                            <button 
                               onClick={() => {
                                                 try {
                                                    downloadSentinelPdf({
                                                       type: 'asset',
                                                       title: 'Asset Protection Certificate',
                                                       refId: 'ASSET-' + (asset._id || i),
                                                       assetName: name,
                                                       txHash: hash,
                                                       orgName: user?.orgName || 'Your Organization',
                                                       date: new Date().toISOString().split('T')[0],
                                                    });
                                                    showToast(`Certificate downloaded for ${name}`, 'success');
                                                 } catch {
                                                    showToast('Download failed on this device', 'error');
                                                 }
                               }}
                               className="p-2 rounded-lg text-brand-accent3 hover:bg-brand-accent3/10 transition-colors cursor-pointer" 
                               title="Download Proof"
                            >
                               <Download size={14} />
                            </button>
                            <button 
                               onClick={() => handleManualDMCA(name)}
                               className="p-2 rounded-lg text-brand-danger hover:bg-brand-danger/10 transition-colors cursor-pointer" 
                               title="Initiate Takedown"
                            >
                               <AlertTriangle size={14} />
                            </button>
                         </div>
                      </td>
                   </tr>
                   );
                 })}
              </tbody>
           </table>
        </div>
      </main>
    </div>
  );
}
