# =====================================================================
# cb_basi.py — Corsa Bis · le quattro basi vuote (B01-B04) con le strade
# Cosa fa: costruisce le tessere base del GDD con le strade generate dai
#   connettori sui lati:
#   B01 dritta      viale 3↔0, urbana viale→2, stretta viale→5 (esempio del GDD)
#   B02 curva larga viale 3→1, urbana 5→viale
#   B03 a T         viale 3↔0, urbana 2→viale al centro
#   B04 incrocio    viale 3↔0 incrociato dall'urbana 1↔4
# Come:
#   - lati numerati come nel GDD: 0 = est, poi in senso antiorario; il
#     connettore è il punto medio del lato (apotema 173,2 unità);
#   - ogni strada è una curva di Bézier che parte perpendicolare al lato
#     (così continua nella tessera vicina in qualsiasi rotazione) e arriva
#     a un altro lato o su un'altra strada;
#   - carreggiata = foglio di cartone grigio spesso 0,3 a tutta larghezza;
#     marciapiedi = secondo strato ai lati; strisce di carta bianca sulla
#     carreggiata (viale: doppia linea al centro + corsie tratteggiate,
#     urbana: tratteggio al centro);
#   - agli incroci marciapiedi e strisce si interrompono da soli dove
#     entrano nella larghezza di un'altra strada;
#   - larghezze dalla tabella del GDD: viale 30 (marciapiedi 4,5),
#     urbana 18 (3), stretta 10,5 (1,5).
#   Esporta anche blender/data/tessere_basi.json: connettori dei
#   6 lati e strade come polilinee (il grafo stradale per il gioco).
# Unità: unità di gioco. Richiede cb_lib.py e cb_tessera.py.
# Uso: apri il file nel Text Editor e premi Run Script.
# =====================================================================
import bpy, math, os, json
from mathutils import Vector, Matrix

def _carica(nome):
    t = bpy.data.texts.get(nome)
    if t is not None: return t.as_string()
    for tx in bpy.data.texts:
        if tx.filepath:
            p = os.path.join(os.path.dirname(bpy.path.abspath(tx.filepath)), nome)
            if os.path.exists(p):
                with open(p, encoding='utf-8') as f: return f.read()
    raise FileNotFoundError(nome + ': aprilo nel Text Editor o mettilo nella stessa cartella di questo script')

_nome_main = __name__; __name__ = 'cb_basi'
if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
exec(_carica('cb_tessera.py'))
__name__ = _nome_main

APOTEMA = RAGGIO*math.sqrt(3)/2
TIPI = {  # larghezza totale, marciapiede per lato
    'viale': (30.0, 4.5), 'urbana': (18.0, 3.0), 'stretta': (10.5, 1.5)}
Z0, DZ, SP = 0.2, 0.06, 0.3        # quota del primo foglio, salto tra strade sovrapposte, spessore
S_STRADA = 5.0                     # scala del cartone delle strade

def connettore(lato):
    a = math.radians(60*lato)
    return Vector((APOTEMA*math.cos(a), APOTEMA*math.sin(a))), Vector((-math.cos(a), -math.sin(a)))  # punto, direzione verso l'interno

# ---------- percorsi ----------
def bezier(p0, d0, p3, d3, passo=1.0):
    k = (p3 - p0).length*0.4
    p1 = p0 + d0*k; p2 = p3 - d3*k
    L = (p3 - p0).length + 1e-6; n = max(8, int(L/passo)*2)
    pts = []
    for i in range(n + 1):
        t = i/n; u = 1 - t
        p = u**3*p0 + 3*u*u*t*p1 + 3*u*t*t*p2 + t**3*p3
        d = 3*u*u*(p1 - p0) + 6*u*t*(p2 - p1) + 3*t*t*(p3 - p2)
        pts.append((p, math.atan2(d.y, d.x)))
    return pts

def da_lato_a_lato(a, b):
    p0, d0 = connettore(a); p3, d3 = connettore(b)
    return bezier(p0, d0, p3, -d3)

def da_lato_a_punto(a, p3, d3):
    p0, d0 = connettore(a)
    return bezier(p0, d0, Vector(p3), Vector(d3).normalized())

def su_strada(a, tr, f):
    # strada dal lato a che arriva perpendicolare su un'altra strada (tr), alla frazione f della sua lunghezza
    p, ang = tr[int(f*(len(tr) - 1))]
    p0, _ = connettore(a); nl = Vector((-math.sin(ang), math.cos(ang)))
    d3 = nl if (p - p0).dot(nl) > 0 else -nl
    return da_lato_a_punto(a, p, d3)

BASI = {
    'B01': ('B01 · dritta', [('viale', lambda: da_lato_a_lato(3, 0)),
                             ('urbana', lambda: da_lato_a_punto(2, (-86.6, 0), (0, -1))),
                             ('stretta', lambda: da_lato_a_punto(5, (86.6, 0), (0, 1)))]),
    'B02': ('B02 · curva larga', [('viale', lambda: da_lato_a_lato(3, 1)),
                                  ('urbana', lambda: su_strada(5, da_lato_a_lato(3, 1), 0.55))]),
    'B03': ('B03 · a T', [('viale', lambda: da_lato_a_lato(3, 0)),
                          ('urbana', lambda: da_lato_a_punto(2, (0, 0), (0, -1)))]),
    'B04': ('B04 · incrocio', [('viale', lambda: da_lato_a_lato(3, 0)),
                               ('urbana', lambda: da_lato_a_lato(1, 4))]),
}

# ---------- geometria ----------
def offset(p, a, d):
    return p + Vector((-math.sin(a), math.cos(a)))*d

def nastro(tr, d0, d1):
    return [tuple(offset(p, a, d1)) for p, a in tr] + [tuple(offset(p, a, d0)) for p, a in reversed(tr)]

def dist_traccia(q, tr):
    return min((q - p).length for p, _ in tr)

def dentro_altre(q, i, strade):
    # True se il punto q cade nella larghezza di un'altra strada
    for j, (tipo, tr) in enumerate(strade):
        if j != i and dist_traccia(q, tr) < TIPI[tipo][0]/2 - 0.05: return True
    return False

def tratti(tr, d, i, strade, filtro=None):
    # spezza la traccia dove lo scostamento d entra in un'altra strada; filtro(s) per il tratteggio
    out, cur, s = [], [], 0.0
    for k, (p, a) in enumerate(tr):
        if k: s += (p - tr[k-1][0]).length
        ok = not dentro_altre(offset(p, a, d), i, strade) and (filtro is None or filtro(s))
        if ok: cur.append((p, a))
        else:
            if len(cur) >= 2: out.append(cur)
            cur = []
    if len(cur) >= 2: out.append(cur)
    return out

def foglio(tr, d0, d1, t, z, seed):
    g = build_panel(nastro(tr, d0, d1), t=t, warp=0.0, step=0.4, seed=seed, scala=S_STRADA)
    return g, Matrix.Translation((0, 0, z))

def materiali_strade():
    return {'strada': mat_vernice('CB_T_Strada', (0.30, 0.30, 0.31, 1), 0.70, S_STRADA),
            'marciapiede': mat_vernice('CB_T_Marciapiede', (0.62, 0.59, 0.54, 1), 0.68, S_STRADA),
            'striscia': mat_vernice('CB_T_Striscia', (0.86, 0.84, 0.78, 1), 0.72, 1.0),
            'bordo': mat_bordo('CB_T_Strada_Bordo', 2.0), 'interno': mat_kraft('CB_T_Interno_Strada', 0.42, S_STRADA)}

def strade_oggetto(nome, strade, MS, coll, loc):
    gr = {'strada': [], 'marciapiede': [], 'striscia': []}; seed = 0
    for i, (tipo, tr) in enumerate(strade):
        L, mw = TIPI[tipo]; hw = L/2; z = Z0 + DZ*i
        gr['strada'].append(foglio(tr, -hw, hw, SP, z, seed := seed + 1))
        for sgn in (-1, 1):
            for t in tratti(tr, sgn*(hw - mw/2), i, strade):
                gr['marciapiede'].append(foglio(t, min(sgn*hw, sgn*(hw - mw)), max(sgn*hw, sgn*(hw - mw)), SP, z + SP + 0.05, seed := seed + 1))
        zs = z + SP + 0.05; lw = 0.35
        if tipo == 'viale':
            for c in (-0.45, 0.45):
                for t in tratti(tr, c, i, strade): gr['striscia'].append(foglio(t, c - lw/2, c + lw/2, 0.05, zs, seed := seed + 1))
            for c in (-5.25, 5.25):
                for t in tratti(tr, c, i, strade, lambda s: s % 9.0 < 4.5): gr['striscia'].append(foglio(t, c - lw/2, c + lw/2, 0.05, zs, seed := seed + 1))
        elif tipo == 'urbana':
            for t in tratti(tr, 0.0, i, strade, lambda s: s % 9.0 < 4.5): gr['striscia'].append(foglio(t, -lw/2, lw/2, 0.05, zs, seed := seed + 1))
    slots = []; geos = []
    for k, items in gr.items():
        mats = [MS[k], MS['bordo'], MS['interno']]; idx = []
        for m in mats:
            if m not in slots: slots.append(m)
            idx.append(slots.index(m))
        for (V, F, M_, U, S), Mx in items: geos.append(((V, F, [idx[m] for m in M_], U, S), Mx))
    return make_object(nome, geos, slots, coll, loc)

# ---------- dati per il gioco ----------
def connettori_di(strade_def):
    lati = ['nessuna']*6
    for tipo, f in strade_def:
        tr = f()
        for p, _ in (tr[0], tr[-1]):
            for lato in range(6):
                if (p - connettore(lato)[0]).length < 0.5: lati[lato] = tipo
    return lati

def cartella_script():
    # La cartella blender/scripts: la cerca tra i testi aperti che hanno un file su disco
    # (di solito questo stesso script), come fa _carica.
    for tx in bpy.data.texts:
        if tx.filepath:
            d = os.path.dirname(bpy.path.abspath(tx.filepath))
            if os.path.exists(os.path.join(d, 'cb_lib.py')): return d
    raise FileNotFoundError('apri cb_basi.py dalla cartella blender/scripts della repo')

def esporta(dati):
    # scripts -> blender -> radice della repo; poi blender/data/tessere_basi.json
    base = os.path.dirname(os.path.dirname(cartella_script()))
    cartella = os.path.join(base, 'blender', 'data'); os.makedirs(cartella, exist_ok=True)
    p = os.path.join(cartella, 'tessere_basi.json')
    with open(p, 'w', encoding='utf-8') as f: json.dump(dati, f, ensure_ascii=False, indent=1)
    return p

def run():
    vista_tessere()
    coll = bpy.data.collections.get('Tessere_Basi')
    if coll:
        for o in list(coll.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0 and isinstance(d, bpy.types.Mesh) and not d.name.startswith('Tessera_'): bpy.data.meshes.remove(d)
    else:
        coll = bpy.data.collections.new('Tessere_Basi'); bpy.context.scene.collection.children.link(coll)
    M = materiali_tessera(); MS = materiali_strade(); dati = {'unita': 'unità di gioco', 'raggio': RAGGIO,
        'lati': '0 = est, poi in senso antiorario; connettore al punto medio', 'tessere': {}}
    for i, (cod, (titolo, sdef)) in enumerate(BASI.items()):
        loc = Vector((i*440.0, -700.0, 0.0))
        tessera(cod, coll, loc, 1, 'erba', M, seed=40 + i)
        strade = [(tipo, f()) for tipo, f in sdef]
        strade_oggetto(f'{cod}_Strade', strade, MS, coll, loc)
        cartello(titolo, (loc.x, loc.y - 260.0, 0), coll, M)
        dati['tessere'][cod] = {'nome': titolo, 'connettori': connettori_di(sdef),
            'strade': [{'tipo': tipo, 'larghezza': TIPI[tipo][0], 'punti': [[round(p.x, 2), round(p.y, 2)] for p, _ in tr[::4] + [tr[-1]]]}
                       for tipo, tr in strade]}
    return esporta(dati)

if __name__ == '__main__':
    print(run())
