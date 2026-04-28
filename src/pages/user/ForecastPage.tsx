import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { SentinelSidebar } from '../../components/shared/SentinelSidebar';
import { TrendingUp, Activity, Zap, Share2, Twitter, AlertCircle, ShieldAlert, Users } from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell
} from 'recharts';
import { cn, formatNumber } from '../../lib/utils';
import { useAuth } from '../../context/AuthContext';
import { apiGet, apiPost } from '../../lib/api';
import { showToast } from '../../components/shared/GlobalToast';


export function ForecastPage() {
  const { user } = useAuth();
   const [forecastData, setForecastData] = useState<{ time: string; predictions: number }[]>([]);
   const [aiCases, setAiCases] = useState<any[]>([]);
   const [aiAudit, setAiAudit] = useState<any[]>([]);
   const [aiCaseCount, setAiCaseCount] = useState(0);
   const [aiAuditCount, setAiAuditCount] = useState(0);
   const [aiConnected, setAiConnected] = useState(false);
   const predictionValues = forecastData.map((item) => Number(item.predictions)).filter((value) => Number.isFinite(value));
   const maxPrediction = predictionValues.length ? Math.max(...predictionValues) : 0;
   const avgPrediction = predictionValues.length
      ? Math.round((predictionValues.reduce((sum, value) => sum + value, 0) / predictionValues.length) * 10) / 10
      : 0;
   const totalPrediction = predictionValues.reduce((sum, value) => sum + value, 0);
   const topEntry = forecastData.find((item) => Number(item.predictions) === maxPrediction);
   const riskLabel = maxPrediction >= 80 ? 'CRITICAL' : maxPrediction >= 50 ? 'ELEVATED' : maxPrediction >= 20 ? 'GUARDED' : 'LOW';
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

   useEffect(() => {
      const loadForecast = async () => {
         try {
            const response = await apiGet<{ forecast: any[] }>('/api/signals/forecast/');
            if (response.forecast?.length) {
               setForecastData(response.forecast);
            }
         } catch {
            // No data available
         }

         try {
            const [healthRes, casesRes, auditRes] = await Promise.all([
              apiGet<{ connected: boolean }>('/api/signals/ai/health/'),
              apiGet<{ items: any[] }>('/api/signals/ai/cases/?limit=500'),
              apiGet<{ items: any[] }>('/api/signals/ai/audit/?limit=500'),
            ]);
            setAiConnected(Boolean(healthRes.connected));
            setAiCaseCount(casesRes.items?.length ?? 0);
            setAiAuditCount(auditRes.items?.length ?? 0);
            setAiCases(casesRes.items?.slice(0, 5) ?? []);
            setAiAudit(auditRes.items?.slice(0, 5) ?? []);
         } catch {
            setAiConnected(false);
            setAiCaseCount(0);
            setAiAuditCount(0);
            setAiCases([]);
            setAiAudit([]);
         }
      };
      loadForecast();
   }, []);

   const triggerAiIngest = async () => {
      const sources = [
         { label: 'YouTube', path: '/api/signals/ai/ingest/youtube/real/', body: { limit: 20 } },
         { label: 'X', path: '/api/signals/ai/ingest/x/real/', body: { limit: 25 } },
         { label: 'Instagram', path: '/api/signals/ai/ingest/instagram/real/', body: { limit: 10 } },
         { label: 'Reddit', path: '/api/signals/ai/ingest/reddit/real/', body: { limit: 25 } },
      ];

      const results = await Promise.allSettled(
         sources.map((source) => apiPost<{ connected?: boolean; message?: string }>(source.path, source.body))
      );

      const successCount = results.filter((result) => {
         if (result.status !== 'fulfilled') return false;
         const payload = result.value;
         return payload.connected !== false;
      }).length;

      if (successCount === 0) {
         showToast('Live ingest failed. Check AI server and API keys.', 'error');
         return;
      }

      const partial = successCount < sources.length;
      showToast(
         partial
            ? `Live ingest queued for ${successCount}/${sources.length} sources`
            : 'Live ingest queued for all sources',
         partial ? 'info' : 'success'
      );
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
              <p className="text-xl font-bold text-white tracking-tight">Predictive Intelligence Forecast</p>
            </div>
          </div>
          <div className="flex gap-3">
             <button className="ghost-button">
                <Share2 size={16} />
                Export Model
             </button>
             <button className="primary-button bg-brand-accent2" onClick={triggerAiIngest}>
                <Zap size={16} />
                Pull Live Feeds
             </button>
          </div>
        </div>

        <div className="glass-card p-8 bg-brand-surface border-brand-accent/20">
           <div className="flex items-center justify-between mb-8">
              <h3 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
                 <TrendingUp className="w-4 h-4 text-brand-accent" />
                 72-Hour Propagation Flux Forecast
              </h3>
              <div className="px-3 py-1 bg-brand-accent/10 border border-brand-accent/30 rounded-lg text-brand-accent text-[9px] font-mono font-bold tracking-widest uppercase">
                 Data Points: {forecastData.length}
              </div>
           </div>

                {forecastData.length === 0 && (
                   <p className="text-xs text-brand-muted mb-6">No forecast data available yet.</p>
                )}
                <div className="h-[400px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                 <AreaChart data={forecastData}>
                    <defs>
                       <linearGradient id="colorPredictions" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#0EA5E9" stopOpacity={0.4}/>
                          <stop offset="95%" stopColor="#0EA5E9" stopOpacity={0}/>
                       </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2D3748" vertical={false} strokeOpacity={0.3} />
                    <XAxis 
                      dataKey="time" 
                      stroke="#4A6080" 
                      fontSize={9} 
                      tickLine={false} 
                      axisLine={false}
                      interval={2}
                    />
                    <YAxis stroke="#4A6080" fontSize={10} tickLine={false} axisLine={false} />
                    <Tooltip 
                       contentStyle={{ backgroundColor: '#0D1421', border: '1px solid rgba(14,165,233,0.2)', borderRadius: '12px', boxShadow: '0 10px 30px rgba(0,0,0,0.5)' }}
                       itemStyle={{ color: '#0EA5E9', fontSize: '12px', fontWeight: 'bold' }}
                       labelStyle={{ color: '#4A6080', fontSize: '10px', marginBottom: '4px', textTransform: 'uppercase' }}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="predictions" 
                      stroke="#0EA5E9" 
                      strokeWidth={3} 
                      fillOpacity={1} 
                      fill="url(#colorPredictions)"
                      animationDuration={2000}
                    />
                 </AreaChart>
              </ResponsiveContainer>
           </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
           <div className="glass-card p-6 border-l-4 border-l-brand-danger bg-brand-danger/[0.02]">
              <div className="flex items-center gap-3 mb-4">
                 <div className="p-2 rounded-lg bg-brand-danger/10 text-brand-danger">
                    <Twitter size={18} />
                 </div>
                 <h4 className="text-sm font-bold text-white uppercase tracking-tight">Platform Risk</h4>
              </div>
              <div className="flex items-baseline gap-2 mb-2">
                 <span className="text-2xl font-bold text-brand-danger tracking-tighter">{riskLabel}</span>
              </div>
              <p className="text-[10px] text-brand-muted leading-relaxed">
                 Peak forecast window: {topEntry?.time || 'N/A'} · Max intensity {maxPrediction || 0}
              </p>
           </div>

           <div className="glass-card p-6 border-l-4 border-l-brand-warn bg-brand-warn/[0.02]">
              <div className="flex items-center gap-3 mb-4">
                 <div className="p-2 rounded-lg bg-brand-warn/10 text-brand-warn">
                    <Activity size={18} />
                 </div>
                 <h4 className="text-sm font-bold text-white uppercase tracking-tight">Velocity Score</h4>
              </div>
              <div className="flex items-baseline gap-2 mb-2">
                 <span className="text-3xl font-bold text-white tracking-tighter">{avgPrediction || 0}</span>
                 <span className="text-xs text-brand-muted">/ 100</span>
              </div>
              <p className="text-[10px] text-brand-muted leading-relaxed">
                 Average signal intensity across the current forecast window.
              </p>
           </div>

           <div className="glass-card p-6 border-l-4 border-l-brand-accent3 bg-brand-accent3/[0.02]">
              <div className="flex items-center gap-3 mb-4">
                 <div className="p-2 rounded-lg bg-brand-accent3/10 text-brand-accent3">
                    <Users size={18} />
                 </div>
                 <h4 className="text-sm font-bold text-white uppercase tracking-tight">Estimated Reach</h4>
              </div>
              <div className="flex items-baseline gap-2 mb-2">
                 <span className="text-3xl font-bold text-white tracking-tighter">{formatNumber(totalPrediction)}</span>
                 <span className="text-xs text-brand-muted uppercase">Total Events</span>
              </div>
              <p className="text-[10px] text-brand-muted leading-relaxed">
                 Aggregate forecast events across the active horizon.
              </p>
           </div>

           <div className="glass-card p-6 border-l-4 border-l-brand-accent bg-brand-accent/[0.03]">
              <div className="flex items-center gap-3 mb-4">
                 <div className="p-2 rounded-lg bg-brand-accent/10 text-brand-accent">
                    <ShieldAlert size={18} />
                 </div>
                 <h4 className="text-sm font-bold text-white uppercase tracking-tight">AI Pipeline Output</h4>
              </div>
              <div className="space-y-1 text-[11px] text-brand-muted font-mono">
                 <p>STATUS: <span className={aiConnected ? 'text-brand-accent3' : 'text-brand-danger'}>{aiConnected ? 'ONLINE' : 'OFFLINE'}</span></p>
                 <p>CASES: <span className="text-white font-bold">{formatNumber(aiCaseCount)}</span></p>
                 <p>AUDIT EVENTS: <span className="text-white font-bold">{formatNumber(aiAuditCount)}</span></p>
              </div>
           </div>
        </div>

        <div className="glass-card p-8 bg-brand-surface2 overflow-hidden relative">
           <div className="absolute top-0 right-0 w-64 h-64 bg-brand-accent/5 rounded-full blur-[80px] -mr-32 -mt-32" />
           <div className="relative z-10">
              <h3 className="text-lg font-bold text-white mb-2">AI Defensive Recommendation</h3>
              <p className="text-sm text-brand-muted max-w-3xl leading-relaxed mb-6">
                 Highest forecast window is <span className="text-white font-bold">{topEntry?.time || 'N/A'}</span> with intensity <span className="text-brand-danger font-bold">{maxPrediction || 0}</span>. 
                 Prioritize review and enforcement actions for the top-risk window.
              </p>
              <div className="flex gap-4">
                 <button className="primary-button bg-brand-danger h-10 px-6 text-xs">Authorize Escalation</button>
                 <button className="ghost-button h-10 px-6 text-xs border-white/10">View Detailed Evidence</button>
              </div>
           </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
           <div className="glass-card p-6 border-brand-accent3/20 bg-brand-accent3/[0.03]">
              <h3 className="text-sm font-bold text-white uppercase tracking-tight mb-4">Recent AI Cases</h3>
              <div className="space-y-2">
                 {!aiConnected ? (
                   <div className="text-[11px] text-brand-danger">AI pipeline offline.</div>
                 ) : aiCases.length === 0 ? (
                   <div className="text-[11px] text-brand-muted">No AI cases yet.</div>
                 ) : aiCases.map((c: any) => (
                   <div key={String(c.case_id)} className="p-3 rounded-xl border border-white/10 bg-black/20">
                      <div className="flex justify-between text-[10px] font-mono">
                         <span className="text-brand-muted uppercase">{String(c.platform || 'unknown')}</span>
                         <span className="text-white">{Number(c.score || 0).toFixed(3)}</span>
                      </div>
                      <p className="text-[10px] text-brand-accent3 uppercase">{String(c.action || 'NO_ACTION')}</p>
                      <p className="text-[10px] text-brand-muted truncate">CASE {String(c.case_id || '')}</p>
                      <p className="text-[10px] text-brand-muted truncate">JOB {String(c.job_id || 'N/A')}</p>
                      <p className="text-[10px] text-brand-muted truncate">POST {String(c.post_id || 'N/A')} · ACCOUNT {String(c.account_id || 'N/A')}</p>
                      <p className="text-[10px] text-brand-muted truncate">MEDIA {String(c.media_type || 'N/A')} · STATUS {String(c.status || 'N/A')} · CONF {String(c.confidence_tier || 'N/A')}</p>
                      <p className="text-[10px] text-brand-muted truncate">SOURCE {String(c.source_type || c.platform || 'N/A')} · SEVERITY {String(c.severity || 'N/A')} · CONFIDENCE {String(c.confidence ?? c.score ?? 'N/A')}</p>
                      <p className="text-[10px] text-brand-muted truncate">MATCHED ASSET {String(c.matched_asset_id || 'N/A')}</p>
                      <p className="text-[10px] text-brand-muted truncate">URL {String(c.media_url || 'N/A')}</p>
                      <p className="text-[10px] text-brand-muted">TIME {formatTs(c.created_at)}</p>
                      <p className="text-[10px] text-brand-muted">EXPLANATION: {String(c.explanation || 'N/A')}</p>
                      <details className="mt-2">
                        <summary className="text-[10px] text-brand-accent cursor-pointer uppercase font-mono">View Evidence JSON</summary>
                        <pre className="mt-2 text-[10px] text-brand-muted bg-black/30 rounded-lg p-2 overflow-x-auto">{toPrettyJson(c.evidence)}</pre>
                      </details>
                   </div>
                 ))}
              </div>
           </div>

           <div className="glass-card p-6 border-brand-accent/20 bg-brand-accent/[0.03]">
              <h3 className="text-sm font-bold text-white uppercase tracking-tight mb-4">Recent AI Audit</h3>
              <div className="space-y-2">
                 {!aiConnected ? (
                   <div className="text-[11px] text-brand-danger">AI pipeline offline.</div>
                 ) : aiAudit.length === 0 ? (
                   <div className="text-[11px] text-brand-muted">No AI audit events yet.</div>
                 ) : aiAudit.map((event: any, idx: number) => (
                   <div key={`${String(event.event_id || idx)}`} className="p-3 rounded-xl border border-white/10 bg-black/20">
                      <p className="text-[10px] text-brand-accent uppercase font-mono truncate">{String(event.event_type || 'EVENT')}</p>
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
        </div>
      </main>
    </div>
  );
}
