import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { CheckCircle, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';
import { cn } from '../../lib/utils';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

let toastListeners: ((toasts: Toast[]) => void)[] = [];
let toasts: Toast[] = [];

export const showToast = (message: string, type: ToastType = 'info') => {
  const id = Math.random().toString(36).substring(2, 9);
  toasts = [{ id, message, type }, ...toasts].slice(0, 4);
  toastListeners.forEach(l => l(toasts));
  setTimeout(() => {
    toasts = toasts.filter(t => t.id !== id);
    toastListeners.forEach(l => l(toasts));
  }, 5000);
};

export function GlobalToast() {
  const [currentToasts, setCurrentToasts] = useState<Toast[]>([]);

  useEffect(() => {
    toastListeners.push(setCurrentToasts);
    return () => {
      toastListeners = toastListeners.filter(l => l !== setCurrentToasts);
    };
  }, []);

  const icons = {
    success: <CheckCircle className="text-brand-accent3" size={18} />,
    error: <AlertCircle className="text-brand-danger" size={18} />,
    warning: <AlertTriangle className="text-brand-warn" size={18} />,
    info: <Info className="text-brand-accent" size={18} />,
  };

  const borders = {
    success: 'border-brand-accent3/20',
    error: 'border-brand-danger/20',
    warning: 'border-brand-warn/20',
    info: 'border-brand-accent/20',
  };

  return (
    <div className="fixed top-6 right-6 z-[100] flex flex-col gap-3">
      <AnimatePresence>
        {currentToasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className={cn(
              "glass-card px-4 py-3 flex items-center gap-3 min-w-[280px] border shadow-xl bg-brand-surface/90",
              borders[toast.type]
            )}
          >
            {icons[toast.type]}
            <span className="text-sm font-medium text-white flex-1">{toast.message}</span>
            <button 
              onClick={() => {
                toasts = toasts.filter(t => t.id !== toast.id);
                toastListeners.forEach(l => l(toasts));
              }}
              className="text-brand-muted hover:text-white"
            >
              <X size={14} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
