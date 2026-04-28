import React from 'react';
import { SentinelSidebar } from './SentinelSidebar';
import { useAuth } from '../../context/AuthContext';

export function WorkInProgress({ title }: { title: string }) {
  const { user } = useAuth();
  const role = user?.role === 'admin' ? 'admin' : 'user';
  return (
    <div className="flex bg-brand-bg min-h-screen">
      <SentinelSidebar role={role} />
      <main className="flex-1 p-8 flex flex-col items-center justify-center text-center">
        <div className="w-20 h-20 rounded-full bg-brand-accent/10 flex items-center justify-center text-brand-accent mb-6 animate-pulse">
          <svg className="w-10 h-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
          </svg>
        </div>
        <h1 className="text-3xl font-bold text-white mb-4">{title}</h1>
        <p className="text-brand-muted max-w-md">
          This secure terminal is currently being synchronized with the global Sentinel network. 
          Real-time data for this sector will be available shortly.
        </p>
        <div className="mt-10 flex gap-4">
          <div className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-[10px] font-mono text-brand-muted uppercase tracking-widest">
            Module: {title.toUpperCase()}
          </div>
          <div className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-[10px] font-mono text-brand-accent3 uppercase tracking-widest flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-accent3 animate-pulse" />
            Active
          </div>
        </div>
      </main>
    </div>
  );
}
