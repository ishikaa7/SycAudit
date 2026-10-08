import { useMemo, useState } from "react";
import { useSubmissionContext } from "../components/layout/SubmissionLayout.jsx";

import SubmissionHeader from "../components/results/SubmissionHeader.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import Notice from "../components/ui/Notice.jsx";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
} from "recharts";

import {
  BACKEND_SCORE_MAX,
  DISPLAY_SCORE_MAX,
  FACET_DEFS,
  buildMatrix,
  collectModels,
  collectVariants,
  formatBackScore,
} from "../utils/scoring.js";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const MODEL_COLORS = [
  "#4F46E5",
  "#0F766E",
  "#C2410C",
  "#7C3AED",
  "#0369A1",
  "#BE123C",
  "#047857",
  "#B45309",
];

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

function modelColor(index) {
  return MODEL_COLORS[index % MODEL_COLORS.length];
}

function ChartFrame({
  title,
  caption,
  children,
  note,
  footnote,
}) {
  return (
    <section className="card mb-6 p-5">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="section-title">{title}</h2>

        {caption && (
          <p className="meta-text">
            {caption}
          </p>
        )}
      </div>

      {children}

      {note && (
        <p className="meta-text mt-3">
          {note}
        </p>
      )}

      {footnote && (
        <p className="meta-text mt-1.5">
          {footnote}
        </p>
      )}
    </section>
  );
}

function Score({
  value,
  digits = 1,
  suffix = "",
}) {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(value)
  ) {
    return (
      <span className="text-slate-300">
        N/A
      </span>
    );
  }

  return (
    <span className="tabular-nums text-slate-800">
      {value.toFixed(digits)}
      {suffix}
    </span>
  );
}

function ScoreTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-lg">
      {label && (
        <p className="mb-1 text-[11px] font-semibold text-slate-500">
          {label}
        </p>
      )}

      {payload.map((item) => {
        const value = item.value;

        return (
          <p
            key={item.dataKey}
            className="text-[12px] text-slate-700"
          >
            <span className="font-medium">
              {item.name || item.dataKey}
            </span>
            {": "}
            {typeof value === "number"
              ? value.toFixed(1)
              : "N/A"}
          </p>
        );
      })}
    </div>
  );
}

function ComparisonSkeleton() {
  return (
    <div
      aria-busy="true"
      aria-label="Loading comparison"
    >
      <div className="card mb-6 animate-pulse p-5">
        <div className="h-3 w-28 rounded bg-surface-200" />
        <div className="mt-3 h-4 w-full rounded bg-surface-200" />
      </div>

      {[300, 320, 280].map((height, index) => (
        <div
          key={index}
          className="card mb-6 animate-pulse p-5"
        >
          <div className="h-3 w-40 rounded bg-surface-200" />

          <div
            className="mt-4 rounded bg-surface-200"
            style={{ height }}
          />
        </div>
      ))}
    </div>
  );
}

function normalizeFacetValue(value) {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(Number(value))
  ) {
    return null;
  }

  return Number(value);
}

/* -------------------------------------------------------------------------- */
/* Main page                                                                  */
/* -------------------------------------------------------------------------- */

export default function ComparisonPage() {
  const {
    submission,
    refresh,
  } = useSubmissionContext();

  const rows = useMemo(
    () => buildMatrix(submission),
    [submission]
  );

  const variants = useMemo(
    () => collectVariants(submission),
    [submission]
  );

  const modelsFromHelper = useMemo(
    () => collectModels(submission),
    [submission]
  );

  /*
   * Build a stable list of actual models stored in this submission.
   * Nothing is hardcoded.
   */
  const modelNames = useMemo(() => {
    const names = [];

    modelsFromHelper.forEach((model) => {
      const name =
        typeof model === "string"
          ? model
          : model?.name;

      if (name && !names.includes(name)) {
        names.push(name);
      }
    });

    rows.forEach((row) => {
      if (
        row.modelName &&
        !names.includes(row.modelName)
      ) {
        names.push(row.modelName);
      }
    });

    return names;
  }, [modelsFromHelper, rows]);

  /*
   * User-controlled model selection.
   *
   * IMPORTANT:
   * Selecting models does NOT create another analysis.
   * It only filters the already-loaded submission.
   */
  const [selectedModels, setSelectedModels] =
    useState(() => new Set());

  function toggleModel(modelName) {
    setSelectedModels((current) => {
      const next = new Set(current);

      if (next.has(modelName)) {
        next.delete(modelName);
      } else {
        next.add(modelName);
      }

      return next;
    });
  }

  const selectedModelList = useMemo(
    () =>
      modelNames.filter((name) =>
        selectedModels.has(name)
      ),
    [modelNames, selectedModels]
  );

  const hasEnoughModels =
    selectedModelList.length >= 2;

  /*
   * Keep the selection valid if the backend data changes after refresh.
   */
  const validSelectedModels = useMemo(() => {
    const available = new Set(modelNames);

    return selectedModelList.filter((name) =>
      available.has(name)
    );
  }, [modelNames, selectedModelList]);

  /*
   * Only rows belonging to selected models.
   */
  const selectedRows = useMemo(
    () =>
      rows.filter((row) =>
        validSelectedModels.includes(row.modelName)
      ),
    [rows, validSelectedModels]
  );

  /*
   * Only scored responses are used for numerical comparison.
   */
  const selectedScoredRows = useMemo(
    () =>
      selectedRows.filter(
        (row) =>
          row.scored &&
          row.finalScore !== null &&
          row.finalScore !== undefined
      ),
    [selectedRows]
  );

  /*
   * Per-model aggregate.
   *
   * WOBBLE is already represented by finalScore in the backend scale:
   * 0–2.
   */
  const modelAggregates = useMemo(() => {
    return validSelectedModels.map(
      (modelName) => {
        const modelRows =
          selectedScoredRows.filter(
            (row) =>
              row.modelName === modelName
          );

        const scores = modelRows
          .map((row) => Number(row.finalScore))
          .filter(Number.isFinite);

        const overallBack =
          scores.length > 0
            ? scores.reduce(
                (sum, value) => sum + value,
                0
              ) / scores.length
            : null;

        const overallDisplay =
          overallBack !== null
            ? (overallBack / BACKEND_SCORE_MAX) *
              DISPLAY_SCORE_MAX
            : null;

        const facets = {};

        FACET_DEFS.forEach((facet) => {
          const values = modelRows
            .map((row) =>
              normalizeFacetValue(
                row.score?.facet_scores?.[
                  facet.key
                ]
              )
            )
            .filter(
              (value) => value !== null
            );

          facets[facet.key] =
            values.length > 0
              ? values.reduce(
                  (sum, value) => sum + value,
                  0
                ) / values.length
              : null;
        });

        return {
          name: modelName,
          overallBack,
          overallDisplay,
          scoredCount: scores.length,
          facets,
        };
      }
    );
  }, [
    validSelectedModels,
    selectedScoredRows,
  ]);

  /*
   * MODEL × VARIANT data.
   */
  const variantChart = useMemo(() => {
    return variants.map((variant) => {
      const entry = {
        variant:
          variant.label ||
          variant.key ||
          "Variant",
      };

      validSelectedModels.forEach(
        (modelName) => {
          const row = selectedScoredRows.find(
            (candidate) =>
              candidate.modelName ===
                modelName &&
              candidate.variantKey ===
                variant.key
          );

          if (
            row &&
            typeof row.finalScore === "number"
          ) {
            entry[modelName] =
              (row.finalScore /
                BACKEND_SCORE_MAX) *
              DISPLAY_SCORE_MAX;
          } else {
            entry[modelName] = null;
          }
        }
      );

      return entry;
    });
  }, [
    variants,
    validSelectedModels,
    selectedScoredRows,
  ]);

  /*
   * FACET × MODEL chart data.
   */
  const facetChart = useMemo(() => {
    return FACET_DEFS.map((facet) => {
      const entry = {
        facet: facet.id,
      };

      modelAggregates.forEach((model) => {
        entry[model.name] =
          model.facets[facet.key];
      });

      return entry;
    }).filter((entry) =>
      validSelectedModels.some(
        (modelName) =>
          entry[modelName] !== null &&
          entry[modelName] !== undefined
      )
    );
  }, [
    modelAggregates,
    validSelectedModels,
  ]);

  /*
   * Heatmap-style table.
   */
  const heatmapRows = useMemo(
    () =>
      modelAggregates.map((model) => ({
        ...model,
        cells: FACET_DEFS.map(
          (facet) => ({
            ...facet,
            value:
              model.facets[facet.key],
          })
        ),
      })),
    [modelAggregates]
  );

  /*
   * Overall graph.
   */
  const overallChart = useMemo(
    () =>
      modelAggregates
        .filter(
          (model) =>
            model.overallDisplay !== null
        )
        .slice()
        .sort(
          (a, b) =>
            (a.overallBack ?? 0) -
            (b.overallBack ?? 0)
        ),
    [modelAggregates]
  );

  /*
   * Model colors remain stable within the page.
   */
  const colorMap = useMemo(() => {
    const map = {};

    modelNames.forEach(
      (modelName, index) => {
        map[modelName] =
          modelColor(index);
      }
    );

    return map;
  }, [modelNames]);

  function colorOf(modelName) {
    return (
      colorMap[modelName] ||
      "#4F46E5"
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Loading / empty states                                                  */
  /* ---------------------------------------------------------------------- */

  if (!submission) {
    return <ComparisonSkeleton />;
  }

  if (
    modelNames.length === 0 ||
    variants.length === 0
  ) {
    return (
      <div className="animate-fade-up">
        <PageHeader
          eyebrow="Model comparison"
          title="Model Comparison"
          subtitle="Compare models within an existing SycAudit evaluation."
        />

        <SubmissionHeader
          submission={submission}
        />

        <div className="mt-6">
          <EmptyState
            icon="chart"
            title="No comparison data available"
            subtitle="This submission contains no stored models or prompt variants to compare."
            action={
              <button
                type="button"
                onClick={refresh}
                className="btn-secondary !py-2"
              >
                Refresh this analysis
              </button>
            }
          />
        </div>
      </div>
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Main UI                                                                 */
  /* ---------------------------------------------------------------------- */

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Model comparison"
        title="Model Comparison"
        subtitle="Select the models you want to compare within this existing evaluation."
      />

      <SubmissionHeader
        submission={submission}
      />

      {/* ------------------------------------------------------------------ */}
      {/* USER PROMPT                                                        */}
      {/* ------------------------------------------------------------------ */}

      <section className="card mt-6 mb-6 p-5">
        <p className="eyebrow">
          User prompt
        </p>

        <p className="mt-2 whitespace-pre-wrap text-[15px] leading-relaxed text-slate-800">
          {submission.prompt ||
            submission.user_prompt ||
            "No prompt stored for this analysis."}
        </p>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* MODEL SELECTOR                                                     */}
      {/* ------------------------------------------------------------------ */}

      <section className="card mb-6 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="section-title">
              Select models to compare
            </h2>

            <p className="section-sub">
              Choose at least two models. The graphs and analysis below
              will update using only your selected models.
            </p>
          </div>

          <div className="rounded-lg bg-slate-100 px-3 py-1.5 text-[11.5px] font-semibold text-slate-600">
            {selectedModelList.length} selected
          </div>
        </div>

        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {modelNames.map((modelName) => {
            const checked =
              selectedModels.has(modelName);

            const modelData =
              modelAggregates.find(
                (model) =>
                  model.name === modelName
              );

            return (
              <label
                key={modelName}
                className={`cursor-pointer rounded-xl border p-3 transition ${
                  checked
                    ? "border-indigo-300 bg-indigo-50"
                    : "border-slate-200 bg-white hover:bg-slate-50"
                }`}
              >
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() =>
                      toggleModel(modelName)
                    }
                    className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />

                  <div className="min-w-0">
                    <p className="truncate text-[13px] font-semibold text-slate-800">
                      {modelName}
                    </p>

                    <p className="mt-1 text-[11px] text-slate-500">
                      {modelData?.scoredCount ?? 0}{" "}
                      scored response
                      {(modelData?.scoredCount ?? 0) === 1
                        ? ""
                        : "s"}
                    </p>
                  </div>
                </div>
              </label>
            );
          })}
        </div>

        {!hasEnoughModels && (
          <div className="mt-4">
            <Notice tone="warning">
              {selectedModelList.length === 0
                ? "Select at least two models to start the comparison."
                : "Select one more model to display the comparison graphs."}
            </Notice>
          </div>
        )}
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* DON'T SHOW ANALYSIS UNTIL 2 MODELS ARE SELECTED                    */}
      {/* ------------------------------------------------------------------ */}

      {!hasEnoughModels ? (
        <section className="card mb-6 p-8 text-center">
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-slate-100 text-slate-500">
            <span className="text-xl">
              ⇄
            </span>
          </div>

          <h2 className="mt-4 text-[16px] font-semibold text-slate-800">
            Choose models to compare
          </h2>

          <p className="mx-auto mt-2 max-w-md text-[12.5px] leading-relaxed text-slate-500">
            Select two or more models above. Once selected, SycAudit will
            show the real stored WOBBLE scores, facet scores, variant
            comparison and detailed model analysis for those models only.
          </p>
        </section>
      ) : (
        <>
          {/* ---------------------------------------------------------------- */}
          {/* DATA NOTICE                                                      */}
          {/* ---------------------------------------------------------------- */}

          <div className="mb-6">
            <Notice>
              Showing comparison data only for{" "}
              <strong>
                {validSelectedModels.join(", ")}
              </strong>
              . Missing values are shown as N/A and are never treated as
              zero.
            </Notice>
          </div>

          {/* ---------------------------------------------------------------- */}
          {/* OVERALL MODEL COMPARISON                                         */}
          {/* ---------------------------------------------------------------- */}

          <ChartFrame
            title="Overall Model Comparison"
            caption="Average WOBBLE across evaluated variants"
            footnote="Lower WOBBLE means less detected sycophancy. Display scale: 0–100."
          >
            {overallChart.length === 0 ? (
              <div className="grid place-items-center rounded-xl border border-dashed border-slate-200 px-4 py-10 text-center">
                <p className="text-[13px] font-semibold text-slate-600">
                  No stored WOBBLE scores
                </p>

                <p className="mt-1 text-[12px] text-slate-400">
                  None of the selected models has a stored response score.
                </p>
              </div>
            ) : (
              <div
                className="w-full"
                style={{
                  height: Math.max(
                    200,
                    overallChart.length * 60
                  ),
                }}
              >
                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >
                  <BarChart
                    data={overallChart}
                    layout="vertical"
                    margin={{
                      top: 4,
                      right: 55,
                      bottom: 4,
                      left: 10,
                    }}
                  >
                    <CartesianGrid
                      strokeDasharray="2 4"
                      horizontal={false}
                    />

                    <XAxis
                      type="number"
                      domain={[
                        0,
                        DISPLAY_SCORE_MAX,
                      ]}
                      tick={{
                        fontSize: 10,
                      }}
                      axisLine={false}
                      tickLine={false}
                    />

                    <YAxis
                      type="category"
                      dataKey="name"
                      width={140}
                      tick={{
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                      axisLine={false}
                      tickLine={false}
                    />

                    <Tooltip
                      content={
                        <ScoreTooltip />
                      }
                    />

                    <Bar
                      dataKey="overallDisplay"
                      name="WOBBLE"
                      radius={[
                        0,
                        4,
                        4,
                        0,
                      ]}
                      isAnimationActive={false}
                    >
                      {overallChart.map(
                        (model) => (
                          <Cell
                            key={model.name}
                            fill={colorOf(
                              model.name
                            )}
                          />
                        )
                      )}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {modelAggregates.map(
                (model) => (
                  <div
                    key={model.name}
                    className="rounded-xl border border-slate-200 bg-white p-3.5"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{
                          backgroundColor:
                            colorOf(
                              model.name
                            ),
                        }}
                      />

                      <p className="truncate text-[12.5px] font-semibold text-slate-800">
                        {model.name}
                      </p>
                    </div>

                    <p className="mt-2 text-[20px] font-bold tabular-nums text-slate-900">
                      {model.overallDisplay !==
                      null
                        ? model.overallDisplay.toFixed(
                            1
                          )
                        : "N/A"}

                      <span className="ml-1 text-[11px] font-medium text-slate-400">
                        / 100
                      </span>
                    </p>

                    <p className="mt-1 text-[11px] text-slate-500">
                      {model.scoredCount} scored
                      response
                      {model.scoredCount === 1
                        ? ""
                        : "s"}
                    </p>
                  </div>
                )
              )}
            </div>
          </ChartFrame>

          {/* ---------------------------------------------------------------- */}
          {/* MODEL × VARIANT                                                  */}
          {/* ---------------------------------------------------------------- */}

          <ChartFrame
            title="Model × Variant"
            caption="WOBBLE for every generated variant"
            footnote="Missing bars mean no stored score exists for that model/variant pair."
          >
            {variantChart.length === 0 ? (
              <div className="py-10 text-center text-[13px] text-slate-400">
                No variant-level scores are available.
              </div>
            ) : (
              <div className="h-[340px] w-full">
                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >
                  <BarChart
                    data={variantChart}
                    margin={{
                      top: 8,
                      right: 8,
                      bottom: 8,
                      left: -12,
                    }}
                  >
                    <CartesianGrid
                      strokeDasharray="2 4"
                      vertical={false}
                    />

                    <XAxis
                      dataKey="variant"
                      tick={{
                        fontSize: 10,
                        fontWeight: 600,
                      }}
                      axisLine={false}
                      tickLine={false}
                    />

                    <YAxis
                      domain={[
                        0,
                        DISPLAY_SCORE_MAX,
                      ]}
                      tick={{
                        fontSize: 10,
                      }}
                      axisLine={false}
                      tickLine={false}
                      width={40}
                    />

                    <Tooltip
                      content={
                        <ScoreTooltip />
                      }
                    />

                    <Legend
                      wrapperStyle={{
                        fontSize: 11,
                        paddingTop: 8,
                      }}
                      iconType="circle"
                      iconSize={7}
                    />

                    {validSelectedModels.map(
                      (modelName) => (
                        <Bar
                          key={modelName}
                          dataKey={modelName}
                          name={modelName}
                          fill={colorOf(
                            modelName
                          )}
                          radius={[
                            4,
                            4,
                            0,
                            0,
                          ]}
                          isAnimationActive={false}
                        />
                      )
                    )}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </ChartFrame>

          {/* ---------------------------------------------------------------- */}
          {/* FACET PERFORMANCE                                                 */}
          {/* ---------------------------------------------------------------- */}

          <ChartFrame
            title="Facet Performance"
            caption={`Average F1–F5 score per model · 0–${BACKEND_SCORE_MAX}`}
            footnote="These are the real stored facet scores aggregated across the selected models' evaluated responses."
          >
            {facetChart.length === 0 ? (
              <div className="grid place-items-center rounded-xl border border-dashed border-slate-200 px-4 py-10 text-center">
                <p className="text-[13px] font-semibold text-slate-600">
                  No facet scores stored
                </p>

                <p className="mt-1 text-[12px] text-slate-400">
                  The selected models do not have stored F1–F5 scores.
                </p>
              </div>
            ) : (
              <div className="h-[330px] w-full">
                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >
                  <BarChart
                    data={facetChart}
                    margin={{
                      top: 8,
                      right: 10,
                      bottom: 8,
                      left: -12,
                    }}
                  >
                    <CartesianGrid
                      strokeDasharray="2 4"
                      vertical={false}
                    />

                    <XAxis
                      dataKey="facet"
                      tick={{
                        fontSize: 11,
                        fontWeight: 700,
                      }}
                      axisLine={false}
                      tickLine={false}
                    />

                    <YAxis
                      domain={[
                        0,
                        BACKEND_SCORE_MAX,
                      ]}
                      tick={{
                        fontSize: 10,
                      }}
                      axisLine={false}
                      tickLine={false}
                      width={35}
                    />

                    <Tooltip
                      content={
                        <ScoreTooltip />
                      }
                    />

                    <Legend
                      wrapperStyle={{
                        fontSize: 11,
                        paddingTop: 8,
                      }}
                      iconType="circle"
                      iconSize={7}
                    />

                    {validSelectedModels.map(
                      (modelName) => (
                        <Bar
                          key={modelName}
                          dataKey={modelName}
                          name={modelName}
                          fill={colorOf(
                            modelName
                          )}
                          radius={[
                            4,
                            4,
                            0,
                            0,
                          ]}
                          isAnimationActive={false}
                        />
                      )
                    )}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </ChartFrame>

          {/* ---------------------------------------------------------------- */}
          {/* FACET × MODEL                                                    */}
          {/* ---------------------------------------------------------------- */}

          <ChartFrame
            title="Facet × Model"
            caption={`Aggregated facet scores · 0–${BACKEND_SCORE_MAX}`}
            footnote="Each cell represents the average stored facet score for that model."
          >
            <div className="scroll-x">
              <table className="w-full min-w-[720px] border-collapse">
                <thead className="border-b border-slate-100 bg-surface-50">
                  <tr>
                    <th className="table-head">
                      Model
                    </th>

                    <th className="table-head text-right">
                      WOBBLE
                    </th>

                    {FACET_DEFS.map(
                      (facet) => (
                        <th
                          key={facet.key}
                          className="table-head text-right"
                        >
                          {facet.id}
                        </th>
                      )
                    )}
                  </tr>
                </thead>

                <tbody>
                  {heatmapRows.map(
                    (model) => (
                      <tr
                        key={model.name}
                        className="border-b border-slate-100 last:border-0"
                      >
                        <th className="table-cell">
                          <span className="flex items-center gap-2">
                            <span
                              className="h-2.5 w-2.5 rounded-full"
                              style={{
                                backgroundColor:
                                  colorOf(
                                    model.name
                                  ),
                              }}
                            />

                            <span className="font-medium text-slate-800">
                              {model.name}
                            </span>
                          </span>
                        </th>

                        <td className="table-num">
                          {model.overallDisplay !==
                          null ? (
                            <span className="font-semibold tabular-nums text-slate-900">
                              {model.overallDisplay.toFixed(
                                1
                              )}
                            </span>
                          ) : (
                            <span className="text-slate-300">
                              N/A
                            </span>
                          )}
                        </td>

                        {model.cells.map(
                          (cell) => (
                            <td
                              key={cell.key}
                              className="table-num"
                            >
                              {cell.value ===
                                null ||
                              cell.value ===
                                undefined ? (
                                <span className="text-slate-300">
                                  N/A
                                </span>
                              ) : (
                                <span className="font-medium tabular-nums text-slate-700">
                                  {formatBackScore(
                                    cell.value,
                                    2
                                  )}
                                </span>
                              )}
                            </td>
                          )
                        )}
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          </ChartFrame>

          {/* ---------------------------------------------------------------- */}
          {/* DETAILED MODEL COMPARISON                                       */}
          {/* ---------------------------------------------------------------- */}

          <section className="mb-6">
            <div className="mb-3">
              <h2 className="section-title">
                Detailed Model Comparison
              </h2>

              <p className="section-sub">
                Only the models you selected above are included.
              </p>
            </div>

            <div className="card overflow-hidden">
              <div className="scroll-x">
                <table className="w-full min-w-[760px] border-collapse">
                  <thead className="border-b border-slate-100 bg-surface-50">
                    <tr>
                      <th className="table-head">
                        Model
                      </th>

                      <th className="table-head text-right">
                        WOBBLE
                      </th>

                      <th className="table-head text-right">
                        Severity
                      </th>

                      <th className="table-head text-right">
                        Scored
                      </th>

                      {FACET_DEFS.map(
                        (facet) => (
                          <th
                            key={facet.key}
                            className="table-head text-right"
                          >
                            {facet.id}
                          </th>
                        )
                      )}
                    </tr>
                  </thead>

                  <tbody>
                    {modelAggregates.map(
                      (model) => (
                        <tr
                          key={model.name}
                          className="border-b border-slate-100 last:border-0 hover:bg-surface-50"
                        >
                          <th className="table-cell">
                            <span className="flex items-center gap-2">
                              <span
                                className="h-2.5 w-2.5 rounded-full"
                                style={{
                                  backgroundColor:
                                    colorOf(
                                      model.name
                                    ),
                                }}
                              />

                              <span className="font-medium text-slate-800">
                                {model.name}
                              </span>
                            </span>
                          </th>

                          <td className="table-num">
                            {model.overallBack !==
                            null ? (
                              <>
                                <span className="block font-semibold tabular-nums text-slate-900">
                                  {model.overallDisplay.toFixed(
                                    1
                                  )}
                                </span>

                                <span className="block text-[10px] tabular-nums text-slate-400">
                                  raw{" "}
                                  {formatBackScore(
                                    model.overallBack
                                  )}{" "}
                                  /{" "}
                                  {BACKEND_SCORE_MAX}
                                </span>
                              </>
                            ) : (
                              <span className="text-slate-300">
                                N/A
                              </span>
                            )}
                          </td>

                          <td className="table-num">
                            {model.overallBack !==
                            null ? (
                              <span className="font-medium tabular-nums text-slate-700">
                                {(
                                  (model.overallBack /
                                    BACKEND_SCORE_MAX) *
                                  DISPLAY_SCORE_MAX
                                ).toFixed(1)}
                                %
                              </span>
                            ) : (
                              <span className="text-slate-300">
                                N/A
                              </span>
                            )}
                          </td>

                          <td className="table-num">
                            {model.scoredCount}
                          </td>

                          {FACET_DEFS.map(
                            (facet) => {
                              const value =
                                model.facets[
                                  facet.key
                                ];

                              return (
                                <td
                                  key={facet.key}
                                  className="table-num"
                                >
                                  {value ===
                                    null ||
                                  value ===
                                    undefined ? (
                                    <span className="text-slate-300">
                                      N/A
                                    </span>
                                  ) : (
                                    <span className="font-medium tabular-nums text-slate-700">
                                      {formatBackScore(
                                        value,
                                        2
                                      )}
                                    </span>
                                  )}
                                </td>
                              );
                            }
                          )}
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-slate-100 bg-surface-50 px-4 py-2.5">
                <span className="text-[10.5px] font-semibold uppercase tracking-wide text-slate-400">
                  Facets
                </span>

                {FACET_DEFS.map(
                  (facet) => (
                    <span
                      key={facet.key}
                      className="text-[11px] text-slate-500"
                    >
                      <span className="font-bold text-slate-700">
                        {facet.id}
                      </span>{" "}
                      = {facet.label}
                    </span>
                  )
                )}
              </div>
            </div>
          </section>

          {/* ---------------------------------------------------------------- */}
          {/* VARIANT DETAILS                                                  */}
          {/* ---------------------------------------------------------------- */}

          <section className="mb-6">
            <details className="card group overflow-hidden">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-4">
                <span>
                  <span className="section-title">
                    View variant-level details
                  </span>

                  <span className="section-sub mt-0.5 block">
                    Real stored WOBBLE and F1–F5 values behind the graphs.
                  </span>
                </span>

                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-4 w-4 shrink-0 text-slate-400 transition-transform duration-150 group-open:rotate-180"
                  aria-hidden="true"
                >
                  <path d="m6 9 6 6 6-6" />
                </svg>
              </summary>

              <div className="border-t border-slate-100 px-5 py-4">
                <div className="space-y-5">
                  {variants.map(
                    (variant) => {
                      const variantRows =
                        selectedScoredRows.filter(
                          (row) =>
                            row.variantKey ===
                            variant.key
                        );

                      if (
                        variantRows.length ===
                        0
                      ) {
                        return null;
                      }

                      return (
                        <div
                          key={variant.key}
                        >
                          <div className="mb-2 flex items-baseline gap-2">
                            <h3 className="text-[13px] font-bold text-slate-800">
                              {variant.label ||
                                variant.key}
                            </h3>

                            {variant.sublabel && (
                              <span className="text-[11px] text-slate-400">
                                {variant.sublabel}
                              </span>
                            )}
                          </div>

                          <div className="scroll-x">
                            <table className="w-full min-w-[720px] border-collapse">
                              <thead>
                                <tr>
                                  <th className="table-head">
                                    Model
                                  </th>

                                  <th className="table-head text-right">
                                    WOBBLE
                                  </th>

                                  {FACET_DEFS.map(
                                    (facet) => (
                                      <th
                                        key={
                                          facet.key
                                        }
                                        className="table-head text-right"
                                      >
                                        {facet.id}
                                      </th>
                                    )
                                  )}
                                </tr>
                              </thead>

                              <tbody>
                                {validSelectedModels.map(
                                  (
                                    modelName
                                  ) => {
                                    const row =
                                      variantRows.find(
                                        (
                                          candidate
                                        ) =>
                                          candidate.modelName ===
                                          modelName
                                      );

                                    if (!row) {
                                      return (
                                        <tr
                                          key={
                                            modelName
                                          }
                                          className="border-t border-slate-100"
                                        >
                                          <td className="table-cell text-slate-700">
                                            {modelName}
                                          </td>

                                          <td
                                            className="table-num"
                                            colSpan={
                                              1 +
                                              FACET_DEFS.length
                                            }
                                          >
                                            <span className="text-slate-300">
                                              N/A
                                            </span>
                                          </td>
                                        </tr>
                                      );
                                    }

                                    const facets =
                                      row.score
                                        ?.facet_scores ||
                                      {};

                                    return (
                                      <tr
                                        key={
                                          modelName
                                        }
                                        className="border-t border-slate-100"
                                      >
                                        <td className="table-cell">
                                          <span className="flex items-center gap-2">
                                            <span
                                              className="h-2 w-2 rounded-full"
                                              style={{
                                                backgroundColor:
                                                  colorOf(
                                                    modelName
                                                  ),
                                              }}
                                            />

                                            <span className="font-medium text-slate-700">
                                              {
                                                modelName
                                              }
                                            </span>
                                          </span>
                                        </td>

                                        <td className="table-num">
                                          <Score
                                            value={
                                              typeof row.finalScore ===
                                              "number"
                                                ? row.finalScore
                                                : null
                                            }
                                            digits={
                                              2
                                            }
                                            suffix={` / ${BACKEND_SCORE_MAX}`}
                                          />
                                        </td>

                                        {FACET_DEFS.map(
                                          (
                                            facet
                                          ) => {
                                            const value =
                                              normalizeFacetValue(
                                                facets[
                                                  facet
                                                    .key
                                                ]
                                              );

                                            return (
                                              <td
                                                key={
                                                  facet.key
                                                }
                                                className="table-num"
                                              >
                                                <Score
                                                  value={
                                                    value
                                                  }
                                                  digits={
                                                    2
                                                  }
                                                />
                                              </td>
                                            );
                                          }
                                        )}
                                      </tr>
                                    );
                                  }
                                )}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      );
                    }
                  )}
                </div>

                <p className="meta-text mt-4">
                  WOBBLE uses the backend 0–
                  {BACKEND_SCORE_MAX} scale. The UI display scale is 0–
                  {DISPLAY_SCORE_MAX}. Facets remain on the backend 0–
                  {BACKEND_SCORE_MAX} scale.
                </p>
              </div>
            </details>
          </section>
        </>
      )}
    </div>
  );
}