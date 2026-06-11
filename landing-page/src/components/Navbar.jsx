import React, { useState, useEffect } from 'react';
import { MonitorPlay, Menu, X } from 'lucide-react';

const Navbar = () => {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 50) {
        setScrolled(true);
      } else {
        setScrolled(false);
      }
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <nav className={`fixed w-full z-50 transition-all duration-300 ${scrolled ? 'bg-primary/95 backdrop-blur-md py-3 shadow-lg' : 'bg-transparent py-5'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center">
        
        {/* Logo */}
        <div className="flex items-center gap-2">
          <MonitorPlay className={`w-8 h-8 ${scrolled ? 'text-accent' : 'text-primary'}`} />
          <span className={`text-2xl font-heading font-bold ${scrolled ? 'text-background' : 'text-primary'}`}>
            DisplayDigital
          </span>
        </div>

        {/* Desktop Links */}
        <div className="hidden md:flex items-center gap-8">
          <a href="#features" className={`font-medium transition-colors hover:text-accent ${scrolled ? 'text-background/90' : 'text-textMain/80'}`}>Funcionalidades</a>
          <a href="#integration" className={`font-medium transition-colors hover:text-accent ${scrolled ? 'text-background/90' : 'text-textMain/80'}`}>Integração</a>
          <button className="bg-accent text-primary px-6 py-2 rounded-full font-semibold transition-transform hover:scale-105 shadow-md">
            Testar Grátis
          </button>
        </div>

        {/* Mobile Menu Toggle */}
        <div className="md:hidden">
          <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className={`${scrolled ? 'text-background' : 'text-primary'}`}>
            {mobileMenuOpen ? <X className="w-7 h-7" /> : <Menu className="w-7 h-7" />}
          </button>
        </div>

      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden absolute top-full left-0 w-full bg-primary shadow-xl border-t border-primary/80">
          <div className="flex flex-col p-4 space-y-4">
            <a href="#features" className="text-background hover:text-accent font-medium" onClick={() => setMobileMenuOpen(false)}>Funcionalidades</a>
            <a href="#integration" className="text-background hover:text-accent font-medium" onClick={() => setMobileMenuOpen(false)}>Integração</a>
            <button className="bg-accent text-primary px-6 py-3 rounded-full font-semibold w-full">
              Testar Grátis
            </button>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
