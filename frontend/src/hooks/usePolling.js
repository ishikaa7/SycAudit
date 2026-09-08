import { useEffect, useRef } from "react";

export default function usePolling(fn, { delay = 3000, enabled = true, deps = [] } = {}) {
  const fnRef = useRef(fn);

  useEffect(() => {
    fnRef.current = fn;
  });

  useEffect(() => {
    if (!enabled) return undefined;
    const id = window.setInterval(() => {
      fnRef.current();
    }, delay);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, delay, ...deps]);
}