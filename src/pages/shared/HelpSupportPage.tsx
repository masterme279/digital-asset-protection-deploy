import React, { useState, FormEvent } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { SentinelSidebar } from '../../components/shared/SentinelSidebar';
import { 
  HelpCircle, MessageSquare, Book, Terminal, Phone, Clock, 
  ExternalLink, Search, CheckCircle2, AlertCircle, FileText, LifeBuoy,
  X, Send, Download, Paperclip, ShieldCheck, Cpu
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { showToast } from '../../components/shared/GlobalToast';

export function HelpSupportPage() {
   const [messages, setMessages] = useState<{ role: 'soc' | 'user'; text: string; isAction?: boolean }[]>([]);
  const [input, setInput] = useState('');
  const [showTicketForm, setShowTicketForm] = useState(false);

  const handleSendMessage = () => {
    if (!input.trim()) return;
    const userMsg = input.trim();
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setInput('');
      showToast("Message queued for support review.", "info");
  };

  const handleOpenTicket = (e?: FormEvent) => {
    if (e) e.preventDefault();
      showToast("Support ticket submitted", "success");
    setShowTicketForm(false);
      setMessages(prev => [...prev, { role: 'soc', text: 'Ticket submitted. Support will follow up via email.' }]);
  };

  return (
    <div className="flex bg-brand-bg min-h-screen">
      <SentinelSidebar role="user" />
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Chat Header */}
        <div className="p-6 border-b border-brand-border bg-brand-surface/40 flex items-center justify-between">
           <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-2xl bg-brand-accent/10 flex items-center justify-center text-brand-accent shadow-[0_0_15px_rgba(14,165,233,0.1)]">
                 <Cpu size={20} />
              </div>
              <div>
                 <h1 className="text-lg font-bold text-white leading-tight">Sentinel Communications Hub</h1>
                 <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-brand-accent3 animate-pulse" />
                    <span className="text-[10px] font-mono text-brand-accent3 font-bold uppercase tracking-widest">Global SOC: ONLINE</span>
                 </div>
              </div>
           </div>
           <div className="flex gap-3">
              <button onClick={() => setShowTicketForm(true)} className="ghost-button h-10 px-4 text-xs font-mono border-brand-accent/20 text-brand-accent">
                 NEW_TICKET.EXE
              </button>
           </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-8 space-y-6 relative">
           <div className="absolute inset-0 sentinel-stamp opacity-[0.03] pointer-events-none" />
           
           <div className="max-w-4xl mx-auto space-y-6">
              {messages.map((m, i) => (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  key={i} 
                  className={cn("flex flex-col", m.role === 'user' ? 'items-end' : 'items-start')}
                >
                   <div className={cn(
                     "max-w-[70%] p-4 rounded-2xl relative shadow-lg",
                     m.role === 'user' 
                       ? 'bg-brand-accent text-white rounded-tr-none' 
                       : 'bg-brand-surface2 border border-brand-border/40 text-brand-text rounded-tl-none glass-card'
                   )}>
                      <p className="text-sm leading-relaxed">{m.text}</p>
                      {m.isAction && (
                        <div className="mt-4 flex gap-2">
                           <button onClick={() => setShowTicketForm(true)} className="px-3 py-1.5 bg-brand-accent text-white text-[10px] font-bold rounded-lg uppercase tracking-wider">Initialize Ticket</button>
                           <button onClick={() => setMessages(prev => [...prev, { role: 'soc', text: 'Acknowledged. Continuing monitoring protocol.' }])} className="px-3 py-1.5 bg-white/5 text-brand-muted text-[10px] font-bold rounded-lg uppercase tracking-wider">Dismiss</button>
                        </div>
                      )}
                   </div>
                   <span className="text-[9px] font-mono text-brand-muted mt-2 uppercase tracking-widest">
                      {m.role === 'soc' ? 'SENTINEL-SOC [01]' : 'FCB-ADMIN [JD]'} • {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                   </span>
                </motion.div>
              ))}
              {showTicketForm && (
                <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="glass-card p-8 border-brand-accent/20 bg-brand-accent/[0.02]">
                   <div className="flex items-center justify-between mb-6">
                      <h3 className="text-md font-bold text-white uppercase tracking-widest flex items-center gap-2">
                         <MessageSquare className="text-brand-accent w-4 h-4" />
                         Priority Ticket Generator
                      </h3>
                      <button onClick={() => setShowTicketForm(false)} className="text-brand-muted hover:text-white"><X size={16}/></button>
                   </div>
                   <form onSubmit={handleOpenTicket} className="grid grid-cols-2 gap-6">
                      <div className="space-y-2">
                         <label className="text-[9px] font-mono font-bold text-brand-muted uppercase tracking-widest">Category</label>
                         <select className="w-full bg-black/40 border border-brand-border rounded-xl px-4 py-3 text-xs text-white outline-none focus:border-brand-accent">
                            <option>Platform Bug</option>
                            <option>Account Issues</option>
                            <option>API Technical Fail</option>
                            <option>Other</option>
                         </select>
                      </div>
                      <div className="space-y-2">
                         <label className="text-[9px] font-mono font-bold text-brand-muted uppercase tracking-widest">ID / Asset Name</label>
                         <input type="text" placeholder="e.g. ASSET-8821" className="w-full bg-black/40 border border-brand-border rounded-xl px-4 py-3 text-xs text-white outline-none focus:border-brand-accent" />
                      </div>
                      <div className="col-span-2 space-y-2">
                         <label className="text-[9px] font-mono font-bold text-brand-muted uppercase tracking-widest">Technical Brief</label>
                         <textarea rows={3} placeholder="Describe the anomaly in detail..." className="w-full bg-black/40 border border-brand-border rounded-xl px-4 py-3 text-xs text-white outline-none focus:border-brand-accent resize-none" />
                      </div>
                      <div className="col-span-2 flex gap-4">
                         <button type="submit" className="primary-button flex-1 h-12 uppercase tracking-widest font-bold text-xs">Transmit to SOC</button>
                         <button type="button" onClick={() => setShowTicketForm(false)} className="ghost-button flex-1 h-12 uppercase tracking-widest font-bold text-xs">Cancel Protocol</button>
                      </div>
                   </form>
                </motion.div>
              )}
           </div>
        </div>

        {/* Input Area */}
        <div className="p-8 border-t border-brand-border bg-brand-surface/20">
           <div className="max-w-4xl mx-auto flex gap-4">
              <div className="flex-1 glass-card flex items-center px-6 py-4 border-brand-accent/10 focus-within:border-brand-accent transition-all">
                 <Terminal size={18} className="text-brand-accent mr-4" />
                 <input 
                    type="text" 
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                    placeholder="Enter support query or technical command..." 
                    className="flex-1 bg-transparent text-sm text-white outline-none" 
                 />
                 <div className="flex items-center gap-4 text-brand-muted">
                    <button className="hover:text-brand-accent transition-colors" title="Attach Logs"><Paperclip size={18} /></button>
                    <button className="hover:text-brand-accent transition-colors" title="Developer Docs"><Book size={18} /></button>
                 </div>
              </div>
              <button 
                onClick={handleSendMessage}
                className="w-14 h-14 rounded-2xl bg-brand-accent text-white flex items-center justify-center hover:shadow-[0_0_20px_rgba(14,165,233,0.4)] transition-all active:scale-95"
              >
                 <Send size={24} />
              </button>
           </div>
           <p className="max-w-4xl mx-auto mt-4 text-center text-[9px] font-mono text-brand-muted uppercase tracking-[0.2em] opacity-50">
              All communications are encrypted and logged for security compliance [SENTINEL-SEC-v4]
           </p>
        </div>
      </main>
    </div>
  );
}

