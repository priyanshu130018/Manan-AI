import { useCallback, useEffect, useState } from "react";
import { DEFAULT_SETTINGS, readSettings, writeSettings } from "@/services/axios";
import type { AppSettings } from "@/types";

export function useSettings() {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);

  useEffect(() => {
    setSettings(readSettings());
    const sync = () => setSettings(readSettings());
    window.addEventListener("manan:settings", sync);
    return () => window.removeEventListener("manan:settings", sync);
  }, []);

  const save = useCallback((next: AppSettings) => {
    writeSettings(next);
    setSettings(next);
  }, []);

  return { settings, save };
}
