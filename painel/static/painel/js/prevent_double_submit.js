/**
 * prevent_double_submit.js
 * 
 * Script global para prevenir que formulários sejam submetidos múltiplas vezes
 * se o usuário der duplo clique no botão de submit.
 * 
 * Ele escuta o evento 'submit' de todos os formulários e desabilita os botões 
 * de envio logo após a primeira submissão válida.
 */

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('form').forEach(function(form) {
        form.addEventListener('submit', function(e) {
            // Se o formulário tiver validação HTML5 nativa e falhar, o browser 
            // já barra antes do submit disparar. Mas se for chamado via JS,
            // podemos verificar:
            if (form.checkValidity && !form.checkValidity()) {
                return;
            }
            
            // Verifica se o form já foi submetido usando um dataset
            if (form.dataset.submitted === 'true') {
                e.preventDefault(); // Impede a segunda submissão
                return;
            }
            
            // Marca o formulário como submetido
            form.dataset.submitted = 'true';
            
            // Encontra todos os botões de submit e desabilita ou troca o texto
            const submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
            
            submitButtons.forEach(function(btn) {
                // Adiciona um pequeno delay para garantir que o valor do botão 
                // seja processado pelo form (alguns forms dependem do name=value do botão)
                setTimeout(() => {
                    // Impede novos cliques e deixa visualmente inativo
                    btn.classList.add('opacity-70', 'cursor-not-allowed');
                    
                    // Se for um botão HTML (<button>), podemos alterar o conteúdo para dar feedback
                    if (btn.tagName === 'BUTTON') {
                        // Salva o conteúdo original caso precise restaurar
                        if (!btn.dataset.originalContent) {
                            btn.dataset.originalContent = btn.innerHTML;
                        }
                        
                        // Opcional: Manter o ícone de spinner girando se estiver usando Phosphor Icons
                        // Usaremos uma classe genérica ou apenas o texto
                        const hasSpinner = btn.querySelector('.ph-spinner') !== null;
                        if (!hasSpinner) {
                            // Se o botão tem flex, podemos colocar o spinner do lado
                            btn.innerHTML = '<i class="ph-bold ph-spinner animate-spin text-lg"></i> Processando...';
                        }
                    }
                    
                    // Só desabilita totalmente no final
                    btn.disabled = true;
                }, 10);
            });
            
            // Se houver um atraso muito grande na rede, o usuário pode ficar preso se algo der erro
            // Opcionalmente poderíamos reativar o botão após 10 segundos, mas para formulários padrão 
            // a página vai recarregar antes disso, ou o backend retornará os erros (recarregando a página).
        });
    });
});
