import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

import Navbar from './components/Navbar';
import Hero from './components/Hero';
import Features from './components/Features';
import ParallaxSection from './components/ParallaxSection';
import DashboardPreview from './components/DashboardPreview';
import Footer from './components/Footer';

gsap.registerPlugin(ScrollTrigger);

function App() {
  const appRef = useRef(null);

  useEffect(() => {
    // Global fade-up animation setup
    const elements = document.querySelectorAll('.fade-up');
    
    elements.forEach((el) => {
      gsap.fromTo(el, 
        { y: 50, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.8,
          ease: "power2.out",
          scrollTrigger: {
            trigger: el,
            start: "top 85%",
            toggleActions: "play none none none"
          }
        }
      );
    });

    return () => {
      ScrollTrigger.getAll().forEach(trigger => trigger.kill());
    };
  }, []);

  return (
    <div ref={appRef} className="overflow-hidden bg-background text-textMain">
      <Navbar />
      <Hero />
      <Features />
      <ParallaxSection />
      <DashboardPreview />
      <Footer />
    </div>
  );
}

export default App;
