import { useState, useEffect, useCallback } from 'react';

export function useSSE() {
  const [statusLogs, setStatusLogs] = useState([]);
  const [progress, setProgress] = useState(0);
  const [activeAgent, setActiveAgent] = useState('');
  const [isCompleted, setIsCompleted] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  const [error, setError] = useState(null);

  const startAudit = useCallback((auditId, config = {}) => {
    // Reset state
    setStatusLogs([]);
    setProgress(0);
    setActiveAgent('');
    setIsCompleted(false);
    setIsFailed(false);
    setError(null);

    const {
      asOnDate = '',
      currencySymbol = 'Rs.',
      duplicateWindowDays = 7,
      customHolidays = []
    } = config;

    // Build URL parameters
    const params = new URLSearchParams();
    if (asOnDate) params.append('as_on_date', asOnDate);
    params.append('currency_symbol', currencySymbol);
    params.append('duplicate_window_days', duplicateWindowDays.toString());
    if (customHolidays.length > 0) {
      params.append('custom_holidays', JSON.stringify(customHolidays));
    }

    const backendUrl = import.meta.env.VITE_API_URL || (window.location.port === '5173' ? 'http://localhost:8000' : '');
    const sseUrl = `${backendUrl}/audit/${auditId}/stream?${params.toString()}`;
    const eventSource = new EventSource(sseUrl);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Add log
        setStatusLogs((prev) => {
          // Replace update for same agent if exists, otherwise append
          const existingIdx = prev.findIndex((log) => log.agent === data.agent);
          if (existingIdx > -1) {
            const next = [...prev];
            next[existingIdx] = data;
            return next;
          }
          return [...prev, data];
        });

        // Set active agent and progress
        if (data.agent) {
          setActiveAgent(data.agent);
        }
        if (data.progress_pct) {
          setProgress(data.progress_pct);
        }

        // Handle terminal states
        if (data.agent === 'Orchestrator' && data.status === 'completed') {
          setIsCompleted(true);
          eventSource.close();
        } else if (data.status === 'failed') {
          setIsFailed(true);
          setError(data.error || 'Audit step failed');
          eventSource.close();
        }
      } catch (err) {
        console.error('Failed to parse SSE event:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('EventSource encountered an error:', err);
      setIsFailed(true);
      setError('Connection to audit server lost.');
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);

  return {
    statusLogs,
    progress,
    activeAgent,
    isCompleted,
    isFailed,
    error,
    startAudit
  };
}
