import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';

import { useToast } from '../context/ToastContext';

const ICONS = {
  info: Info,
  success: CheckCircle2,
  error: AlertTriangle,
};

const TONE = {
  info: 'border-ultron-primary/40 text-ultron-bright',
  success: 'border-ultron-success/40 text-ultron-success',
  error: 'border-ultron-danger/40 text-ultron-danger',
};

export default function ToastContainer() {
  const { toasts, dismiss } = useToast();

  return (
    <div
      className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 w-[min(360px,90vw)]"
      role="region"
      aria-label="Notifications"
    >
      <AnimatePresence initial={false}>
        {toasts.map((toast) => {
          const Icon = ICONS[toast.type] || Info;
          return (
            <motion.div
              key={toast.id}
              layout
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, x: 40 }}
              role="alert"
              className={`glass-panel border ${TONE[toast.type]} px-4 py-3 flex items-start gap-3`}
            >
              <Icon className="w-4 h-4 mt-0.5 shrink-0" aria-hidden />
              <span className="flex-1 text-sm text-ultron-text">{toast.message}</span>
              <button
                onClick={() => dismiss(toast.id)}
                className="text-ultron-muted hover:text-ultron-text"
                aria-label="Dismiss notification"
              >
                <X className="w-4 h-4" aria-hidden />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
