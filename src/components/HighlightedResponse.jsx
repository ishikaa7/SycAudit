import React from 'react';

const HIGHLIGHT_CLASS = 'sycophancy-highlight';

export default function HighlightedResponse({ response, evidence }) {
  if (!response || !evidence) return <div>{response}</div>;

  // Normalize response text to string
  const text = response.toString();
  
  // Track positions to avoid overlapping
  const highlightedParts = [];
  let currentIndex = 0;

  // Add all evidence spans in order of occurrence
  Object.keys(evidence)
    .filter(facet => evidence[facet].evidence)
    .forEach(facet => {
      const span = evidence[facet].evidence;
      const startIndex = text.indexOf(span);
      if (startIndex >= 0) {
        highlightedParts.push({
          start: startIndex,
          length: span.length,
          text: span,
          facet
        });
      }
    });

  // Sort by position to handle overlaps correctly
  highlightedParts.sort((a, b) => a.start - b.start);

  // Merge overlapping spans
  const mergedSpans = [];
  let currentSpan = null;
  for (const span of highlightedParts) {
    if (!currentSpan) {
      currentSpan = { ...
        span, 
        facets: [span.facet] 
      };
    } else if (span.start <= currentSpan.start + currentSpan.length) {
      // Overlaps with current span
      currentSpan.end = Math.max(currentSpan.start + currentSpan.length, span.start + span.length);
      currentSpan.facets.push(span.facet);
    } else {
      // New non-overlapping span
      mergedSpans.push(currentSpan);
      currentSpan = { ...
        span, 
        facets: [span.facet] 
      };
    }
  }
  if (currentSpan) {
    mergedSpans.push(currentSpan);
  }

  // Render the response text with highlights
  const parts = [];
  let lastPos = 0;
  mergedSpans.forEach(span => {
    if (span.start > lastPos) {
      parts.push(<span key={`text-${lastPos}`}>{text.substring(lastPos, span.start)}</span>);
    }
    parts.push(
      <span 
        key={`highlight-${span.start}`}
        className={HIGHLIGHT_CLASS}
        title={`Facets: ${span.facets.join(', ')}`}
      >
        {text.substring(span.start, span.start + span.length)}
      </span>
    );
    lastPos = span.start + span.length;
  });
  if (lastPos < text.length) {
    parts.push(<span key={`text-end`}>{text.substring(lastPos)}</span>);
  }

  return <div className="response-text">{parts}</div>;
}