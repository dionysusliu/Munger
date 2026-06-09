import { useState, useCallback } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  BookOpen,
  Upload,
  PanelLeftClose,
  PanelLeftOpen,
  BookMarked,
  type LucideIcon,
} from 'lucide-react';

interface NavItem {
  label: string;
  icon: LucideIcon;
  path: string;
}

const navItems: NavItem[] = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/' },
  { label: 'Wiki', icon: BookOpen, path: '/wiki' },
  { label: 'Ingest', icon: Upload, path: '/ingest' },
];

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export default function Sidebar({ collapsed, onToggleCollapse }: SidebarProps) {
  const location = useLocation();
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  const isActivePath = useCallback(
    (path: string) => {
      if (path === '/') {
        return location.pathname === '/';
      }
      return location.pathname.startsWith(path);
    },
    [location.pathname]
  );

  return (
    <aside
      className="h-screen flex flex-col fixed left-0 top-0 z-50 transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)] border-r border-amber-800/20"
      style={{
        width: collapsed ? '64px' : '240px',
        background: 'linear-gradient(180deg, #14100D 0%, #0C0907 100%)',
      }}
    >
      <div className="h-16 flex items-center px-4 border-b border-amber-800/20 overflow-hidden">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-amber-900/60 flex items-center justify-center flex-shrink-0">
            <BookMarked className="w-5 h-5 text-amber-300" />
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.2 }}
                className="font-display text-[22px] font-semibold text-amber-300 whitespace-nowrap overflow-hidden"
              >
                Munger
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </div>

      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto overflow-x-hidden scrollbar-none">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = isActivePath(item.path);
          const isHovered = hoveredItem === item.label;

          return (
            <NavLink
              key={item.path}
              to={item.path}
              onMouseEnter={() => setHoveredItem(item.label)}
              onMouseLeave={() => setHoveredItem(null)}
              className={({ isActive: navActive }) =>
                `relative flex items-center h-10 rounded-md transition-all duration-200 ease-[cubic-bezier(0.4,0,0.2,1)] group ${
                  navActive
                    ? 'bg-bg-active text-amber-300'
                    : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                } ${collapsed ? 'justify-center px-0' : 'px-3'}`
              }
            >
              {isActive && (
                <motion.div
                  layoutId="sidebar-active"
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 bg-amber-400 rounded-r-full"
                  transition={{ duration: 0.2, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
                />
              )}

              <Icon
                className={`w-5 h-5 flex-shrink-0 transition-colors duration-200 ${
                  isActive
                    ? 'text-amber-300'
                    : isHovered
                    ? 'text-text-primary'
                    : 'text-text-secondary'
                }`}
              />

              <AnimatePresence>
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -8 }}
                    transition={{ duration: 0.15 }}
                    className="ml-2 text-sm font-medium whitespace-nowrap overflow-hidden"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>

              {collapsed && (isHovered || isActive) && (
                <div className="absolute left-full ml-2 px-2.5 py-1.5 bg-bg-elevated rounded-md shadow-lg border border-amber-800/20 whitespace-nowrap z-50 pointer-events-none">
                  <span className="text-xs font-medium text-text-primary">{item.label}</span>
                  <div className="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2 w-2 h-2 bg-bg-elevated border-l border-b border-amber-800/20 rotate-45" />
                </div>
              )}
            </NavLink>
          );
        })}
      </nav>

      <div className="py-3 px-2 border-t border-amber-800/20">
        <button
          onClick={onToggleCollapse}
          className={`w-full flex items-center h-10 rounded-md text-text-secondary hover:bg-bg-hover hover:text-text-primary transition-all duration-200 ${
            collapsed ? 'justify-center px-0' : 'px-3'
          }`}
        >
          {collapsed ? (
            <PanelLeftOpen className="w-5 h-5 flex-shrink-0" />
          ) : (
            <>
              <PanelLeftClose className="w-5 h-5 flex-shrink-0" />
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="ml-2 text-sm font-medium whitespace-nowrap"
              >
                Collapse
              </motion.span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
