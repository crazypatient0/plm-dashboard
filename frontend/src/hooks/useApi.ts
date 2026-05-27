import { useCallback, useEffect, useRef, useState } from 'react';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

type UseApiResult<T> = UseApiState<T> & { refetch: () => void };

/**
 * Generic hook for fetching data from an async API function.
 * Automatically fetches on mount and provides a refetch function.
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
): UseApiResult<T> {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: true,
    error: null,
  });
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const fetch = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const data = await fetcherRef.current();
      setState({ data, loading: false, error: null });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'An unknown error occurred';
      setState({ data: null, loading: false, error: message });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { ...state, refetch: fetch };
}

/**
 * Hook that only provides a manual trigger (no auto-fetch).
 */
export function useMutation<T, A extends unknown[]>(
  fetcher: (...args: A) => Promise<T>,
) {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const mutate = useCallback(
    async (...args: A) => {
      setState({ data: null, loading: true, error: null });
      try {
        const data = await fetcher(...args);
        setState({ data, loading: false, error: null });
        return data;
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : 'An unknown error occurred';
        setState({ data: null, loading: false, error: message });
        throw err;
      }
    },
    [fetcher],
  );

  return { ...state, mutate };
}
