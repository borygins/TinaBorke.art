(() => {
    const buttons = Array.from(document.querySelectorAll('.portfolio-photo'));
    const lightbox = document.getElementById('portfolioLightbox');
    if (!buttons.length || !lightbox) return;

    const image = lightbox.querySelector('.lightbox__image');
    const closeButton = lightbox.querySelector('.lightbox__close');
    const prevButton = lightbox.querySelector('.lightbox__nav--prev');
    const nextButton = lightbox.querySelector('.lightbox__nav--next');
    let index = 0;
    let touchStartX = 0;

    function show(nextIndex) {
        index = (nextIndex + buttons.length) % buttons.length;
        const item = buttons[index];
        image.src = item.dataset.full;
        image.alt = item.dataset.alt || '';
        lightbox.hidden = false;
        document.body.style.overflow = 'hidden';
    }

    function close() {
        lightbox.hidden = true;
        image.src = '';
        document.body.style.overflow = '';
    }

    buttons.forEach((button, buttonIndex) => {
        button.addEventListener('click', () => show(buttonIndex));
    });

    closeButton.addEventListener('click', close);
    prevButton.addEventListener('click', () => show(index - 1));
    nextButton.addEventListener('click', () => show(index + 1));

    lightbox.addEventListener('click', (event) => {
        if (event.target === lightbox) close();
    });

    document.addEventListener('keydown', (event) => {
        if (lightbox.hidden) return;
        if (event.key === 'Escape') close();
        if (event.key === 'ArrowLeft') show(index - 1);
        if (event.key === 'ArrowRight') show(index + 1);
    });

    lightbox.addEventListener('touchstart', (event) => {
        touchStartX = event.changedTouches[0].clientX;
    }, { passive: true });

    lightbox.addEventListener('touchend', (event) => {
        const delta = event.changedTouches[0].clientX - touchStartX;
        if (Math.abs(delta) < 40) return;
        show(delta > 0 ? index - 1 : index + 1);
    }, { passive: true });
})();
