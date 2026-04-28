import { useState, useEffect } from 'react';
import { Menu, X } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '../../lib/utils';
import { SentinelLogo } from './SentinelLogo';
import { useAuth } from '../../context/AuthContext';

export function NavBar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  const { isAuthenticated, logout } = useAuth();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 60);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { name: 'Features', href: '/#features' },
    { name: 'How It Works', href: '/#how-it-works' },
    { name: 'Blockchain', href: '/#blockchain' },
  ];

  return (
    <nav 
      className={cn(
        "fixed top-0 left-0 w-full z-50 transition-all duration-300",
        scrolled ? "bg-brand-bg/95 backdrop-blur-md border-b border-brand-border py-3 shadow-[0_8px_30px_rgb(0,0,0,0.5)]" : "bg-transparent py-6"
      )}
    >
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 group">
          <SentinelLogo
            iconClassName="w-8 h-8 transition-transform group-hover:scale-110"
            textClassName="hidden sm:block"
          />
        </Link>

        {/* Desktop Links */}
        <div className="hidden md:flex items-center gap-10">
          {navLinks.map((link) => (
             location.pathname === '/' ? (
               <a 
                 key={link.name} 
                 href={link.href.replace('/', '')} 
                 className="font-mono text-[11px] uppercase tracking-widest text-brand-muted hover:text-brand-accent transition-colors"
               >
                 {link.name}
               </a>
             ) : (
               <Link 
                 key={link.name} 
                 to={link.href} 
                 className="font-mono text-[11px] uppercase tracking-widest text-brand-muted hover:text-brand-accent transition-colors"
               >
                 {link.name}
               </Link>
             )
          ))}
        </div>

        {/* Right Actions */}
        <div className="hidden md:flex items-center gap-4">
          {isAuthenticated ? (
            <>
              <Link to="/dashboard" className="primary-button text-sm h-10">
                Open Console
              </Link>
              <button
                onClick={logout}
                className="text-sm font-medium text-brand-muted px-4 py-2 hover:bg-white/5 rounded-lg transition-all"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm font-medium text-brand-accent px-4 py-2 hover:bg-brand-accent/10 rounded-lg transition-all">
                Login
              </Link>
              <Link to="/register" className="primary-button text-sm h-10">
                Start Free Trial
              </Link>
            </>
          )}
        </div>

        {/* Mobile Toggle */}
        <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="md:hidden text-brand-text">
          {mobileMenuOpen ? <X /> : <Menu />}
        </button>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 top-[60px] bg-brand-bg z-40 p-6 flex flex-col gap-8 md:hidden">
          {navLinks.map((link) => (
            <a 
              key={link.name} 
              href={link.href} 
              onClick={() => setMobileMenuOpen(false)}
              className="text-2xl font-bold text-white"
            >
              {link.name}
            </a>
          ))}
          <div className="flex flex-col gap-4 mt-auto">
            {isAuthenticated ? (
              <>
                <Link to="/dashboard" onClick={() => setMobileMenuOpen(false)} className="primary-button w-full">Open Console</Link>
                <button onClick={logout} className="ghost-button w-full">Logout</button>
              </>
            ) : (
              <>
                <Link to="/login" className="ghost-button w-full">Login</Link>
                <Link to="/register" className="primary-button w-full">Start Free Trial</Link>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
