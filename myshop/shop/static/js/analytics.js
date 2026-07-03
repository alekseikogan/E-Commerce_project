(function () {
  const trackUrl = document.body.dataset.analyticsTrackUrl;
  if (!trackUrl) {
    return;
  }

  const queue = [];
  const page = document.body.dataset.analyticsPage || window.location.pathname;

  function elementDescriptor(target) {
    if (!target) {
      return '';
    }
    const tag = target.tagName ? target.tagName.toLowerCase() : 'element';
    const id = target.id ? '#' + target.id : '';
    const classes = target.classList && target.classList.length
      ? '.' + Array.from(target.classList).slice(0, 3).join('.')
      : '';
    return tag + id + classes;
  }

  function sendPayload(payload) {
    const body = JSON.stringify(payload);

    fetch(trackUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'text/plain;charset=UTF-8',
      },
      body: body,
      keepalive: true,
      credentials: 'same-origin',
    }).catch(() => {});
  }

  function flush() {
    if (!queue.length) {
      return;
    }

    sendPayload({
      page: page,
      events: queue.splice(0, queue.length),
    });
  }

  function enqueueClick(event) {
    const target = event.target.closest(
      'a, button, input, select, textarea, summary, label, .button, .nav-link, .product-card, .product-card-title, .product-card-media'
    );
    if (!target) {
      return;
    }

    queue.push({
      path: window.location.pathname,
      page: page,
      element: elementDescriptor(target),
      text: (target.innerText || target.value || target.getAttribute('aria-label') || '')
        .trim()
        .slice(0, 200),
      href: target.href || '',
    });

    flush();
  }

  document.addEventListener('click', enqueueClick, true);
  window.addEventListener('pagehide', flush);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      flush();
    }
  });
})();
