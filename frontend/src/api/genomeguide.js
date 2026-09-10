/**
 * GenomeGuide API client
 * Handles SSE streaming from the FastAPI backend
 */

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace(/\/+$/, '')}/api`
  : '/api';

/**
 * Stream variant analysis via SSE
 * @param {string} variant - Raw HGVS variant input
 * @param {object} callbacks - { onProgress, onResult, onError }
 * @returns {function} cleanup function
 */
export function analyzeVariant(variant, { onProgress, onResult, onError }) {
  let aborted = false;

  const run = async () => {
    try {
      const response = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ variant }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Server error' }));
        onError(err.detail || 'Analysis failed');
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (!aborted) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep incomplete last line

        let event = null;
        let data  = null;

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            event = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const raw = line.slice(6).trim();
            try { data = JSON.parse(raw); } catch { data = raw; }
          } else if (line === '' && event && data !== null) {
            // Dispatch event
            if (event === 'progress' && onProgress) onProgress(data);
            if (event === 'result'   && onResult)   onResult(data);
            if (event === 'error'    && onError)     onError(data.message || 'Unknown error');
            event = null;
            data  = null;
          }
        }
      }
    } catch (err) {
      if (!aborted) onError(err.message || 'Network error');
    }
  };

  run();

  return () => { aborted = true; };
}

/** Fetch example variants from the backend */
export async function fetchExamples() {
  try {
    const r = await fetch(`${API_BASE}/examples`);
    return await r.json();
  } catch {
    // Fallback examples
    return [
      { label: 'BRCA1 c.68_69delAG',      variant: 'BRCA1 c.68_69delAG',      gene: 'BRCA1', description: 'Frameshift deletion — hereditary breast/ovarian cancer' },
      { label: 'BRCA2 c.5946delT',         variant: 'BRCA2 c.5946delT',         gene: 'BRCA2', description: 'Frameshift deletion — breast/ovarian/pancreatic cancer' },
      { label: 'CFTR c.1521_1523delCTT',   variant: 'CFTR c.1521_1523delCTT',   gene: 'CFTR',  description: 'delF508 — most common cystic fibrosis variant' },
      { label: 'MLH1 c.1A>G',              variant: 'MLH1 c.1A>G',              gene: 'MLH1',  description: 'Start codon loss — Lynch syndrome' },
    ];
  }
}

/** Health check */
export async function healthCheck() {
  const r = await fetch(`${API_BASE}/health`);
  return r.json();
}

/** Fetch live evaluation benchmark results */
export async function fetchEvalResults() {
  try {
    const r = await fetch(`${API_BASE}/eval-results`);
    if (!r.ok) throw new Error('Eval results unavailable');
    return await r.json();
  } catch (err) {
    console.warn('Failed to load eval results from server:', err);
    return null;
  }
}

