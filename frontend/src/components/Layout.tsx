import { useState, useEffect, useRef, useCallback } from "react";
import {
  Outlet,
  NavLink,
  useLocation,
  Link,
  useNavigate,
} from "react-router-dom";
import {
  LayoutDashboard,
  PlusCircle,
  FileText,
  Building2,
  Settings,
  Activity,
  ArrowUpDown,
  Bell,
  Layers,
  Menu,
  X,
  ChevronRight,
  Home,
  Search,
  AlertTriangle,
  CheckCircle,
  Info,
  Moon,
  Sun,
} from "lucide-react";
import clsx from "clsx";
import GlobalSearch from "./GlobalSearch";
import { api } from "@/lib/api";
import type { Notification } from "@/lib/types";

const ROUTE_LABELS: Record<string, string> = {
  "": "Dashboard",
  companies: "Companii",
  company: "Companie",
  reports: "Rapoarte",
  report: "Raport",
  compare: "Comparator",
  monitoring: "Monitorizare",
  settings: "Setari",
  "new-analysis": "Analiza Noua",
  batch: "Batch",
  analysis: "Progres Analiza",
};

function Breadcrumbs() {
  const location = useLocation();
  const segments = location.pathname.split("/").filter(Boolean);

  if (segments.length === 0) return null;

  const crumbs: { label: string; to: string }[] = [];
  let currentPath = "";

  for (const segment of segments) {
    currentPath += `/${segment}`;
    const label = ROUTE_LABELS[segment];
    if (label) {
      crumbs.push({ label, to: currentPath });
    }
    // Skip dynamic ID segments (UUIDs, numbers) — they don't get their own breadcrumb
  }

  if (crumbs.length === 0) return null;

  return (
    <nav className="flex items-center gap-1.5 text-xs text-gray-500 mb-4">
      <Link
        to="/"
        className="flex items-center gap-1 hover:text-gray-300 transition-colors"
      >
        <Home className="w-3 h-3" />
        <span>Dashboard</span>
      </Link>
      {crumbs.map((crumb, i) => (
        <span key={crumb.to} className="flex items-center gap-1.5">
          <ChevronRight className="w-3 h-3 text-gray-600" />
          {i === crumbs.length - 1 ? (
            <span className="text-gray-300">{crumb.label}</span>
          ) : (
            <Link
              to={crumb.to}
              className="hover:text-gray-300 transition-colors"
            >
              {crumb.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  );
}

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/new-analysis", label: "Analiza Noua", icon: PlusCircle },
  { to: "/reports", label: "Rapoarte", icon: FileText },
  { to: "/companies", label: "Companii", icon: Building2 },
  { to: "/compare", label: "Comparator", icon: ArrowUpDown },
  { to: "/monitoring", label: "Monitorizare", icon: Bell },
  { to: "/batch", label: "Batch Analysis", icon: Layers },
  { to: "/settings", label: "Configurare", icon: Settings },
];

const SEVERITY_ICON: Record<string, typeof AlertTriangle> = {
  error: AlertTriangle,
  warning: AlertTriangle,
  success: CheckCircle,
  info: Info,
};

const SEVERITY_COLOR: Record<string, string> = {
  error: "text-red-400",
  warning: "text-yellow-400",
  success: "text-green-400",
  info: "text-blue-400",
};

function NotificationBell() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const panelRef = useRef<HTMLDivElement>(null);

  const fetchNotifications = useCallback(() => {
    api
      .listNotifications({ unread_only: true, limit: 10 })
      .then((res) => {
        setNotifications(res.notifications);
        setUnreadCount(res.unread_count);
      })
      .catch(() => {
        /* fail silently */
      });
  }, []);

  // Fetch on mount + poll every 60s
  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 60_000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const handleClick = (notif: Notification) => {
    api.markNotificationRead(notif.id).catch(() => {});
    setNotifications((prev) => prev.filter((n) => n.id !== notif.id));
    setUnreadCount((prev) => Math.max(0, prev - 1));
    setOpen(false);
    if (notif.link) navigate(notif.link);
  };

  const handleMarkAllRead = () => {
    api.markAllNotificationsRead().catch(() => {});
    setNotifications([]);
    setUnreadCount(0);
  };

  const formatTime = (dateStr: string) => {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "acum";
    if (diffMin < 60) return `${diffMin}m`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `${diffH}h`;
    return d.toLocaleDateString("ro-RO", { day: "2-digit", month: "short" });
  };

  return (
    <div ref={panelRef} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-lg text-gray-400 hover:text-white hover:bg-dark-hover transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
        aria-label={`Notificari${unreadCount > 0 ? ` (${unreadCount} necitite)` : ""}`}
        title="Notificari"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4.5 h-4.5 min-w-[18px] flex items-center justify-center text-[10px] font-bold text-white bg-red-500 rounded-full leading-none px-1">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-dark-card border border-dark-border rounded-xl shadow-2xl z-50 overflow-hidden">
          <div className="px-4 py-3 border-b border-dark-border flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Notificari</h3>
            {unreadCount > 0 && (
              <span className="text-[10px] text-gray-500 bg-dark-surface px-1.5 py-0.5 rounded">
                {unreadCount} necitite
              </span>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="py-8 text-center">
                <Bell className="w-6 h-6 text-gray-600 mx-auto mb-2" />
                <p className="text-xs text-gray-500">Nicio notificare noua</p>
              </div>
            ) : (
              notifications.map((notif) => {
                const Icon = SEVERITY_ICON[notif.severity] || Info;
                const color = SEVERITY_COLOR[notif.severity] || "text-gray-400";
                return (
                  <button
                    key={notif.id}
                    onClick={() => handleClick(notif)}
                    className="w-full text-left px-4 py-3 hover:bg-dark-hover transition-colors border-b border-dark-border/50 last:border-0"
                  >
                    <div className="flex items-start gap-3">
                      <Icon
                        className={clsx("w-4 h-4 mt-0.5 shrink-0", color)}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-200 font-medium truncate">
                          {notif.title}
                        </p>
                        <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">
                          {notif.message}
                        </p>
                      </div>
                      <span className="text-[10px] text-gray-600 shrink-0 mt-0.5">
                        {formatTime(notif.created_at)}
                      </span>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {notifications.length > 0 && (
            <div className="px-4 py-2.5 border-t border-dark-border">
              <button
                onClick={handleMarkAllRead}
                className="w-full text-center text-xs text-accent-secondary hover:text-accent-light transition-colors"
              >
                Marcare toate ca citite
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ThemeToggle() {
  const [isDark, setIsDark] = useState(() => {
    return localStorage.getItem("ris_theme") !== "light";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
    localStorage.setItem("ris_theme", isDark ? "dark" : "light");
  }, [isDark]);

  return (
    <button
      onClick={() => setIsDark((d) => !d)}
      className="w-full flex items-center gap-2 px-2 py-1.5 text-xs text-gray-500 bg-dark-card rounded-lg border border-dark-border hover:border-gray-600 hover:text-gray-400 transition-colors"
      title={isDark ? "Comuta la tema Light" : "Comuta la tema Dark"}
      aria-label={isDark ? "Comuta la tema Light" : "Comuta la tema Dark"}
    >
      {isDark ? (
        <>
          <Sun className="w-3.5 h-3.5" />
          <span className="flex-1 text-left">Tema Light</span>
        </>
      ) : (
        <>
          <Moon className="w-3.5 h-3.5" />
          <span className="flex-1 text-left">Tema Dark</span>
        </>
      )}
    </button>
  );
}

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const sidebar = (
    <>
      {/* Logo */}
      <div className="p-5 border-b border-dark-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-accent-primary flex items-center justify-center">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-white text-sm">RIS</h1>
            <p className="text-[10px] text-gray-500">Intelligence System</p>
          </div>
          {/* Close button on mobile */}
          <button
            onClick={() => setSidebarOpen(false)}
            className="ml-auto md:hidden text-gray-400 hover:text-white p-1 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
            aria-label="Inchide meniul"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            onClick={() => setSidebarOpen(false)}
            className={({ isActive }) =>
              clsx("sidebar-link", isActive && "active")
            }
          >
            <item.icon className="w-5 h-5" aria-hidden="true" />
            <span className="text-sm">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-dark-border space-y-2">
        <button
          onClick={() =>
            window.dispatchEvent(
              new KeyboardEvent("keydown", { key: "k", ctrlKey: true }),
            )
          }
          className="w-full flex items-center gap-2 px-2 py-1.5 text-xs text-gray-500 bg-dark-card rounded-lg border border-dark-border hover:border-gray-600 hover:text-gray-400 transition-colors"
        >
          <Search className="w-3.5 h-3.5" />
          <span className="flex-1 text-left">Cauta...</span>
          <kbd className="text-[10px] bg-dark-surface px-1 py-0.5 rounded border border-dark-border/50">
            Ctrl+K
          </kbd>
        </button>
        <ThemeToggle />
        <p className="text-[10px] text-gray-600">
          Roland Intelligence System v3.0
        </p>
      </div>
    </>
  );

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Global Search (Ctrl+K) */}
      <GlobalSearch />

      {/* Desktop Sidebar */}
      <aside className="hidden md:flex w-64 bg-dark-surface border-r border-dark-border flex-col shrink-0">
        {sidebar}
      </aside>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-50 w-64 bg-dark-surface border-r border-dark-border flex flex-col",
          "transform transition-transform duration-200 ease-in-out md:hidden",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {sidebar}
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {/* Mobile Header */}
        <div className="sticky top-0 z-30 bg-dark-surface border-b border-dark-border px-4 py-3 md:hidden flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-gray-400 hover:text-white p-1 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
            aria-label="Deschide meniul de navigare"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2 flex-1">
            <Activity className="w-4 h-4 text-accent-primary" />
            <span className="text-sm font-semibold text-white">RIS</span>
          </div>
          {/* B4: Search button pe mobile — deschide GlobalSearch (Ctrl+K) */}
          <button
            className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-dark-hover transition-colors"
            onClick={() =>
              window.dispatchEvent(
                new KeyboardEvent("keydown", { key: "k", ctrlKey: true }),
              )
            }
            aria-label="Cauta (Ctrl+K)"
            title="Cauta"
          >
            <Search className="w-5 h-5" />
          </button>
          <NotificationBell />
        </div>
        {/* Desktop Top Bar */}
        <div className="hidden md:flex sticky top-0 z-30 bg-dark-surface/80 backdrop-blur-sm border-b border-dark-border px-6 py-2 items-center justify-end">
          <NotificationBell />
        </div>
        <div className="p-6 max-w-7xl mx-auto">
          <Breadcrumbs />
          <Outlet />
        </div>
      </main>
    </div>
  );
}
