(function () {
    'use strict';

    const container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);

    function showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = 'toast ' + type;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(function () {
            toast.classList.add('leaving');
            toast.addEventListener('animationend', function () {
                toast.remove();
            });
        }, duration);
    }

    window.showToast = showToast;
})();
