import { useEffect, useState, createContext, useContext, useCallback } from "react";
import { X, CheckCircle, AlertTriangle, Info } from "lucide-react";
import clsx from "clsx";

type ToastType = "success" | "error" | "warning" | "info";

interface ToastItem {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue>({
  toast: () => {},
});

export function useToast() {
  return useContext(ToastContext);
}

let nextId = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const toast = useCallback((message: string, type: ToastType = "info") => {
    const id = nextId++;
    setToasts((prev) => [...prev, { id, message, type }]);
  }, []);

  const remove = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
        {toasts.map((t) => (
          <ToastItem key={t.id} item={t} onRemove={remove} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

const ICONS = {
  success: CheckCircle,
  error: AlertTriangle,
  warning: AlertTriangle,
  info: Info,
};

const COLORS = {
  success: "border-green-500/50 bg-green-500/10 text-green-300",
  error: "border-red-500/50 bg-red-500/10 text-red-300",
  warning: "border-yellow-500/50 bg-yellow-500/10 text-yellow-300",
  info: "border-blue-500/50 bg-blue-500/10 text-blue-300",
};

const ICON_COLORS = {
  success: "text-green-400",
  error: "text-red-400",
  warning: "text-yellow-400",
  info: "text-blue-400",
};

function ToastItem({
  item,
  onRemove,
}: {
  item: ToastItem;
  onRemove: (id: number) => void;
}) {
  useEffect(() => {
    const timer = setTimeout(() => onRemove(item.id), 4000);
    return () => clearTimeout(timer);
  }, [item.id, onRemove]);

  const Icon = ICONS[item.type];

  return (
    <div
      className={clsx(
        "flex items-start gap-2 px-4 py-3 rounded-lg border backdrop-blur-sm",
        "animate-in slide-in-from-right shadow-lg",
        COLORS[item.type]
      )}
    >
      <Icon className={clsx("w-4 h-4 mt-0.5 shrink-0", ICON_COLORS[item.type])} />
      <p className="text-sm flex-1">{item.message}</p>
      <button
        onClick={() => onRemove(item.id)}
        className="text-gray-500 hover:text-gray-300 shrink-0"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
