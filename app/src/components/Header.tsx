import { useLocation } from 'react-router-dom';
import { Search, Bell } from 'lucide-react';

const routeTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/wiki': 'Wiki Browser',
  '/search': 'Search',
  '/entities': 'Entity Explorer',
  '/ingest': 'Ingestion Manager',
  '/graph': 'Knowledge Graph',
  '/analysis': 'Munger Analysis',
  '/logs': 'System Logs',
  '/settings': 'Settings',
};

function getPageTitle(pathname: string): string {
  if (routeTitles[pathname]) return routeTitles[pathname];
  if (pathname.startsWith('/wiki/')) return 'Wiki Page';
  if (pathname.startsWith('/analysis/')) return 'Munger Analysis';
  return 'Munger';
}

export default function Header() {
  const location = useLocation();
  const pageTitle = getPageTitle(location.pathname);

  return (
    <header className="h-14 flex items-center justify-between px-6 bg-bg-void/80 backdrop-blur-md border-b border-amber-800/15 z-40 sticky top-0">
      {/* Left: Page title / breadcrumbs */}
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-body-sm text-muted font-body">Munger</span>
        <span className="text-body-sm text-muted">/</span>
        <span className="text-body-sm text-text-primary font-medium truncate">
          {pageTitle}
        </span>
      </div>

      {/* Center: Search trigger */}
      <button className="flex items-center gap-2 px-4 py-2 bg-bg-surface rounded-md border border-amber-800/15 text-text-muted hover:bg-bg-elevated hover:text-amber-300 hover:border-amber-700/30 transition-all duration-200 min-w-[280px] max-w-[400px] w-full mx-4">
        <Search className="w-4 h-4 flex-shrink-0" />
        <span className="text-body-sm truncate">Search or jump to...</span>
        <kbd className="ml-auto text-[11px] font-mono text-text-muted bg-bg-hover px-1.5 py-0.5 rounded border border-amber-800/20 flex-shrink-0">
          ⌘K
        </kbd>
      </button>

      {/* Right: Notification bell */}
      <button className="relative p-2 text-text-muted hover:text-amber-300 hover:bg-bg-hover rounded-md transition-all duration-200">
        <Bell className="w-5 h-5" />
        {/* Unread indicator dot */}
        <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-amber-400 rounded-full" />
      </button>
    </header>
  );
}
