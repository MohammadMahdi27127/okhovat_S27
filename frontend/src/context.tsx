import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from 'react';
import { api, AppState, Attendance, User } from './api';

type Session = { user: User | null; attendance: Attendance | null };
type ContextValue = Session & {
  data: AppState | null; loading: boolean; error: string;
  refresh: () => Promise<void>; restore: () => Promise<void>;
  toast: (message: string) => void; logout: () => Promise<void>;
};
const Context = createContext<ContextValue | null>(null);
export function AppProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session>({ user: null, attendance: null });
  const [data, setData] = useState<AppState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const refresh = useCallback(async () => setData(await api<AppState>('state/')), []);
  const restore = useCallback(async () => {
    const next = await api<Session>('session/');
    setSession(next);
    if (next.user) await refresh();
    else setData(null);
  }, [refresh]);
  useEffect(() => {
    restore().catch(e => setError(e.message)).finally(() => setLoading(false));
  }, [restore]);
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(''), 4000);
    return () => clearTimeout(timer);
  }, [message]);
  const logout = async () => {
    await api('logout/', 'POST');
    setSession({ user: null, attendance: null });
    setData(null);
    location.assign('/login/');
  };
  return <Context.Provider value={{ ...session, data, loading, error, refresh, restore, toast: setMessage, logout }}>
    {children}{message && <div id="toast" className="show" role="status">{message}</div>}
  </Context.Provider>;
}
export function useApp() {
  const value = useContext(Context);
  if (!value) throw new Error('Missing application provider');
  return value;
}
