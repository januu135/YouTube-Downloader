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

    // 2. Table download buttons (MP3 / Video) loading state
    const downloadLinks = document.querySelectorAll('.btn-table-download');
    downloadLinks.forEach(function (link) {
        link.addEventListener('click', function () {
            if (this.classList.contains('is-loading')) return;

            const self = this;
            const originalHTML = self.innerHTML;
            const href = self.getAttribute('href') || '';
            const isMp3 = href.includes('convert-mp3');

            let loadingMsg = isMp3 ? 'Converting MP3...' : 'Preparing File...';
            const lang = document.documentElement.lang || '';
            if (originalHTML.includes('Baixar')) {
                loadingMsg = isMp3 ? 'Convertendo MP3...' : 'Preparando...';
            } else if (originalHTML.includes('Télécharger')) {
                loadingMsg = isMp3 ? 'Conversion MP3...' : 'Préparation...';
            }

            self.classList.add('is-loading');
            self.innerHTML = '<span class="spinner-icon"></span> <span>' + loadingMsg + '</span>';

            // Reset after 8 seconds (browser download has already started)
            setTimeout(function () {
                self.classList.remove('is-loading');
                self.innerHTML = originalHTML;
            }, 8000);
        });
    });
});
