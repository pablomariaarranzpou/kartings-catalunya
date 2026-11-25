(function () {
  // Idioma por hash (solo en la versión de una sola página).
  var views = document.querySelectorAll('.lang-view');
  function showLang() {
    if (!views.length) return;
    var h = (location.hash || '').slice(1);
    if (['es', 'ca', 'en'].indexOf(h) === -1) {
      var m = h.match(/^(es|ca|en)-/);
      if (!m) return;
      h = m[1];
    }
    views.forEach(function (v) { v.hidden = v.getAttribute('data-lang') !== h; });
  }
  window.addEventListener('hashchange', showLang);
  showLang();

  // Ordenar tablas.
  document.querySelectorAll('table[data-sortable]').forEach(function (table) {
    var body = table.tBodies[0];
    table.querySelectorAll('thead button[data-sort]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var col = +btn.getAttribute('data-sort');
        var kind = btn.getAttribute('data-kind');
        var dir = btn.getAttribute('data-dir') === 'asc' ? 'desc' : 'asc';
        table.querySelectorAll('thead button').forEach(function (b) { b.removeAttribute('data-dir'); });
        btn.setAttribute('data-dir', dir);
        var rows = Array.prototype.slice.call(body.rows);
        rows.sort(function (a, b) {
          var ca = a.cells[col], cb = b.cells[col];
          if (kind === 'n') {
            var va = ca.getAttribute('data-v'), vb = cb.getAttribute('data-v');
            if (va === '' && vb === '') return 0;
            if (va === '' || va === null) return 1;
            if (vb === '' || vb === null) return -1;
            return dir === 'asc' ? va - vb : vb - va;
          }
          var r = ca.textContent.localeCompare(cb.textContent);
          return dir === 'asc' ? r : -r;
        });
        rows.forEach(function (r) { body.appendChild(r); });
      });
    });
  });

  // Filtros por provincia y tipo (afectan al comparador y a las fichas del mismo idioma).
  document.querySelectorAll('.chips').forEach(function (bar) {
    var scope = bar.closest('.lang-view') || document;
    var state = { prov: '*', type: '*' };
    function apply() {
      scope.querySelectorAll('.cmp tbody tr, .card').forEach(function (el) {
        var okP = state.prov === '*' || el.getAttribute('data-prov') === state.prov;
        var t = state.type;
        var okT = t === '*' || (t === 'el' ? el.getAttribute('data-el') === '1'
          : t === 'indoor' ? /indoor|mixed/.test(el.getAttribute('data-type'))
          : /outdoor|mixed/.test(el.getAttribute('data-type')));
        el.hidden = !(okP && okT);
      });
      scope.querySelectorAll('.prov-h').forEach(function (h) {
        var grid = h.nextElementSibling;
        var any = grid && grid.querySelector('.card:not([hidden])');
        h.hidden = grid.hidden = !any;
      });
    }
    bar.addEventListener('click', function (ev) {
      var b = ev.target.closest('.chip');
      if (!b) return;
      var f = b.getAttribute('data-f'), v = b.getAttribute('data-val');
      if (f === 'type' && state.type === v) v = '*';
      state[f] = v;
      bar.querySelectorAll('.chip[data-f="' + f + '"]').forEach(function (c) {
        c.setAttribute('aria-pressed', String(c.getAttribute('data-val') === state[f]));
      });
      apply();
    });
  });
})();
