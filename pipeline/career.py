"""Parcours vérifié d'un joueur : on lit la carrière senior dans DEUX sources indépendantes
(infobox Wikipedia anglaise + infobox Wikipedia française), on identifie chaque club par son
identifiant Wikidata, et on exige que les deux séquences soient IDENTIQUES (mêmes clubs, même
ordre, années de début à ±1 an). Au moindre doute, le joueur est rejeté."""
import re, json, time, urllib.request, urllib.parse

UA = {'User-Agent': 'LaVignette/1.0 (erwan.lievrouw@orange.fr)'}
RESERVE = re.compile(r"(\bII\b|\bB\b$|\bB\)|reserve|réserve|youth|academy|académie|castilla|^jong |\bU-?\d{2}\b|under-?\d{2}|primavera|atlètic|juvenil|\bespoirs?\b)", re.I)

def _get(url, tries=6):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read().decode('utf-8')
        except Exception as e:
            if '404' in str(e): raise
            time.sleep(5 * (i + 1))
    raise RuntimeError('échec réseau: ' + url)

def wikitext(lang, title):
    return _get(f'https://{lang}.wikipedia.org/w/index.php?' + urllib.parse.urlencode({'title': title, 'action': 'raw'}))

def titles_to_qids(lang, titles):
    out = {}
    titles = list(dict.fromkeys(t for t in titles if t))
    for k in range(0, len(titles), 40):
        chunk = titles[k:k + 40]
        q = json.loads(_get(f'https://{lang}.wikipedia.org/w/api.php?' + urllib.parse.urlencode({
            'action': 'query', 'format': 'json', 'redirects': 1, 'prop': 'pageprops', 'ppprop': 'wikibase_item',
            'titles': '|'.join(chunk)})))['query']
        norm = {n['from']: n['to'] for n in q.get('normalized', [])}
        redir = {r['from']: r['to'] for r in q.get('redirects', [])}
        bytitle = {p['title']: p.get('pageprops', {}).get('wikibase_item') for p in q.get('pages', {}).values()}
        for t in chunk:
            t2 = norm.get(t, t); t3 = redir.get(t2, t2)
            out[t] = bytitle.get(t3)
    return out

def _link(s):
    m = re.search(r'\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]', s)
    return (m.group(1).strip(), (m.group(2) or m.group(1)).strip()) if m else (None, None)

def _year(s):
    m = re.search(r'(1[89]\d\d|20\d\d)', s)
    return int(m.group(1)) if m else None

def _strip_refs(t):
    t = re.sub(r'<ref[^>]*/>', '', t)
    t = re.sub(r'<ref[^>]*>.*?</ref>', '', t, flags=re.S)
    return re.sub(r'<!--.*?-->', '', t, flags=re.S)

def career_en(title):
    t = _strip_refs(wikitext('en', title))
    years = {int(n): v for n, v in re.findall(r'\|\s*years(\d+)\s*=\s*([^\n|]*)', t)}
    clubs = {int(n): v for n, v in re.findall(r'\|\s*clubs(\d+)\s*=\s*([^\n]*)', t)}
    rows = []
    for n in sorted(clubs):
        target, disp = _link(clubs[n])
        y = _year(years.get(n, ''))
        if not target or not y: return None, 'infobox EN illisible'
        if RESERVE.search(target) or RESERVE.search(disp): continue
        rows.append((y, target))
    open_ended = bool(re.search(r'–\s*$', years.get(max(years), ''))) if years else False
    return rows, ('actif' if open_ended else 'ok')

def career_fr(title):
    t = _strip_refs(wikitext('fr', title))
    m = re.search(r'\|\s*parcours (?:senior|pro)\s*=\s*\{\{(?:trois|deux|quatre) colonnes(.*?)\n\s*\}\}', t, re.S | re.I)
    if not m:
        m = re.search(r'\|\s*parcours (?:senior|pro)\s*=\s*\n?\s*\{\{(?:trois|deux|quatre) colonnes(.*?)\}\}\s*\n\s*\|', t, re.S | re.I)
    if not m: return None, 'infobox FR introuvable'
    rows = []
    for line in m.group(1).split('\n'):
        line = line.strip()
        if not line.startswith('|') or not re.search(r'\d{4}', line): continue
        parts = [p for p in re.split(r'\|(?![^\[]*\]\])(?![^{]*\}\})', line) if p.strip()]
        if len(parts) < 2: continue
        y = _year(re.sub(r'\[\[(\d{4}) en football\|', '', parts[0]))
        club_part = next((p for p in parts[1:] if '[[' in p), '')
        target, disp = _link(club_part)
        if not target or not y: continue
        if RESERVE.search(target) or RESERVE.search(disp): continue
        rows.append((y, target))
    return (rows, 'ok') if rows else (None, 'parcours FR vide')

def _collapse(seq):
    out = []
    for y, q in seq:
        if out and out[-1][1] == q: continue
        out.append((y, q))
    return out

def verified_career(sitelinks):
    """sitelinks : dict Wikidata (enwiki/frwiki). Retourne [(année, qid), ...] vérifié, ou lève ValueError."""
    en_t = sitelinks.get('enwiki', {}).get('title'); fr_t = sitelinks.get('frwiki', {}).get('title')
    if not en_t or not fr_t: raise ValueError('pas de page Wikipedia EN et FR')
    en, st_en = career_en(en_t)
    if en is None: raise ValueError(st_en)
    fr, st_fr = career_fr(fr_t)
    if fr is None: raise ValueError(st_fr)
    qe = titles_to_qids('en', [r[1] for r in en]); qf = titles_to_qids('fr', [r[1] for r in fr])
    if any(not qe.get(r[1]) for r in en) or any(not qf.get(r[1]) for r in fr):
        raise ValueError('club non identifiable')
    se = _collapse([(y, qe[t]) for y, t in en]); sf = _collapse([(y, qf[t]) for y, t in fr])
    if [q for _, q in se] != [q for _, q in sf]:
        raise ValueError('parcours EN et FR différents')
    for (ye, _), (yf, _) in zip(se, sf):
        if abs(ye - yf) > 1: raise ValueError('années EN et FR différentes')
    return se, st_en
