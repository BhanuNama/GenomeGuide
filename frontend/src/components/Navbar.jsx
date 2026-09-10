import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Dna, Menu, X } from 'lucide-react';

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <nav className={`navbar ${scrolled ? 'scrolled' : ''}`}>
      <motion.div
        className="navbar-logo"
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Dna size={22} color="var(--sage-500)" strokeWidth={1.8} />
        GenomeGuide
        <span className="navbar-logo-dot" />
      </motion.div>

      <motion.ul
        className="navbar-links"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <li><a href="#how-it-works">How it Works</a></li>
        <li><a href="#analyzer">Analyzer</a></li>
        <li><a href="#metrics">Eval Metrics</a></li>
        <li><a href="#architecture">Architecture</a></li>
        <li>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
            style={{ padding: '0.55rem 1.25rem', fontSize: '0.85rem' }}
          >
            GitHub ↗
          </a>
        </li>
      </motion.ul>

      <button
        className="btn btn-secondary"
        style={{ display: 'none', padding: '0.5rem' }}
        onClick={() => setMenuOpen(o => !o)}
        aria-label="Toggle menu"
      >
        {menuOpen ? <X size={20} /> : <Menu size={20} />}
      </button>
    </nav>
  );
}
