import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

/** A counter bumped after every reviewer decision so the queue, counters and audit refetch. */
const Ctx = createContext<{ version: number; bump: () => void }>({ version: 0, bump: () => undefined });

export function LiveProvider({ children }: { children: ReactNode }) {
  const [version, setVersion] = useState(0);
  const bump = useCallback(() => setVersion((v) => v + 1), []);
  const value = useMemo(() => ({ version, bump }), [version, bump]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useLive() {
  return useContext(Ctx);
}
