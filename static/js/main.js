/**
 * JavaScript principal da aplicação Vida Arroz
 */

// Aguarda o carregamento completo do DOM
document.addEventListener('DOMContentLoaded', function() {
    initMobileMenu();
    initSmoothScroll();
    initAnimations();
    initCicloVidaAnimation();
    initFaleConoscoModal();
    initWhatsAppModal();
    initContatoForm();
    initPhoneMasks();
});

/**
 * Máscara de telefone: (00) 00000-0000 ou (00) 0000-0000
 */
function initPhoneMasks() {
    function formatPhone(value) {
        var digits = (value || '').replace(/\D/g, '').slice(0, 11);
        if (digits.length <= 2) {
            return digits ? '(' + digits : '';
        }
        if (digits.length <= 7) {
            return '(' + digits.slice(0, 2) + ') ' + digits.slice(2);
        }
        return '(' + digits.slice(0, 2) + ') ' + digits.slice(2, 7) + '-' + digits.slice(7, 11);
    }
    function applyMask(e) {
        var el = e.target;
        var start = el.selectionStart;
        var end = el.selectionEnd;
        var oldLen = el.value.length;
        var newVal = formatPhone(el.value);
        el.value = newVal;
        var newLen = newVal.length;
        var diff = newLen - oldLen;
        var newStart = Math.max(0, start + diff);
        var newEnd = Math.max(0, end + diff);
        el.setSelectionRange(newStart, newEnd);
    }
    document.querySelectorAll('input[type="tel"]').forEach(function(input) {
        input.addEventListener('input', applyMask);
        input.addEventListener('paste', function(e) {
            e.preventDefault();
            var pasted = (e.clipboardData || window.clipboardData).getData('text');
            var digits = pasted.replace(/\D/g, '');
            input.value = formatPhone(digits);
        });
        if (input.value) input.value = formatPhone(input.value);
    });
}

/**
 * Inicializa o menu mobile
 */
function initMobileMenu() {
    const toggle = document.querySelector('.mobile-menu-toggle');
    const menu = document.querySelector('.nav-menu');
    
    if (toggle && menu) {
        toggle.addEventListener('click', function() {
            const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
            toggle.setAttribute('aria-expanded', !isExpanded);
            menu.classList.toggle('active');
            
            // Anima as barras do hamburger
            const spans = toggle.querySelectorAll('span');
            if (!isExpanded) {
                spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
                spans[1].style.opacity = '0';
                spans[2].style.transform = 'rotate(-45deg) translate(7px, -6px)';
            } else {
                spans[0].style.transform = 'none';
                spans[1].style.opacity = '1';
                spans[2].style.transform = 'none';
            }
        });
        
        // Fecha o menu ao clicar em um link (exceto dropdown toggle)
        const navLinks = menu.querySelectorAll('a:not(.dropdown-toggle)');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                menu.classList.remove('active');
                toggle.setAttribute('aria-expanded', 'false');
                const spans = toggle.querySelectorAll('span');
                spans[0].style.transform = 'none';
                spans[1].style.opacity = '1';
                spans[2].style.transform = 'none';
                // Fecha dropdown se estiver aberto
                const dropdown = menu.querySelector('.dropdown.active');
                if (dropdown) {
                    dropdown.classList.remove('active');
                }
            });
        });
        
        // Toggle dropdown no mobile
        const dropdownToggle = menu.querySelector('.dropdown-toggle');
        const dropdown = menu.querySelector('.dropdown');
        if (dropdownToggle && dropdown) {
            dropdownToggle.addEventListener('click', function(e) {
                e.preventDefault();
                dropdown.classList.toggle('active');
            });
        }
    }
}

/**
 * Modal Fale Conosco: abre ao clicar no CTA e fecha com botão/backdrop/ESC
 */
function initFaleConoscoModal() {
    const modal = document.getElementById('modal-fale-conosco');
    const backdrop = document.getElementById('modal-fale-conosco-backdrop');
    const btnClose = document.getElementById('modal-fale-conosco-close');
    const btnCancel = document.getElementById('modal-fale-conosco-cancel');
    const form = document.getElementById('form-fale-conosco');

    if (!modal) return;

    function openModal() {
        modal.classList.remove('hidden');
        modal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        document.getElementById('fale-nome')?.focus();
    }

    function closeModal() {
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
    }

    document.querySelectorAll('.js-open-fale-conosco').forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            openModal();
        });
    });

    if (backdrop) backdrop.addEventListener('click', closeModal);
    if (btnClose) btnClose.addEventListener('click', closeModal);
    if (btnCancel) btnCancel.addEventListener('click', closeModal);

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
            closeModal();
        }
    });

    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            var submitBtn = form.querySelector('button[type="submit"]');
            var originalText = submitBtn ? submitBtn.textContent : '';
            if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Enviando...'; }
            var payload = {
                nome: document.getElementById('fale-nome').value.trim(),
                telefone: document.getElementById('fale-telefone').value.trim(),
                email: document.getElementById('fale-email').value.trim(),
                mensagem: '',
                origem: 'produtos'
            };
            fetch('/api/leads', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(function(res) { return res.json().then(function(data) { return { ok: res.ok, data: data }; }); })
            .then(function(result) {
                if (result.ok && result.data.ok) {
                    form.reset();
                    closeModal();
                    alert('Mensagem recebida! Entraremos em contato em breve.');
                } else {
                    alert(result.data.error || 'Não foi possível enviar. Tente novamente.');
                }
            })
            .catch(function() { alert('Erro ao enviar. Tente novamente.'); })
            .finally(function() {
                if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = originalText; }
            });
        });
    }
}

/**
 * Inicializa scroll suave para âncoras
 */
function initSmoothScroll() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#' && href.length > 1) {
                const target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    const headerOffset = 80;
                    const elementPosition = target.getBoundingClientRect().top;
                    const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
                    
                    window.scrollTo({
                        top: offsetPosition,
                        behavior: 'smooth'
                    });
                }
            }
        });
    });
}

/**
 * Inicializa animações de entrada (Intersection Observer)
 */
function initAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0) scale(1)';
            }
        });
    }, observerOptions);

    // Elementos da home e gerais
    const animatedElements = document.querySelectorAll('.produto-card, .diferencial-item, .institucional-content');
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });

    // Internas de produto: bloco de texto
    const productContent = document.querySelector('.product-content');
    if (productContent) {
        productContent.style.opacity = '0';
        productContent.style.transform = 'translateY(24px)';
        productContent.style.transition = 'opacity 0.65s ease 0.05s, transform 0.65s ease 0.05s';
        observer.observe(productContent);
    }

    // Internas de produto: imagem
    const productImageWrap = document.querySelector('.product-image-wrap');
    if (productImageWrap) {
        productImageWrap.style.opacity = '0';
        productImageWrap.style.transform = 'translateY(28px) scale(0.98)';
        productImageWrap.style.transition = 'opacity 0.7s ease 0.15s, transform 0.7s ease 0.15s';
        observer.observe(productImageWrap);
    }

    // Título "Diferenciais" nas internas
    const productDiferenciaisSection = document.querySelector('.diferenciais-section .section-title');
    if (productDiferenciaisSection && document.querySelector('.product-diferenciais-grid')) {
        productDiferenciaisSection.style.opacity = '0';
        productDiferenciaisSection.style.transform = 'translateY(16px)';
        productDiferenciaisSection.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        observer.observe(productDiferenciaisSection);
    }

    // Cards das internas: delay escalonado para entrada em sequência
    const productCards = document.querySelectorAll('.product-diferenciais-grid .diferencial-item');
    productCards.forEach(function(card, index) {
        card.style.transitionDelay = (0.08 * index) + 's';
    });
}

/**
 * Animação da seção "O Ciclo de Vida do Arroz": ao rolar, ativa cards e setas
 */
function initCicloVidaAnimation() {
    const section = document.querySelector('.ciclo-vida-section');
    if (!section) return;

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                section.classList.add('is-visible');
            }
        });
    }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });

    observer.observe(section);
}

/**
 * Formulário da página Contato: envia para /api/leads com origem "contato"
 */
function initContatoForm() {
    var form = document.getElementById('form-contato');
    if (!form) return;
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        var submitBtn = form.querySelector('button[type="submit"]');
        var originalText = submitBtn ? submitBtn.textContent : '';
        if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Enviando...'; }
        var payload = {
            nome: (document.getElementById('contato-nome') && document.getElementById('contato-nome').value) ? document.getElementById('contato-nome').value.trim() : '',
            telefone: (document.getElementById('contato-telefone') && document.getElementById('contato-telefone').value) ? document.getElementById('contato-telefone').value.trim() : '',
            email: (document.getElementById('contato-email') && document.getElementById('contato-email').value) ? document.getElementById('contato-email').value.trim() : '',
            mensagem: (document.getElementById('contato-mensagem') && document.getElementById('contato-mensagem').value) ? document.getElementById('contato-mensagem').value.trim() : '',
            origem: 'contato'
        };
        fetch('/api/leads', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(function(res) { return res.json().then(function(data) { return { ok: res.ok, data: data }; }); })
        .then(function(result) {
            if (result.ok && result.data.ok) {
                form.reset();
                alert('Mensagem enviada! Entraremos em contato em breve.');
            } else {
                alert(result.data.error || 'Não foi possível enviar. Tente novamente.');
            }
        })
        .catch(function() { alert('Erro ao enviar. Tente novamente.'); })
        .finally(function() {
            if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = originalText; }
        });
    });
}

/**
 * Botão flutuante WhatsApp: abre modal de conversão (estilo WhatsApp)
 */
function initWhatsAppModal() {
    const modal = document.getElementById('modal-whatsapp');
    const backdrop = document.getElementById('modal-whatsapp-backdrop');
    const btnOpen = document.getElementById('btn-whatsapp-float');
    const btnClose = document.getElementById('modal-whatsapp-close');
    const form = document.getElementById('form-whatsapp');

    if (!modal || !btnOpen) return;

    function openModal() {
        modal.classList.remove('hidden');
        modal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        document.getElementById('wa-nome')?.focus();
    }

    function closeModal() {
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
    }

    btnOpen.addEventListener('click', openModal);
    if (backdrop) backdrop.addEventListener('click', closeModal);
    if (btnClose) btnClose.addEventListener('click', closeModal);

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
            closeModal();
        }
    });

    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            var submitBtn = form.querySelector('button[type="submit"]');
            var originalText = submitBtn ? submitBtn.textContent : '';
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Enviando...';
            }
            var formData = new FormData(form);
            var payload = {
                nome: formData.get('nome'),
                telefone: formData.get('telefone'),
                email: formData.get('email'),
                mensagem: formData.get('mensagem') || '',
                origem: formData.get('origem') || 'whatsapp'
            };
            fetch('/api/leads', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(function(res) { return res.json().then(function(data) { return { ok: res.ok, data: data }; }); })
            .then(function(result) {
                if (result.ok && result.data.ok) {
                    form.reset();
                    closeModal();
                    alert('Mensagem enviada! Entraremos em contato em breve pelo WhatsApp.');
                } else {
                    alert(result.data.error || 'Não foi possível enviar. Tente novamente.');
                }
            })
            .catch(function() {
                alert('Erro ao enviar. Verifique sua conexão e tente novamente.');
            })
            .finally(function() {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                }
            });
        });
    }
}

/**
 * Função utilitária para fazer requisições AJAX
 */
async function fetchData(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Erro ao buscar dados:', error);
        throw error;
    }
}
