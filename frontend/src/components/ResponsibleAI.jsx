import { motion } from 'framer-motion';

const RAI_POINTS = [
  {
    icon: '⚕️',
    title: 'Mandatory Disclaimer',
    desc: 'Every generated report carries a visible disclaimer. Not a legal formality — it changes how the output should be interpreted.',
  },
  {
    icon: '❓',
    title: 'VUS Never Implies Risk',
    desc: '"Variant of Uncertain Significance" copy explicitly states: not enough evidence yet, not a confirmed finding. Never worded as alarming.',
  },
  {
    icon: '🔒',
    title: 'Public Data Only',
    desc: 'The system never runs on real patient-identifiable data. MVP and demo use public ClinVar test variants exclusively.',
  },
];

export default function ResponsibleAI() {
  return (
    <section className="rai-section">
      <div className="container" style={{ textAlign: 'center' }}>
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <span className="badge" style={{ background: 'rgba(255,255,255,0.1)', color: 'var(--sand-300)' }}>
            Responsible AI
          </span>
          <h2 style={{ color: 'var(--white)', marginTop: '0.75rem' }}>
            Ethics First, Not Optional
          </h2>
          <p style={{ color: 'var(--sand-300)', maxWidth: 520, margin: '1rem auto 0', fontSize: '1.05rem' }}>
            This framing materially changes how a reviewer or interviewer perceives the project's judgment.
          </p>
        </motion.div>

        <motion.div
          className="rai-banner"
          initial={{ opacity: 0, scale: 0.97 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2, duration: 0.6 }}
        >
          <p>
            GenomeGuide closes the waiting-room gap between receiving a raw variant report
            and getting a qualified explanation. It does <strong style={{ color: 'var(--white)' }}>not replace</strong> a
            genetic counsellor — it gives the patient a grounded, honest first read
            while they wait for the specialist appointment.
          </p>

          <div className="rai-points">
            {RAI_POINTS.map((p, i) => (
              <motion.div
                key={i}
                className="rai-point"
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.3 + i * 0.1, duration: 0.5 }}
              >
                <span className="rai-point-icon">{p.icon}</span>
                <div className="rai-point-title">{p.title}</div>
                <div className="rai-point-desc">{p.desc}</div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
