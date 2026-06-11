import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';

const Hero = () => {
  const containerRef = useRef(null);
  const ambientRef = useRef(null);
  const imgRef = useRef(null);

  useEffect(() => {
    const q = gsap.utils.selector(containerRef);

    // Máscaras de Tipografia (Clip-Path Reveals) para o título
    gsap.fromTo(q('.title-line'), 
      { y: 100, clipPath: 'polygon(0% 100%, 100% 100%, 100% 100%, 0% 100%)' },
      { 
        y: 0, 
        clipPath: 'polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%)', 
        duration: 1.2, 
        stagger: 0.15, 
        ease: "power4.out", 
        delay: 0.2 
      }
    );

    // Fade up normal para o resto do texto
    gsap.fromTo(q('.hero-fade'), 
      { y: 30, opacity: 0 },
      { y: 0, opacity: 1, duration: 1, stagger: 0.15, ease: "power3.out", delay: 0.8 }
    );

    // Fade and float para a imagem
    gsap.fromTo(imgRef.current,
      { y: 30, opacity: 0 },
      { y: 0, opacity: 1, duration: 1.2, ease: "power3.out", delay: 0.6 }
    );

    // Movimento Ambiente Contínuo (Ambient Motion)
    gsap.to(ambientRef.current, {
      rotation: 360,
      scale: 1.1,
      duration: 30,
      repeat: -1,
      yoyo: true,
      ease: "sine.inOut"
    });
  }, []);

  return (
    <section ref={containerRef} className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden bg-background">
      
      {/* Movimento Ambiente - SVG com Turbulence + Gradiente Animado */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        {/* Malha de gradiente que se move suavemente */}
        <div 
          ref={ambientRef} 
          className="absolute -inset-[50%] w-[200%] h-[200%] bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-accent/10 via-background to-background"
        ></div>
        
        {/* SVG de Turbulência para textura premium */}
        <svg className="absolute inset-0 w-full h-full opacity-[0.15] mix-blend-overlay">
          <filter id="noiseFilter">
            <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" stitchTiles="stitch" />
          </filter>
          <rect width="100%" height="100%" filter="url(#noiseFilter)" />
        </svg>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="lg:grid lg:grid-cols-2 lg:gap-16 items-center">
          
          {/* Texto à esquerda */}
          <div className="max-w-2xl">
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-heading text-primary leading-tight">
              {/* Wrappers para garantir que o clip-path corte o texto perfeitamente */}
              <div className="overflow-hidden pb-2">
                <span className="block text-textMain/80 text-3xl sm:text-4xl mb-2 font-body font-normal title-line">Seu cardápio, sempre</span>
              </div>
              <div className="overflow-hidden pb-4">
                <span className="block italic font-bold text-primary title-line">Atualizado e</span>
              </div>
              <div className="overflow-hidden pb-4">
                <span className="block italic font-bold text-primary title-line">Impecável.</span>
              </div>
            </h1>
            <p className="mt-6 text-xl text-textMain/70 font-body hero-fade">
              Tabelas de preços digitais integradas ao seu ERP em tempo real. Solução premium para carnes, empórios e padarias modernas.
            </p>
            <div className="mt-10 flex gap-4 hero-fade relative group">
              <button className="bg-accent text-primary px-8 py-4 rounded-full font-bold text-lg transition-all hover:scale-105 hover:bg-[#b07d4e] shadow-xl relative overflow-hidden">
                {/* Pseudo-elemento para o efeito de varredura hover (diretriz de botões) */}
                <span className="absolute inset-0 w-full h-full bg-primary -translate-x-full group-hover:translate-x-0 transition-transform duration-300 ease-out z-0"></span>
                <span className="relative z-10 group-hover:text-background transition-colors duration-300">Testar Grátis</span>
              </button>
            </div>
            
            <div className="mt-8 flex items-center gap-3 hero-fade text-sm text-textMain/60 font-body">
              <span className="flex items-center gap-1">
                <svg className="w-5 h-5 text-accent" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Integração Direta
              </span>
              <span className="flex items-center gap-1">
                <svg className="w-5 h-5 text-accent" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Fácil de Usar
              </span>
            </div>
          </div>

          {/* Imagem à direita */}
          <div className="mt-16 lg:mt-0 relative" ref={imgRef}>
            <div className="relative rounded-xl overflow-hidden shadow-2xl border-8 border-primary/90 bg-primary transform rotate-1 hover:rotate-0 transition-transform duration-500">
              <img 
                src="https://images.unsplash.com/photo-1550989460-0adf9ea622e2?q=80&w=1000&auto=format&fit=crop" 
                alt="Smart TV exibindo preços de cortes de carne"
                className="w-full h-auto object-cover opacity-90"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-primary/60 to-transparent"></div>
              <div className="absolute bottom-4 left-6 right-6 flex justify-between items-end">
                <div className="bg-background/95 backdrop-blur rounded-lg p-3 shadow-lg">
                  <p className="font-heading font-bold text-primary text-sm">Picanha Premium</p>
                  <p className="font-body text-accent font-bold">R$ 89,90 /kg</p>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
};

export default Hero;
