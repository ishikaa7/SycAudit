import { useCallback, useEffect, useState } from "react";
import { getSubmission } from "../api/submissions.js";
import { errorMessage } from "../api/client.js";
import usePolling from "./usePolling.js";

export default function useSubmission(submissionId) {
  const [submission, setSubmission] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    if (!submissionId) return;
    try {
      const res = await getSubmission(submissionId);
      const data = res.data && typeof res.data === "object" ? res.data : null;
      if (data) {
        setSubmission(data);
        setError(null);
      } else {
        throw new Error("Request succeeded but returned an empty submission.");
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [submissionId]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setSubmission(null);
    refresh();
  }, [refresh]);

  const isActive = Boolean(
    submission && (submission.status === "pending" || submission.status === "processing")
  );

  usePolling(refresh, { enabled: isActive, delay: 2500, deps: [submissionId] });

  return { submission, loading, error, refresh };
}