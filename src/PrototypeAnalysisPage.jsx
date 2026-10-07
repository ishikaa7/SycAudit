// ... existing imports ... 
import { extractFacetEvidence, getActualExplanation } from './prototype_analysis';
import HighlightedResponse from './components/HighlightedResponse';

// ... existing code ... 
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