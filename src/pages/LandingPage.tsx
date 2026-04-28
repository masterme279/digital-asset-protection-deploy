import { motion, AnimatePresence } from 'motion/react';
import { NavBar } from '../components/shared/NavBar';
import { 
  Shield, CheckCircle, Upload, Fingerprint, Link as LinkIcon, 
  Radar, TrendingUp, ArrowRight, PlayCircle, Globe, ChevronRight,
  Twitter, Github, Linkedin, Slack, Database, ExternalLink
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useState, useEffect, useRef } from 'react';
import React from 'react';
import { cn, formatNumber } from '../lib/utils';
import { showToast } from '../components/shared/GlobalToast';
import { apiGet } from '../lib/api';
import { useAuth } from '../context/AuthContext';

export function LandingPage() {
  const { isAuthenticated } = useAuth();
  const [stats, setStats] = useState<{
    violations: number | null;
    assets: number | null;
    dmca: number | null;
  }>({
    violations: null,
    assets: null,
    dmca: null,
  });

  useEffect(() => {
    if (!isAuthenticated) {
      setStats({ violations: null, assets: null, dmca: null });
      return;
    }
    const loadStats = async () => {
      try {
        const [violationsRes, assetsRes, dmcaRes] = await Promise.all([
          apiGet<{ violations: any[] }>('/api/signals/violations/'),
          apiGet<{ assets: any[]; total?: number }>('/api/assets/'),
          apiGet<{ notices: any[] }>('/api/signals/dmca/'),
        ]);
        setStats({
          violations: violationsRes.violations?.length ?? 0,
          assets: assetsRes.total ?? assetsRes.assets?.length ?? 0,
          dmca: dmcaRes.notices?.length ?? 0,
        });
      } catch {
        setStats({ violations: null, assets: null, dmca: null });
      }
    };
    loadStats();
  }, [isAuthenticated]);

  useEffect(() => {
    document.title = "SENTINEL · Digital Asset Protection";
  }, []);

  const [demoStep, setDemoStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setDemoStep((prev) => (prev + 1) % 3);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const headlineWords = "Protect Your Digital Assets in Real-Time".split(" ");

  return (
    <div className="min-h-screen bg-brand-bg overflow-x-hidden font-sans">
      <NavBar />
      
      {/* Hero Section */}
      <section className="relative min-h-[90vh] flex items-center justify-center pt-32 pb-32">
        <div className="bg-grid" />
        
        {/* Animated Orbs */}
        <div className="orb orb-1 float-animation" />
        <div className="orb orb-2 float-animation" style={{ animationDelay: '2s' }} />

        <div className="max-w-7xl mx-auto px-6 flex flex-col lg:flex-row items-center gap-16 relative z-10">
          <div className="w-full lg:w-3/5 flex flex-col items-center lg:items-start text-center lg:text-left">
            <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="inline-flex items-center px-4 py-1.5 rounded-full border border-brand-accent/30 bg-brand-accent/10 text-brand-accent font-mono text-[11px] mb-8 uppercase tracking-wider"
            >
              Google Solution Challenge 2026 · AI + Blockchain + Real-Time Detection
            </motion.div>

            <h1 className="text-[clamp(36px,6vw,64px)] font-bold leading-[1.1] tracking-tight text-white mb-6">
              {headlineWords.map((word, i) => (
                <motion.span
                  key={i}
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1, duration: 0.5, ease: "easeOut" }}
                  className="inline-block mr-[0.25em]"
                >
                  {word}
                </motion.span>
              ))}
            </h1>

            <motion.p 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="text-lg text-brand-muted max-w-xl mb-10 leading-relaxed font-sans"
            >
              SENTINEL fingerprints your content with AI, registers ownership on the Polygon blockchain, 
              and detects unauthorized copies within 15 minutes — before revenue is lost.
            </motion.p>

            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
              className="flex flex-col sm:flex-row gap-4"
            >
              <Link to={isAuthenticated ? "/dashboard" : "/register"} className="primary-button group h-[48px] px-8 text-base">
                {isAuthenticated ? "Open Console" : "Upload Your First Asset"}
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
              <button 
                onClick={() => showToast("Loading high-fidelity protocol documentation...", "info")}
                className="ghost-button group h-[48px] px-8 text-base border-brand-border text-white hover:bg-white/5"
              >
                <PlayCircle className="w-5 h-5 mr-2" />
                Watch 2-min Demo
              </button>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.2 }}
              className="mt-16 flex items-center divide-x divide-white/10 gap-8"
            >
              {[
                { val: stats.violations, label: 'violations detected', prefix: '', suffix: '' },
                { val: stats.assets, label: 'assets protected', prefix: '', suffix: '+' },
                { val: stats.dmca, label: 'dmca notices', prefix: '', suffix: '+' },
              ].map((stat, i) => (
                <div key={i} className="pl-8 first:pl-0 font-mono">
                  <Counter value={stat.val} prefix={stat.prefix} suffix={stat.suffix} />
                  <div className="text-[10px] uppercase text-brand-muted tracking-[0.2em] mt-1">{stat.label}</div>
                </div>
              ))}
            </motion.div>
          </div>

          {/* Hero Mockup */}
          <div className="w-full lg:w-2/5 relative flex justify-center perspective-2000 h-[400px]">
            <motion.div 
              initial={{ opacity: 0, rotateX: 0, rotateY: 0, z: -100 }}
              animate={{ opacity: 1, rotateX: 12, rotateY: -15, z: 0 }}
              whileHover={{ rotateX: 5, rotateY: -5, scale: 1.02 }}
              transition={{ duration: 1, ease: "easeOut" }}
              className="glass-card-3d p-6 w-full max-w-[400px] h-[320px] relative overflow-hidden border-brand-accent/30 shadow-[20px_40px_60px_rgba(0,0,0,0.6)]"
            >
              <div className="scan-line-element" />
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-brand-danger animate-pulse" />
                  <span className="text-[11px] font-mono text-brand-danger uppercase font-bold tracking-widest">Violation Detected</span>
                </div>
                <span className="text-[10px] font-mono text-brand-muted">2 min ago</span>
              </div>

              <div className="space-y-6">
                <div 
                  className="flex items-start gap-4 p-4 bg-white/5 rounded-xl border border-white/5 backdrop-blur-sm transition-transform duration-300 hover:translate-z-10"
                  style={{ transform: 'translateZ(20px)' }}
                >
                  <div className="w-10 h-10 rounded-lg bg-brand-accent/20 flex items-center justify-center text-brand-accent border border-brand-accent/30">
                    <Globe className="w-5 h-5" />
                  </div>
                  <div className="flex-1">
                    <div className="text-[10px] font-mono text-white mb-1 uppercase tracking-wider opacity-60">Twitter / X</div>
                    <div className="text-sm font-bold text-white mb-1">Match Highlights Clip</div>
                    <div className="flex items-center gap-2">
                       <span className="badge-high text-[9px] px-1.5 py-0">Similarity 97%</span>
                       <span className="text-[9px] font-mono text-brand-muted">Ref: 0x4f...</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-2" style={{ transform: 'translateZ(40px)' }}>
                   <div className="flex justify-between text-[10px] font-mono text-brand-muted uppercase tracking-widest">
                      <span>AI Verification</span>
                      <span>97.42%</span>
                   </div>
                   <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: '97%' }}
                        transition={{ duration: 2, delay: 1 }}
                        className="h-full bg-brand-accent shadow-[0_0_12px_rgba(14,165,233,0.6)]"
                      />
                   </div>
                </div>

                <button 
                  style={{ transform: 'translateZ(30px)' }}
                  onClick={() => showToast("Issuing Automated DMCA Notice [SENTINEL-ENFORCE-v4]", "warning")}
                  className="w-full py-2 bg-brand-danger text-white font-mono text-[11px] uppercase font-bold rounded-lg shadow-[0_0_20px_rgba(239,68,68,0.3)] hover:scale-[1.05] transition-transform"
                >
                  Issue Automated DMCA
                </button>
              </div>
            </motion.div>
            
            {/* Floating Elements for extra 3D feel */}
            <motion.div 
              animate={{ y: [0, -20, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              className="absolute -top-10 -right-10 glass-card p-3 border-brand-accent3/30"
              style={{ transform: 'translateZ(100px)' }}
            >
               <CheckCircle className="text-brand-accent3 w-6 h-6" />
            </motion.div>

            <motion.div 
              animate={{ y: [0, 20, 0] }}
              transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
              className="absolute -bottom-10 -left-10 glass-card p-3 border-brand-accent/30"
              style={{ transform: 'translateZ(80px)' }}
            >
               <Fingerprint className="text-brand-accent w-6 h-6" />
            </motion.div>
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section className="border-y border-brand-border py-10 px-6 bg-brand-surface/20">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-center gap-6 md:gap-16">
          <span className="text-[10px] font-mono font-bold text-brand-muted uppercase tracking-[0.25em] whitespace-nowrap">
            Trusted by Global Rights Holders
          </span>
          <div className="flex flex-wrap justify-center gap-6">
            {[
              { name: 'UEFA', icon: Globe },
              { name: 'FIFA', icon: Shield },
              { name: 'LA LIGA', icon: Globe },
              { name: 'PREMIER LEAGUE', icon: Shield },
              { name: 'NBA', icon: Globe }
            ].map((brand) => (
              <motion.div
                key={brand.name}
                whileHover={{ y: -2, scale: 1.05 }}
                className="px-5 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.07] hover:border-brand-accent/30 hover:bg-brand-accent/5 transition-all cursor-crosshair group flex items-center gap-3"
              >
                <brand.icon className="w-4 h-4 text-white/20 group-hover:text-brand-accent transition-colors" />
                <span className="font-mono text-[11px] font-black text-white/30 group-hover:text-white/60 tracking-[0.2em] transition-colors uppercase">
                  {brand.name}
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-32 px-6 relative overflow-hidden">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-4xl font-bold text-white mb-6">Four Angles of Protection</h2>
            <p className="text-brand-muted max-w-2xl mx-auto">Our unique stack combines high-dimensionality AI search with immutable blockchain ledgering to provide absolute asset security.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {[
              { 
                icon: Fingerprint, 
                title: "AI Fingerprinting", 
                accent: "brand-accent2", 
                tags: ['pHash', 'CLIP', 'FAISS', 'Watermark'],
                desc: "pHash + CLIP embeddings + FAISS vector search. Detects cropped, recolored, or re-encoded copies. Invisible steganographic watermark survives JPEG re-encoding."
              },
              { 
                icon: LinkIcon, 
                title: "Blockchain Provenance", 
                accent: "brand-accent3", 
                tags: ['Polygon', 'IPFS', 'Immutable'],
                desc: "Every asset registered on Polygon Amoy. Immutable SHA256 hash + timestamp. Publicly verifiable on Polygonscan. Ownership disputes become mathematically provable."
              },
              { 
                icon: Radar, 
                title: "Real-Time Detection", 
                accent: "brand-danger", 
                tags: ['15-min SLA', 'Scrapy', 'WebSocket'],
                desc: "Scrapy + Playwright crawlers sweep Google Images, Twitter, YouTube, Reddit. Violations appear on your dashboard within 15 minutes. Evidence stored on IPFS."
              },
              { 
                icon: TrendingUp, 
                title: "Predictive Forecasting", 
                accent: "brand-warn", 
                tags: ['Prophet', 'NetworkX', '72h Forecast'],
                desc: "NetworkX propagation graphs + Meta Prophet time-series. Forecasts how a leak spreads 24–72 hours ahead. Risk score by severity × platform × viral velocity."
              }
            ].map((f, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <FeatureCard {...f} />
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-32 px-6 bg-brand-surface2/30 relative">
         <div className="max-w-7xl mx-auto">
            <div className="text-center mb-24">
               <h2 className="text-4xl font-bold text-white mb-6">From Upload to Enforcement in Minutes</h2>
               <p className="text-brand-muted">A streamlined verification and detection loop.</p>
            </div>

            <div className="relative">
               {/* Animated Path */}
               <div className="absolute top-[24px] left-0 w-full h-[2px] hidden md:block px-12">
                  <div className="w-full h-full border-t border-dashed border-brand-accent/30 dash-animation" />
               </div>

               <div className="grid grid-cols-1 md:grid-cols-5 gap-12 relative z-10">
                  {[
                    { step: '1', title: 'Upload Asset', desc: 'Securely upload image or video highlights.' },
                    { step: '2', title: 'AI Fingerprint', desc: 'Neural embeddings generated in <2s.' },
                    { step: '3', title: 'On-Chain Registry', desc: 'Proof anchored to Polygon Amoy.' },
                    { step: '4', title: 'Real-Time Crawl', desc: 'Continuous similarity sweeps.' },
                    { step: '5', title: 'Enforce', desc: 'Automated DMCA with proof links.' },
                  ].map((item, i) => (
                    <motion.div 
                      key={i} 
                      initial={{ opacity: 0, scale: 0.8 }}
                      whileInView={{ opacity: 1, scale: 1 }}
                      viewport={{ once: true }}
                      transition={{ delay: i * 0.15 }}
                      className="flex flex-col items-center text-center group"
                    >
                       <div className="w-12 h-12 rounded-full bg-brand-accent flex items-center justify-center text-brand-bg font-bold text-lg mb-8 shadow-[0_0_24px_rgba(14,165,233,0.4)] group-hover:scale-110 transition-transform">
                          {item.step}
                       </div>
                       <h3 className="text-white font-bold mb-3">{item.title}</h3>
                       <p className="text-sm text-brand-muted leading-relaxed">{item.desc}</p>
                    </motion.div>
                  ))}
               </div>
            </div>
         </div>
      </section>

      {/* Blockchain Callout */}
      <section id="blockchain" className="py-32 px-6 border-y border-brand-border relative overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-brand-accent/5 rounded-full blur-[140px] pointer-events-none" />
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
           <motion.div 
             initial={{ opacity: 0, x: -40 }}
             whileInView={{ opacity: 1, x: 0 }}
             viewport={{ once: true }}
           >
              <h2 className="text-4xl font-bold text-white mb-8">Every Asset. <br />Immutably Proven.</h2>
              <p className="text-lg text-brand-muted mb-10 leading-relaxed max-w-lg">
                 When you upload to SENTINEL, ownership is registered on the Polygon blockchain in seconds. 
                 Show any court, any platform, any regulator — an immutable transaction hash with your asset's fingerprint and timestamp.
              </p>
              <div className="flex flex-col gap-6">
                 <button 
                  onClick={() => showToast("Navigating to Polygonscan Mainnet Node...", "info")}
                  className="font-mono text-brand-accent font-bold flex items-center gap-3 group w-fit"
                 >
                    <span className="border-b border-brand-accent/0 group-hover:border-brand-accent/100 transition-all text-left">View Ecosystem on Polygonscan</span>
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-2 transition-transform" />
                 </button>
                 <div className="flex items-center gap-8 mt-4 opacity-60">
                    <div className="flex items-center gap-3">
                       <LinkIcon className="h-5 w-5 text-brand-accent3" />
                       <span className="text-[10px] font-mono font-bold text-white/40 uppercase tracking-widest">POLYGON</span>
                    </div>
                    <div className="flex items-center gap-3">
                       <Shield className="h-5 w-5 text-brand-accent3" />
                       <span className="text-[10px] font-mono font-bold text-white/40 uppercase tracking-widest">IPFS</span>
                    </div>
                 </div>
              </div>
           </motion.div>

           <motion.div 
             initial={{ opacity: 0, x: 40 }}
             whileInView={{ opacity: 1, x: 0 }}
             viewport={{ once: true }}
             className="glass-card p-1 min-h-[300px] bg-brand-accent/5"
           >
              <div className="glass-card bg-brand-bg/60 p-8 font-mono text-[13px] h-full flex flex-col">
                 <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-3">
                       <div className="w-3 h-3 rounded-full bg-brand-accent3 shadow-[0_0_10px_rgba(16,185,129,0.5)]" />
                       <span className="text-brand-accent3 font-bold tracking-widest uppercase">Verified Payload</span>
                    </div>
                    <span className="text-brand-muted">Block #48291...</span>
                 </div>
                 <div className="space-y-4 flex-1">
                    {[
                      { label: 'Asset Hash', val: '0x4f3a...d9e1', icon: Fingerprint },
                      { label: 'TX Hash', val: '0x8c91...7a2b', icon: LinkIcon },
                      { label: 'Network', val: 'Polygon Amoy', icon: Globe },
                      { label: 'Timestamp', val: '2026-04-15 10:23:44', icon: CheckCircle },
                    ].map((row, i) => (
                      <div key={i} className="flex justify-between items-center opacity-80 group/row">
                        <div className="flex items-center gap-2">
                          <row.icon size={12} className="text-brand-muted group-hover/row:text-brand-accent transition-colors" />
                          <span className="text-brand-muted">{row.label}</span>
                        </div>
                        <span className={cn("font-bold", i < 2 ? "text-brand-accent" : "text-white")}>{row.val}</span>
                      </div>
                    ))}
                 </div>
                 <div className="mt-12 p-3 bg-brand-accent3/10 border border-brand-accent3/20 rounded-lg text-brand-accent3 text-[11px] text-center font-bold flex items-center justify-center gap-2">
                    <CheckCircle size={14} className="animate-pulse" />
                    TRANSACTION CONFIRMED & INDEXED
                 </div>
              </div>
           </motion.div>
        </div>
      </section>

      {/* Live Violation Feed */}
      <section className="py-32 px-6">
         <div className="max-w-3xl mx-auto">
            <div className="text-center mb-16">
               <h2 className="text-4xl font-bold text-white mb-6">See a Violation Get Caught</h2>
               <p className="text-brand-muted">Our crawlers detect similarities with extreme precision.</p>
            </div>

            <div className="glass-card overflow-hidden shadow-2xl">
               <div className="bg-white/5 px-8 py-5 border-b border-brand-border flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-brand-accent3 animate-pulse" />
                    <span className="font-mono text-xs uppercase font-bold text-white tracking-widest">Real-Time Detection Engine</span>
                  </div>
                  <span className="badge font-mono text-[9px] uppercase tracking-tighter">15-min SLA Active</span>
               </div>
               
               <div className="relative">
                  <AnimatePresence mode="popLayout">
                    {demoStep === 0 && (
                      <motion.div key="v1" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}>
                        <ViolationRow severity="high" platform="Twitter" asset="UCL Final Match Highlights" similarity="97.8%" time="2 min ago" />
                      </motion.div>
                    )}
                    {demoStep === 1 && (
                      <motion.div key="v2" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}>
                        <ViolationRow severity="med" platform="Reddit" asset="Vinícius Jr Training Leak" similarity="84.2%" time="11 min ago" />
                      </motion.div>
                    )}
                    {demoStep === 2 && (
                      <motion.div key="v3" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}>
                        <ViolationRow severity="high" platform="Telegram" asset="Broadcaster Direct Feed Leak" similarity="99.4%" time="Just now" />
                      </motion.div>
                    )}
                  </AnimatePresence>
               </div>
            </div>
         </div>
      </section>

      {/* Stats Row */}
      <section className="py-24 border-y border-brand-border bg-brand-surface/40">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
           {[
             { val: '15 min', label: 'Avg detection time' },
             { val: '99.2%', label: 'Fingerprint Accuracy' },
             { val: 'Polygon', label: 'Settlement Engine' },
             { val: '$0', label: 'to start building' },
           ].map((s, i) => (
             <div key={i} className="text-center font-mono">
                <div className="text-4xl font-bold text-brand-accent mb-2 uppercase">{s.val}</div>
                <div className="text-[11px] text-brand-muted uppercase tracking-[0.2em]">{s.label}</div>
             </div>
           ))}
        </div>
      </section>

      {/* Final CTA Banner */}
      <section className="py-32 px-6 relative overflow-hidden text-center bg-brand-surface">
         <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(14,165,233,0.08)_0%,transparent_70%)]" />
         <div className="max-w-4xl mx-auto relative z-10">
            <h2 className="text-5xl font-bold text-white mb-8">Start Protecting Your Assets Today</h2>
            <p className="text-xl text-brand-muted mb-12 max-w-2xl mx-auto leading-relaxed">
               Every second you wait is a second of lost revenue. Deploy SENTINEL in under 5 minutes.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
               <Link to="/register" className="primary-button h-[60px] px-12 text-lg font-bold shadow-[0_0_32px_rgba(14,165,233,0.4)]">
                 Create Free Account
               </Link>
               <Link to="/login" className="text-white hover:text-brand-accent font-mono text-sm uppercase tracking-widest font-bold">
                 Access Portal
               </Link>
            </div>
            <p className="mt-10 text-[11px] font-mono text-brand-muted uppercase tracking-widest font-bold opacity-40">
               Free to register • No credit card required • Standard API Access included
            </p>
         </div>
      </section>

      <footer className="bg-brand-bg pt-24 pb-12 border-t border-brand-border px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-16 mb-24">
            <div className="col-span-2">
              <div className="flex items-center gap-2 mb-8">
                <Shield className="w-10 h-10 text-brand-accent fill-brand-accent" />
                <span className="font-mono text-2xl font-bold tracking-widest text-white">SENTINEL</span>
              </div>
              <p className="text-brand-muted text-lg max-w-sm mb-10 leading-relaxed uppercase tracking-tighter opacity-80">
                AI + BLOCKCHAIN ASSET DEFENSE PROTOCOL FOR GLOBAL SPORTS IP.
              </p>
              <div className="flex gap-4">
                 {[
                   { icon: Twitter, color: 'text-sky-400', name: 'Twitter' },
                   { icon: Github, color: 'text-white', name: 'Github' },
                   { icon: Linkedin, color: 'text-blue-400', name: 'LinkedIn' },
                   { icon: Slack, color: 'text-emerald-400', name: 'Slack' }
                 ].map((social, i) => (
                   <button 
                     key={i} 
                     onClick={() => showToast(`Opening Sentinel ${social.name} channel...`, "info")}
                     className="w-10 h-10 rounded-lg bg-white/5 border border-white/5 flex items-center justify-center hover:bg-brand-accent/20 cursor-pointer transition-all hover:-translate-y-1"
                   >
                      <social.icon className={cn("w-5 h-5 opacity-60 hover:opacity-100", social.color)} />
                   </button>
                 ))}
              </div>
            </div>
            <div>
               <h4 className="text-white font-bold mb-8 uppercase tracking-widest text-sm">Product</h4>
               <ul className="space-y-6 text-sm text-brand-muted font-medium">
                  <li><Link to="/violations" className="hover:text-brand-accent transition-colors cursor-pointer text-left font-mono uppercase text-[10px] block">Digital Fingerprinting</Link></li>
                  <li><Link to="/blockchain" className="hover:text-brand-accent transition-colors cursor-pointer text-left font-mono uppercase text-[10px] block">Blockchain Ledger</Link></li>
                  <li><Link to="/forecast" className="hover:text-brand-accent transition-colors cursor-pointer text-left font-mono uppercase text-[10px] block">Real-Time Search</Link></li>
                  <li><Link to="/dmca" className="hover:text-brand-accent transition-colors cursor-pointer text-left font-mono uppercase text-[10px] block">Legal Automation</Link></li>
               </ul>
            </div>
            <div>
               <h4 className="text-white font-bold mb-8 uppercase tracking-widest text-sm">Ecosystem</h4>
               <ul className="space-y-6 text-sm text-brand-muted font-medium">
                  <li><button onClick={() => showToast("Redirecting to API Portal...", "info")} className="hover:text-brand-accent transition-colors cursor-pointer text-left font-mono uppercase text-[10px]">API Docs</button></li>
                  <li><button onClick={() => window.open("https://amoy.polygonscan.com", "_blank", "noopener noreferrer")} className="hover:text-brand-accent transition-colors cursor-pointer text-left font-mono uppercase text-[10px]">Polygon Explorer</button></li>
                  <li><button onClick={() => showToast("Viewing Trust Certificate...", "info")} className="hover:text-brand-accent transition-colors cursor-pointer text-left font-mono uppercase text-[10px]">Trust Center</button></li>
                  <li><button onClick={() => showToast("Entering Developer Sandbox...", "info")} className="hover:text-brand-accent transition-colors cursor-pointer text-left font-mono uppercase text-[10px]">Developer Portal</button></li>
               </ul>
            </div>
            <div>
               <h4 className="text-white font-bold mb-8 uppercase tracking-widest text-sm">Company</h4>
               <ul className="space-y-6 text-sm text-brand-muted font-medium">
                  <li><button onClick={() => showToast("Legal Policy Center loading...", "info")} className="hover:text-brand-accent transition-colors cursor-pointer font-mono uppercase text-[10px]">Privacy Policy</button></li>
                  <li><button onClick={() => showToast("Terms of Service loading...", "info")} className="hover:text-brand-accent transition-colors cursor-pointer font-mono uppercase text-[10px]">Terms of Service</button></li>
                  <li><button onClick={() => showToast("Opening Network Status Dashboard...", "info")} className="hover:text-brand-accent transition-colors cursor-pointer font-mono uppercase text-[10px]">Service Status</button></li>
                  <li><button onClick={() => showToast("Directing to Legal Council...", "info")} className="hover:text-brand-accent transition-colors cursor-pointer font-mono uppercase text-[10px]">Contact Legal</button></li>
               </ul>
            </div>
          </div>
          <div className="pt-12 border-t border-brand-border flex flex-col md:flex-row justify-between items-center gap-6 text-[10px] text-brand-muted font-mono uppercase tracking-[0.3em] font-bold">
            <span className="opacity-60 text-center md:text-left leading-relaxed">© 2026 SENTINEL Digital Asset Protection Systems · Google Solution Challenge 2026</span>
            <div className="flex items-center gap-4">
               <span className="text-brand-accent3">SENSORS ACTIVE</span>
               <span className="w-1.5 h-1.5 rounded-full bg-brand-accent3 animate-pulse" />
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Counter({ value, prefix = "", suffix = "" }: { value: number | null; prefix?: string; suffix?: string }) {
  const [count, setCount] = useState(0);
  const ref = useRef<number | null>(null);
  const isEmpty = value == null;

  useEffect(() => {
    if (isEmpty) {
      setCount(0);
      return;
    }
    const duration = 2200;
    const startTime = performance.now();

    const tick = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(eased * (value ?? 0)));
      if (progress < 1) {
        ref.current = requestAnimationFrame(tick);
      }
    };

    ref.current = requestAnimationFrame(tick);
    return () => { if (ref.current) cancelAnimationFrame(ref.current!); };
  }, [value, isEmpty]);

  const display = count >= 1_000_000
    ? (count / 1_000_000).toFixed(1) + "M"
    : count >= 1_000
    ? count.toLocaleString()
    : String(count);

  return (
    <div className="text-2xl font-bold text-white mb-1 font-mono">
      {isEmpty ? "—" : `${prefix}${display}${suffix}`}
    </div>
  );
}


function FeatureCard({ icon: Icon, title, desc, accent, tags }: any) {
  const borderClass = accent === 'brand-accent2' ? 'border-l-brand-accent2' : 
                   accent === 'brand-accent3' ? 'border-l-brand-accent3' :
                   accent === 'brand-danger' ? 'border-l-brand-danger' : 
                   'border-l-brand-warn';
                   
  const iconBgClass = accent === 'brand-accent2' ? 'bg-brand-accent2/10 text-brand-accent2' : 
                   accent === 'brand-accent3' ? 'bg-brand-accent3/10 text-brand-accent3' :
                   accent === 'brand-danger' ? 'bg-brand-danger/10 text-brand-danger' : 
                   'bg-brand-warn/10 text-brand-warn';

  return (
    <motion.div 
      whileHover={{ y: -4, scale: 1.005 }}
      className={cn(
        "glass-card p-8 flex flex-col h-full border-l-4 transition-all duration-300",
        borderClass
      )}
    >
      <div className={cn("w-12 h-12 rounded-xl mb-6 flex items-center justify-center", iconBgClass)}>
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-xl font-bold text-white mb-4">{title}</h3>
      <p className="text-brand-muted mb-8 leading-relaxed flex-1">{desc}</p>
      <div className="flex flex-wrap gap-2">
        {tags.map((tag: string) => (
          <span key={tag} className="text-[10px] font-mono font-bold uppercase tracking-widest px-2 py-1 bg-white/5 rounded border border-white/5 text-brand-muted">
            {tag}
          </span>
        ))}
      </div>
    </motion.div>
  );
}

function ViolationRow({ severity, platform, asset, similarity, time }: any) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-center gap-4 px-6 py-5 hover:bg-white/5 transition-colors border-l-4 border-l-transparent hover:border-l-brand-accent"
    >
       <div className={cn(
         "w-2 h-2 rounded-full",
         severity === 'high' ? 'bg-brand-danger' : 
         severity === 'med' ? 'bg-brand-warn' : 'bg-brand-accent3'
       )} />
       <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
             <span className="text-xs font-bold text-white font-mono uppercase">{platform}</span>
             <span className="text-[10px] text-brand-muted">•</span>
             <span className="text-[10px] text-brand-muted">{time}</span>
          </div>
          <p className="text-sm text-brand-text truncate">{asset}</p>
       </div>
       <div className="flex items-center gap-4">
          <span className={severity === 'high' ? 'badge-high' : severity === 'med' ? 'badge-med' : 'badge-low'}>
            {similarity} Similarity
          </span>
          <button 
            onClick={() => showToast(`DMCA notice generated · PDF ready for download · Reference: SENT-${Math.floor(100000 + Math.random() * 900000)}`, "warning")}
            className="px-3 py-1 text-[10px] font-mono border border-brand-danger text-brand-danger rounded hover:bg-brand-danger hover:text-white transition-all uppercase"
          >
            DMCA
          </button>
       </div>
    </motion.div>
  );
}
