import React, { useRef, useMemo } from 'react';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { DrawSVGPlugin } from 'gsap-trial/DrawSVGPlugin';
import { MotionPathPlugin } from 'gsap-trial/MotionPathPlugin';

gsap.registerPlugin(useGSAP, ScrollTrigger, DrawSVGPlugin, MotionPathPlugin);

const FloatingDebris = () => {
  const debrisRef = useRef(null);
  
  // Gerar um array estático de partículas para evitar re-renders do React
  const debrisItems = useMemo(() => {
    return Array.from({ length: 20 }).map((_, i) => {
      const type = i % 3; // 0: rect, 1: circle, 2: text/shape
      return {
        id: i,
        type,
        startX: Math.random() * 100, // vw
        startY: Math.random() * 100, // vh
        startZ: Math.random() * -500, // profundidade inicial
        scale: Math.random() * 0.5 + 0.2
      };
    });
  }, []);

  useGSAP(() => {
    if (!debrisRef.current) return;
    const items = gsap.utils.toArray('.debris-item', debrisRef.current);
    
    items.forEach(item => {
      // Definir estado inicial com perspectiva 3D
      gsap.set(item, { 
        transformPerspective: 1000, 
        transformStyle: "preserve-3d" 
      });

      // Animação contínua e aleatória
      gsap.to(item, {
        x: `+=${gsap.utils.random(-150, 150)}`,
        y: `+=${gsap.utils.random(-150, 150)}`,
        z: `+=${gsap.utils.random(-300, 300)}`,
        rotationX: gsap.utils.random(-360, 360),
        rotationY: gsap.utils.random(-360, 360),
        rotationZ: gsap.utils.random(-180, 180),
        duration: gsap.utils.random(8, 15),
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
        delay: gsap.utils.random(-10, 0) // Inicia já em movimento
      });
    });
  }, { scope: debrisRef });

  return (
    <div ref={debrisRef} className="absolute inset-0 z-0 pointer-events-none perspective-[1000px] overflow-hidden">
      {debrisItems.map(item => (
        <div 
          key={item.id} 
          className="debris-item absolute border border-accent/20 bg-background/40 backdrop-blur-sm"
          style={{
            left: `${item.startX}vw`,
            top: `${item.startY}vh`,
            transform: `translateZ(${item.startZ}px) scale(${item.scale})`,
            width: item.type === 0 ? '60px' : item.type === 1 ? '40px' : '80px',
            height: item.type === 0 ? '40px' : item.type === 1 ? '40px' : '20px',
            borderRadius: item.type === 1 ? '50%' : '4px'
          }}
        />
      ))}
    </div>
  );
};

const Hero = () => {
  const sectionRef = useRef(null);
  const textContentRef = useRef(null);
  const groupRef = useRef(null); // Grupo que viaja e aplica Inércia 3D
  
  // Displays Refs
  const display1Ref = useRef(null);
  const display2Ref = useRef(null);
  const display3Ref = useRef(null);
  
  // SVG Refs
  const pathRef = useRef(null);
  const particleRef = useRef(null);

  useGSAP(() => {
    // Animação de entrada do texto
    gsap.fromTo('.hero-text-line', 
      { y: 50, opacity: 0 },
      { y: 0, opacity: 1, duration: 1, stagger: 0.15, ease: 'power3.out' }
    );

    // Animação inicial do Display Principal no Grid
    gsap.fromTo(display1Ref.current,
      { opacity: 0, rotationY: 15, scale: 0.9 },
      { opacity: 1, rotationY: 0, scale: 1, duration: 1.5, ease: 'power4.out', delay: 0.3 }
    );

    // SCROLL TIMELINE (Parallax, Inércia 3D, Mitose)
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: sectionRef.current,
        start: 'top top',
        end: '+=3000', 
        scrub: 1,
        pin: true,
        anticipatePin: 1
      }
    });

    // 1. Textos saem da tela (Parallax)
    tl.to(textContentRef.current, { x: '-50vw', opacity: 0, duration: 1 }, 0);
    
    // DrawSVG & Motion Path sincronizado com scroll
    tl.fromTo(pathRef.current, { drawSVG: "0%" }, { drawSVG: "100%", duration: 2, ease: "power1.inOut" }, 0.2);
    tl.to(particleRef.current, {
      motionPath: {
        path: pathRef.current,
        align: pathRef.current,
        alignOrigin: [0.5, 0.5],
        autoRotate: true
      },
      duration: 2,
      ease: "power1.inOut",
      opacity: 1
    }, 0.2);

    // 2. Viagem com Inércia 3D (O grupo viaja para a esquerda/centro)
    // O container "corta o vento" enquanto se move e depois nivela
    tl.to(groupRef.current, { 
      x: '-25vw', 
      rotateY: -15, // Inclina 3D simulando resistência
      rotateX: 5,
      duration: 1,
      ease: "power1.inOut"
    }, 0.5);
    
    tl.to(groupRef.current, {
      rotateY: 0, // Nivela quando chega ao destino
      rotateX: 0,
      duration: 0.5,
      ease: "power2.out"
    }, 1.5);

    // 3. A MITOSE (Mutação e Ejeção)
    // Display 1 morphing de TV horizontal para Tela Vertical 9:16
    tl.to(display1Ref.current, { 
      width: '20vw',   // aspect 9:16 approx
      height: '35.5vw', 
      x: '-12vw',      // move left within the group
      borderRadius: '8px',
      borderWidth: '4px',
      duration: 1.5, 
      ease: 'power2.inOut' 
    }, 1);

    // Transição interna Display 1
    tl.to('.initial-tv-content', { opacity: 0, duration: 0.5 }, 1);
    tl.to('.vertical-menu-content', { opacity: 1, duration: 0.5 }, 1.5);

    // Ejeção do Display 2 (Top Right)
    tl.fromTo(display2Ref.current, 
      { scale: 0, opacity: 0, x: 0, y: 0, z: -100 },
      { 
        scale: 1, 
        opacity: 1, 
        x: '10vw',   // ejeta pra direita
        y: '-10vw',  // ejeta pra cima
        z: 0,
        width: '24vw', // aspect 16:9 approx
        height: '13.5vw',
        duration: 1.2, 
        ease: 'back.out(1.2)' 
      }, 
      1.2
    );

    // Ejeção do Display 3 (Bottom Right)
    tl.fromTo(display3Ref.current, 
      { scale: 0, opacity: 0, x: 0, y: 0, z: -100 },
      { 
        scale: 1, 
        opacity: 1, 
        x: '10vw',   // ejeta pra direita
        y: '5vw',    // ejeta pra baixo
        z: 0,
        width: '24vw', // aspect 16:9
        height: '13.5vw',
        duration: 1.2, 
        ease: 'back.out(1.2)' 
      }, 
      1.4
    );

    // Revelar Itens Menus
    tl.fromTo('.menu-item-reveal', 
      { y: 20, opacity: 0 },
      { y: 0, opacity: 1, duration: 0.5, stagger: 0.1 }, 
      2
    );

  }, { scope: sectionRef });

  return (
    <section ref={sectionRef} className="relative w-full h-screen overflow-hidden bg-background">
      
      {/* Ecosystem 3D Floating Debris */}
      <FloatingDebris />
      
      {/* Background Motion Paths */}
      <div className="absolute inset-0 w-full h-full pointer-events-none z-0">
        <svg className="w-full h-full" viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid slice">
          <path 
            ref={pathRef}
            d="M -100 800 C 400 800, 600 200, 1000 500 S 1400 300, 2000 600" 
            fill="transparent" 
            stroke="url(#gradientGlow)" 
            strokeWidth="3" 
            strokeLinecap="round"
            className="opacity-50"
          />
          <defs>
            <linearGradient id="gradientGlow" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#b07d4e" stopOpacity="0" />
              <stop offset="50%" stopColor="#FFCC00" stopOpacity="1" />
              <stop offset="100%" stopColor="#b07d4e" stopOpacity="0" />
            </linearGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
        </svg>
        
        {/* Particle */}
        <div ref={particleRef} className="absolute w-6 h-6 -ml-3 -mt-3 opacity-0 z-10" style={{ filter: 'url(#glow)' }}>
          <div className="w-full h-full bg-[#FFCC00] rounded-full shadow-[0_0_20px_#FFCC00]"></div>
        </div>
      </div>

      {/* Main Container - Flexbox para evitar sobreposição */}
      <div className="relative z-10 w-full h-full flex items-center justify-between max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* LEFT COLUMN: Texto inicial */}
        <div ref={textContentRef} className="w-1/2 pr-8 flex-shrink-0 z-20">
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-heading text-primary leading-tight">
            <span className="block text-textMain/80 text-3xl sm:text-4xl mb-2 font-body font-normal hero-text-line">Seu cardápio, sempre</span>
            <span className="block italic font-bold text-primary hero-text-line">Atualizado e</span>
            <span className="block italic font-bold text-primary hero-text-line">Impecável.</span>
          </h1>
          <p className="mt-6 text-xl text-textMain/70 font-body hero-text-line">
            Tabelas de preços digitais integradas ao seu ERP em tempo real. Solução premium para o varejo moderno.
          </p>
          <div className="mt-10 hero-text-line">
            <button className="bg-accent text-primary px-8 py-4 rounded-full font-bold text-lg transition-all hover:scale-105 hover:bg-[#b07d4e] shadow-[0_0_30px_rgba(176,125,78,0.3)]">
              Transformar Minha Loja
            </button>
          </div>
        </div>

        {/* RIGHT COLUMN: Área de Mitose e Inércia 3D */}
        <div className="w-1/2 h-full relative perspective-[1500px] flex items-center justify-center pointer-events-none">
          {/* Grupo de Inércia que viaja */}
          <div ref={groupRef} className="relative w-full flex items-center justify-center transform-style-3d">
            
            {/* O Ponto de Origem para a Mitose (Todos nascem do centro deste container) */}
            
            {/* DISPLAY 2 (Horizontal - Hortifruti) - Ejetado pra cima */}
            <div 
              ref={display2Ref}
              className="absolute z-10 bg-black border-4 border-primary shadow-2xl overflow-hidden p-6 opacity-0"
              style={{ width: '35vw', height: '19.6vw' }} /* Inicia grande mas a timeline escala de 0 para o width/height alvo */
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-accent/10 rounded-bl-full blur-2xl"></div>
              <h2 className="text-white font-heading text-xl tracking-[0.2em] uppercase border-b-2 border-accent pb-2 mb-4">Hortifruti Fresco</h2>
              <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                {[
                  { name: 'TOMATE CARMELA', price: '12,90' },
                  { name: 'ASPARGOS FRESCOS', price: '24,90' },
                  { name: 'COGUMELO PARIS', price: '35,00' },
                  { name: 'UVA THOMPSON', price: '18,50' }
                ].map((item, i) => (
                  <div key={i} className="flex flex-col border-b border-white/10 pb-1 menu-item-reveal">
                    <span className="text-white/80 font-body text-xs tracking-wider uppercase">{item.name}</span>
                    <span className="text-[#FFCC00] font-heading font-bold text-lg">{item.price}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* DISPLAY 3 (Horizontal - Promo) - Ejetado pra baixo */}
            <div 
              ref={display3Ref}
              className="absolute z-10 bg-black border-4 border-primary shadow-2xl overflow-hidden relative opacity-0 flex items-center justify-center group"
              style={{ width: '35vw', height: '19.6vw' }}
            >
              <img 
                src="https://images.unsplash.com/photo-1603360946369-pt2r2u2p1623?q=80&w=1000&auto=format&fit=crop" 
                alt="Promoção" 
                className="absolute inset-0 w-full h-full object-cover opacity-40 mix-blend-luminosity"
              />
              <div className="absolute inset-0 bg-gradient-to-r from-black/80 to-transparent"></div>
              <div className="relative z-20 text-left w-full px-6 menu-item-reveal">
                <span className="bg-red-600 text-white px-2 py-1 text-[10px] font-bold tracking-widest uppercase mb-2 inline-block">Oferta Especial</span>
                <h3 className="text-[#FFCC00] font-heading text-3xl uppercase font-bold leading-none mb-1">Fim de<br/>Semana</h3>
                <p className="text-white tracking-widest text-xs uppercase">Kit Churrasco com 15% OFF</p>
              </div>
            </div>

            {/* DISPLAY 1 (Vertical - Carnes) - Original que reduz pra 9:16 */}
            <div 
              ref={display1Ref} 
              className="absolute z-30 bg-black border-8 border-primary shadow-2xl overflow-hidden pointer-events-auto"
              style={{ width: '35vw', height: '24vw' }} // Start slightly horizontal
            >
              {/* Conteúdo Inicial */}
              <div className="initial-tv-content absolute inset-0 w-full h-full">
                <img 
                  src="https://images.unsplash.com/photo-1550989460-0adf9ea622e2?q=80&w=1000&auto=format&fit=crop" 
                  alt="Display Inicial"
                  className="w-full h-full object-cover opacity-80"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent"></div>
                <div className="absolute bottom-6 left-6">
                  <p className="font-heading font-bold text-white text-2xl tracking-wider">PREMIUM QUALITY</p>
                  <div className="w-12 h-1 bg-accent mt-2"></div>
                </div>
              </div>

              {/* Conteúdo Mutado Vertical 9:16 */}
              <div className="vertical-menu-content absolute inset-0 w-full h-full bg-black p-6 opacity-0 flex flex-col">
                <div className="border-b-2 border-accent pb-4 mb-6 text-center">
                  <h2 className="text-white font-heading text-2xl tracking-[0.2em] uppercase">Cortes Gourmet</h2>
                </div>
                <div className="flex-1 flex flex-col gap-4">
                  {[
                    { name: 'PICANHA ANGUS', price: '129,90' },
                    { name: 'ANCHO WAGYU', price: '289,00' },
                    { name: 'BIFE DE CHORIZO', price: '89,90' },
                    { name: 'T-BONE PREMIUM', price: '115,00' },
                    { name: 'FRALDINHA RED', price: '75,90' }
                  ].map((item, i) => (
                    <div key={i} className="flex justify-between items-end border-b border-white/10 pb-2 menu-item-reveal">
                      <span className="text-white font-body text-sm tracking-wider uppercase">{item.name}</span>
                      <span className="text-[#FFCC00] font-heading font-bold text-xl">{item.price}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-auto pt-4 text-center">
                  <p className="text-white/50 text-[10px] uppercase tracking-widest">Preços por KG</p>
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
