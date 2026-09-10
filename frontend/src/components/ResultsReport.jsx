import { motion } from 'framer-motion';
import { CheckCircle2, AlertTriangle, Info, ExternalLink } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

// Map classification string → CSS class suffix
function getClassBannerClass(cls) {
  if (!cls) return 'vus';
  const c = cls.toLowerCase();
  if (c === 'pathogenic')          return 'pathogenic';
  if (c === 'likely pathogenic')   return 'likely-path';
  if (c.includes('uncertain'))     return 'vus';
  if (c === 'likely benign')       return 'likely-benign';
  if (c === 'benign')              return 'benign';
  return 'vus';
}

function getClassificationColor(cls) {
  const c = (cls || '').toLowerCase();
  if (c === 'pathogenic')         return '#B91C1C';
  if (c === 'likely pathogenic')  return '#92400E';
  if (c.includes('uncertain'))    return '#1E40AF';
  if (c === 'likely benign')      return '#065F46';
  if (c === 'benign')             return '#065F46';
  return '#374151';
}

function getACMGChipClass(crit) {
  if (crit.startsWith('PVS')) return 'chip-pvs';
  if (crit.startsWith('PS'))  return 'chip-ps';
  if (crit.startsWith('PM'))  return 'chip-pm';
  if (crit.startsWith('PP'))  return 'chip-pp';
  if (crit.startsWith('BA'))  return 'chip-ba';
  if (crit.startsWith('BS'))  return 'chip-bs';
  if (crit.startsWith('BP'))  return 'chip-bp';
  return '';
}

function StarRating({ stars, max = 4 }) {
  return (
    <div className="star-rating">
      {Array.from({ length: max }).map((_, i) => (
        <span key={i} className={`star ${i < stars ? 'star-filled' : 'star-empty'}`}>★</span>
      ))}
    </div>
  );
}

function FreqBar({ af }) {
  // Logarithmic scale for display: 0 → 0, 0.0001 → 20%, 0.05 → 80%, 1 → 100%
  let pct = 0;
  if (af > 0) {
    const logScale = (Math.log10(af) + 6) / 6; // AF of 1e-6 → 0, AF of 1 → 100%
    pct = Math.max(2, Math.min(100, logScale * 100));
  }

  let color = 'var(--rose-500)';
  if (af > 0.05)        color = 'var(--sage-500)';
  else if (af > 0.001)  color = 'var(--gold-500)';

  return (
    <div className="freq-bar-wrapper">
      <div className="freq-bar-track">
        <motion.div
          className="freq-bar-fill"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 1, delay: 0.3 }}
        />
      </div>
      <div className="freq-thresholds">
        <span className="freq-threshold-label">PM2 (&lt;0.01%)</span>
        <span className="freq-threshold-label">BA1 (&gt;5%)</span>
      </div>
    </div>
  );
}

function ConfidenceBar({ confidence }) {
  const pct = confidence === 'High' ? 90 : confidence === 'Moderate' ? 55 : 25;
  const color = confidence === 'High' ? 'var(--sage-500)' : confidence === 'Moderate' ? 'var(--gold-500)' : 'var(--charcoal-500)';
  return (
    <div className="confidence-bar-wrapper">
      <div className="confidence-bar-label">
        <span>Classifier Confidence</span>
        <span style={{ fontWeight: 600, color }}>{confidence}</span>
      </div>
      <div className="confidence-bar">
        <motion.div
          className="confidence-bar-fill"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, delay: 0.2 }}
        />
      </div>
    </div>
  );
}

export default function ResultsReport({ result }) {
  if (!result) return null;

  const { parsed, clinvar, gnomad, acmg, explanation, critic } = result;
  const bannerClass  = getClassBannerClass(acmg?.classification);
  const classColor   = getClassificationColor(acmg?.classification);

  return (
    <div className="results-panel">
      {/* 1. Classification Banner */}
      <motion.div
        className={`classification-banner class-banner-${bannerClass}`}
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
      >
        <div className="classification-label">ACMG/AMP Classification</div>
        <div className="classification-value" style={{ color: classColor }}>
          {acmg?.classification || 'Unknown'}
        </div>

        {/* Criteria chips */}
        {acmg?.triggered_criteria?.length > 0 && (
          <div className="acmg-criteria">
            {acmg.triggered_criteria.map(crit => (
              <span key={crit} className={`acmg-chip ${getACMGChipClass(crit)}`} title={acmg.criteria_details?.[crit]}>
                {crit}
              </span>
            ))}
          </div>
        )}

        {acmg?.confidence && (
          <div style={{ marginTop: '1rem' }}>
            <ConfidenceBar confidence={acmg.confidence} />
          </div>
        )}

        {/* Parsed variant header */}
        <div style={{
          marginTop: '1rem',
          padding: '0.6rem 0.9rem',
          background: 'rgba(255,255,255,0.5)',
          borderRadius: 'var(--radius-sm)',
          fontFamily: 'Inter, monospace',
          fontSize: '0.88rem',
          color: 'var(--charcoal-700)',
        }}>
          <strong>{parsed?.gene}</strong>{' '}
          {parsed?.hgvs_c}
          {parsed?.hgvs_p && ` (${parsed.hgvs_p})`}
          {' · '}
          <span style={{ textTransform: 'capitalize' }}>{parsed?.variant_type}</span>
        </div>
      </motion.div>

      {/* 2. Evidence grid: ClinVar + gnomAD */}
      <motion.div
        className="result-card"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.4 }}
      >
        <h4 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span>🗄️</span> Retrieved Evidence
        </h4>
        <div className="evidence-grid">
          {/* ClinVar */}
          <div className="evidence-item">
            <div className="evidence-item-label">ClinVar</div>
            {clinvar?.found ? (
              <>
                <div className="evidence-item-value">{clinvar.classification || 'Found'}</div>
                <div className="evidence-item-sub" style={{ marginTop: '0.4rem' }}>
                  <StarRating stars={clinvar.star_rating} />
                  <span style={{ fontSize: '0.75rem', color: 'var(--charcoal-500)', marginTop: '0.2rem', display: 'block' }}>
                    {clinvar.submitters} submitter{clinvar.submitters !== 1 ? 's' : ''}
                    {clinvar.conflicting && ' · ⚠ Conflicting'}
                  </span>
                </div>
                {clinvar.variation_id && (
                  <a
                    href={`https://www.ncbi.nlm.nih.gov/clinvar/variation/${clinvar.variation_id}/`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem', marginTop: '0.4rem' }}
                  >
                    View in ClinVar <ExternalLink size={11} />
                  </a>
                )}
              </>
            ) : (
              <>
                <div className="evidence-item-value" style={{ color: 'var(--charcoal-500)' }}>Not Found</div>
                <div className="evidence-item-sub">No prior ClinVar submission</div>
              </>
            )}
          </div>

          {/* gnomAD */}
          <div className="evidence-item">
            <div className="evidence-item-label">gnomAD Population Freq.</div>
            {gnomad?.found ? (
              <>
                <div className="evidence-item-value">
                  {gnomad.allele_frequency !== null
                    ? `${(gnomad.allele_frequency * 100).toFixed(4)}%`
                    : '0%'}
                </div>
                <FreqBar af={gnomad.allele_frequency || 0} />
                <div className="evidence-item-sub" style={{ marginTop: '0.3rem' }}>
                  AC: {gnomad.allele_count?.toLocaleString()} / AN: {gnomad.allele_number?.toLocaleString()}
                  <br />{gnomad.dataset}
                </div>
              </>
            ) : (
              <>
                <div className="evidence-item-value" style={{ color: 'var(--sage-600)' }}>Absent</div>
                <div className="evidence-item-sub">Not found in gnomAD r4</div>
                <div className="evidence-item-sub" style={{ marginTop: '0.3rem' }}>
                  Supports PM2 criterion
                </div>
              </>
            )}
          </div>
        </div>

        {/* ACMG criteria details */}
        {acmg?.criteria_details && Object.keys(acmg.criteria_details).length > 0 && (
          <div style={{ marginTop: '1.25rem' }}>
            <div style={{
              fontSize: '0.78rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--charcoal-500)',
              marginBottom: '0.75rem',
            }}>
              ACMG Criteria Applied
            </div>
            {Object.entries(acmg.criteria_details).map(([crit, detail]) => (
              <div
                key={crit}
                style={{
                  display: 'flex',
                  gap: '0.75rem',
                  alignItems: 'flex-start',
                  padding: '0.6rem 0',
                  borderBottom: '1px solid var(--sand-200)',
                }}
              >
                <span className={`acmg-chip ${getACMGChipClass(crit)}`} style={{ flexShrink: 0 }}>
                  {crit}
                </span>
                <span style={{ fontSize: '0.84rem', color: 'var(--charcoal-600)', lineHeight: 1.6 }}>
                  {detail}
                </span>
              </div>
            ))}
          </div>
        )}
      </motion.div>

      {/* 3. Plain-English Explanation */}
      {explanation && (
        <motion.div
          className="result-card"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.4 }}
        >
          <h4 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>✍️</span> Patient-Facing Explanation
            <span className="badge badge-neutral" style={{ marginLeft: 'auto', fontSize: '0.72rem' }}>
              Groq LLaMA 3.1 70B
            </span>
          </h4>

          {/* Critic status */}
          <div className={`critic-status ${critic?.passed ? 'critic-passed' : 'critic-retry'}`} style={{ marginBottom: '1rem' }}>
            {critic?.passed
              ? <><CheckCircle2 size={15} /> Critic verified — all claims evidence-backed</>
              : <><AlertTriangle size={15} /> Critic forced {critic?.retry_count} revision{critic?.retry_count !== 1 ? 's' : ''}</>
            }
          </div>

          <div className="explanation-text">
            <ReactMarkdown>{explanation}</ReactMarkdown>
          </div>
        </motion.div>
      )}

      {/* 4. Responsible AI Disclaimer */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.4 }}
        style={{
          background: 'var(--sand-200)',
          border: '1px solid var(--sand-300)',
          borderRadius: 'var(--radius-sm)',
          padding: '1rem 1.25rem',
          fontSize: '0.82rem',
          color: 'var(--charcoal-600)',
          display: 'flex',
          gap: '0.75rem',
          alignItems: 'flex-start',
          lineHeight: 1.7,
        }}
      >
        <Info size={15} style={{ flexShrink: 0, marginTop: 3, color: 'var(--sage-600)' }} />
        <span>
          <strong>5-criterion MVP disclaimer:</strong> This tool implements PVS1, PS3/PP5, PM2, BA1, and BP6
          — a subset of the full 28-criterion ACMG/AMP framework. It is an educational tool and is{' '}
          <strong>not a substitute for professional genetic counselling.</strong>{' '}
          Discuss results with a certified genetic counsellor or physician before making any medical decisions.
        </span>
      </motion.div>
    </div>
  );
}
