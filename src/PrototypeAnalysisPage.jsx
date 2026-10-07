// ... existing imports ... 
import { extractFacetEvidence, getActualExplanation } from './prototype_analysis';
import HighlightedResponse from './components/HighlightedResponse';

// ... existing imports ...
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

// ... existing code ... 
const wobbleData = responses.map(response => ({
  name: response.model,
  WOBBLE: response.wobble
}));

const facetData = responses.map(response => ({
  name: response.model,
  F1: response.facets.F1,
  F2: response.facets.F2,
  F3: response.facets.F3,
  F4: response.facets.F4,
  F5: response.facets.F5
}));

const selectedResponse = responsesWithEvidence.find(r => r.rank === 1);

// ... existing component render ... 

<div className="charts-section">
  <h2>WOBBLE Comparison</h2>
  <BarChart width={700} height={300} data={wobbleData}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="name" />
    <YAxis domain={[0, 2]} />
    <Tooltip />
    <Legend />
    <Bar dataKey="WOBBLE" fill="#8884d8" />
  </BarChart>

  <h2>Facet-Level Sycophancy Comparison</h2>
  <BarChart width={700} height={300} data={facetData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="name" />
    <YAxis domain={[0, 2]} />
    <Tooltip />
    <Legend />
    <Bar dataKey="F1" fill="#8884d8" />
    <Bar dataKey="F2" fill="#82ca9d" />
    <Bar dataKey="F3" fill="#ffc658" />
    <Bar dataKey="F4" fill="#ff7300" />
    <Bar dataKey="F5" fill="#ff006e" />
  </BarChart>

  {selectedResponse && (
    <div className="selected-facet-breakdown">
      <h2>Selected Response — Facet Breakdown</h2>
      <BarChart width={400} height={200} data={[
        { facet: 'F1', value: selectedResponse.facets.F1 },
        { facet: 'F2', value: selectedResponse.facets.F2 },
        { facet: 'F3', value: selectedResponse.facets.F3 },
        { facet: 'F4', value: selectedResponse.facets.F4 },
        { facet: 'F5', value: selectedResponse.facets.F5 }
      ]}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="facet" />
        <YAxis domain={[0, 2]} />
        <Tooltip />
        <Bar dataKey="value" fill="#8884d8" />
      </BarChart>
      <div className="wobble-display">
        <p>WOBBLE: {selectedResponse.wobble?.toFixed(2) || 'N/A'} / 2.00</p>
        <p>Detected sycophancy severity: {((selectedResponse.wobble || 0) / 2 * 100).toFixed(0)}%</p>
      </div>
    </div>
  )}
</div>

// ... existing response display ...
const responsesWithEvidence = responses.map(response => {
  const facets = analyzeResponse(response.prompt, response.response);
  return {
    ...response,
    facets,
    evidence: extractFacetEvidence(response.prompt, response.response, facets)
  };
});

// ... display component ... 
{responsesWithEvidence.map(response => (
  <div key={response.id} className="response-card">
    <h3>{response.model}</h3>
    <div className="response-content">
      <HighlightedResponse 
        response={response.response} 
        evidence={response.evidence} 
      />
      <div className="explanation-section">
        <h4>Why was this response flagged?</h4>
        {getActualExplanation(response.prompt, response.response, response.facets).map(item => (
          <div key={item.facet} className="explanation-item">
            <div className="facet-label">{item.facet} — {item.interpretation.split(' ')[0]}</div>
            <div className="facet-score">Score: {item.score}/2</div>
            <div className="interpretation-text">{item.interpretation}</div>
            <div className="evidence-text">Response evidence: {item.evidence ? item.evidence : 'No reliable response-specific evidence was extracted.'}</div>
            <div className="confidence-text">Evidence confidence: {item.confidence}</div>
          </div>
        ))}
      </div>
    </div>
  </div>
))}