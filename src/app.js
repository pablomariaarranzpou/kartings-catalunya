(function () {
  // ---- Idioma por hash (solo versión de una sola página) ----
  var views = document.querySelectorAll('.lang-view');
  function showLang() {
    if (!views.length) return;
    var h = (location.hash || '').slice(1);
    var m = h.match(/^(es|ca|en)(-|$)/);
    if (!m) return;
    views.forEach(function (v) { v.hidden = v.getAttribute('data-lang') !== m[1]; });
  }

  // ---- Abrir la ficha a la que apunta un enlace ----
  function openTarget() {
    var id = decodeURIComponent((location.hash || '').slice(1));
    if (!id) return;
    var el = document.getElementById(id);
    if (el && el.tagName === 'DETAILS') { el.open = true; el.scrollIntoView({ block: 'start' }); }
  }
  window.addEventListener('hashchange', function () { showLang(); openTarget(); });
  showLang();
  openTarget();

  // ---- Pestañas ----
  document.querySelectorAll('[role=tablist]').forEach(function (list) {
    list.addEventListener('click', function (ev) {
      var b = ev.target.closest('[role=tab]');
      if (!b) return;
      list.querySelectorAll('[role=tab]').forEach(function (t) {
        var on = t === b;
        t.setAttribute('aria-selected', String(on));
        var p = document.getElementById(t.getAttribute('aria-controls'));
        if (p) p.hidden = !on;
      });
    });
  });

  // ---- Buscador ----
  function haversine(a, b) {
    var R = 6371, r = Math.PI / 180;
    var dLa = (b[0] - a[0]) * r, dLo = (b[1] - a[1]) * r;
    var h = Math.sin(dLa / 2) * Math.sin(dLa / 2) +
      Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin(dLo / 2) * Math.sin(dLo / 2);
    return 2 * R * Math.asin(Math.sqrt(h));
  }
  function kmRound(d) { return d < 20 ? Math.max(1, Math.round(d)) : Math.round(d / 5) * 5; }

  document.querySelectorAll('.finder').forEach(function (f) {
    var cfg = JSON.parse(f.querySelector('.cfg').textContent);
    var list = f.querySelector('.results');
    var rows = Array.prototype.slice.call(list.children);
    var form = f.querySelector('.controls');
    var zoneSel = f.querySelector('[data-ctl=zone]');
    var sortSel = f.querySelector('[data-ctl=sort]');
    var nInp = f.querySelector('[data-ctl=n]');
    var ppl = f.querySelector('.ppl');
    var countEl = f.querySelector('.count');
    var emptyEl = f.querySelector('.empty');
    var geoMsg = f.querySelector('.geo-msg');
    var eurOpt = sortSel.querySelector('option[value=eurmin]');
    var origin = [41.3874, 2.1686], fromYou = false;
    var money = new Intl.NumberFormat(cfg.lang, { style: 'currency', currency: 'EUR', minimumFractionDigits: 0, maximumFractionDigits: 2 });

    rows.forEach(function (r) { r._d = haversine(origin, [+r.dataset.lat, +r.dataset.lon]); });

    function mode() { return form.querySelector('input[type=radio]:checked').value; }
    function num(r, k) { var v = r.dataset[k]; return v === '' || v === undefined ? null : +v; }

    function update() {
      var m = mode(), z = zoneSel.value, n = Math.max(1, Math.min(40, parseInt(nInp.value, 10) || 1));
      var sort = sortSel.value;
      ppl.hidden = m !== 'race';
      eurOpt.disabled = eurOpt.hidden = m === 'race';
      if (m === 'race' && sort === 'eurmin') { sort = 'price'; sortSel.value = 'price'; }

      var cand = rows.filter(function (r) {
        if (r.dataset.mode !== m) return false;
        if (z !== '*' && r.dataset.zone !== z) return false;
        if (m === 'race') {
          var mn = num(r, 'minp'), mx = num(r, 'maxp');
          if (mn !== null && n < mn) return false;
          if (mx !== null && n > mx) return false;
        }
        return true;
      });
      if (m === 'race') { // la carrera más barata posible por circuito
        var best = {};
        cand.forEach(function (r) { var k = r.dataset.k; if (!best[k] || +r.dataset.price < +best[k].dataset.price) best[k] = r; });
        cand = Object.keys(best).map(function (k) { return best[k]; });
        cand.forEach(function (r) { r.querySelector('.r-total').textContent = cfg.total.replace('{n}', n).replace('{t}', money.format(+r.dataset.price * n)); });
      }
      var key = sort === 'dist' ? function (r) { return r._d; } : function (r) { var v = num(r, sort); return v === null ? Infinity : v; };
      cand.sort(function (a, b) { return key(a) - key(b) || +a.dataset.price - +b.dataset.price; });

      rows.forEach(function (r) { r.hidden = true; r.classList.remove('top'); r.querySelector('.badge').hidden = true; });
      cand.forEach(function (r, i) {
        r.hidden = false;
        list.appendChild(r);
        r.querySelector('.dist').textContent = (fromYou ? cfg.from_you : cfg.from_bcn).replace('{km}', kmRound(r._d));
      });
      if (cand[0]) {
        cand[0].classList.add('top');
        var b = cand[0].querySelector('.badge');
        b.textContent = cfg.badge[sort]; b.hidden = false;
      }
      countEl.textContent = cand.length === 1 ? cfg.count1 : cfg.count.replace('{n}', cand.length);
      emptyEl.hidden = cand.length > 0;
    }

    form.addEventListener('change', function (ev) {
      if (ev.target.type === 'radio' && sortSel.value !== 'dist') sortSel.value = ev.target.value === 'race' ? 'price' : 'eurmin';
      update();
    });
    form.addEventListener('input', function (ev) { if (ev.target === nInp) update(); });
    form.addEventListener('submit', function (ev) { ev.preventDefault(); });
    f.querySelectorAll('[data-step]').forEach(function (b) {
      b.addEventListener('click', function () {
        nInp.value = Math.max(1, Math.min(40, (parseInt(nInp.value, 10) || 1) + +b.dataset.step));
        update();
      });
    });
    f.querySelector('[data-near]').addEventListener('click', function () {
      function fail() { geoMsg.textContent = cfg.near_fail; geoMsg.hidden = false; }
      try {
        if (!navigator.geolocation) return fail();
        navigator.geolocation.getCurrentPosition(function (p) {
          origin = [p.coords.latitude, p.coords.longitude]; fromYou = true;
          rows.forEach(function (r) { r._d = haversine(origin, [+r.dataset.lat, +r.dataset.lon]); });
          sortSel.value = 'dist';
          geoMsg.textContent = cfg.near_ok; geoMsg.hidden = false;
          update();
        }, fail, { timeout: 10000, maximumAge: 600000 });
      } catch (e) { fail(); }
    });
    update();
  });
})();
