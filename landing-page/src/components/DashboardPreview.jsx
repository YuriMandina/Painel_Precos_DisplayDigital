import React from 'react';
import { Smartphone, LayoutGrid, Zap } from 'lucide-react';

const DashboardPreview = () => {
  return (
    <section className="py-24 bg-background overflow-hidden relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        <div className="text-center max-w-3xl mx-auto mb-16 fade-up">
          <h2 className="text-4xl font-heading font-bold text-primary mb-4">Simplicidade na Gestão</h2>
          <p className="text-lg text-textMain/70 font-body">
            Gerencie múltiplos displays ou atualize o menu de uma TV específica diretamente do celular ou do caixa, com um clique.
          </p>
        </div>

        {/* Dashboard Mockup */}
        <div className="relative mx-auto max-w-5xl fade-up">
          <div className="bg-primary rounded-t-2xl p-4 shadow-2xl flex items-center gap-2">
             <div className="w-3 h-3 rounded-full bg-red-500"></div>
             <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
             <div className="w-3 h-3 rounded-full bg-green-500"></div>
             <div className="ml-4 flex-1 bg-textMain/10 h-6 rounded px-2 text-xs flex items-center text-background/50">app.displaydigital.com</div>
          </div>
          <div className="bg-background border-x border-b border-primary/20 rounded-b-2xl shadow-2xl p-6 sm:p-10 flex flex-col md:flex-row gap-8">
            
            {/* Sidebar Mockup */}
            <div className="w-full md:w-64 flex-shrink-0 space-y-4">
               <div className="h-10 bg-primary/10 rounded-lg flex items-center px-4 font-bold text-primary">Telas Ativas (4)</div>
               <div className="h-10 bg-background border border-primary/10 rounded-lg flex items-center px-4 justify-between">
                 <span className="text-sm font-medium">TV Balcão 1</span>
                 <span className="w-2 h-2 rounded-full bg-green-500"></span>
               </div>
               <div className="h-10 bg-background border border-primary/10 rounded-lg flex items-center px-4 justify-between">
                 <span className="text-sm font-medium">TV Balcão 2</span>
                 <span className="w-2 h-2 rounded-full bg-green-500"></span>
               </div>
               <div className="h-10 bg-background border border-primary/10 rounded-lg flex items-center px-4 justify-between">
                 <span className="text-sm font-medium">TV Vitrine Externa</span>
                 <span className="w-2 h-2 rounded-full bg-yellow-500"></span>
               </div>
            </div>

            {/* Main Content Mockup */}
            <div className="flex-1">
              <div className="flex justify-between items-center mb-6">
                <h3 className="font-heading font-bold text-xl text-primary">Editando: TV Balcão 1</h3>
                <button className="bg-accent text-primary px-4 py-2 rounded-md text-sm font-bold flex items-center gap-2">
                  <Zap className="w-4 h-4" /> Publicar Agora
                </button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="aspect-video bg-textMain/5 rounded-lg border-2 border-dashed border-primary/20 flex items-center justify-center">
                  <span className="text-textMain/40 font-medium">+ Adicionar Vídeo</span>
                </div>
                <div className="bg-background border border-primary/10 rounded-lg p-4">
                   <div className="flex justify-between border-b border-primary/10 pb-2 mb-2">
                     <span className="font-medium text-sm">Picanha Premium</span>
                     <span className="font-bold text-accent text-sm">R$ 89,90</span>
                   </div>
                   <div className="flex justify-between border-b border-primary/10 pb-2 mb-2">
                     <span className="font-medium text-sm">Costela Bovina</span>
                     <span className="font-bold text-accent text-sm">R$ 45,90</span>
                   </div>
                   <div className="flex justify-between pb-2">
                     <span className="font-medium text-sm">Alcatra</span>
                     <span className="font-bold text-accent text-sm">R$ 52,90</span>
                   </div>
                </div>
              </div>
            </div>

          </div>

          {/* Floating Mobile Mockup */}
          <div className="absolute -right-4 md:-right-12 -bottom-12 w-32 md:w-48 bg-primary rounded-[2rem] border-4 border-primary p-2 shadow-2xl hidden sm:block transform rotate-6 hover:rotate-0 transition-transform duration-500">
             <div className="bg-background w-full h-64 md:h-80 rounded-[1.5rem] overflow-hidden relative">
                <div className="absolute top-0 w-full h-6 bg-primary flex justify-center">
                   <div className="w-12 h-3 bg-primary rounded-b-xl"></div>
                </div>
                <div className="p-4 pt-8">
                  <div className="font-heading font-bold text-primary mb-4 text-sm">TV Balcão 1</div>
                  <button className="w-full bg-accent text-primary py-2 rounded font-bold text-xs mb-2">Sincronizar ERP</button>
                  <button className="w-full border border-primary/20 text-primary py-2 rounded font-bold text-xs">Desligar Tela</button>
                </div>
             </div>
          </div>
        </div>

      </div>
    </section>
  );
};

export default DashboardPreview;
