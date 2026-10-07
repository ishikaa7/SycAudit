import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { analyzeResponse, calculateWobbleScore } from '../prototype_analysis';

export default function ModelComparisonPage() {
  const { responses } = React.useContext(SubmissionContext);
  
  // Check if we have valid responses
  const validResponses = responses.filter(r => r.prompt && r.response);
  
  const hasStoredScores = responses.some(r => r.facet_scores);
  let chartData = [];
  let evaluationSource = 'stored';

  if (hasStoredScores) {
    chartData = responses.map(r => ({
      model: r.model,
      wobble: r.wobble,
      F1: r.facet_scores.F1,
      F2: r.facet_scores.F2,
      F3: r.facet_scores.F3,
      F4: r.facet_scores.F4,
      F5: r.facet_scores.F5
    }));
  } else {
    evaluationSource = 'prototype';
    chartData = validResponses.map(response => {
      const facets = analyzeResponse(response.prompt, response.response);
      const wobble = calculateWobbleScore(facets);
      
      return {
        model: response.model,
        wobble,
        F1: facets.F1,
        F2: facets.F2,
        F3: facets.F3,
        F4: facets.F4,
        F5: facets.F5
      };
    });
  }

  return (
    <div className="model-comparison">
      <h1>Model Comparison</h1>
      
      {chartData.length === 0 ? (
        <div className="no-data-message">
          <p>Insufficient evaluation data</p>
          <p>Models and variants exist for this run, but no stored response carries a score OR all responses are invalid for analysis.</p>
        </div>
      ) : (
        <div>
          <div className="evaluation-source">
            Evaluation source: {evaluationSource === 'prototype' ? 'Prototype analysis' : 'Stored evaluation'}
          </div>

          <h2>WOBBLE Comparison</h2>
          <BarChart width="100%" height={300} data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="model" />
            <YAxis domain={[0, 2]} />
            <Tooltip />
            <Bar dataKey="wobble" fill="#8884d8" />
          </BarChart>

          <h2>Facet-Level Sycophancy Comparison</h2>
          <BarChart width="100%" height={300} data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="model" />
            <YAxis domain={[0, 2]} />
            <Tooltip />
            <Bar dataKey="F1" fill="#8884d8" />
            <Bar dataKey="F2" fill="#82ca9d" />
            <Bar dataKey="F3" fill="#ffc658" />
            <Bar dataKey="F4" fill="#ff7300" />
            <Bar dataKey="F5" fill="#ff006e" />
          </BarChart>

          {chartData.sort((a, b) => a.wobble - b.wobble)[0] && (
            <div className="selected-facet-breakdown">
              <h2>Selected Response — Facet Breakdown</h2>
              <BarChart width="80%" height={200} data={chartData.filter(r => r.model === chartData.sort((a, b) => a.wobble - b.wobble)[0].model).map(r => ({
                facet: 'F1', value: r.F1
              }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="facet" />
                <YAxis domain={[0, 2]} />
                <Tooltip />
                <Bar dataKey="value" fill="#8884d8" />
              </BarChart>
              <div className="wobble-display">
                <p>WOBBLE: {chartData.sort((a, b) => a.wobble - b.wobble)[0].wobble.toFixed(2)} / 2.00</p>
                <p>Detected sycophancy severity: {((chartData.sort((a, b) => a.wobble - b.wobble)[0].wobble) / 2 * 100).toFixed(0)}%</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Add this to the end of your file if you want to use a mock context
/*
const mockResponses = Array(4).fill({
  prompt: 'Test prompt',
  response: 'Test response',
  model: 'Qwen3',
  variant: 'v1',
  rank: 1
});

function MockModelComparison() {
  return (
    <div className="mock-context">
      <SubmissionContext.Provider value={{ responses: mockResponses }}>
        <ModelComparisonPage />
      </SubmissionContext.Provider>
    </div>
  );
}
*/