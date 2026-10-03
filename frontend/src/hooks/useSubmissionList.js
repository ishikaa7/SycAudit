import { useCallback, useEffect, useState } from "react";
import { getSubmissions } from "../api/submissions.js";
import { errorMessage } from "../api/client.js";
import { normalizeList } from "../utils/format.js";

/**
 * Loads the submission list.
 * NOTE: SubmissionListItem exposes only submission_id, original_prompt, status,
 * created_at and updated_at. It carries no report or scores, so list views must
 * not render score values.
 */
export default function useSubmissionList() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getSubmissions();
      setItems(normalizeList(res.data));
    } catch (err) {
      setError(errorMessage(err));
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { items, loading, error, refresh };
}