import { motion } from 'framer-motion';

const POINTS = [
  {
    icon: '⚖️',
    bg: 'var(--gold-50)',
    title: 'Deterministic Classification',
    desc: 'The ACMG rule engine is pure Python — no LLM involved. Delete the LLM and a working classifier remains. PVS1, PM2, BA1, PS3, BP6 computed entirely from retrieved data.',
  },
  {
    icon: '🗄️',
    bg: 'var(--blue-50)',
    title: 'Real Data, Not Retrieval-Augmented Hallucination',
    desc: 'ClinVar and gnomAD are queried directly via their public APIs on every request. The LLM never invents allele frequencies or submitter counts — they come from NCBI and Broad Institute servers.',
  },
  {
    icon: '🔄',
    bg: 'var(--sage-50)',
    title: 'Self-Checking Critic Loop',
    desc: 'The Critic Agent verifies every sentence in the explanation traces to a retrieved field. Unsupported claims trigger a conditional retry edge in LangGraph — not a post-hoc filter.',
  },
  {
    icon: '🔬',
    bg: 'var(--rose-50)',
    title: 'LLM Has Two Jobs Only',
    desc: 'Parse messy HGVS notation. Write a plain-English summary of an already-made decision. Both are genuinely language-shaped tasks. Every clinical judgment is made before the LLM is invoked.',
  },
];

const STATE_FIELDS = [
  { key: 'raw_variant_input', type: 'string',   note: 'Input' },
  { key: 'parsed',            type: 'object',   note: 'Parser Agent' },
  { key: 'clinvar_result',    type: 'object',   note: 'Lookup Agent' },
  { key: 'gnomad_result',     type: 'object',   note: 'Lookup Agent' },
  { key: 'acmg_evidence',     type: 'object',   note: 'Classifier (no LLM)' },
  { key: 'draft_explanation', type: 'string',   note: 'Explainer Agent' },
  { key: 'critic_verdict',    type: 'object',   note: 'Critic Agent' },
  { key: 'final_output',      type: 'string',   note: 'Output' },
];

export default function Architecture() {
  return (
    <section id="architecture" className="section" style={{ background: 'var(--sand-50)' }}>
      <div className="arch-section">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <span className="badge badge-neutral" style={{ marginBottom: '1rem' }}>Architecture</span>
          <h2>Why This Isn't "Just an LLM Wrapper"</h2>
          <p style={{ marginTop: '0.75rem', maxWidth: 560, fontSize: '1.05rem' }}>
            Apply the test: delete the LLM entirely. What remains is a working ClinVar/gnomAD
            retrieval layer and a deterministic ACMG rule engine that already produces a real classification.
          </p>
        </motion.div>

        <div className="arch-grid">
          {/* Points */}
          <div>
            {POINTS.map((p, i) => (
              <motion.div
                key={i}
                className="arch-point"
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1, duration: 0.5 }}
              >
                <div className="arch-point-icon" style={{ background: p.bg }}>
                  {p.icon}
                </div>
                <div>
                  <div className="arch-point-title">{p.title}</div>
                  <div className="arch-point-desc">{p.desc}</div>
                </div>
              </motion.div>
            ))}
          </div>

          {/* State schema visual */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2, duration: 0.6 }}
          >
            <div style={{
              background: 'var(--charcoal-900)',
              borderRadius: 'var(--radius-md)',
              padding: '1.75rem',
              fontFamily: 'Inter, monospace',
              fontSize: '0.82rem',
            }}>
              <div style={{
                color: 'var(--charcoal-500)',
                fontSize: '0.75rem',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                marginBottom: '1rem',
                fontFamily: 'Inter, sans-serif',
              }}>
                LangGraph State Schema (TypedDict)
              </div>

              <div style={{ color: 'var(--sage-400)', marginBottom: '0.5rem' }}>
                class <span style={{ color: '#7AB0DE' }}>GenomeGuideState</span>(TypedDict):
              </div>

              {STATE_FIELDS.map((f, i) => (
                <motion.div
                  key={f.key}
                  initial={{ opacity: 0, x: 8 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.3 + i * 0.06, duration: 0.3 }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '0.3rem 0',
                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                    gap: '0.5rem',
                  }}
                >
                  <span style={{ color: 'var(--sand-300)', paddingLeft: '1rem', flex: 1 }}>
                    {f.key}
                  </span>
                  <span style={{ color: 'var(--gold-400)' }}>{f.type}</span>
                  <span style={{
                    color: 'var(--charcoal-500)',
                    fontSize: '0.72rem',
                    background: 'rgba(255,255,255,0.06)',
                    padding: '0.15rem 0.5rem',
                    borderRadius: '100px',
                    whiteSpace: 'nowrap',
                  }}>
                    {f.note}
                  </span>
                </motion.div>
              ))}

              <div style={{
                marginTop: '1.25rem',
                padding: '0.75rem',
                background: 'rgba(78,136,96,0.15)',
                border: '1px solid rgba(78,136,96,0.3)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--sage-400)',
                fontSize: '0.78rem',
                lineHeight: 1.6,
              }}>
                ✓ Downstream agents can only read upstream fields.<br />
                ✓ LLM cannot skip straight to an opinion without evidence.
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
