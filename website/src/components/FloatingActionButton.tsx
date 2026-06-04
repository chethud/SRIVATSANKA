import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, MessageSquare, ShoppingBag } from 'lucide-react';

export function FloatingActionButton() {
  const [open, setOpen] = useState(false);

  return (
    <div className="fab-root fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
      <AnimatePresence>
        {open && (
          <>
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }}>
              <Link
                to="/enquiries"
                className="flex items-center gap-2 px-4 py-2.5 rounded-full glass-panel shadow-[var(--shadow-md)] text-sm font-medium text-[var(--foreground)] hover:bg-[var(--primary-light)]"
                onClick={() => setOpen(false)}
              >
                <MessageSquare size={18} className="text-[var(--primary)]" />
                New enquiry
              </Link>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }} transition={{ delay: 0.05 }}>
              <Link
                to="/orders"
                className="flex items-center gap-2 px-4 py-2.5 rounded-full glass-panel shadow-[var(--shadow-md)] text-sm font-medium text-[var(--foreground)] hover:bg-[var(--primary-light)]"
                onClick={() => setOpen(false)}
              >
                <ShoppingBag size={18} className="text-[var(--primary)]" />
                Orders
              </Link>
            </motion.div>
          </>
        )}
      </AnimatePresence>
      <motion.button
        type="button"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setOpen((o) => !o)}
        className="w-14 h-14 rounded-full bg-[var(--primary)] text-white shadow-[var(--shadow-lg)] flex items-center justify-center"
        aria-label="Quick actions"
      >
        <motion.div animate={{ rotate: open ? 45 : 0 }}>
          <Plus size={26} strokeWidth={2.5} />
        </motion.div>
      </motion.button>
    </div>
  );
}
