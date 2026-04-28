import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, Database, AlertCircle, Map, 
  Link as LinkIcon, FileText, TrendingUp, User, Settings, HelpCircle, LogOut,
  Building2, Cpu, Terminal, Wrench, Users, Radar, Menu, X
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useAuth } from '../../context/AuthContext';
import { SentinelLogo } from './SentinelLogo';

interface SidebarProps {
  role: 'admin' | 'user';
}

export function SentinelSidebar({ role }: SidebarProps) {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  const userNav = [
    { group: 'Main', items: [
      { name: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' },
      { name: 'My Assets', icon: Database, href: '/assets' },
      { name: 'Violations', icon: AlertCircle, href: '/violations' },
      { name: 'Threat Map', icon: Map, href: '/threat-map' },
    ]},
    { group: 'Tools', items: [
      { name: 'Blockchain Proof', icon: LinkIcon, href: '/blockchain' },
      { name: 'DMCA Center', icon: FileText, href: '/dmca' },
      { name: 'Propagation Forecast', icon: TrendingUp, href: '/forecast' },
    ]},
    { group: 'Account', items: [
      { name: 'Profile', icon: User, href: '/profile' },
      { name: 'Settings', icon: Settings, href: '/settings' },
      { name: 'Help', icon: HelpCircle, href: '/help' },
    ]}
  ];

  const adminNav = [
    { group: 'Overview', items: [
      { name: 'Dashboard', icon: LayoutDashboard, href: '/admin' },
    ]},
    { group: 'Monitoring', items: [
      { name: 'All Violations', icon: AlertCircle, href: '/admin/violations' },
      { name: 'Live Crawl Feed', icon: TrendingUp, href: '/admin/crawl-feed' },
      { name: 'Threat Map', icon: Map, href: '/admin/threat-map' },
    ]},
    { group: 'Platform', items: [
      { name: 'Organizations', icon: Building2, href: '/admin/organizations' },
      { name: 'All Assets', icon: Database, href: '/admin/assets' },
      { name: 'Blockchain Registry', icon: LinkIcon, href: '/admin/blockchain' },
    ]},
    { group: 'System', items: [
      { name: 'AI Service Health', icon: Cpu, href: '/admin/ai-health' },
      { name: 'Crawler Status', icon: Radar, href: '/admin/crawlers' },
      { name: 'System Logs', icon: Terminal, href: '/admin/logs' },
    ]},
    { group: 'Settings', items: [
      { name: 'Platform Settings', icon: Wrench, href: '/admin/settings' },
      { name: 'Admin Users', icon: Users, href: '/admin/users' },
    ]},
  ];

  const currentNav = role === 'admin' ? adminNav : userNav;

  const initials = user.name
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  return (
    <>
      {/* Mobile Toggle Button */}
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-6 left-6 z-[100] lg:hidden p-2 glass-card border-white/10 text-white hover:bg-white/10 transition-all"
      >
        {isOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[80] lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      <aside className={cn(
        "w-[240px] flex-shrink-0 border-r border-brand-border h-screen sticky top-0 bg-brand-surface/50 backdrop-blur-xl flex flex-col pt-6 overflow-y-auto transition-all duration-300 z-[90]",
        "fixed inset-y-0 left-0 lg:sticky lg:translate-x-0",
        isOpen ? "translate-x-0" : "-translate-x-full"
      )}>
      <div className="px-6 mb-8 flex flex-col gap-1">
        <Link to="/" className="flex items-center gap-2 mb-2">
          <SentinelLogo iconClassName="w-8 h-8" textClassName="[&_span:first-child]:tracking-[0.18em]" />
        </Link>
        <div className="flex items-center gap-2 mt-2">
          <span className="text-white font-medium text-sm truncate">{user.orgName}</span>
          <span className={cn(
            "text-[10px] font-mono px-1.5 py-0.5 rounded-sm uppercase tracking-tighter",
            user.role === 'admin'
              ? "bg-brand-danger/20 text-brand-danger"
              : "bg-brand-accent/20 text-brand-accent"
          )}>
            {user.role === 'admin' ? 'Admin' : user.plan}
          </span>
        </div>
      </div>

      <nav className="flex-1 px-4 space-y-8">
        {currentNav.map((group) => (
          <div key={group.group}>
            <h3 className="mission-control-header px-4 mb-4">
              {group.group}
            </h3>
            <div className="space-y-1">
              {group.items.map((item) => {
                const isActive = location.pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    onClick={() => setIsOpen(false)}
                    className={cn(
                      "flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm transition-all duration-200 group relative",
                      isActive 
                        ? "bg-brand-accent/10 border-l-[3px] border-brand-accent text-brand-accent" 
                        : "text-brand-muted hover:text-white hover:bg-white/5"
                    )}
                  >
                    <item.icon className={cn("w-4 h-4", isActive ? "text-brand-accent" : "group-hover:text-white")} />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="p-4 border-t border-brand-border mt-auto">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-full bg-brand-accent2/20 border border-brand-accent2/30 flex items-center justify-center text-brand-accent2 font-bold text-xs font-mono">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user.email}</p>
            <p className="text-[10px] text-brand-muted truncate font-mono uppercase">{user.plan} Plan</p>
          </div>
          <button
            onClick={logout}
            className="text-brand-muted hover:text-brand-danger transition-colors p-2"
            title="Logout"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
    </>
  );
}
