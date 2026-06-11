import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const ParallaxSection = () => {
  const containerRef = useRef(null);
  const imageRef = useRef(null);

  useEffect(() => {
    // Parallax Effect
    gsap.to(imageRef.current, {
      y: "20%", // Moves the image slightly opposite to the scroll
      ease: "none",
      scrollTrigger: {
        trigger: containerRef.current,
        start: "top bottom", 
        end: "bottom top",
        scrub: true
      }
    });
  }, []);

  return (
    <section 
      ref={containerRef} 
      className="relative w-full h-screen overflow-hidden flex items-center justify-center"
    >
      {/* Background Image with Parallax */}
      <div 
        ref={imageRef}
        className="absolute inset-0 -top-[20%] h-[140%] w-full"
      >
        <img 
          src="https://images.unsplash.com/photo-1604328698692-f76ea9498e76?q=80&w=2000&auto=format&fit=crop" 
          alt="Ambiente de varejo com iluminação quente" 
          className="w-full h-full object-cover"
        />
      </div>

      {/* Dark Overlay */}
      <div className="absolute inset-0 bg-primary/70"></div>

      {/* Content */}
      <div className="relative z-10 max-w-5xl mx-auto px-4 text-center fade-up">
        <h2 className="text-5xl md:text-7xl font-heading font-bold text-background leading-tight">
          O cliente decide no balcão. <br/>
          <span className="text-accent italic">Garanta que ele veja a melhor oferta.</span>
        </h2>
      </div>
    </section>
  );
};

export default ParallaxSection;
