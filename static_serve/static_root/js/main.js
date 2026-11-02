document.addEventListener('DOMContentLoaded', function () {
    // 1. Search form submit preloader
    const searchForms = document.querySelectorAll('form.search-form, .search-form-container form');
    searchForms.forEach(function (form) {
        form.addEventListener('submit', function (e) {
            const btn = form.querySelector('.btn-download-action, button[type="submit"]');
            const wrapper = form.closest('.search-box-wrapper') || form.querySelector('.search-box-wrapper');
            const input = form.querySelector('input[type="text"]');

            if (!input || !input.value.trim()) {
                return;
            }

            if (btn && !btn.classList.contains('is-loading')) {
                btn.classList.add('is-loading');
                if (wrapper) wrapper.classList.add('is-loading');

                const currentText = (btn.innerText || '').toLowerCase();
                let loadingText = 'Fetching Video...';
                if (currentText.includes('baixar')) {
                    loadingText = 'Buscando Vídeo...';
                } else if (currentText.includes('télécharger')) {
                    loadingText = 'Recherche en cours...';
                } else if (currentText.includes('memuat') || currentText.includes('unduh')) {
                    loadingText = 'Memuat Video...';
                }

                btn.innerHTML = '<span class="spinner-icon"></span> <span>' + loadingText + '</span>';
            }
        });
    });

    // 2. Table download buttons (MP3 / Video) - Preloader without text, stays on page
    const downloadLinks = document.querySelectorAll('.btn-table-download');
    downloadLinks.forEach(function (link) {
        link.addEventListener('click', function (e) {
            if (this.classList.contains('is-loading')) {
                e.preventDefault();
                return;
            }

            const self = this;
            const originalHTML = self.innerHTML;
            const originalWidth = self.offsetWidth;

            self.classList.add('is-loading');
            if (originalWidth) {
                self.style.minWidth = originalWidth + 'px';
            }
            // Show only the spinning preloader without any text
            self.innerHTML = '<span class="spinner-icon spinner-only"></span>';

            // Reset back to original button text/icon after 7 seconds
            setTimeout(function () {
                self.classList.remove('is-loading');
                self.style.minWidth = '';
                self.innerHTML = originalHTML;
            }, 7000);
        });
    });
});
