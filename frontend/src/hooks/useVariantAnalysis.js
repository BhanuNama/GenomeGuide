import { useState, useCallback, useRef } from 'react';
import { analyzeVariant } from '../api/genomeguide';

const PIPELINE_STEPS = [
  { id: 'parsing',    label: 'Parsing variant notation',       agent: 'Parser Agent (LLM)' },
  { id: 'lookup',     label: 'Querying ClinVar & gnomAD',      agent: 'Database Lookup Agent' },
  { id: 'classifying',label: 'Running ACMG rule engine',       agent: 'Classifier (deterministic)' },
  { id: 'explaining', label: 'Generating patient explanation', agent: 'Explainer Agent (LLM)' },
  { id: 'verifying',  label: 'Critic verification check',      agent: 'Critic Agent (LLM)' },
  { id: 'complete',   label: 'Analysis complete',              agent: 'Pipeline' },
];

export function useVariantAnalysis() {
  const [status, setStatus]         = useState('idle'); // idle | loading | success | error
  const [progress, setProgress]     = useState([]);
  const [activeStep, setActiveStep] = useState(null);
  const [result, setResult]         = useState(null);
  const [error, setError]           = useState(null);
  const cleanupRef = useRef(null);

  const analyze = useCallback((variant) => {
    // Cancel any in-flight request
    if (cleanupRef.current) cleanupRef.current();

    setStatus('loading');
    setProgress([]);
    setActiveStep('parsing');
    setResult(null);
    setError(null);

    const cleanup = analyzeVariant(variant, {
      onProgress: (data) => {
        setActiveStep(data.step);
        setProgress(prev => {
          const exists = prev.find(p => p.step === data.step);
          if (exists) return prev.map(p => p.step === data.step ? { ...p, ...data } : p);
          return [...prev, data];
        });
      },
      onResult: (data) => {
        setResult(data);
        setStatus('success');
        setActiveStep('complete');
      },
      onError: (msg) => {
        setError(msg);
        setStatus('error');
        setActiveStep(null);
      },
    });

    cleanupRef.current = cleanup;
  }, []);

  const reset = useCallback(() => {
    if (cleanupRef.current) cleanupRef.current();
    setStatus('idle');
    setProgress([]);
    setActiveStep(null);
    setResult(null);
    setError(null);
  }, []);

  const getStepStatus = useCallback((stepId) => {
    if (!activeStep) return 'waiting';
    const stepIdx  = PIPELINE_STEPS.findIndex(s => s.id === stepId);
    const activeIdx = PIPELINE_STEPS.findIndex(s => s.id === activeStep);
    if (stepIdx < activeIdx)  return 'done';
    if (stepIdx === activeIdx) return status === 'success' ? 'done' : 'active';
    return 'waiting';
  }, [activeStep, status]);

  return { status, progress, activeStep, result, error, analyze, reset, getStepStatus, PIPELINE_STEPS };
}
