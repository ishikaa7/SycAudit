import { useCallback, useEffect, useState } from "react";
import { getModels, setModelActive } from "../api/models.js";
import { errorMessage } from "../api/client.js";
import { formatDateTime } from "../utils/format.js";
import { scoreHex, scoreText } from "../utils/constants.js";
import Toggle from "../components/ui/Toggle.jsx";
import Spinner from "../components/ui/Spinner.jsx";

function getAvgScore(model) {
  const value =
    model?.avg_sycophancy_score ??
    model?.average_syaphancy_score ??
    model?.avg_syaphancy_score ??
    model?.average_sycophancy_score;
  return typeof value === "number" ? value : null;
}

function getLastUsed(model) {
  return model?.last_used_at ?? model?.updated_at ?? null;
}

export default function AdminPage() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [togglingId, setTogglingId] = useState(null);

  const load = useCallback(async () => {
    try {
      const res = await getModels();
      const data = Array.isArray(res.data) ? res.data : res.data?.items ?? [];
      setModels(data);
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleToggle = async (model) => {
    const next = !model.is_active;
    setTogglingId(model.model_id);
    const previous = models;
    setModels((prev) =>
      prev.map((m) =>
        m.model_id === model.model_id ? { ...m, is_active: next } : m
      )
    );
    try {
      const res = await setModelActive(model.model_id, next);
      const updated = res.data;
      if (updated) {
        setModels((prev) =>
          prev.map((m) => (m.model_id === model.model_id ? { ...m, ...updated } : m))
        );
      }
    } catch (err) {
      setModels(previous);
      setError(errorMessage(err));
    } finally {
      setTogglingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl font-semibold tracking-tight text-slate-900">
          Model health
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Toggle responder models on or off. Average sycophancy is computed across
          all scored responses for each model.
        </p>
      </header>

      {error && (
        <div className="rounded-lg bg-red-50 px-3 py-2.5 text-sm text-red-700 ring-1 ring-inset ring-red-200">
          {error}
        </div>
      )}

      {models.length === 0 ? (
        <div className="rounded-xl bg-white px-6 py-12 text-center shadow-sm ring-1 ring-slate-200">
          <p className="text-sm font-medium text-slate-700">No models configured</p>
          <p className="mt-1 text-sm text-slate-400">
            Models appear here once the backend exposes the model registry.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl bg-white shadow-sm ring-1 ring-slate-200">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-400">
                <th className="px-4 py-3 font-semibold">Model</th>
                <th className="px-4 py-3 font-semibold">Provider</th>
                <th className="px-4 py-3 font-semibold">Active</th>
                <th className="px-4 py-3 font-semibold">Avg sycophancy</th>
                <th className="px-4 py-3 font-semibold">Last used</th>
              </tr>
            </thead>
            <tbody>
              {models.map((model) => {
                const avg = getAvgScore(model);
                const pct = avg === null ? 0 : Math.min(100, (avg / 5) * 100);
                return (
                  <tr
                    key={model.model_id}
                    className="border-b border-slate-50 last:border-0"
                  >
                    <td className="px-4 py-3.5 font-medium text-slate-800">
                      {model.model_name ?? model.name ?? "—"}
                      {model.version ? (
                        <span className="ml-1.5 text-xs font-normal text-slate-400">
                          {model.version}
                        </span>
                      ) : null}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium capitalize text-slate-600">
                        {model.provider ?? "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2">
                        <Toggle
                          checked={Boolean(model.is_active)}
                          onChange={() => handleToggle(model)}
                          disabled={togglingId !== null && togglingId !== model.model_id}
                          label={`${model.model_name ?? "model"} active`}
                        />
                        {togglingId === model.model_id && (
                          <Spinner className="h-3.5 w-3.5 text-brand-600" />
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <div className="h-2 w-24 overflow-hidden rounded-full bg-slate-100">
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{
                              width: `${pct}%`,
                              backgroundColor: avg === null ? "#cbd5e1" : scoreHex(avg ?? 0),
                            }}
                          />
                        </div>
                        <span
                          className={`w-10 text-right text-xs font-semibold tabular-nums ${
                            avg === null ? "text-slate-400" : scoreText(avg ?? 0)
                          }`}
                        >
                          {avg === null ? "—" : avg.toFixed(1)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-500">
                      {formatDateTime(getLastUsed(model))}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}