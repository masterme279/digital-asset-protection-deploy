import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { SentinelSidebar } from '../../components/shared/SentinelSidebar';
import { Settings, Shield, Bell, User, Lock, Eye, Globe, Database, Cpu, Zap, CreditCard } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useAuth } from '../../context/AuthContext';
import { apiGet } from '../../lib/api';

export function SettingsPage() {
   const { user } = useAuth();
   const [assetsCount, setAssetsCount] = useState(0);
   const [blockchainCount, setBlockchainCount] = useState(0);

   useEffect(() => {
      const loadSettingsMetrics = async () => {
         try {
            const [assetsRes, blockchainRes] = await Promise.all([
               apiGet<{ assets: any[] }>('/api/assets/'),
               apiGet<{ records: any[] }>('/api/signals/blockchain/'),
            ]);
            setAssetsCount(assetsRes.assets?.length ?? 0);
            setBlockchainCount(blockchainRes.records?.length ?? 0);
         } catch {
            setAssetsCount(0);
            setBlockchainCount(0);
         }
      };
      loadSettingsMetrics();
   }, []);

   const workspaceName = user?.orgName || 'Workspace';
   const nodeId = user?.registrationId || user?.signature || 'N/A';
   const deploymentPercent = assetsCount ? Math.min(100, assetsCount * 10) : 0;
  const settingsGroups = [
    { name: 'Organization Setup', icon: Shield, desc: 'Team members, permissions, and entity profiles.' },
    { name: 'AI Monitoring Nodes', icon: Eye, desc: 'Configure fingerprinting sensitivity and crawler frequency.' },
    { name: 'Global Notifications', icon: Bell, desc: 'Webhook triggers, email alerts, and Slack/Teams integration.' },
    { name: 'Cloud Integration', icon: Globe, desc: 'Manage your SENTINEL API keys and cloud storage buckets.' },
    { name: 'Privacy & Compliance', icon: Lock, desc: 'Data retention policies, encryption standards, and logs.' },
    { name: 'Invoicing & Quotas', icon: CreditCard, desc: 'Subscription tier, usage quotas, and monthly billing history.' },
  ];

  return (
    <div className="flex bg-brand-bg min-h-screen font-sans">
      <SentinelSidebar role="user" />
      <main className="flex-1 p-8 space-y-8 overflow-x-hidden">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white mb-1">Platform Configuration</h1>
            <p className="text-xs font-mono text-brand-muted uppercase tracking-widest">Global workspace controls and AI node orchestration</p>
          </div>
          <button className="primary-button h-9">Save Global Config</button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
           <div className="lg:col-span-1 space-y-4">
              <div className="glass-card p-6 border-brand-accent/20">
                 <div className="flex flex-col items-center text-center">
                    <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-brand-accent/10 to-brand-accent2/10 border border-brand-accent/20 mb-4 flex items-center justify-center">
                       <Database className="text-brand-accent w-10 h-10" />
                    </div>
                    <h3 className="text-white font-bold">{workspaceName} Workspace</h3>
                    <p className="text-[10px] text-brand-muted mb-4 uppercase tracking-[0.2em]">Enterprise Node ID: {nodeId}</p>
                    <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden mb-2">
                       <div className="h-full bg-brand-accent" style={{ width: `${deploymentPercent}%` }} />
                    </div>
                    <span className="text-[9px] font-mono text-brand-muted uppercase">Assets protected: {assetsCount}</span>
                 </div>
              </div>

              <div className="glass-card p-6">
                 <h4 className="text-[10px] font-mono text-brand-muted uppercase tracking-widest mb-4">Node Performance</h4>
                 <div className="space-y-4">
                    <div className="flex justify-between items-center text-xs">
                       <span className="text-brand-muted">Latency (Avg)</span>
                       <span className="text-brand-accent3 font-bold font-mono">N/A</span>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                       <span className="text-brand-muted">Crawl Throughput</span>
                       <span className="text-white font-mono font-bold">{blockchainCount} anchors</span>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                       <span className="text-brand-muted">Cluster Uptime</span>
                       <span className="text-brand-accent3 font-bold uppercase tracking-tighter">{assetsCount ? 'ACTIVE' : 'IDLE'}</span>
                    </div>
                 </div>
              </div>
           </div>

           <div className="lg:col-span-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                 {settingsGroups.map((group) => (
                   <motion.button 
                     key={group.name}
                     whileHover={{ y: -4, backgroundColor: 'rgba(255,255,255,0.05)' }}
                     className="glass-card p-6 text-left border-brand-border/40 transition-colors"
                   >
                     <div className="flex items-start gap-4">
                        <div className="w-10 h-10 rounded-xl bg-brand-surface2 border border-brand-border flex items-center justify-center text-brand-accent">
                           <group.icon size={20} />
                        </div>
                        <div>
                           <h4 className="text-white font-bold mb-1">{group.name}</h4>
                           <p className="text-xs text-brand-muted leading-relaxed">{group.desc}</p>
                        </div>
                     </div>
                   </motion.button>
                 ))}
              </div>

              <div className="mt-8 glass-card p-8 border-brand-danger/20 bg-brand-danger/5">
                 <h4 className="text-brand-danger font-bold mb-2">Danger Zone</h4>
                 <p className="text-xs text-brand-muted mb-6">Irreversible actions for your organization and protected assets.</p>
                 <div className="flex gap-4">
                    <button className="danger-ghost-button px-6 text-xs h-9">Flush All Assets</button>
                    <button className="danger-ghost-button px-6 text-xs h-9">Deactivate Org</button>
                 </div>
              </div>
           </div>
        </div>
      </main>
    </div>
  );
}
