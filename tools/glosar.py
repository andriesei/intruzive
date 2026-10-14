#!/usr/bin/env python3
"""Generator de glosar pentru blogul Hugo "Gânduri Intruzive"."""
import re, sys, json, collections, urllib.parse
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"


def parse_post(path):
    """Întoarce (titlu, draft, corp) pentru un fișier .md."""
    t = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").lstrip()
    # front matter-ul TOML stă între două linii +++
    sfarsit = t.index("\n+++", 3)
    front = tomllib.loads(t[3:sfarsit])
    corp = t[sfarsit + 4:]
    return front.get("title", path.stem), bool(front.get("draft", False)), corp


def posts():
    """Parcurge articolele publicate (sare peste drafturi)."""
    for p in sorted(POSTS.glob("*.md")):
        titlu, draft, corp = parse_post(p)
        if draft:
            continue
        yield p, titlu, corp


# ---------------------------------------------------------------- utilitare
DIAC = str.maketrans("ăâîșşțţĂÂÎȘŞȚŢ", "aaisstt" "AAISSTT")
CUVANT = r"[^\W\d_]+"          # un cuvânt: doar litere, cu diacritice

STOP = set("""
si sau dar iar ca ce cu de din in la pe pentru prin spre sub fara nu da mai foarte este sunt
era fi fost fie va vor o un niste nici acel acea acei acele acest aceasta acestei acestui
aceste acestea acesta se le li il lui lor ei ea el ele noi voi eu tu cand cum unde cine care
cat cata cati cate daca desi deci insa totusi doar tot toata toate toti orice fiecare am ai
are au avea avut fac face facut poate putea pot putem vrea trebuie asa astfel aici acolo
atunci acum apoi inca deja prea chiar decat dupa inainte intre peste printre contra catre
langa fata despre dintre asupra sine sale sa nostru noastra mea meu fiind avand faptul fapt
ceea ceva nimic nimeni cineva oricum altfel unul una unii unele altul alta alti alte
aceeasi acelasi doua doi trei mult multa multi multe putin fel felul ori oricare
""".split())


def fara_diacritice(s):
    return s.translate(DIAC)


# --------------------------------------------------------------- sugestii
def sugestii():
    out = ROOT / "tools" / "sugestii"
    out.mkdir(exist_ok=True)

    stem_occ = collections.Counter()               # apariții pe radical
    stem_docs = collections.defaultdict(set)       # în câte articole
    stem_forme = collections.defaultdict(collections.Counter)
    nume_occ = collections.Counter()
    nume_docs = collections.defaultdict(set)
    nr = 0

    for p, titlu, corp in posts():
        nr += 1
        for m in re.finditer(CUVANT, corp):
            w = m.group(0)
            wl = fara_diacritice(w.lower())
            if len(wl) >= 5 and wl not in STOP:
                s = wl[:6]                          # radical = primele 6 litere
                stem_occ[s] += 1
                stem_docs[s].add(p.stem)
                stem_forme[s][w.lower()] += 1
            # nume proprii: cu majusculă, dar nu la început de propoziție
            if w[0].isupper() and len(w) >= 3 and not w.isupper():
                prev = corp[:m.start()].rstrip()[-1:]
                if prev and prev not in ".!?…„\"”:;—–-\n*#>" and wl not in STOP:
                    nume_occ[w] += 1
                    nume_docs[w].add(p.stem)

    with open(out / "termeni.tsv", "w", encoding="utf-8") as f:
        f.write("# radical\tapariții\tarticole\tforme frecvente\n")
        for s, n in stem_occ.most_common(300):
            forme = ", ".join(f"{k}({v})" for k, v in stem_forme[s].most_common(4))
            f.write(f"{s}\t{n}\t{len(stem_docs[s])}\t{forme}\n")

    with open(out / "nume.tsv", "w", encoding="utf-8") as f:
        f.write("# nume\tapariții\tarticole\n")
        for w, n in nume_occ.most_common(400):
            if n >= 1:
                f.write(f"{w}\t{n}\t{len(nume_docs[w])}\n")

    print(f"{nr} articole analizate -> {out}")


# ------------------------------------------------------------ citirea listelor
def incarca(fisier, ignora_majuscule=True):
    """Citește o listă. Întoarce [(etichetă, regex compilat), ...]."""
    intrari = []
    cale = ROOT / "tools" / fisier
    for nr, linie in enumerate(cale.read_text(encoding="utf-8").splitlines(), 1):
        linie = linie.strip()
        if not linie or linie.startswith("#"):
            continue
        eticheta, _, pat = (x.strip() for x in linie.partition("|"))
        rx = pat if pat else r"(?<!\w)" + re.escape(eticheta) + r"\w*"
        try:
            flaguri = (re.I if ignora_majuscule else 0) | re.U
            intrari.append((eticheta, re.compile(rx, flaguri)))
        except re.error as e:
            sys.exit(f"{fisier}, linia {nr}: expresie regulată invalidă ({e})")
    return intrari


# ------------------------------------------------------- fragment de text
MARKUP = set("*_[]()<>\\|#`{}~=")

def _cod(txt):
    """Codare pentru #:~:text= (cratima, punctul și ! au sens special)."""
    return (urllib.parse.quote(txt, safe="")
            .replace("-", "%2D").replace(".", "%2E").replace("!", "%21"))

def fragment(corp, start, end):
    """Valoarea directivei #:~:text= pentru o apariție din articol."""
    forma = re.sub(r"\s+", " ", corp[start:end]).strip()
    # 1) cuvintele care urmează (maximum 2)
    rest = corp[end:end + 80]
    extra = re.match(rf"(?: {CUVANT}){{1,2}}", rest)
    if extra and not (MARKUP & set(corp[start:end + extra.end()])):
        return _cod(forma + extra.group(0))
    # 2) altfel, cuvintele care preced (maximum 2), ca prefix de context
    inainte = corp[max(0, start - 80):start]
    pre = re.search(rf"(?:{CUVANT}[,;:]? ){{1,2}}$", inainte)
    if pre and not (MARKUP & set(pre.group(0))):
        return _cod(pre.group(0).strip()) + "-," + _cod(forma)
    return _cod(forma)


def construieste(intrari, articole):
    rezultat = []
    for eticheta, rx in intrari:
        gasite, total = [], 0
        for p, titlu, corp in articole:
            potriviri = list(rx.finditer(corp))
            if not potriviri:
                continue
            total += len(potriviri)
            m = potriviri[0]
            gasite.append({"t": titlu, "n": len(potriviri),
                           "q": fragment(corp, m.start(), m.end())})
        rezultat.append({"nume": eticheta, "total": total, "articole": gasite})
    rezultat.sort(key=lambda e: fara_diacritice(e["nume"].lower()))
    return rezultat


def build():
    articole = list(posts())
    date = {
        "termeni": construieste(incarca("glosar_termeni.txt"), articole),
        "nume": construieste(incarca("glosar_nume.txt", ignora_majuscule=False), articole),
    }
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "glosar.json").write_text(
        json.dumps(date, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(articole)} articole (drafturile sunt ignorate)")
    for cheie, lista in date.items():
        goale = [e["nume"] for e in lista if not e["articole"]]
        mesaj = f"  {cheie}: {len(lista)} intrări"
        if goale:
            mesaj += " | FĂRĂ potriviri: " + ", ".join(goale)
        print(mesaj)





if __name__ == "__main__":
    if "--sugestii" in sys.argv:
        sugestii()
    elif "--build" in sys.argv:
        build()
    else:
        print(__doc__)