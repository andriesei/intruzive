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
      a.href = item.url;
      a.textContent = item.title;
      li.appendChild(a);
      list.appendChild(li);
    });
    if (!list.children.length) list.innerHTML = '<li>Niciun rezultat</li>';
  });
})();