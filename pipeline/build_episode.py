#!/usr/bin/env python3
"""La Vignette — prépare un épisode : choisit 3 joueurs (facile/moyen/expert),
récupère et vérifie leur parcours sur Wikidata, télécharge une photo sous licence libre.
Usage : python3 build_episode.py <dossier racine La Vignette>
Sortie : episodes/NNN/episode.json + photos brutes. Code de sortie 0 si OK."""
import json, os, re, sys, time, random, urllib.request, urllib.parse, datetime

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {'User-Agent': 'LaVignette/1.0 (erwan.lievrouw@orange.fr)'}
FOOTBALLER = 'Q937857'
NATIONAL_TYPES = {'Q6979593', 'Q1194951', 'Q23759293', 'Q48982806', 'Q15944511'}

def get(url, tries=6):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()
        except Exception as e:
            print('  retry', i + 1, e, file=sys.stderr)
            time.sleep(6 * (i + 1))
    raise RuntimeError('échec réseau: ' + url)

def jget(url): return json.loads(get(url))

def wd_api(**params):
    params['format'] = 'json'
    return jget('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(params))

def label(ent, lang=('fr', 'en')):
    for l in lang:
        if l in ent.get('labels', {}): return ent['labels'][l]['value']
    return ent.get('id', '?')

def claim_ids(ent, prop):
    out = []
    for c in ent.get('claims', {}).get(prop, []):
        v = c['mainsnak'].get('datavalue', {}).get('value')
        if isinstance(v, dict) and 'id' in v: out.append(v['id'])
    return out

def year_of(c, prop):
    try: return int(c['qualifiers'][prop][0]['datavalue']['value']['time'][1:5])
    except Exception: return None

SHORT = {
    'Paris Saint-Germain Football Club': 'PSG', 'Paris Saint-Germain FC': 'PSG', 'Olympique de Marseille': 'Marseille',
    'Olympique lyonnais': 'Lyon', 'Lille OSC': 'Lille', 'AS Monaco FC': 'Monaco', 'AS Monaco': 'Monaco',
    'Manchester United Football Club': 'Man United', 'Manchester United FC': 'Man United',
    'Manchester City Football Club': 'Man City', 'Manchester City FC': 'Man City',
    'Real Madrid Club de Fútbol': 'Real Madrid', 'Real Madrid CF': 'Real Madrid', 'FC Barcelone': 'Barça',
    'Futbol Club Barcelona': 'Barça', 'Bayern Munich': 'Bayern', 'FC Bayern Munich': 'Bayern',
    'Borussia Dortmund': 'Dortmund', 'Juventus FC': 'Juventus', 'Juventus Football Club': 'Juventus',
    'Associazione Calcio Milan': 'AC Milan', 'Inter Milan': 'Inter', 'FC Internazionale Milano': 'Inter',
    'Los Angeles Football Club': 'LAFC', 'Tottenham Hotspur Football Club': 'Tottenham', 'Tottenham Hotspur FC': 'Tottenham',
    'Atlético de Madrid': 'Atlético', 'Club Atlético de Madrid': 'Atlético', 'Stade rennais FC': 'Rennes',
    'Stade rennais football club': 'Rennes', 'Girondins de Bordeaux': 'Bordeaux', 'FC Girondins de Bordeaux': 'Bordeaux',
    'AS Saint-Étienne': 'Saint-Étienne', 'FC Nantes': 'Nantes', 'OGC Nice': 'Nice', 'RC Lens': 'Lens', 'Racing Club de Lens': 'Lens',
    'Montpellier Hérault SC': 'Montpellier', 'Montpellier Hérault Sport Club': 'Montpellier', 'Stade brestois 29': 'Brest',
    'Toulouse FC': 'Toulouse', 'FC Metz': 'Metz', 'RC Strasbourg Alsace': 'Strasbourg', 'Stade de Reims': 'Reims',
    'AJ Auxerre': 'Auxerre', 'SM Caen': 'Caen', 'Le Havre AC': 'Le Havre', 'FC Lorient': 'Lorient', 'EA Guingamp': 'Guingamp',
    'Grenoble Foot 38': 'Grenoble', 'Football Club de Nantes': 'Nantes', 'AS Nancy-Lorraine': 'Nancy', 'Cercle athlétique bastiais': 'CA Bastia',
    'SC Bastia': 'Bastia', 'Stade Malherbe Caen': 'Caen', 'Stade Malherbe de Caen': 'Caen', 'AS Nancy-Lorraine': 'Nancy',
    'Al Nasr Riyad': 'Al-Nassr', 'Olympique Gymnaste Club de Nice': 'Nice', 'En Avant Guingamp': 'Guingamp', 'Amiens Sporting Club': 'Amiens', 'Sporting Club de Bastia': 'Bastia', 'Chamois niortais FC': 'Niort', 'Amiens SC': 'Amiens', 'Istres FC': 'Istres', 'Tours FC': 'Tours', 'US Boulogne CO': 'Boulogne',
    "Olympique d'Alès": 'Alès', 'Galatasaray SK': 'Galatasaray', 'Fenerbahçe Istanbul': 'Fenerbahçe', 'Fenerbahçe SK': 'Fenerbahçe',
    'Beşiktaş JK': 'Beşiktaş', 'U.S. Salernitana 1919': 'Salernitana', 'ACF Fiorentina': 'Fiorentina', 'SSC Naples': 'Naples',
    'SSC Napoli': 'Naples', 'AS Rome': 'AS Roma', 'SS Lazio': 'Lazio', 'Bolton Wanderers FC': 'Bolton',
    'West Bromwich Albion': 'West Brom', 'West Bromwich Albion FC': 'West Brom', 'West Ham United FC': 'West Ham',
    'Newcastle United FC': 'Newcastle', 'Mumbai City Football Club': 'Mumbai City', 'Shanghai Shenhua FC': 'Shanghai',
    'Al-Nassr FC': 'Al-Nassr', 'Al-Hilal FC': 'Al-Hilal', 'Al-Ittihad Club': 'Al-Ittihad', 'Inter Miami CF': 'Inter Miami',
    'Sporting Clube de Portugal': 'Sporting', 'Sporting CP': 'Sporting', 'SL Benfica': 'Benfica', 'FC Porto': 'Porto',
    'AFC Ajax': 'Ajax', 'PSV Eindhoven': 'PSV', 'Feyenoord Rotterdam': 'Feyenoord', 'RSC Anderlecht': 'Anderlecht',
    'Celtic Football Club': 'Celtic', 'Celtic FC': 'Celtic', 'Rangers FC': 'Rangers', 'Santos FC': 'Santos',
}
STRIP = r'\b(Football Club|Club Atlético|CA|Futbol Club|Fútbol Club|Calcio|FC|F\.C\.|CF|AFC|SC|SK|JK|CFC|SV|VfB|VfL|TSG|1\.|S\.p\.A\.)\b'

def short_club(name):
    if name in SHORT: return SHORT[name]
    s = re.sub(STRIP, '', name)
    s = re.sub(r'\s+', ' ', s).strip(' .-')
    s = re.sub(r'^(de|du|des|d\')\s*', '', s, flags=re.I)
    return s or name

FLAGS = {  # (orientation, couleurs)
    'France': ('v', ['#1B3A8C', '#FFFFFF', '#D7263D']), 'Italie': ('v', ['#1F7A4D', '#FFFFFF', '#D7263D']),
    'Belgique': ('v', ['#161616', '#F2C14E', '#D7263D']), 'Irlande': ('v', ['#1F7A4D', '#FFFFFF', '#F28C28']),
    "Côte d'Ivoire": ('v', ['#F28C28', '#FFFFFF', '#1F7A4D']), 'Mali': ('v', ['#1F7A4D', '#F2C14E', '#D7263D']),
    'Guinée': ('v', ['#D7263D', '#F2C14E', '#1F7A4D']), 'Nigeria': ('v', ['#1F7A4D', '#FFFFFF', '#1F7A4D']),
    'Allemagne': ('h', ['#161616', '#D7263D', '#F2C14E']), 'Pays-Bas': ('h', ['#D7263D', '#FFFFFF', '#1B3A8C']),
    'Espagne': ('h', ['#D7263D', '#F2C14E', '#D7263D']), 'Argentine': ('h', ['#7EB6E6', '#FFFFFF', '#7EB6E6']),
    'Autriche': ('h', ['#D7263D', '#FFFFFF', '#D7263D']), 'Gabon': ('h', ['#1F7A4D', '#F2C14E', '#1B3A8C']),
    'Russie': ('h', ['#FFFFFF', '#1B3A8C', '#D7263D']), 'Colombie': ('h', ['#F2C14E', '#1B3A8C', '#D7263D']),
    'Pologne': ('h', ['#FFFFFF', '#D7263D']), 'Ukraine': ('h', ['#1B3A8C', '#F2C14E']), 'Portugal': ('v', ['#1F7A4D', '#D7263D', '#D7263D']),
    'Sénégal': ('v', ['#1F7A4D', '#F2C14E', '#D7263D']), 'Cameroun': ('v', ['#1F7A4D', '#D7263D', '#F2C14E']),
    'Algérie': ('v', ['#1F7A4D', '#FFFFFF']), 'Maroc': ('v', ['#D7263D']), 'Tunisie': ('v', ['#D7263D']),
    'Brésil': ('v', ['#1F7A4D', '#F2C14E', '#1F7A4D']), 'Suède': ('h', ['#1B3A8C', '#F2C14E', '#1B3A8C']),
    'Uruguay': ('h', ['#FFFFFF', '#7EB6E6', '#FFFFFF']), 'Chili': ('h', ['#FFFFFF', '#D7263D']),
    'Croatie': ('h', ['#D7263D', '#FFFFFF', '#1B3A8C']), 'Égypte': ('h', ['#D7263D', '#FFFFFF', '#161616']),
    'Ghana': ('h', ['#D7263D', '#F2C14E', '#1F7A4D']), 'Togo': ('h', ['#1F7A4D', '#F2C14E', '#1F7A4D']),
    'Bosnie-Herzégovine': ('v', ['#1B3A8C', '#F2C14E']), 'Turquie': ('v', ['#D7263D']),
    'Angleterre': ('h', ['#FFFFFF', '#D7263D', '#FFFFFF']), 'Pays de Galles': ('h', ['#FFFFFF', '#1F7A4D']),
    'Norvège': ('v', ['#D7263D', '#1B3A8C', '#D7263D']), 'Danemark': ('v', ['#D7263D', '#FFFFFF', '#D7263D']),
    'Burkina Faso': ('h', ['#D7263D', '#1F7A4D']), 'République démocratique du Congo': ('h', ['#7EB6E6', '#D7263D', '#F2C14E']),
}
COUNTRY_FIX = {'Royaume-Uni': 'Angleterre'}

def position(labels):
    s = ' '.join(labels).lower()
    for k, v in [('gardien', 'GARDIEN'), ('ailier', 'AILIER'), ('avant-centre', 'ATTAQUANT'), ('attaquant', 'ATTAQUANT'),
                 ('milieu', 'MILIEU'), ('défenseur', 'DÉFENSEUR'), ('arrière', 'DÉFENSEUR'), ('latéral', 'DÉFENSEUR')]:
        if k in s: return v
    return 'JOUEUR'

FREE = re.compile(r'(CC[ -]BY|CC0|Public domain|Domaine public|Attribution|GFDL|FAL)', re.I)

def strip_html(s): return re.sub(r'<[^>]+>', '', s or '').strip()

def find_player(name):
    r = wd_api(action='wbsearchentities', search=name, language='fr', uselang='fr', type='item', limit=8)
    ids = [x['id'] for x in r.get('search', [])]
    if not ids: return None
    ents = wd_api(action='wbgetentities', ids='|'.join(ids), languages='fr|en')['entities']
    for i in ids:
        e = ents[i]
        if FOOTBALLER in claim_ids(e, 'P106'): return e
    return None

def build_player(name, level):
    e = find_player(name)
    if not e: raise ValueError('introuvable sur Wikidata')
    # parcours
    rows = []
    for c in e['claims'].get('P54', []):
        v = c['mainsnak'].get('datavalue', {}).get('value')
        if not v: continue
        rows.append((year_of(c, 'P580'), year_of(c, 'P582'), v['id']))
    ids = list({r[2] for r in rows})
    extra = claim_ids(e, 'P413') + (claim_ids(e, 'P1532') or claim_ids(e, 'P27'))[:1]
    ents = {}
    for k in range(0, len(ids + extra), 45):
        chunk = (ids + extra)[k:k + 45]
        ents.update(wd_api(action='wbgetentities', ids='|'.join(chunk), props='labels|claims', languages='fr|en')['entities'])
    clubs = []
    for st, en, cid in sorted([r for r in rows if r[0]], key=lambda r: (r[0], r[1] or 9999)):
        ce = ents.get(cid, {})
        nm = label(ce)
        types = set(claim_ids(ce, 'P31'))
        if types & NATIONAL_TYPES or re.search(r'^(équipe|selección|national)|national|espoirs|moins de|under-?\d|olympique$', nm, re.I):
            continue
        sn = short_club(nm)
        if clubs and clubs[-1][0] == sn: continue
        clubs.append([sn, st])
    if len(clubs) < 4: raise ValueError(f'parcours trop court ({len(clubs)} clubs)')
    clubs = clubs[-15:]
    pos = position([label(ents[i]) for i in claim_ids(e, 'P413') if i in ents])
    nat_ids = claim_ids(e, 'P1532') or claim_ids(e, 'P27')
    nat = label(ents.get(nat_ids[0], {})) if nat_ids else ''
    nat = COUNTRY_FIX.get(nat, nat)
    # photo
    imgs = [c['mainsnak']['datavalue']['value'] for c in e['claims'].get('P18', []) if 'datavalue' in c['mainsnak']]
    if not imgs: raise ValueError('pas de photo libre')
    f = imgs[-1]
    q = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'query', 'format': 'json', 'prop': 'imageinfo',
        'iiprop': 'url|extmetadata', 'iiurlwidth': 960, 'titles': 'File:' + f})
    ii = list(jget(q)['query']['pages'].values())[0]['imageinfo'][0]
    m = ii['extmetadata']
    lic = strip_html(m.get('LicenseShortName', {}).get('value'))
    if not FREE.search(lic): raise ValueError('licence photo non libre: ' + lic)
    artist = strip_html(m.get('Artist', {}).get('value')) or 'Wikimedia Commons'
    if 'unknown' in artist.lower() or 'inconnu' in artist.lower(): artist = 'auteur inconnu'
    artist = re.sub(r'\s+', ' ', artist)[:40]
    full = label(e)
    parts = full.split(' ', 1)
    first, last = (parts[0], parts[1]) if len(parts) == 2 else ('', parts[0])
    return {'lvl': level, 'qid': e['id'], 'name': full, 'first': first.upper(), 'last': last.upper(), 'pos': pos,
            'nat': nat.upper(), 'flag': FLAGS.get(nat), 'clubs': clubs,
            'photo': {'file': f, 'page': ii['descriptionurl'], 'url': (ii.get('thumburl') or ii['url']).replace('://thumb.wikimedia.org/', '://upload.wikimedia.org/').split('?')[0], 'artist': artist, 'license': lic},
            'credit': f'Photo : {artist} · {lic}'}

def main():
    pool = json.load(open(os.path.join(ROOT, 'data', 'players.json')))
    hpath = os.path.join(ROOT, 'data', 'history.json')
    hist = json.load(open(hpath)) if os.path.exists(hpath) else {'episodes': [], 'used': [], 'rejected': {}}
    num = len(hist['episodes']) + 1
    epdir = os.path.join(ROOT, 'episodes', f'{num:03d}')
    os.makedirs(epdir, exist_ok=True)
    players = []
    for level in ['FACILE', 'MOYEN', 'EXPERT']:
        cands = [n for n in pool[level] if n not in hist['used'] and n not in hist['rejected']]
        random.shuffle(cands)
        for name in cands:
            print(f'[{level}] essai : {name}')
            try:
                p = build_player(name, level)
            except Exception as ex:
                print('  rejeté :', ex); hist['rejected'][name] = str(ex); time.sleep(1); continue
            p['src'] = name
            slug = f'p{len(players) + 1}'
            ext = os.path.splitext(p['photo']['url'].split('?')[0])[1].lower() or '.jpg'
            try:
                open(os.path.join(epdir, slug + '_raw' + ext), 'wb').write(get(p['photo']['url']))
            except Exception as ex:
                print('  photo KO :', ex); continue
            p['raw'] = slug + '_raw' + ext; p['img'] = slug + '_ht.png'
            players.append(p); print('  OK :', len(p['clubs']), 'clubs'); break
        else:
            json.dump(hist, open(hpath, 'w'), ensure_ascii=False, indent=1)
            sys.exit(f'ERREUR : plus de joueur valide au niveau {level}')
    ep = {'num': num, 'date': datetime.date.today().isoformat(), 'players': players}
    names = ', '.join(p['name'] for p in players)
    credits = '\n'.join(f"- {p['name']} : {p['photo']['artist']}, {p['photo']['license']} ({p['photo']['page']})" for p in players)
    ep['title'] = f'Devine les 3 joueurs grâce à leur parcours ! Qui suis-je ? #{num:03d}'
    ep['caption'] = (f"Qui suis-je ? 3 joueurs, 3 niveaux : facile, moyen, expert.\n"
                     f"Tu en trouves combien ? Ton score en commentaire ↓\n\n"
                     f"Nouvelle vignette chaque jour à 18h30.\n\n"
                     f"#foot #football #quizfoot #quisuisje #footballquiz #ligue1 #lavignette\n\n"
                     f"Crédits photos (Wikimedia Commons) :\n{credits}")
    ep['answers'] = names
    json.dump(ep, open(os.path.join(epdir, 'episode.json'), 'w'), ensure_ascii=False, indent=1)
    # l'épisode est réservé : ses joueurs ne ressortiront plus
    hist['used'] += [p['src'] for p in players] + [p['qid'] for p in players]
    hist['episodes'].append({'num': num, 'date': ep['date'], 'players': [p['name'] for p in players]})
    json.dump(hist, open(hpath, 'w'), ensure_ascii=False, indent=1)
    print('EPISODE_DIR=' + epdir)
    print('EPISODE_NUM=%03d' % num)

if __name__ == '__main__':
    main()
