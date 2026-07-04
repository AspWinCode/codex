import { useCallback, useEffect, useRef, useState } from 'react';
import { submissionsApi } from '../../../api';
import { SubmissionSocketClient } from '../../../services/realtime/submissionSocket';
import type { Submission } from '../../../types';

interface UseSubmissionWatcherParams {
  refreshHistory: (taskId: number) => void;
  refreshHints: (taskId: number) => void;
}

export function useSubmissionWatcher({ refreshHistory, refreshHints }: UseSubmissionWatcherParams) {
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const socketRef = useRef<SubmissionSocketClient | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const stopSocket = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.stop();
      socketRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      stopPolling();
      stopSocket();
    };
  }, [stopPolling, stopSocket]);

  const fallbackPoll = useCallback((submissionId: number, taskId: number) => {
    stopPolling();

    pollRef.current = setInterval(async () => {
      try {
        const res = await submissionsApi.get(submissionId);
        setSubmission(res.data);

        if (res.data.status === 'finished') {
          stopPolling();
          setSubmitting(false);
          refreshHistory(taskId);
          refreshHints(taskId);
        }
      } catch {
        // keep polling on transient failures
      }
    }, 1500);
  }, [refreshHistory, refreshHints, stopPolling]);

  const waitForResult = useCallback((submissionId: number, taskId: number) => {
    const token = localStorage.getItem('token');
    if (!token) {
      fallbackPoll(submissionId, taskId);
      return;
    }

    let finished = false;
    let fallbackStarted = false;

    const startFallback = () => {
      if (finished || fallbackStarted) return;
      fallbackStarted = true;
      fallbackPoll(submissionId, taskId);
    };

    const socket = new SubmissionSocketClient({
      token,
      submissionId,
      onUpdate: (msg) => {
        setSubmission((prev) => prev ? {
          ...prev,
          status: msg.status,
          verdict: msg.verdict as Submission["verdict"],
          runtime: msg.runtime,
          memory: msg.memory,
          error_output: msg.error_output,
        } : prev);

        if (msg.status === 'finished') {
          finished = true;
          setSubmitting(false);
          stopPolling();

          submissionsApi.get(submissionId).then(({ data: full }) => setSubmission(full));
          refreshHistory(taskId);
          refreshHints(taskId);
          stopSocket();
        }
      },
      onTerminalDisconnect: () => {
        startFallback();
      },
    });

    socketRef.current = socket;
    socket.start();
  }, [fallbackPoll, refreshHistory, refreshHints, stopPolling, stopSocket]);

  const submitSolution = useCallback(async (taskId: number, code: string) => {
    stopPolling();
    stopSocket();
    setSubmitting(true);

    try {
      const { data } = await submissionsApi.submit(taskId, code);
      setSubmission(data);
      waitForResult(data.id, taskId);
    } catch {
      setSubmitting(false);
    }
  }, [stopPolling, stopSocket, waitForResult]);

  return {
    submission,
    submitting,
    submitSolution,
  };
}

