import { useState, useEffect, useRef, useCallback } from "react";

export default function usePolling(fetchFn, interval = 3000) {
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);
    const savedFetchFn = useRef(fetchFn);
    const timeoutRef = useRef(null);
    const mountedRef = useRef(true);

    useEffect(() => {
        savedFetchFn.current = fetchFn;
    }, [fetchFn]);

    const refresh = useCallback(async () => {
        try {
            const result = await savedFetchFn.current();
            if (mountedRef.current) {
                setData(result);
                setError(null);
            }
        } catch (err) {
            if (mountedRef.current) {
                setError(err);
            }
        } finally {
            if (mountedRef.current) {
                setLoading(false);
            }
        }
    }, []);

    useEffect(() => {
        mountedRef.current = true;
        setLoading(true);
        setData(null);
        setError(null);

        async function poll() {
            await refresh();
            if (mountedRef.current) {
                timeoutRef.current = setTimeout(poll, interval);
            }
        }

        poll();

        return () => {
            mountedRef.current = false;
            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current);
            }
        };
    }, [interval, refresh]);

    return { data, error, loading, refresh };
}