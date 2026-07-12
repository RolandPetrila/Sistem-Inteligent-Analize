import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export type VersionInfo = Awaited<ReturnType<typeof api.getVersion>>;

// Store partajat (o singura sursa de adevar) — evita ca doua componente sa afiseze versiuni diferite.
let _cache: VersionInfo | null = null;
const _subs = new Set<(v: VersionInfo) => void>();
let _timer: ReturnType<typeof setInterval> | null = null;

function _refresh() {
  api
    .getVersion()
    .then((v) => {
      _cache = v;
      // Decuplat pt module non-React (ex. logger) — evita import circular logger->hook->api->logger
      (window as unknown as { __RIS_APP_VERSION?: string }).__RIS_APP_VERSION =
        v.version;
      _subs.forEach((fn) => fn(v));
    })
    .catch(() => {
      /* fail silently — pastram ultima valoare */
    });
}

/** Versiunea aplicatiei (build git + update_available), partajata + reimprospatata la 2 min. */
export function useAppVersion(): VersionInfo | null {
  const [info, setInfo] = useState<VersionInfo | null>(_cache);

  useEffect(() => {
    _subs.add(setInfo);
    if (_cache) setInfo(_cache);
    else _refresh();
    if (_timer === null) _timer = setInterval(_refresh, 120_000);
    return () => {
      _subs.delete(setInfo);
      if (_subs.size === 0 && _timer !== null) {
        clearInterval(_timer);
        _timer = null;
      }
    };
  }, []);

  return info;
}
