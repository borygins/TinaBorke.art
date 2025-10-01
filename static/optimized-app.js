// Оптимизированный JavaScript с исправлениями для мобильных устройств
class MobileOptimizedApp {
  constructor() {
    this.burger = null;
    this.navList = null;
    this.navLinks = [];
    this.header = null;
    this.isMenuOpen = false;
    this.touchStartY = 0;
    this.touchStartX = 0;
    
    this.init();
  }

  init() {
    document.addEventListener('DOMContentLoaded', () => {
      this.initElements();
      this.initNavigation();
      this.initScrollEffects();
      this.initForms();
      this.initAnimations();
      this.initModals();
      this.initTouchHandlers();
      this.fixViewport();
    });
  }

  initElements() {
    this.burger = document.getElementById('burger') || document.querySelector('.header__burger');
    this.navList = document.querySelector('.nav-list') || document.querySelector('.header__nav');
    this.navLinks = document.querySelectorAll('.nav-link');
    this.header = document.getElementById('header') || document.querySelector('.header');
    
    // Создаем элементы если их нет
    if (!this.burger) {
      console.warn('Burger menu element not found');
    }
  }

  initNavigation() {
    // Улучшенная обработка гамбургер меню
    if (this.burger) {
      // Удаляем старые обработчики
      this.burger.removeEventListener('click', this.toggleMobileMenu);
      this.burger.removeEventListener('touchstart', this.handleTouchStart);
      
      // Добавляем новые обработчики с правильным контекстом
      this.burger.addEventListener('click', (e) => this.toggleMobileMenu(e));
      this.burger.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: true });
      
      // iOS Safari fix
      this.burger.style.webkitTapHighlightColor = 'transparent';
      this.burger.style.webkitTouchCallout = 'none';
      this.burger.style.webkitUserSelect = 'none';
      this.burger.style.userSelect = 'none';
    }

    // Обработка навигационных ссылок
    this.navLinks.forEach(link => {
      link.addEventListener('click', (e) => this.handleNavClick(e, link));
      
      // Touch improvements for iOS
      link.style.webkitTapHighlightColor = 'rgba(212, 175, 55, 0.2)';
    });

    // Закрытие меню при клике вне его
    document.addEventListener('click', (e) => this.handleDocumentClick(e));
    
    // Закрытие меню при нажатии Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isMenuOpen) {
        this.closeMobileMenu();
      }
    });

    // Обработка изменения размера окна
    window.addEventListener('resize', () => this.handleResize());
    
    // Scroll effects
    window.addEventListener('scroll', () => this.handleHeaderScroll(), { passive: true });
    window.addEventListener('scroll', () => this.highlightActiveLink(), { passive: true });
  }

  toggleMobileMenu(e) {
    e.preventDefault();
    e.stopPropagation();
    
    console.log('Toggle mobile menu called', this.isMenuOpen);
    
    if (this.isMenuOpen) {
      this.closeMobileMenu();
    } else {
      this.openMobileMenu();
    }
  }

  openMobileMenu() {
    console.log('Opening mobile menu');
    
    this.isMenuOpen = true;
    
    if (this.burger) {
      this.burger.classList.add('active');
      this.burger.setAttribute('aria-expanded', 'true');
    }
    
    if (this.navList) {
      this.navList.classList.add('active');
    }
    
    // Предотвращаем скролл body
    document.body.style.overflow = 'hidden';
    document.body.style.position = 'fixed';
    document.body.style.width = '100%';
    
    // Focus management
    setTimeout(() => {
      const firstLink = this.navList?.querySelector('.nav-link');
      if (firstLink) {
        firstLink.focus();
      }
    }, 300);
  }

  closeMobileMenu() {
    console.log('Closing mobile menu');
    
    this.isMenuOpen = false;
    
    if (this.burger) {
      this.burger.classList.remove('active');
      this.burger.setAttribute('aria-expanded', 'false');
    }
    
    if (this.navList) {
      this.navList.classList.remove('active');
    }
    
    // Восстанавливаем скролл body
    document.body.style.overflow = '';
    document.body.style.position = '';
    document.body.style.width = '';
  }

  handleNavClick(e, link) {
    // Проверяем модальные ссылки
    if (link.hasAttribute('data-page')) {
      e.preventDefault();
      const page = link.getAttribute('data-page');
      
      if (page === 'portfolio') {
        this.openModal('portfolioModal');
      } else if (page === 'blog') {
        this.openModal('blogModal');
      }
      
      this.closeMobileMenu();
      return;
    }

    // Обычные якорные ссылки
    const targetId = link.getAttribute('href');
    if (targetId && targetId.startsWith('#')) {
      e.preventDefault();
      
      const targetSection = document.querySelector(targetId);
      if (targetSection) {
        // Закрываем меню перед скроллом
        this.closeMobileMenu();
        
        // Скролл с задержкой для закрытия меню
        setTimeout(() => {
          const headerHeight = this.header?.offsetHeight || 80;
          const targetTop = targetSection.offsetTop - headerHeight - 20;
          
          window.scrollTo({
            top: targetTop,
            behavior: 'smooth'
          });
        }, 250);
      }
    }
  }

  handleDocumentClick(e) {
    if (!this.isMenuOpen) return;
    
    // Проверяем, был ли клик вне меню и кнопки
    const isClickInsideNav = this.navList?.contains(e.target);
    const isClickOnBurger = this.burger?.contains(e.target);
    
    if (!isClickInsideNav && !isClickOnBurger) {
      this.closeMobileMenu();
    }
  }

  handleResize() {
    // Закрываем мобильное меню при изменении размера на десктоп
    if (window.innerWidth > 768 && this.isMenuOpen) {
      this.closeMobileMenu();
    }
  }

  handleHeaderScroll() {
    if (!this.header) return;
    
    const scrollY = window.scrollY;
    
    if (scrollY > 100) {
      this.header.style.background = 'rgba(20, 20, 20, 0.98)';
      this.header.style.backdropFilter = 'blur(20px)';
      this.header.style.boxShadow = '0 2px 20px rgba(212, 175, 55, 0.1)';
    } else {
      this.header.style.background = 'rgba(20, 20, 20, 0.95)';
      this.header.style.backdropFilter = 'blur(10px)';
      this.header.style.boxShadow = 'none';
    }
  }

  highlightActiveLink() {
    const sections = document.querySelectorAll('section[id]');
    const scrollPosition = window.scrollY + 150;

    sections.forEach(section => {
      const sectionTop = section.offsetTop;
      const sectionHeight = section.offsetHeight;
      const sectionId = section.getAttribute('id');
      const correspondingLink = document.querySelector(`.nav-link[href="#${sectionId}"]`);

      if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
        // Remove active class from all nav links
        this.navLinks.forEach(link => {
          if (!link.hasAttribute('data-page')) {
            link.classList.remove('active');
          }
        });
        
        // Add active class to current link
        if (correspondingLink && !correspondingLink.hasAttribute('data-page')) {
          correspondingLink.classList.add('active');
        }
      }
    });
  }

  initTouchHandlers() {
    // Улучшенная обработка touch событий
    if (this.navList) {
      this.navList.addEventListener('touchstart', (e) => {
        this.touchStartY = e.touches[0].clientY;
        this.touchStartX = e.touches[0].clientX;
      }, { passive: true });

      this.navList.addEventListener('touchmove', (e) => {
        if (!this.isMenuOpen) return;
        
        const touchY = e.touches[0].clientY;
        const touchX = e.touches[0].clientX;
        const deltaY = touchY - this.touchStartY;
        const deltaX = touchX - this.touchStartX;
        
        // Закрываем меню при свайпе влево
        if (deltaX < -100 && Math.abs(deltaX) > Math.abs(deltaY)) {
          this.closeMobileMenu();
        }
      }, { passive: true });
    }
  }

  fixViewport() {
    // Исправления для мобильных устройств
    const viewport = document.querySelector('meta[name=viewport]');
    if (!viewport) {
      const meta = document.createElement('meta');
      meta.name = 'viewport';
      meta.content = 'width=device-width, initial-scale=1.0, user-scalable=no, viewport-fit=cover';
      document.head.appendChild(meta);
    }
    
    // iOS Safari fix для 100vh
    const setVH = () => {
      const vh = window.innerHeight * 0.01;
      document.documentElement.style.setProperty('--vh', `${vh}px`);
    };
    
    setVH();
    window.addEventListener('resize', setVH);
    window.addEventListener('orientationchange', () => {
      setTimeout(setVH, 100);
    });
  }

  // Modal functionality
  initModals() {
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('modal__backdrop')) {
        const modal = e.target.closest('.modal');
        if (modal) {
          this.closeModal(modal.id);
        }
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const openModal = document.querySelector('.modal:not(.hidden)');
        if (openModal) {
          this.closeModal(openModal.id);
        }
      }
    });

    document.querySelectorAll('.modal__close').forEach(button => {
      button.addEventListener('click', () => {
        const modal = button.closest('.modal');
        if (modal) {
          this.closeModal(modal.id);
        }
      });
    });
  }

  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
      
      // Focus management
      const closeButton = modal.querySelector('.modal__close');
      if (closeButton) {
        closeButton.focus();
      }
    }
  }

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('hidden');
      document.body.style.overflow = '';
    }
  }

  // Scroll effects and animations
  initScrollEffects() {
    const observerOptions = {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }
      });
    }, observerOptions);

    const animatedElements = document.querySelectorAll('.advantage, .service-card, .event-card, .review-card, .contact-block');
    animatedElements.forEach(el => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(30px)';
      el.style.transition = 'all 0.6s ease-out';
      observer.observe(el);
    });
  }

  initAnimations() {
    // Parallax effect для hero
    window.addEventListener('scroll', () => {
      const scrolled = window.pageYOffset;
      const heroBackground = document.querySelector('.hero__bg');
      if (heroBackground) {
        heroBackground.style.transform = `translateY(${scrolled * 0.5}px)`;
      }
    }, { passive: true });
  }

  // Form handling
  initForms() {
    const bookingForm = document.getElementById('bookingForm');
    const quickBookingForm = document.getElementById('quickBookingForm');

    if (bookingForm) {
      bookingForm.addEventListener('submit', (e) => this.handleBookingSubmit(e, bookingForm));
    }

    if (quickBookingForm) {
      quickBookingForm.addEventListener('submit', (e) => this.handleQuickBookingSubmit(e, quickBookingForm));
    }

    // Phone number formatting
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach(input => {
      input.addEventListener('input', this.formatPhoneNumber);
      
      // Mobile keyboard optimization
      input.setAttribute('inputmode', 'tel');
    });

    // Date input optimization
    const dateInputs = document.querySelectorAll('input[type="date"]');
    const today = new Date().toISOString().split('T')[0];
    dateInputs.forEach(input => {
      input.setAttribute('min', today);
    });
  }

  async handleBookingSubmit(e, form) {
    e.preventDefault();
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    // Validation
    if (!data.name?.trim()) {
      this.showNotification('Пожалуйста, укажите ваше имя', 'error');
      return;
    }
    
    if (!data.phone?.trim()) {
      this.showNotification('Пожалуйста, укажите ваш телефон', 'error');
      return;
    }
    
    if (!this.isValidPhone(data.phone)) {
      this.showNotification('Пожалуйста, укажите корректный номер телефона', 'error');
      return;
    }
    
    try {
      // Отправляем данные на сервер
      const response = await fetch('/api/booking', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
      });
      
      if (response.ok) {
        this.showNotification('Заявка отправлена! Я свяжусь с вами в ближайшее время.', 'success');
        form.reset();
      } else {
        throw new Error('Ошибка сервера');
      }
    } catch (error) {
      this.showNotification('Произошла ошибка при отправке заявки. Попробуйте еще раз.', 'error');
      console.error('Booking error:', error);
    }
  }

  async handleQuickBookingSubmit(e, form) {
    e.preventDefault();
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    if (!data.name?.trim() || !data.phone?.trim()) {
      this.showNotification('Пожалуйста, заполните обязательные поля', 'error');
      return;
    }
    
    if (!this.isValidPhone(data.phone)) {
      this.showNotification('Пожалуйста, укажите корректный номер телефона', 'error');
      return;
    }
    
    try {
      const response = await fetch('/api/quick-booking', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
      });
      
      if (response.ok) {
        this.showNotification('Быстрая заявка отправлена! Скоро свяжусь с вами.', 'success');
        form.reset();
      } else {
        throw new Error('Ошибка сервера');
      }
    } catch (error) {
      this.showNotification('Произошла ошибка при отправке заявки. Попробуйте еще раз.', 'error');
      console.error('Quick booking error:', error);
    }
  }

  formatPhoneNumber(e) {
    let value = e.target.value.replace(/\D/g, '');
    
    if (value.startsWith('8')) {
      value = '7' + value.slice(1);
    }
    
    if (value.startsWith('7') && value.length <= 11) {
      const formatted = value.replace(/^7(\d{3})(\d{3})(\d{2})(\d{2})$/, '+7 ($1) $2-$3-$4');
      if (formatted.includes('(')) {
        e.target.value = formatted;
      } else {
        e.target.value = '+7 ' + value.slice(1);
      }
    } else if (value.length <= 10) {
      e.target.value = value;
    }
  }

  isValidPhone(phone) {
    const cleanPhone = phone.replace(/\D/g, '');
    return cleanPhone.length >= 10 && cleanPhone.length <= 11;
  }

  showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => notification.remove());

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification--${type}`;
    notification.innerHTML = `
      <div class="notification__content">
        ${message}
      </div>
      <button class="notification__close" onclick="this.parentElement.remove()">×</button>
    `;

    document.body.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
      if (notification.parentElement) {
        notification.remove();
      }
    }, 5000);
  }
}

// Initialize the app
const app = new MobileOptimizedApp();

// Make some methods available globally for compatibility
window.closeModal = (modalId) => app.closeModal(modalId);
window.openModal = (modalId) => app.openModal(modalId);