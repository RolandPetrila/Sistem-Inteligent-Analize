import { Component } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { logError } from "@/lib/logger";

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error) {
    logError("ErrorBoundary", error, "React render crash");
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-[50vh]">
          <div className="card max-w-md text-center space-y-4">
            <AlertTriangle className="w-12 h-12 text-yellow-400 mx-auto" />
            <h2 className="text-lg font-semibold text-white">
              Ceva nu a mers bine
            </h2>
            <p className="text-sm text-gray-400">
              Pagina a intampinat o eroare. Incearca sa reincarci.
            </p>
            <p className="text-xs text-gray-600 font-mono bg-dark-surface rounded p-2 break-all">
              {this.state.error?.message || "Eroare necunoscuta"}
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              className="btn-primary inline-flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Reincarcare Pagina
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
