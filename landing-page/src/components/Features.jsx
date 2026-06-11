import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Database, MonitorPlay, Tv, Play } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

const Features = () => {
  const integrationRef = useRef(null);
  const screenPriceRef = useRef(null);
  const dbPriceRef = useRef(null);
  const tiltRef = useRef(null);

  useEffect(() => {
    const q = gsap.utils.selector(integrationRef);

    // Scroll-Scrubbing e Pinning para a Seção de Integração
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: integrationRef.current,
        start: "center center",
        end: "+=120%", // Trava na tela por 120% do viewport
        pin: true,
        scrub: 1, // Animação amarrada ao scroll (Scroll-Scrubbing)
      }
    });

    // 1. Anima a luz percorrendo o cabo SVG
    tl.fromTo(q('.data-cable'), 
      { strokeDashoffset: 130 }, 
      { strokeDashoffset: -30, duration: 1, ease: "none" }
    );

    // 2. Quando a luz atinge a tela (em 85% do progresso)
    tl.to(screenPriceRef.current, {
      color: "#C48B57", // Muda para a cor de destaque (accent)
      scale: 1.15,
      duration: 0.1,
      onStart: () => {
        if(screenPriceRef.current) screenPriceRef.current.innerText = "R$ 95,00";
      },
      onReverseComplete: () => {
        if(screenPriceRef.current) screenPriceRef.current.innerText = "R$ 89,90";
      }
    }, 0.85);

    tl.to(screenPriceRef.current, {
      scale: 1,
      duration: 0.1
    }, 0.95);

    // Fade normal para os outros features
    gsap.utils.toArray('.fade-up').forEach(elem => {
      gsap.fromTo(elem, 
        { y: 50, opacity: 0 },
        { 
          y: 0, opacity: 1, duration: 1, ease: "power3.out",
          scrollTrigger: {
            trigger: elem,
            start: "top 80%",
          }
        }
      );
    });

    // Loop contínuo simulando o banco de dados atualizando loucamente
    const interval = setInterval(() => {
      if(dbPriceRef.current) {
        dbPriceRef.current.innerText = (Math.random() * (99.99 - 50.00) + 50.00).toFixed(2);
      }
    }, 80);

    return () => clearInterval(interval);
  }, []);

  // Handlers para o Parallax 3D (Tilt) na seção Mídia Dinâmica
  const handleMouseMove = (e) => {
    if (!tiltRef.current) return;
    const { left, top, width, height } = tiltRef.current.getBoundingClientRect();
    const x = (e.clientX - left) / width - 0.5; // -0.5 a 0.5
    const y = (e.clientY - top) / height - 0.5;

    gsap.to(tiltRef.current, {
      rotationY: x * 30, // max 15 graus de inclinação
      rotationX: -y * 30,
      ease: "power2.out",
      duration: 0.6
    });
  };

  const handleMouseLeave = () => {
    if (!tiltRef.current) return;
    gsap.to(tiltRef.current, {
      rotationY: 0,
      rotationX: 0,
      ease: "elastic.out(1, 0.4)",
      duration: 1.5
    });
  };

  return (
    <section id="features" className="bg-background pt-24 pb-12 overflow-hidden">
      
      {/* Header */}
      <div className="text-center max-w-3xl mx-auto mb-10 fade-up px-4">
        <h2 className="text-4xl font-heading font-bold text-primary mb-4">O Motor do seu Comércio</h2>
        <p className="text-lg text-textMain/70 font-body">
          Fim dos preços desatualizados. Nossa tecnologia transforma qualquer tela na vitrine perfeita para os seus produtos.
        </p>
      </div>

      {/* Feature 1: INTEGRAÇÃO (Pinned & Scrubbing) */}
      <div ref={integrationRef} className="min-h-[80vh] w-full flex flex-col justify-center relative bg-background z-10 py-10">
        
        <div className="text-center mb-12 px-4">
          <h3 className="text-3xl font-heading font-bold text-primary mb-2">O Fluxo de Dados</h3>
          <p className="text-lg text-textMain/60 font-body max-w-xl mx-auto">
            Role a tela para baixo. Veja como o preço sai do banco de dados e atualiza a sua tela em tempo real.
          </p>
        </div>

        <div className="max-w-6xl mx-auto px-4 w-full flex flex-col lg:flex-row items-center justify-between gap-6">
          
          {/* Esquerda: Banco de Dados / API Falsa */}
          <div className="flex-1 w-full lg:max-w-sm bg-primary p-6 rounded-xl shadow-2xl relative border border-primary/20">
            <div className="absolute top-0 right-0 bg-accent text-primary text-xs font-bold px-3 py-1 rounded-bl-lg">API / Omie</div>
            <div className="font-mono text-sm text-[#F9F6F0]/60 mt-4">
              <p className="text-accent mb-2">{">"} GET /api/v1/products/picanha</p>
              <p>{"{"}</p>
              <p className="pl-4">"id": "prod_192",</p>
              <p className="pl-4">"name": "Picanha Premium",</p>
              <p className="pl-4">
                 "price": <span ref={dbPriceRef} className="text-white font-bold bg-white/10 px-1 rounded inline-block min-w-[50px]">89.90</span>,
              </p>
              <p className="pl-4">"stock_status": "in_stock"</p>
              <p>{"}"}</p>
            </div>
            <div className="mt-6 flex items-center gap-2">
               <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
               <span className="text-xs text-[#F9F6F0]/40 font-mono">Loop de Sincronização...</span>
            </div>
          </div>

          {/* Centro: Cabo de Dados (SVG) */}
          <div className="w-full h-24 lg:w-48 lg:h-8 flex items-center justify-center">
            <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
               {/* Fundo do Cabo - Desktop */}
               <line x1="0" y1="50" x2="100" y2="50" stroke="#2C1A12" strokeWidth="2" strokeOpacity="0.1" className="hidden lg:block" />
               {/* Fundo do Cabo - Mobile */}
               <line x1="50" y1="0" x2="50" y2="100" stroke="#2C1A12" strokeWidth="2" strokeOpacity="0.1" className="block lg:hidden" />
               
               {/* Feixe de Luz - Desktop */}
               <line className="data-cable hidden lg:block" x1="0" y1="50" x2="100" y2="50" stroke="#C48B57" strokeWidth="6" strokeDasharray="30 100" strokeDashoffset="130" style={{ filter: 'drop-shadow(0px 0px 8px #C48B57)' }} />
               {/* Feixe de Luz - Mobile */}
               <line className="data-cable block lg:hidden" x1="50" y1="0" x2="50" y2="100" stroke="#C48B57" strokeWidth="6" strokeDasharray="30 100" strokeDashoffset="130" style={{ filter: 'drop-shadow(0px 0px 8px #C48B57)' }} />
            </svg>
          </div>

          {/* Direita: A Tela do Comércio */}
          <div className="flex-1 w-full lg:max-w-md bg-[#F9F6F0] border-[12px] border-primary rounded-2xl shadow-2xl relative overflow-hidden">
            <div className="bg-primary px-6 py-4 flex items-center gap-3">
              <MonitorPlay className="w-6 h-6 text-accent" />
              <span className="font-heading font-bold text-[#F9F6F0] tracking-wide">DisplayDigital</span>
            </div>
            <div className="p-8">
              <div className="flex justify-between items-center border-b-2 border-primary/10 pb-4 mb-4">
                <span className="font-heading text-xl text-primary font-bold">Picanha Premium</span>
                <span ref={screenPriceRef} className="font-body text-3xl font-black text-textMain/40 transition-colors duration-200">
                  R$ 89,90
                </span>
              </div>
              <div className="flex justify-between items-center border-b-2 border-primary/10 pb-4 mb-4">
                <span className="font-heading text-lg text-primary font-bold opacity-70">Fraldinha Grill</span>
                <span className="font-body text-xl font-bold text-primary opacity-70">R$ 54,90</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-heading text-lg text-primary font-bold opacity-70">Costela Bovina</span>
                <span className="font-body text-xl font-bold text-primary opacity-70">R$ 38,00</span>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* Outras Features */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-24 space-y-32">
        
        {/* Feature 2: Mídia Dinâmica (Parallax 3D) */}
        <div className="flex flex-col lg:flex-row-reverse items-center gap-16 fade-up">
          <div className="flex-1">
            <div className="bg-primary/5 w-16 h-16 rounded-2xl flex items-center justify-center mb-6 text-accent">
              <MonitorPlay className="w-8 h-8" />
            </div>
            <h3 className="text-3xl font-heading font-bold text-primary mb-4">Parallax de Vídeo e Tabela</h3>
            <p className="text-lg text-textMain/70 font-body leading-relaxed">
              O ecossistema perfeito de mídia. Misturamos "camadas" flutuantes: um vídeo apetitoso no fundo atraindo a atenção, enquanto a tabela com os preços dinâmicos paira na frente em vidro translúcido (Glassmorphism).
            </p>
          </div>
          
          {/* Container com perspectiva 3D */}
          <div 
            className="flex-1 relative cursor-pointer" 
            style={{ perspective: "1000px" }}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
          >
            {/* O "Cartão" 3D que gira com o mouse */}
            <div 
              ref={tiltRef} 
              className="aspect-video relative rounded-xl"
              style={{ transformStyle: "preserve-3d" }}
            >
              
              {/* CAMADA DE TRÁS (Background) - Profundidade Negativa */}
              <div 
                className="absolute inset-0 rounded-xl overflow-hidden shadow-2xl" 
                style={{ transform: "translateZ(-50px) scale(1.1)" }}
              >
                <img 
                  src="https://images.unsplash.com/photo-1542838132-92c53300491e?q=80&w=1000&auto=format&fit=crop" 
                  alt="Padaria Moderna"
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-primary/40 mix-blend-multiply"></div>
                {/* Fake Play Button */}
                <div className="absolute top-4 right-4 bg-background/20 backdrop-blur rounded-full p-3">
                  <Play className="w-5 h-5 text-background" fill="currentColor" />
                </div>
              </div>

              {/* CAMADA DA FRENTE (Foreground / Tabela Glassmorphism) - Profundidade Positiva */}
              <div 
                className="absolute inset-0 flex items-center justify-center pointer-events-none"
                style={{ transform: "translateZ(80px)" }}
              >
                 <div className="bg-background/85 backdrop-blur-xl p-6 rounded-xl shadow-2xl w-4/5 border border-background/40">
                    <div className="flex justify-between items-center border-b border-primary/20 pb-3 mb-3">
                      <span className="font-heading font-bold text-xl text-primary drop-shadow-sm">Croissant Francês</span>
                      <span className="font-body font-black text-xl text-accent">R$ 12,00</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-primary/20 pb-3 mb-3">
                      <span className="font-heading font-bold text-xl text-primary drop-shadow-sm">Baguette Rústica</span>
                      <span className="font-body font-black text-xl text-accent">R$ 8,50</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="font-heading font-bold text-xl text-primary drop-shadow-sm">Café Espresso</span>
                      <span className="font-body font-black text-xl text-accent">R$ 6,00</span>
                    </div>
                 </div>
              </div>
              
              {/* Elementos flutuantes extras (Profundidade Extrema) */}
              <div 
                className="absolute -bottom-6 -left-6 bg-accent text-background px-6 py-3 rounded-lg shadow-xl font-bold font-heading pointer-events-none"
                style={{ transform: "translateZ(120px)" }}
              >
                Promoção Ativa
              </div>

            </div>
          </div>
        </div>

        {/* Feature 3: Compatibilidade Universal */}
        <div className="flex flex-col lg:flex-row items-center gap-16 fade-up">
          <div className="flex-1">
            <div className="bg-primary/5 w-16 h-16 rounded-2xl flex items-center justify-center mb-6 text-accent">
              <Tv className="w-8 h-8" />
            </div>
            <h3 className="text-3xl font-heading font-bold text-primary mb-4">Compatibilidade Universal</h3>
            <p className="text-lg text-textMain/70 font-body leading-relaxed">
              Qualquer TV serve. Nosso sistema funciona perfeitamente em Smart TVs novas ou em televisores antigos utilizando simples adaptadores (como TV Box ou Fire Stick). Escalonamento fácil e de baixo custo.
            </p>
          </div>
          <div className="flex-1 relative">
            <div className="aspect-video bg-background border border-primary/10 rounded-xl shadow-xl flex flex-col items-center justify-center p-8">
              <div className="flex items-center gap-8">
                <div className="flex flex-col items-center">
                  <Tv className="w-20 h-20 text-primary mb-4" />
                  <span className="font-heading font-bold text-primary">Smart TV</span>
                </div>
                <span className="text-2xl text-accent font-bold">OU</span>
                <div className="flex flex-col items-center">
                  <div className="relative">
                    <Tv className="w-20 h-20 text-textMain/50 mb-4" />
                    <div className="absolute -bottom-2 -right-2 bg-accent p-2 rounded-lg text-background">
                       <MonitorPlay className="w-6 h-6" />
                    </div>
                  </div>
                  <span className="font-heading font-bold text-textMain/70">TV + Adaptador</span>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </section>
  );
};

export default Features;
