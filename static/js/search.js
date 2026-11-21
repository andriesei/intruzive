// ===== Căutare =====
(function () {
  const input = document.getElementById('search-input');
  const list = document.getElementById('search-results');
  if (!input) return;
  let fuse = null;

  async function init() {
    if (fuse) return;
    try {
      const data = await (await fetch(input.dataset.index)).json();
      fuse = new Fuse(data, {
        keys: [{ name: 'title', weight: 2 }, 'content'],
        threshold: 0.3,
        ignoreLocation: true,
        ignoreDiacritics: true,
        minMatchCharLength: 2
      });
    } catch (e) { console.error('Index de căutare indisponibil', e); }
  }

  input.addEventListener('focus', init);
  input.addEventListener('input', async () => {
    await init();
    const q = input.value.trim();
    list.innerHTML = '';
    if (!fuse || q.length < 2) return;
    fuse.search(q, { limit: 10 }).forEach(({ item }) => {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = item.url + '?q=' + encodeURIComponent(q);
      a.textContent = item.title;
      li.appendChild(a);
      list.appendChild(li);
    });
    if (!list.children.length) list.innerHTML = '<li>Niciun rezultat</li>';
  });
})();

// ===== Evidențiere termen căutat în articol (font roșu, fără fundal) =====
function evidentiaza() {
  const q = new URLSearchParams(location.search).get('q');
  if (!q || q.trim().length < 2) return;

  const norm = s => s.split('').map(c => {
    const n = c.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    return n.length === 1 ? n : c;
  }).join('');

  const needle = norm(q.trim());
  const root = document.querySelector('main') || document.body;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: n => n.parentElement.closest('header, script, style, .gi-hl, #search-wrap')
      ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT
  });

  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);

  let first = null;
  nodes.forEach(node => {
    const text = node.nodeValue;
    const hay = norm(text);
    let i = hay.indexOf(needle);
    if (i < 0) return;
    const frag = document.createDocumentFragment();
    let last = 0;
    while (i >= 0) {
      frag.append(text.slice(last, i));
      const m = document.createElement('span');
      m.className = 'gi-hl';
      m.textContent = text.slice(i, i + needle.length);
      frag.append(m);
      if (!first) first = m;
      last = i + needle.length;
      i = hay.indexOf(needle, last);
    }
    frag.append(text.slice(last));
    node.replaceWith(frag);
  });

  if (first) first.scrollIntoView({ block: 'center' });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', evidentiaza);
} else {
  evidentiaza();
}