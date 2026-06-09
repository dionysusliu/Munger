import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from './Sidebar';
import Header from './Header';

interface LayoutProps {
  children?: React.ReactNode;
}

const pageVariants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
};

const pageTransition = {
  duration: 0.4,
  ease: [0.23, 1, 0.32, 1] as [number, number, number, number],
};

export default function Layout({ children }: LayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const location = useLocation();

  return (
    <div className="min-h-[100dvh] flex">
      {/* Sidebar */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((c) => !c)}
      />

      {/* Main content area */}
      <div
        className="flex-1 flex flex-col transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)]"
        style={{
          marginLeft: sidebarCollapsed ? '64px' : '240px',
        }}
      >
        <Header />

        {/* Page content with transitions */}
        <main className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={pageTransition}
              className="h-full"
            >
              {children || <Outlet />}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
