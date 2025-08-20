(function () {
  function norm(s){return (s||"").toLowerCase().trim();}

  function filterCards(q) {
    const needle = norm(q);
    // attributes are on an inner element; hide the LI parent
    document.querySelectorAll('[data-marketplace-card]').forEach(el => {
      const hay = norm(el.getAttribute('data-filter'));
      const li = el.closest('li, .card'); // works for list- or block-based cards
      if (!li) return;
      li.style.display = hay.includes(needle) ? '' : 'none';
    });
  }

  function attach(){
    const input = document.getElementById('marketplace-filter-input');
    if (input) input.addEventListener('input', e => filterCards(e.target.value));
  }

  document.addEventListener('DOMContentLoaded', attach);
  if (window.document$) window.document$.subscribe(attach); // SPA nav hook
})();
