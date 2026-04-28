import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { SentinelSidebar } from '../../components/shared/SentinelSidebar';
import { Link as LinkIcon, Shield, ExternalLink, Database, Search, Lock, Download, CheckCircle } from 'lucide-react';
import { cn } from '../../lib/utils';
import { showToast } from '../../components/shared/GlobalToast';
import { downloadSentinelPdf } from '../../lib/downloadPdf';
import { useAuth } from '../../context/AuthContext';
import { apiGet } from '../../lib/api';

export function BlockchainProofCenter() {
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
   const [registryRecords, setRegistryRecords] = useState<any[]>([]);
   const [chainMode, setChainMode] = useState<string>('demo');

   useEffect(() => {
      const loadRecords = async () => {
         try {
            const response = await apiGet<{ records: any[] }>('/api/signals/blockchain/');
            if (response.records?.length) {
               setRegistryRecords(response.records);
            }
         } catch {
            showToast('Unable to fetch blockchain records', 'error');
         }
      };
      loadRecords();
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

  return (
    <div className="flex bg-brand-bg min-h-screen">
      <SentinelSidebar role="user" />
      <main className="flex-1 p-8 space-y-8 overflow-x-hidden">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="mission-control-header !text-brand-accent mb-2">Authenticated: {user?.orgName || 'Your Organization'}</h1>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-brand-accent animate-pulse" />
              <p className="text-xl font-bold text-white tracking-tight">On-Chain Registry & Provenance</p>
            </div>
            {chainMode === 'demo' ? (
              <div className="mt-3 inline-flex items-center gap-2 rounded-lg border border-brand-warn/30 bg-brand-warn/10 px-3 py-1.5 text-[11px]">
                 <span className="font-bold text-brand-warn uppercase tracking-wide">Demo Chain Mode</span>
                 <span className="text-brand-muted">Simulated Output for Prototype</span>
              </div>
            ) : null}
          </div>
          <button className="primary-button" onClick={() => showToast("Scanning for external assets...", "info")}>
            <Search className="w-4 h-4" />
            Verify External Hash
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
           <div className="lg:col-span-2 space-y-6">
              <div className="glass-card p-6">
                 <h3 className="mission-control-header mb-6 !text-white !opacity-100 uppercase tracking-[0.2em] font-mono text-[10px] flex items-center gap-2">
                    <Database className="w-3 h-3 text-brand-accent" />
                    Registry Ledger
                 </h3>
                 <div className="overflow-x-auto">
                    <table className="w-full text-left">
                       <thead>
                          <tr className="border-b border-brand-border text-[10px] font-mono text-brand-muted uppercase tracking-widest">
                             <th className="pb-4 px-2">Registry ID</th>
                             <th className="pb-4 px-2">Asset Name</th>
                             <th className="pb-4 px-2">Transaction Hash</th>
                             <th className="pb-4 px-2">Status</th>
                             <th className="pb-4 px-2">Actions</th>
                          </tr>
                       </thead>
                                  <tbody className="divide-y divide-brand-border/50">
                                       {registryRecords.length === 0 ? (
                                          <tr>
                                             <td className="py-6 px-2 text-sm text-brand-muted" colSpan={5}>
                                                No blockchain records available yet.
                                             </td>
                                          </tr>
                                       ) : registryRecords.map((record) => (
                            <tr key={record.id} className="text-sm hover:bg-white/5 transition-colors group">
                               <td className="py-4 px-2 font-mono text-brand-accent text-xs">{record.id}</td>
                               <td className="py-4 px-2 text-white font-medium">{record.asset}</td>
                               <td className="py-4 px-2 font-mono text-brand-muted text-[10px]">{record.hash}</td>
                               <td className="py-4 px-2">
                                  <span className="flex items-center gap-1.5 text-brand-accent3 text-xs font-bold">
                                     <CheckCircle size={12} />
                                     Verified
                                  </span>
                               </td>
                               <td className="py-4 px-2">
                                  <div className="flex gap-2">
                                     <button 
                                       onClick={() => showToast(`Opening Explorer for ${record.hash}`, "info")}
                                       className="p-1.5 hover:bg-white/10 rounded-lg text-brand-muted hover:text-white transition-colors cursor-pointer"
                                     >
                                        <ExternalLink size={14} />
                                     </button>
                                     <button 
                                       onClick={() => {
                                          downloadSentinelPdf({
                                            type: 'blockchain',
                                            title: 'Blockchain Proof Certificate',
                                            refId: record.id,
                                            assetName: record.asset,
                                                                  txHash: record.tx_hash || record.hash || 'N/A',
                                                                  network: record.network,
                                                                  status: record.status,
                                                                  demoMode: String(record.mode || '').toLowerCase() === 'demo' || String(record.status || '').includes('DEMO'),
                                            orgName: user?.orgName || 'Your Organization',
                                                                  ...issuer,
                                                                  date: String(record.time || '').split('T')[0] || new Date().toISOString().split('T')[0],
                                          });
                                          showToast(`Proof certificate downloaded · ${record.id}`, 'success');
                                       }}
                                       className="p-1.5 hover:bg-brand-accent3/10 rounded-lg text-brand-accent3 transition-colors cursor-pointer"
                                     >
                                        <Download size={14} />
                                     </button>
                                  </div>
                               </td>
                            </tr>
                          ))}
                       </tbody>
                    </table>
                 </div>
              </div>

              <div className="glass-card p-6 border-brand-accent/20">
                 <div className="flex items-center gap-4 mb-6">
                    <div className="w-12 h-12 rounded-xl bg-brand-accent/10 flex items-center justify-center text-brand-accent">
                       <Lock className="w-6 h-6" />
                    </div>
                    <div>
                       <h4 className="text-white font-bold">Zero-Knowledge Verification</h4>
                       <p className="text-xs text-brand-muted">Verify asset ownership without exposing original raw files or PII.</p>
                    </div>
                 </div>
                 <button 
                   onClick={() => {
                      downloadSentinelPdf({
                        type: 'blockchain',
                        title: 'Zero-Knowledge Proof Certificate',
                        refId: 'ZK-' + Math.floor(Math.random() * 9000 + 1000),
                        assetName: 'Aggregate Registry — All Assets',
                                    txHash: 'DEMO-ZK-CERT',
                                    network: 'Polygon Amoy (Simulated)',
                                    status: 'CONFIRMED (DEMO)',
                                    demoMode: true,
                        orgName: user?.orgName || 'Your Organization',
                                    ...issuer,
                        date: new Date().toISOString().split('T')[0],
                      });
                      showToast("Zero-knowledge certificate downloaded", 'success');
                   }}
                   className="ghost-button w-full border-brand-accent/30 text-brand-accent cursor-pointer"
                 >
                   Generate Verification Certificate
                 </button>
              </div>
           </div>

           <div className="space-y-6">
              <div className="glass-card p-6 bg-gradient-to-br from-brand-accent/10 to-transparent">
                 <div className="flex flex-col items-center text-center p-4">
                    <LinkIcon className="w-12 h-12 text-brand-accent mb-4 animate-pulse" />
                    <h3 className="text-white font-bold mb-2">Polygon Amoy Testnet</h3>
                    <p className="text-xs text-brand-muted mb-6">Current Network Status: Operational</p>
                    <div className="w-full space-y-3 pt-4 border-t border-brand-border">
                       <div className="flex justify-between text-[10px] font-mono uppercase tracking-widest text-brand-muted">
                          <span>Block Height</span>
                          <span className="text-white font-bold">12,842,941</span>
                       </div>
                       <div className="flex justify-between text-[10px] font-mono uppercase tracking-widest text-brand-muted">
                          <span>Avg Gas (gwei)</span>
                          <span className="text-white font-bold">32.4</span>
                       </div>
                       <div className="flex justify-between text-[10px] font-mono uppercase tracking-widest text-brand-muted">
                          <span>Settlement</span>
                          <span className="text-brand-accent3 font-bold">INSTANT</span>
                       </div>
                    </div>
                 </div>
              </div>

              <div className="glass-card p-6">
                 <h4 className="text-[11px] font-mono font-bold text-brand-muted uppercase tracking-widest mb-4">Registry Security</h4>
                 <div className="space-y-4">
                    <div className="flex items-start gap-3">
                       <Shield className="w-4 h-4 text-brand-accent mt-0.5" />
                       <div className="text-xs text-brand-text">
                          <span className="font-bold block">pHash Matching</span>
                          Perceptual hashing ensures registry works even with re-encoded videos.
                       </div>
                    </div>
                    <div className="flex items-start gap-3">
                       <Download className="w-4 h-4 text-brand-accent3 mt-0.5" />
                       <div className="text-xs text-brand-text">
                          <span className="font-bold block">Bulk Export</span>
                          Export all immutable hash certificates as a signed PDF package.
                       </div>
                    </div>
                 </div>
              </div>
           </div>
        </div>
      </main>
    </div>
  );
}
