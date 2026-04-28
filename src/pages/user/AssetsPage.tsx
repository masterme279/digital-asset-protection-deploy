import React, { useEffect, useState, useRef, DragEvent } from 'react';
import { motion } from 'motion/react';
import { SentinelSidebar } from '../../components/shared/SentinelSidebar';
import { 
  Plus, Layers, Database, Search, Filter, UploadCloud, 
  CheckCircle, Link as LinkIcon, Edit2, Share2, Download, Trash2
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { showToast } from '../../components/shared/GlobalToast';
import { downloadSentinelPdf } from '../../lib/downloadPdf';
import { useAuth } from '../../context/AuthContext';
import { apiGet, apiPostForm } from '../../lib/api';

export function AssetsPage() {
  const { user } = useAuth();
   const [assets, setAssets] = useState<{ id: string; name: string; type: string; size: string; sizeBytes: number; date: string; status: string; hash: string; contentType: string }[]>([]);
   const [blockchainRecords, setBlockchainRecords] = useState<any[]>([]);
   const totalBytes = assets.reduce((sum, asset) => sum + (asset.sizeBytes || 0), 0);
   const formatBytes = (bytes: number) => {
      if (!bytes) return '0 B';
      const units = ['B', 'KB', 'MB', 'GB', 'TB'];
      const index = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
      const value = bytes / Math.pow(1024, index);
      return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
   };
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
   const uploadTimerRef = useRef<number | null>(null);

   const loadAssets = async () => {
      try {
         const response = await apiGet<{ assets: any[] }>('/api/assets/');
         const mapped = response.assets.map((asset) => {
            const name = asset.file_name || asset.metadata?.original_name || 'Untitled';
            const extension = String(name).split('.').pop()?.toUpperCase() || 'FILE';
            const sizeBytes = asset.metadata?.size || 0;
            const sizeMb = sizeBytes ? `${Math.round(sizeBytes / (1024 * 1024))}MB` : 'N/A';
            const uploaded = asset.uploaded_at ? String(asset.uploaded_at).split('T')[0] : 'N/A';
            return {
               id: asset._id || asset.id,
               name,
               type: extension,
               size: sizeMb,
               sizeBytes,
               date: uploaded,
               status: String(asset.status || 'secured'),
               hash: asset.file_hash || 'N/A',
               contentType: asset.metadata?.content_type || 'UNKNOWN',
            };
         });
         setAssets(mapped);
      } catch {
         showToast('Unable to load assets from backend', 'error');
      }
   };

   const getStatusMeta = (rawStatus: string) => {
      const value = String(rawStatus || '').toLowerCase();
      if (['checking', 'processing', 'pending'].includes(value)) {
         return { label: 'CHECKING', tone: 'text-brand-warn' };
      }
      if (value === 'failed') {
         return { label: 'FAILED', tone: 'text-brand-danger' };
      }
      if (value === 'checked') {
         return { label: 'CHECKED', tone: 'text-brand-accent3' };
      }
      return { label: 'SECURED', tone: 'text-brand-accent3' };
   };

   const loadBlockchainRecords = async () => {
      try {
         const response = await apiGet<{ records: any[] }>('/api/signals/blockchain/');
         setBlockchainRecords(response.records || []);
      } catch {
         setBlockchainRecords([]);
      }
   };

   useEffect(() => {
      loadAssets();
      loadBlockchainRecords();
   }, []);

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
      showToast(`Anchoring DNA for ${file.name}...`, "info");
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
            showToast(uploadResponse.message || `${file.name} fully authenticated`, 'success');
         }
         await loadAssets();
         setUploadStep(5);
      } catch {
         showToast('Upload failed. Check backend status.', 'error');
      } finally {
         stopUploadTimer();
         window.setTimeout(() => {
            setIsUploading(false);
            setUploadStep(0);
         }, 600);
      }
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    processUpload(e.dataTransfer.files);
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

   const copyTextFallback = async (text: string) => {
      if (navigator.clipboard?.writeText) {
         await navigator.clipboard.writeText(text);
         return;
      }

      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.setAttribute('readonly', '');
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();
      const copied = document.execCommand('copy');
      document.body.removeChild(textarea);

      if (!copied) {
         throw new Error('Copy fallback failed');
      }
   };

   const shareAsset = async (assetName: string, hash: string) => {
      const verifyUrl = `https://amoy.polygonscan.com/search?q=${encodeURIComponent(hash)}`;
      const shareData: ShareData = {
         title: `SENTINEL - ${assetName}`,
         text: `Asset protected by SENTINEL. TX: ${hash}`,
         url: verifyUrl,
      };

      try {
         const canUseNativeShare =
            typeof navigator.share === 'function' &&
            (typeof navigator.canShare !== 'function' || navigator.canShare(shareData));

         if (canUseNativeShare) {
            await navigator.share(shareData);
            showToast('Shared via system share sheet', 'success');
            return;
         }

         const fallback = `SENTINEL Protected Asset\nName: ${assetName}\nTX Hash: ${hash}\nVerify: ${verifyUrl}`;
         await copyTextFallback(fallback);
         showToast('Share details copied to clipboard', 'success');
      } catch {
         showToast('Unable to share this asset on this browser', 'error');
      }
   };

   const handleBulkShare = async () => {
      const summary = assets
         .map((asset) => `${asset.name} -> https://amoy.polygonscan.com/search?q=${encodeURIComponent(asset.hash)}`)
         .join('\n');

      const shareData: ShareData = {
         title: `SENTINEL - ${assets.length} Protected Assets`,
         text: `Protected assets:\n${summary}`,
      };

      try {
         const canUseNativeShare =
            typeof navigator.share === 'function' &&
            (typeof navigator.canShare !== 'function' || navigator.canShare(shareData));

         if (canUseNativeShare) {
            await navigator.share(shareData);
            showToast('Bulk share sent', 'success');
            return;
         }

         await copyTextFallback(shareData.text || '');
         showToast('Bulk share content copied to clipboard', 'success');
      } catch {
         showToast('Unable to share multiple assets right now', 'error');
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
              <p className="text-xl font-bold text-white tracking-tight">DNA Registry Center</p>
            </div>
          </div>
          <div className="flex gap-3">
             <button className="ghost-button cursor-pointer" onClick={handleBulkShare}>
                <Share2 size={16} />
                Bulk Share
             </button>
             <button onClick={triggerFileInput} className="primary-button">
                <Plus size={16} />
                Register New Asset
             </button>
             <input 
               type="file" 
               ref={fileInputRef} 
               className="hidden" 
               onChange={(e) => processUpload(e.target.files)} 
             />
          </div>
        </div>

        {/* Upload Terminal */}
        <div 
          onClick={!isUploading ? triggerFileInput : undefined}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={cn(
            "glass-card p-10 border-2 border-dashed flex flex-col items-center justify-center cursor-pointer transition-all relative overflow-hidden group",
            isUploading ? "border-brand-accent bg-brand-accent/5" : 
            isDragging ? "border-brand-accent3 bg-brand-accent3/5 scale-[1.01]" :
            "border-brand-accent/20 hover:border-brand-accent hover:bg-brand-accent/5"
          )}
        >
          {isUploading ? (
            <div className="w-full max-w-md space-y-8 relative z-10">
               <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-mono text-brand-accent uppercase font-bold tracking-widest">Securing Digital Blueprint</span>
                  <span className="text-xs text-brand-muted">{Math.min(uploadStep * 20, 100)}%</span>
               </div>
               <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(uploadStep * 20, 100)}%` }}
                    className="h-full bg-brand-accent shadow-[0_0_12px_rgba(14,165,233,0.5)]"
                  />
               </div>
               <div className="flex justify-between gap-2">
                  {["Upload", "Analyze", "Stamp", "Chain", "Live"].map((s, i) => (
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
                 <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="pt-4 text-center">
                    <p className="text-brand-accent3 text-sm font-bold mb-4 italic">Registry Entry Finalized</p>
                    <button className="ghost-button h-8 text-[11px] font-mono px-4" onClick={(e) => {e.stopPropagation(); setIsUploading(false); setUploadStep(0);}}>ADD ANOTHER</button>
                 </motion.div>
               )}
            </div>
          ) : (
            <>
              <div className="absolute inset-0 bg-brand-accent/5 opacity-0 group-hover:opacity-100 transition-opacity" />
              <UploadCloud className="w-12 h-12 text-brand-accent mb-4" />
              <h3 className="text-lg font-bold text-white mb-1">Initialize DNA Registration</h3>
              <p className="text-brand-muted text-xs text-center max-w-sm">Drag files or click to begin AI fingerprinting and blockchain anchoring</p>
            </>
          )}
        </div>

        {/* Assets Explorer */}
        <div className="glass-card overflow-hidden">
           <div className="p-6 border-b border-brand-border flex items-center justify-between bg-white/[0.02]">
              <div className="flex items-center gap-6">
                 <div className="flex items-center gap-2 bg-black/20 rounded-lg px-3 py-1.5 border border-white/5">
                    <Search className="w-4 h-4 text-brand-muted" />
                    <input type="text" placeholder="Search DNA records..." onKeyDown={(e) => e.key === 'Enter' && showToast(`Filtering registry for "${(e.target as HTMLInputElement).value}"...`, "info")} className="bg-transparent text-sm text-white outline-none w-48 font-mono" />
                 </div>
                 <div className="flex items-center gap-3">
                    <button className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs text-brand-muted hover:text-white transition-colors uppercase font-bold tracking-wider cursor-pointer">
                       <Filter size={14} />
                       Asset Type
                    </button>
                    <button className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs text-brand-muted hover:text-white transition-colors uppercase font-bold tracking-wider cursor-pointer">
                       Date Range
                    </button>
                 </div>
              </div>
              <div className="flex bg-black/20 p-1 rounded-lg border border-white/5">
                 <button className="p-1.5 bg-brand-accent/10 text-brand-accent rounded-md cursor-pointer" onClick={() => showToast("Switching to Grid View", "info")}><Layers size={16} /></button>
                 <button className="p-1.5 text-brand-muted hover:text-white cursor-pointer"><Edit2 size={16} /></button>
              </div>
           </div>
           
           <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                 <thead>
            <tr className="border-b border-brand-border bg-white/[0.01]">
               <th className="px-6 py-4 mission-control-header !opacity-100 !text-white/40">Preview</th>
               <th className="px-6 py-4 mission-control-header !opacity-100 !text-white/40">Resource Name</th>
               <th className="px-6 py-4 mission-control-header !opacity-100 !text-white/40">Signal Metadata</th>
               <th className="px-6 py-4 mission-control-header !opacity-100 !text-white/40">On-Chain Status</th>
               <th className="px-6 py-4 mission-control-header !opacity-100 !text-white/40">Anchored</th>
               <th className="px-6 py-4 mission-control-header !opacity-100 !text-white/40 text-right pr-10">Actions</th>
            </tr>
                 </thead>
                 <tbody className="divide-y divide-brand-border">
                    {assets.map((asset) => (
                      <tr key={asset.id} className="hover:bg-white/[0.02] transition-colors group">
                         <td className="px-6 py-4">
                            <div className="w-10 h-10 rounded-lg bg-brand-accent/5 border border-white/5 flex items-center justify-center text-brand-accent">
                               <Database size={18} />
                            </div>
                         </td>
                         <td className="px-6 py-4">
                            <div>
                               <p className="text-sm font-bold text-white mb-0.5">{asset.name}</p>
                               <p className="text-[10px] font-mono text-brand-muted uppercase tracking-tighter">{asset.type} • {asset.size}</p>
                            </div>
                         </td>
                         <td className="px-6 py-4">
                            <div className="flex gap-2">
                               <span className="px-1.5 py-0.5 rounded bg-white/5 text-[9px] font-mono text-brand-muted border border-white/5">{asset.type}</span>
                               <span className="px-1.5 py-0.5 rounded bg-white/5 text-[9px] font-mono text-brand-muted border border-white/5">{asset.contentType}</span>
                            </div>
                         </td>
                         <td className="px-6 py-4">
                            <div className="flex flex-col gap-1">
                               <div className={`flex items-center gap-1.5 ${getStatusMeta(asset.status).tone}`}>
                                  <LinkIcon size={12} />
                                  <span className="text-[10px] font-bold font-mono">{getStatusMeta(asset.status).label}</span>
                               </div>
                               <span className="text-[9px] font-mono text-brand-muted truncate max-w-[80px]">{asset.hash}</span>
                            </div>
                         </td>
                         <td className="px-6 py-4">
                            <p className="text-xs text-brand-text font-medium">{asset.date}</p>
                         </td>
                         <td className="px-6 py-4">
                            <div className="flex justify-end gap-2 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-all pr-4">
                               <button 
                                 onClick={() => {
                                                    try {
                                                       downloadSentinelPdf({
                                                          type: 'asset',
                                                          title: 'Asset Protection Certificate',
                                                          refId: 'ASSET-' + asset.id,
                                                          assetName: asset.name,
                                                          txHash: asset.hash || 'N/A',
                                                          orgName: user?.orgName || 'Your Organization',
                                                          ...issuer,
                                                          date: asset.date,
                                                       });
                                                       showToast(`Certificate downloaded for ${asset.name}`, 'success');
                                                    } catch {
                                                       showToast('Download failed. Please try again.', 'error');
                                                    }
                                 }}
                                 className="p-2 text-brand-accent3 hover:bg-brand-accent3/10 rounded-lg transition-colors border border-transparent hover:border-brand-accent3/20 cursor-pointer"
                               >
                                  <Download size={14}/>
                               </button>
                               <button className="p-2 text-brand-accent hover:bg-brand-accent/10 rounded-lg transition-colors cursor-pointer" onClick={() => showToast("Opening metadata editor...", "info")}><Edit2 size={14}/></button>
                               <button 
                                 className="p-2 text-brand-muted hover:text-white rounded-lg transition-colors cursor-pointer" 
                                                 onClick={() => shareAsset(asset.name, asset.hash)}
                               >
                                 <Share2 size={14}/>
                               </button>
                               <button className="p-2 text-brand-danger hover:bg-brand-danger/10 rounded-lg transition-colors cursor-pointer" onClick={() => showToast("Asset removed from local registry", "warning")}><Trash2 size={14}/></button>
                            </div>
                         </td>
                      </tr>
                    ))}
                 </tbody>
              </table>
           </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pb-12">
           <div className="glass-card p-6 bg-brand-accent/5">
              <h4 className="text-[10px] font-mono font-bold text-brand-accent uppercase tracking-widest mb-4">Storage Metrics</h4>
              <div className="flex items-end gap-2 mb-4">
                 <span className="text-2xl font-bold text-white leading-none">{formatBytes(totalBytes)}</span>
                 <span className="text-[10px] text-brand-muted font-mono mb-1">total stored</span>
              </div>
              <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                 <div className="h-full bg-brand-accent" style={{ width: totalBytes ? '100%' : '0%' }} />
              </div>
           </div>
           <div className="glass-card p-6">
              <h4 className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest mb-4">Network Sync</h4>
              <div className="flex items-center gap-3">
                 <div className="w-2 h-2 rounded-full bg-brand-accent3 animate-pulse" />
                 <span className="text-sm font-bold text-white uppercase tracking-tighter">
                    {assets.length ? 'DNA Propagation Active' : 'No assets to sync'}
                 </span>
              </div>
              <p className="text-[10px] text-brand-muted mt-2 leading-relaxed">
                 Assets synced: {assets.length}. Anchored records: {blockchainRecords.length}.
              </p>
           </div>
           <div className="glass-card p-6">
              <h4 className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-widest mb-4">Blockchain Latency</h4>
              <div className="flex items-end gap-2">
                 <span className="text-2xl font-bold text-brand-accent3 leading-none">
                    {blockchainRecords.length ? 'ACTIVE' : 'N/A'}
                 </span>
                 <span className="text-[10px] text-brand-muted font-mono mb-1">ANCHOR STATUS</span>
              </div>
              <p className="text-[10px] text-brand-muted mt-2 leading-relaxed">
                 Latest anchor: {blockchainRecords[0]?.time ? String(blockchainRecords[0].time).split('T')[0] : 'N/A'}
              </p>
           </div>
        </div>
      </main>
    </div>
  );
}
