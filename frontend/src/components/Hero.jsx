import { motion } from 'framer-motion';
import { ArrowRight, FlaskConical } from 'lucide-react';

const ANNOTATIONS = [
  { dot: '#4E8860', label: 'BRCA1 c.68_69delAG', sub: 'Pathogenic — PVS1 + PM2 triggered', color: '#FEE2E2', textColor: '#B91C1C' },
  { dot: '#2D5B8E', label: 'gnomAD AF: 0.000000', sub: 'Absent from 125,748 individuals',  color: '#DBEAFE', textColor: '#1E40AF' },
  { dot: '#C8963C', label: 'ClinVar: 2★ Review',  sub: 'Multiple independent submitters',   color: '#FEF3C7', textColor: '#92400E' },
];

const STATS = [
  { value: '5',    label: 'ACMG Criteria' },
  { value: '4',    label: 'Target Genes' },
  { value: 'Live', label: 'API Data' },
];

export default function Hero() {
  return (
    <section style={{ background: 'var(--sand-100)' }}>
      <div className="hero">
        {/* Left: Copy */}
        <motion.div
          initial={{ opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.4, 0, 0.2, 1] }}
        >
          <div className="hero-badge">
            <span style={{ width: 8, height: 8, background: 'var(--sage-500)', borderRadius: '50%', display: 'inline-block' }} />
            Portfolio · September 2026
          </div>

          <h1 className="hero-title">
            Genetic Variant
            <br />
            <em>Interpretation,</em>
            <br />
            Grounded in Data.
          </h1>

          <p className="hero-subtitle">
            An agentic RAG pipeline that turns raw HGVS variant codes into
            clinically grounded ACMG classifications — using live ClinVar and
            gnomAD data, not LLM guesswork.
          </p>

          <div className="hero-actions">
            <a href="#analyzer" className="btn btn-primary" id="hero-cta-analyze">
              <FlaskConical size={17} />
              Analyze a Variant
            </a>
            <a href="#how-it-works" className="btn btn-secondary" id="hero-cta-learn">
              How It Works
              <ArrowRight size={16} />
            </a>
          </div>

          {/* Tech stack pills */}
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '2.5rem' }}>
            {['LangGraph', 'Groq LLaMA 3.1 70B', 'FastAPI', 'ClinVar API', 'gnomAD GraphQL', 'React'].map(t => (
              <span key={t} className="badge badge-neutral">{t}</span>
            ))}
          </div>
        </motion.div>

        {/* Right: Visual */}
        <motion.div
          className="hero-image-panel"
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.3, ease: [0.4, 0, 0.2, 1] }}
        >
          <div className="hero-main-card">
            <div className="hero-dna-bg" />
            <div className="hero-floating-badges">
              {/* DNA helix visual */}
              <div style={{
                textAlign: 'center',
                padding: '2rem 0 1rem',
                position: 'relative',
                zIndex: 2,
              }}>
                <div style={{
                  fontSize: '5rem',
                  lineHeight: 1,
                  filter: 'drop-shadow(0 4px 16px rgba(78,136,96,0.3))',
                }}>
                  🧬
                </div>
                <p style={{
                  fontFamily: 'Playfair Display, serif',
                  fontSize: '1.1rem',
                  color: 'var(--charcoal-800)',
                  marginTop: '0.75rem',
                  fontStyle: 'italic',
                }}>
                  AI-Powered Variant Analysis
                </p>
              </div>

              {/* Floating annotation cards */}
              {ANNOTATIONS.map((ann, i) => (
                <motion.div
                  key={i}
                  className="hero-annotation"
                  style={{
                    background: ann.color,
                    border: `1px solid ${ann.dot}40`,
                    animationDelay: `${i * 1.3}s`,
                  }}
                  initial={{ opacity: 0, x: -16 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.6 + i * 0.2, duration: 0.5 }}
                >
                  <span
                    className="annotation-dot"
                    style={{ background: ann.dot }}
                  />
                  <div>
                    <div style={{
                      fontFamily: 'Inter, monospace',
                      fontWeight: 700,
                      fontSize: '0.85rem',
                      color: ann.textColor,
                    }}>
                      {ann.label}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--charcoal-600)' }}>
                      {ann.sub}
                    </div>
                  </div>
                </motion.div>
              ))}

              {/* Stats row */}
              <div className="hero-stats" style={{ position: 'relative', zIndex: 2 }}>
                {STATS.map((s, i) => (
                  <motion.div
                    key={i}
                    className="hero-stat"
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.9 + i * 0.1, duration: 0.4 }}
                  >
                    <div className="hero-stat-value">{s.value}</div>
                    <div className="hero-stat-label">{s.label}</div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
