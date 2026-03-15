/**
 * useIndexingProgress — SSE hook for real-time indexing progress.
 *
 * Flow:
 *   1. GET /indexing/tasks → list active jobs
 *   2. For each active job → open SSE /indexing/{job_id}/progress
 *   3. On "completed"/"failed" → close, call onComplete callback
 */
"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { IndexingProgress } from "@/types/models";

const API_BASE = process.env.NEXT_PUBLIC_CMS_API_URL || "http://localhost:8002/api/v1";
export function useIndexingProgress(
  jobId: string | null,
  options?: {
    onComplete?: () => void;
    onFailed?: (error: string) => void;
  },
): IndexingProgress | null {
  const [progress, setProgress] = useState<IndexingProgress | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const url = `${API_BASE}/tenant/knowledge/indexing/${jobId}/progress`;
    const es = new EventSource(url, { withCredentials: true });
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const data: IndexingProgress = JSON.parse(event.data);
        setProgress(data);

        if (data.status === "completed") {
          es.close();
          options?.onComplete?.();
        } else if (data.status === "failed") {
          es.close();
          options?.onFailed?.(data.error || "Indexing failed");
        }
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      es.close();
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [jobId]); // eslint-disable-line react-hooks/exhaustive-deps

  return progress;
}

/**
 * Track indexing progress for multiple documents at once.
 * Maps document_id → IndexingProgress.
 */
export function useDocumentIndexingMap(
  documentIds: string[],
  activeJobs: Array<{ id: string; document_id: string }>,
  onAnyComplete?: () => void,
): Map<string, IndexingProgress> {
  const [progressMap, setProgressMap] = useState<Map<string, IndexingProgress>>(new Map());
  const eventSourcesRef = useRef<Map<string, EventSource>>(new Map());

  const handleComplete = useCallback(() => {
    onAnyComplete?.();
  }, [onAnyComplete]);

  useEffect(() => {
    // Close existing connections for jobs no longer active
    const activeJobIds = new Set(activeJobs.map((j) => j.id));
    for (const [jobId, es] of eventSourcesRef.current) {
      if (!activeJobIds.has(jobId)) {
        es.close();
        eventSourcesRef.current.delete(jobId);
      }
    }

    // Open SSE for new active jobs
    for (const job of activeJobs) {
      if (eventSourcesRef.current.has(job.id)) continue;

      const url = `${API_BASE}/tenant/knowledge/indexing/${job.id}/progress`;
      const es = new EventSource(url, { withCredentials: true });
      eventSourcesRef.current.set(job.id, es);

      es.onmessage = (event) => {
        try {
          const data: IndexingProgress = JSON.parse(event.data);
          setProgressMap((prev) => {
            const next = new Map(prev);
            next.set(data.document_id, data);
            return next;
          });

          if (data.status === "completed" || data.status === "failed") {
            es.close();
            eventSourcesRef.current.delete(job.id);
            if (data.status === "completed") handleComplete();
          }
        } catch {
          // ignore
        }
      };

      es.onerror = () => {
        es.close();
        eventSourcesRef.current.delete(job.id);
      };
    }

    return () => {
      for (const es of eventSourcesRef.current.values()) es.close();
      eventSourcesRef.current.clear();
    };
  }, [activeJobs, handleComplete]);

  return progressMap;
}
