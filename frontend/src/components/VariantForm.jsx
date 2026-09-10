import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FlaskConical, Loader2, Check, X, AlertCircle, ChevronRight } from 'lucide-react';
import { useVariantAnalysis } from '../hooks/useVariantAnalysis';
import { fetchExamples } from '../api/genomeguide';
import ResultsReport from './ResultsReport';

export default function VariantForm() {
  const [input, setInput] = useState('');
  const [examples, setExamples] = useState([]);
  const { status, result, error, analyze, reset, getStepStatus, PIPELINE_STEPS } = useVariantAnalysis();

  useEffect(() => {
    fetchExamples().then(setExamples);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    analyze(input.trim());
  };

  const handleExample = (variant) => {
    setInput(variant);
    if (status !== 'idle') reset();
  };

  return (
    <section id="analyzer" className="section" style={{ background: 'var(--sand-100)' }}>
      <div className="analyzer-section">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          style={{ marginBottom: '0.5rem' }}
        >
          <span className="badge badge-sage" style={{ marginBottom: '1rem' }}>Live Demo</span>
          <h2>Analyze a Genetic Variant</h2>
          <p style={{ marginTop: '0.75rem', maxWidth: 560, fontSize: '1.05rem' }}>
            Enter any HGVS-notation variant from BRCA1, BRCA2, CFTR, or MLH1.
            The pipeline queries live ClinVar and gnomAD data, then applies ACMG rules.
          </p>
        </motion.div>

        <div className="analyzer-grid">
          {/* ---- Input Panel ---- */}
          <motion.div
            className="card input-panel"
            initial={{ opacity: 0, x: -24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <h3 style={{ marginBottom: '1.5rem' }}>Variant Input</h3>

            {/* Examples */}
            <div className="examples-section">
              <span className="examples-label">Try an example:</span>
              <div className="examples-chips">
                {examples.map((ex) => (
                  <button
                    key={ex.variant}
                    id={`example-${ex.gene}`}
                    className="example-chip"
                    onClick={() => handleExample(ex.variant)}
                    title={ex.description}
                  >
                    {ex.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Input form */}
            <form onSubmit={handleSubmit}>
              <label className="input-label" htmlFor="variant-input">HGVS Variant Notation</label>
              <div className="variant-input-wrapper">
                <input
                  id="variant-input"
                  type="text"
                  className="variant-input"
                  placeholder="e.g. BRCA1 c.68_69delAG"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  disabled={status === 'loading'}
                  autoComplete="off"
                  spellCheck={false}
                />
              </div>

              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button
                  id="analyze-btn"
                  type="submit"
                  className="btn btn-sage"
                  disabled={status === 'loading' || !input.trim()}
                  style={{ flex: 1, justifyContent: 'center' }}
                >
                  {status === 'loading' ? (
                    <><Loader2 size={16} className="spin" style={{ animation: 'spin 1s linear infinite' }} /> Analyzing...</>
                  ) : (
                    <><FlaskConical size={16} /> Analyze Variant</>
                  )}
                </button>

                {status !== 'idle' && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => { reset(); setInput(''); }}
                    style={{ padding: '0.75rem 1rem' }}
                  >
                    <X size={16} />
                  </button>
                )}
              </div>
            </form>

            {/* Pipeline progress */}
            <AnimatePresence>
              {status !== 'idle' && (
                <motion.div
                  className="progress-panel"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.3 }}
                  style={{ marginTop: '1.5rem', overflow: 'hidden' }}
                >
                  <div style={{
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    color: 'var(--charcoal-500)',
                    marginBottom: '0.75rem',
                  }}>
                    Pipeline Progress
                  </div>
                  {PIPELINE_STEPS.map((step) => {
                    const stepStatus = getStepStatus(step.id);
                    return (
                      <motion.div
                        key={step.id}
                        className={`progress-step ${stepStatus === 'active' ? 'active' : stepStatus === 'done' ? 'done' : ''}`}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.3 }}
                      >
                        <div className={`progress-step-dot dot-${stepStatus === 'error' ? 'error' : stepStatus}`}>
                          {stepStatus === 'done'   ? <Check size={12} /> :
                           stepStatus === 'active'  ? <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} /> :
                           <ChevronRight size={12} />}
                        </div>
                        <span className="progress-step-text">{step.label}</span>
                        {stepStatus !== 'waiting' && (
                          <span className="progress-step-agent">{step.agent}</span>
                        )}
                      </motion.div>
                    );
                  })}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Error display */}
            <AnimatePresence>
              {status === 'error' && error && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  style={{
                    marginTop: '1rem',
                    padding: '1rem',
                    background: 'var(--rose-50)',
                    border: '1px solid var(--rose-200)',
                    borderRadius: 'var(--radius-sm)',
                    display: 'flex',
                    gap: '0.75rem',
                    alignItems: 'flex-start',
                    fontSize: '0.88rem',
                    color: 'var(--rose-600)',
                  }}
                >
                  <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 2 }} />
                  <span>{error}</span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Disclaimer */}
            <div className="disclaimer" style={{ marginTop: '1.5rem' }}>
              <span className="disclaimer-icon">⚕️</span>
              <span>
                <strong>Educational use only.</strong> This tool applies a simplified 5-criterion
                ACMG subset — not the full clinical 28-criterion evaluation. Always consult a
                certified genetic counsellor before making medical decisions.
              </span>
            </div>
          </motion.div>

          {/* ---- Results Panel ---- */}
          <motion.div
            initial={{ opacity: 0, x: 24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <AnimatePresence mode="wait">
              {status === 'idle' && (
                <motion.div
                  key="idle"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  style={{
                    height: '100%',
                    minHeight: 320,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'var(--white)',
                    borderRadius: 'var(--radius-md)',
                    border: '2px dashed var(--sand-300)',
                    padding: '3rem',
                    textAlign: 'center',
                    gap: '0.75rem',
                  }}
                >
                  <span style={{ fontSize: '3rem' }}>🧬</span>
                  <h4>Results will appear here</h4>
                  <p style={{ fontSize: '0.9rem', maxWidth: 280 }}>
                    Enter a variant above or click one of the example chips to analyze
                  </p>
                </motion.div>
              )}

              {status === 'loading' && (
                <motion.div
                  key="loading"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  style={{
                    minHeight: 320,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '1rem',
                  }}
                >
                  {[80, 140, 100, 60].map((w, i) => (
                    <div
                      key={i}
                      className="skeleton"
                      style={{ height: w, borderRadius: 'var(--radius-md)' }}
                    />
                  ))}
                </motion.div>
              )}

              {status === 'success' && result && (
                <motion.div
                  key="result"
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5 }}
                >
                  <ResultsReport result={result} />
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </section>
  );
}
