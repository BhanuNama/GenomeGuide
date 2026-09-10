import { motion } from 'framer-motion';

const STEPS = [
  {
    number: '01',
    label: 'Parser Agent',
    desc: 'Accepts raw HGVS notation. Groq LLaMA 3.1 70B extracts gene, coding notation, protein change, and variant type.',
    icon: '🔬',
    style: 'step-llm',
    tag: 'LLM',
    tagStyle: 'tag-llm',
  },
  {
    number: '02',
    label: 'Lookup Agent',
    desc: 'Queries ClinVar E-utilities and gnomAD GraphQL in parallel. Returns raw evidence. No LLM.',
    icon: '🗄️',
    style: 'step-api',
    tag: 'API calls',
    tagStyle: 'tag-api',
  },
  {
    number: '03',
    label: 'Classifier Agent',
    desc: 'Deterministic Python rule engine applies 5 ACMG/AMP criteria (PVS1, PS3, PM2, BA1, BP6). Zero LLM.',
    icon: '⚖️',
    style: 'step-rule',
    tag: 'Deterministic',
    tagStyle: 'tag-rule',
  },
  {
    number: '04',
    label: 'Explainer Agent',
    desc: 'Groq LLaMA writes plain-English patient summary strictly from the already-made classification.',
    icon: '✍️',
    style: 'step-llm',
    tag: 'LLM',
    tagStyle: 'tag-llm',
  },
  {
    number: '05',
    label: 'Critic Agent',
    desc: 'Verifies every claim traces back to retrieved evidence. Conditional retry edge if hallucination detected.',
    icon: '🔍',
    style: 'step-critic',
    tag: 'LLM + Retry',
    tagStyle: 'tag-llm',
  },
];

export default function Pipeline() {
  return (
    <section id="how-it-works" className="pipeline-section">
      <div className="container">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <span className="badge" style={{ background: 'rgba(78,136,96,0.2)', color: 'var(--sage-400)' }}>
              System Architecture
            </span>
          </div>
          <h2 className="pipeline-title">5-Agent LangGraph Pipeline</h2>
          <p className="pipeline-subtitle">
            Each agent has exactly one job. The clinical classification is computed
            by deterministic rules — the LLM only handles language-shaped tasks.
          </p>
        </motion.div>

        <div className="pipeline-grid">
          {STEPS.map((step, i) => (
            <motion.div
              key={step.number}
              className="pipeline-step"
              initial={{ opacity: 0, y: 32 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.12, duration: 0.5 }}
            >
              <div className={`pipeline-step-icon ${step.style}`}>
                <span>{step.icon}</span>
                <span className="pipeline-step-number">{step.number}</span>
              </div>
              <div className="pipeline-step-label">{step.label}</div>
              <div className="pipeline-step-desc">{step.desc}</div>
              <span className={`pipeline-step-tag ${step.tagStyle}`}>{step.tag}</span>
            </motion.div>
          ))}
        </div>

        {/* Critic loop callout */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.7, duration: 0.5 }}
          style={{
            marginTop: '3rem',
            background: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 'var(--radius-md)',
            padding: '1.75rem 2rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '1.25rem',
          }}
        >
          <span style={{ fontSize: '1.8rem', flexShrink: 0 }}>🔄</span>
          <div>
            <div style={{
              fontFamily: 'Playfair Display, serif',
              fontSize: '1.1rem',
              color: 'white',
              marginBottom: '0.4rem',
            }}>
              Real Conditional Retry Edge
            </div>
            <p style={{ color: 'var(--charcoal-500)', fontSize: '0.9rem', lineHeight: 1.7 }}>
              The Critic Agent re-reads the Explainer's draft against the retrieved evidence.
              If a claim isn't backed by ClinVar, gnomAD, or ACMG data — it rejects the draft
              and routes control back to the Explainer (max 2 retries). This is a genuine
              LangGraph conditional edge, not a formality. It's how the system self-checks for hallucination.
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
