(function () {
  const trackUrl = document.body.dataset.analyticsTrackUrl;
  if (!trackUrl) {
    return;
  }

  const queue = [];
  let flushTimer = null;
  const page = document.body.dataset.analyticsPage || window.location.pathname;

  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) {
      return meta.content;
    }
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

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

  function flush() {
    if (flushTimer) {
      window.clearTimeout(flushTimer);
      flushTimer = null;
    }
    if (!queue.length) {
      return;
    }

    const payload = {
      page: page,
      events: queue.splice(0, queue.length),
    };

    const csrfToken = getCsrfToken();
    fetch(trackUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify(payload),
      keepalive: true,
      credentials: 'same-origin',
    }).catch(() => {});
  }

  function scheduleFlush(immediate) {
    if (immediate) {
      flush();
      return;
    }
    if (!flushTimer) {
      flushTimer = window.setTimeout(flush, 300);
    }
  }

  function enqueueClick(event) {
    const target = event.target.closest(
      'a, button, input[type="submit"], .button, .nav-link, .product-card, summary'
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

    const navigates = target.tagName === 'A' && Boolean(target.href);
    const submits = target.tagName === 'BUTTON'
      || target.tagName === 'INPUT'
      || target.type === 'submit';

    if (navigates || submits || queue.length >= 10) {
      scheduleFlush(true);
    } else {
      scheduleFlush(false);
    }
  }

  document.addEventListener('click', enqueueClick, true);
  window.addEventListener('pagehide', flush);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      flush();
    }
  });
})();
