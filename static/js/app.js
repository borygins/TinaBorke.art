// DOM Elements
const burger = document.getElementById('burger');
const navList = document.querySelector('.nav-list');
const navLinks = document.querySelectorAll('.nav-link');
const header = document.getElementById('header');
const bookingForm = document.getElementById('bookingForm');
const quickBookingForm = document.getElementById('quickBookingForm');

// Маппинг услуг с английского на русский
const serviceMapping = {
    'wedding': 'Свадебный макияж',
    'event': 'Макияж для мероприятий',
    'photo': 'Макияж для фотосессии',
    'lesson': 'Уроки макияжа',
    'theater': 'Грим для театра и кино',
    'evening': 'Вечерний макияж',
    'business': 'Деловой макияж',
    'graduation': 'Выпускной макияж'
};

// Функция для преобразования услуги
function getServiceName(serviceKey) {
    return serviceMapping[serviceKey] || serviceKey || 'Не указана';
}

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initNavigation();
    initScrollEffects();
    initForms();
    initAnimations();
    initModals();
});

// Modal functionality
function initModals() {
    // Close modals when clicking backdrop
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal__backdrop')) {
            const modal = e.target.closest('.modal');
            if (modal) {
                closeModal(modal.id);
            }
        }
    });

    // Close modals with escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const openModal = document.querySelector('.modal:not(.hidden)');
            if (openModal) {
                closeModal(openModal.id);
            }
        }
    });

    // Close button functionality
    document.querySelectorAll('.modal__close').forEach(button => {
        button.addEventListener('click', function() {
            const modal = this.closest('.modal');
            if (modal) {
                closeModal(modal.id);
            }
        });
    });
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = 'auto';
    }
}

// Make closeModal available globally for onclick handlers
window.closeModal = closeModal;

// Navigation functionality
function initNavigation() {
    // Mobile menu toggle
    burger.addEventListener('click', toggleMobileMenu);

    // Handle navigation links
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();

            // Check if it's a modal link
            if (link.hasAttribute('data-page')) {
                const page = link.getAttribute('data-page');
                if (page === 'portfolio') {
                    openModal('portfolioModal');
                } else if (page === 'blog') {
                    openModal('blogModal');
                }
            } else {
                // Regular anchor link
                const targetId = link.getAttribute('href');
                const targetSection = document.querySelector(targetId);

                if (targetSection) {
                    targetSection.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }

            // Close mobile menu
            navList.classList.remove('active');
            burger.classList.remove('active');
        });
    });

    // Header scroll effect
    window.addEventListener('scroll', handleHeaderScroll);

    // Active link highlighting
    window.addEventListener('scroll', highlightActiveLink);
}

function toggleMobileMenu() {
    navList.classList.toggle('active');
    burger.classList.toggle('active');
}

function handleHeaderScroll() {
    if (window.scrollY > 100) {
        header.style.background = 'rgba(26, 26, 26, 0.98)';
        header.style.boxShadow = '0 2px 20px rgba(212, 175, 55, 0.1)';
    } else {
        header.style.background = 'rgba(26, 26, 26, 0.95)';
        header.style.boxShadow = 'none';
    }
}

function highlightActiveLink() {
    const sections = document.querySelectorAll('section[id]');
    const scrollPosition = window.scrollY + 150;

    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.offsetHeight;
        const sectionId = section.getAttribute('id');
        const correspondingLink = document.querySelector(`.nav-link[href="#${sectionId}"]`);

        if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
            navLinks.forEach(link => {
                if (!link.hasAttribute('data-page')) {
                    link.classList.remove('active');
                }
            });
            if (correspondingLink && !correspondingLink.hasAttribute('data-page')) {
                correspondingLink.classList.add('active');
            }
        }
    });
}

// Scroll effects and animations
function initScrollEffects() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(handleIntersection, observerOptions);

    // Observe elements for animation
    const animatedElements = document.querySelectorAll('.advantage, .service-card, .event-card, .review-card, .contact-block');
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'all 0.6s ease-out';
        observer.observe(el);
    });
}

function handleIntersection(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}

function initAnimations() {
    // Stagger animation for service cards
    const serviceCards = document.querySelectorAll('.service-card');
    serviceCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
    });

    // Stagger animation for contact blocks
    const contactBlocks = document.querySelectorAll('.contact-block');
    contactBlocks.forEach((block, index) => {
        block.style.animationDelay = `${index * 0.2}s`;
    });

    // Parallax effect for hero background
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const heroBackground = document.querySelector('.hero__bg');
        if (heroBackground) {
            heroBackground.style.transform = `translateY(${scrolled * 0.5}px)`;
        }
    });
}

// Form handling
function initForms() {
    if (bookingForm) {
        bookingForm.addEventListener('submit', handleBookingSubmit);
    }

    if (quickBookingForm) {
        quickBookingForm.addEventListener('submit', handleQuickBookingSubmit);
    }

    // Phone number formatting
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach(input => {
        input.addEventListener('input', formatPhoneNumber);
    });

    // Date input minimum date
    const dateInputs = document.querySelectorAll('input[type="date"]');
    const today = new Date().toISOString().split('T')[0];
    dateInputs.forEach(input => {
        input.setAttribute('min', today);
    });
}

async function handleBookingSubmit(e) {
    e.preventDefault();

    const formData = new FormData(bookingForm);
    const data = Object.fromEntries(formData);

    // Подготавливаем данные для отправки
    const requestData = {
        name: data.name.trim(),
        phone: data.phone.trim(),
        service: getServiceName(data.service),
        date: data.date || 'Не указана',
        message: data.message ? data.message.trim() : 'Не указано'
    };

    // Basic validation
    if (!requestData.name) {
        showNotification('Пожалуйста, укажите ваше имя', 'error');
        return;
    }

    if (!requestData.phone) {
        showNotification('Пожалуйста, укажите ваш телефон', 'error');
        return;
    }

    if (!isValidPhone(requestData.phone)) {
        showNotification('Пожалуйста, укажите корректный номер телефона', 'error');
        return;
    }

    // Добавляем состояние загрузки
    const submitButton = e.target.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.textContent = 'Отправка...';
    submitButton.disabled = true;

    try {
        // РЕАЛЬНАЯ ОТПРАВКА НА СЕРВЕР
        const response = await fetch('/api/booking', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showNotification('Заявка успешно отправлена! Я свяжусь с вами в ближайшее время.', 'success');
            bookingForm.reset();
            console.log('Booking created with ID:', result.booking_id);
        } else {
            throw new Error(result.message || 'Ошибка сервера');
        }

    } catch (error) {
        console.error('Error submitting booking:', error);
        showNotification('Ошибка при отправке заявки. Пожалуйста, попробуйте еще раз.', 'error');
    } finally {
        // Восстанавливаем кнопку
        submitButton.textContent = originalText;
        submitButton.disabled = false;
    }
}

async function handleQuickBookingSubmit(e) {
    e.preventDefault();

    const formData = new FormData(quickBookingForm);
    const data = Object.fromEntries(formData);

    // Подготавливаем данные для быстрой заявки
    const requestData = {
        name: data.name.trim(),
        phone: data.phone.trim(),
        service: getServiceName(data.service),
        date: data.date || 'Не указана',
        message: data.message ? data.message.trim() : 'Не указано'
    };

    // Basic validation
    if (!requestData.name.trim() || !requestData.phone.trim()) {
        showNotification('Пожалуйста, заполните обязательные поля', 'error');
        return;
    }

    if (!isValidPhone(requestData.phone)) {
        showNotification('Пожалуйста, укажите корректный номер телефона', 'error');
        return;
    }

    // Добавляем состояние загрузки
    const submitButton = e.target.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.textContent = 'Отправка...';
    submitButton.disabled = true;

    try {
        // РЕАЛЬНАЯ ОТПРАВКА НА СЕРВЕР
        const response = await fetch('/api/quick-booking', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showNotification('Быстрая заявка отправлена! Скоро свяжусь с вами.', 'success');
            quickBookingForm.reset();
            console.log('Quick booking created with ID:', result.booking_id);
        } else {
            throw new Error(result.message || 'Ошибка сервера');
        }

    } catch (error) {
        console.error('Error submitting quick booking:', error);
        showNotification('Ошибка при отправке заявки. Пожалуйста, попробуйте еще раз.', 'error');
    } finally {
        // Восстанавливаем кнопку
        submitButton.textContent = originalText;
        submitButton.disabled = false;
    }
}

function formatPhoneNumber(e) {
    let value = e.target.value.replace(/\D/g, '');

    // Russian phone number format
    if (value.startsWith('8')) {
        value = '7' + value.slice(1);
    }

    if (value.startsWith('7') && value.length <= 11) {
        const formatted = value.replace(/^7(\d{3})(\d{3})(\d{2})(\d{2})$/, '+7 ($1) $2-$3-$4');
        if (formatted.includes('(') && formatted.includes(')')) {
            e.target.value = formatted;
        } else {
            e.target.value = '+7 ' + value.slice(1);
        }
    } else if (value.length <= 10) {
        e.target.value = value;
    }
}

function isValidPhone(phone) {
    const cleanPhone = phone.replace(/\D/g, '');
    return cleanPhone.length >= 10 && cleanPhone.length <= 11;
}

function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => notification.remove());

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification--${type}`;
    notification.innerHTML = `
        <div class="notification__content">
            <span class="notification__message">${message}</span>
            <button class="notification__close">&times;</button>
        </div>
    `;

    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#2196F3'};
        color: white;
        padding: 16px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 10000;
        max-width: 400px;
        animation: slideInRight 0.3s ease-out;
        font-family: var(--font-family-base);
        font-size: 14px;
    `;

    // Add animation styles
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOutRight {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        .notification__content {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        }
        .notification__close {
            background: none;
            border: none;
            color: white;
            font-size: 18px;
            cursor: pointer;
            padding: 0;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .notification__close:hover {
            opacity: 0.7;
        }
    `;
    document.head.appendChild(style);

    document.body.appendChild(notification);

    // Close button functionality
    const closeBtn = notification.querySelector('.notification__close');
    closeBtn.addEventListener('click', () => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    });

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }
    }, 5000);
}

// Service card hover effects
function initServiceCardEffects() {
    const serviceCards = document.querySelectorAll('.service-card');

    serviceCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-8px) scale(1.02)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
}

// Contact block hover effects
function initContactBlockEffects() {
    const contactBlocks = document.querySelectorAll('.contact-block');

    contactBlocks.forEach(block => {
        block.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-6px) scale(1.02)';
        });

        block.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
}

// Smooth reveal animations
function initRevealAnimations() {
    const revealElements = document.querySelectorAll('.hero__content, .about__content, .services__title, .events__title, .reviews__title, .contacts__title, .booking__content');

    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    });

    revealElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(50px)';
        el.style.transition = 'all 0.8s ease-out';
        revealObserver.observe(el);
    });
}

// Initialize additional effects after DOM load
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        initServiceCardEffects();
        initContactBlockEffects();
        initRevealAnimations();
    }, 100);
});

// Handle window resize
window.addEventListener('resize', function() {
    // Close mobile menu on resize
    if (window.innerWidth > 768) {
        navList.classList.remove('active');
        burger.classList.remove('active');
    }
});

// Prevent form submission on enter in text inputs (except textarea)
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && e.target.tagName === 'INPUT' && e.target.type !== 'submit') {
        e.preventDefault();
    }
});

// Add scroll-to-top functionality
function addScrollToTop() {
    const scrollToTopBtn = document.createElement('button');
    scrollToTopBtn.innerHTML = '↑';
    scrollToTopBtn.className = 'scroll-to-top';
    scrollToTopBtn.style.cssText = `
        position: fixed;
        bottom: 30px;
        right: 30px;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background: linear-gradient(45deg, #D4AF37, #E8B4A0);
        color: #1a1a1a;
        border: none;
        font-size: 20px;
        font-weight: bold;
        cursor: pointer;
        z-index: 1000;
        opacity: 0;
        visibility: hidden;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(212, 175, 55, 0.3);
    `;

    document.body.appendChild(scrollToTopBtn);

    // Show/hide based on scroll position
    window.addEventListener('scroll', () => {
        if (window.scrollY > 500) {
            scrollToTopBtn.style.opacity = '1';
            scrollToTopBtn.style.visibility = 'visible';
        } else {
            scrollToTopBtn.style.opacity = '0';
            scrollToTopBtn.style.visibility = 'hidden';
        }
    });

    // Scroll to top on click
    scrollToTopBtn.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

// Phone number click tracking
function initPhoneTracking() {
    const phoneLinks = document.querySelectorAll('a[href^="tel:"]');
    phoneLinks.forEach(link => {
        link.addEventListener('click', function() {
            console.log('Phone number clicked:', this.href);
            // Here you could add analytics tracking
        });
    });
}

// Telegram link tracking
function initTelegramTracking() {
    const telegramLinks = document.querySelectorAll('a[href*="t.me"]');
    telegramLinks.forEach(link => {
        link.addEventListener('click', function() {
            console.log('Telegram link clicked:', this.href);
            // Here you could add analytics tracking
        });
    });
}

// Initialize scroll-to-top and tracking after page load
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        addScrollToTop();
        initPhoneTracking();
        initTelegramTracking();
    }, 1000);
});

// Add contact animation effects
function initContactAnimations() {
    const contactBlocks = document.querySelectorAll('.contact-block');

    contactBlocks.forEach((block, index) => {
        block.style.animationDelay = `${index * 0.1}s`;

        // Add special hover effect for phone block
        if (block.querySelector('a[href^="tel:"]')) {
            block.addEventListener('mouseenter', function() {
                const icon = this.querySelector('.contact-block__icon');
                if (icon) {
                    icon.style.transform = 'scale(1.2) rotate(10deg)';
                    icon.style.transition = 'transform 0.3s ease';
                }
            });

            block.addEventListener('mouseleave', function() {
                const icon = this.querySelector('.contact-block__icon');
                if (icon) {
                    icon.style.transform = 'scale(1) rotate(0deg)';
                }
            });
        }

        // Add special hover effect for Telegram block
        if (block.querySelector('a[href*="t.me"]')) {
            block.addEventListener('mouseenter', function() {
                const icon = this.querySelector('.contact-block__icon');
                if (icon) {
                    icon.style.transform = 'scale(1.2)';
                    icon.style.transition = 'transform 0.3s ease';
                }
            });

            block.addEventListener('mouseleave', function() {
                const icon = this.querySelector('.contact-block__icon');
                if (icon) {
                    icon.style.transform = 'scale(1)';
                }
            });
        }
    });
}

// Initialize contact animations
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(initContactAnimations, 500);
});

// External links tracking for cloud and avito
function initExternalLinksTracking() {
    // Track cloud portfolio link clicks
    const cloudLinks = document.querySelectorAll('a[href*="cloud.mail.ru"]');
    cloudLinks.forEach(link => {
        link.addEventListener('click', function() {
            console.log('Portfolio cloud link clicked:', this.href);
            // Here you could add analytics tracking
        });
    });

    // Track Avito link clicks
    const avitoLinks = document.querySelectorAll('a[href*="avito.ru"]');
    avitoLinks.forEach(link => {
        link.addEventListener('click', function() {
            console.log('Avito profile link clicked:', this.href);
            // Here you could add analytics tracking
        });
    });
}

// Initialize external links tracking
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(initExternalLinksTracking, 1000);
});