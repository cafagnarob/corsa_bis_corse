# =====================================================================
# cb_lod.py — Corsa Bis · livelli di dettaglio (LOD) per i mezzi di cartone
# Cosa fa: parte dai pezzi di un mezzo (lo stesso elenco del tutorial) e
#   ne ricava versioni più leggere ripensando il modello, non solo
#   riducendo i poligoni:
#   LOD1  toglie interni e nastro, ruote da 4 a 2 dischi, bordi meno fitti
#   LOD2  toglie anche pezzi nascosti (longheroni, assi, aste),
#         ruota in un disco solo, niente forellini, contorni semplificati
#   LOD3  solo i volumi che si leggono da lontano, contorni dritti,
#         tutto unito in una mesh (instancing nel gioco)
#   LOD4 e LOD5 dipendono dalla forma del mezzo: li costruisce il file del
#   mezzo (sagoma estrusa, gettone 2D).
# Come: ogni pezzo viene filtrato per nome, i contorni sono semplificati con
#   Douglas-Peucker, i fori piccoli eliminati, le ruote ricostruite.
#   LOD1 e LOD2 tengono i pezzi separati con gli stessi nomi del LOD0, così
#   lo stesso rig può muoverli; da LOD3 il mezzo è un pezzo unico.
# Richiede: cb_lib.py e cb_tutorial.py (caricati dal file del mezzo).
# =====================================================================
import bpy, math
from mathutils import Vector, Matrix

# pezzi da togliere: un livello toglie anche tutto quello dei livelli precedenti
TOGLI = {
    1: ('Posto_Guida', 'Cruscotto', 'Piantone', 'Sedili', 'Corrimano', 'Divano'),
    2: ('Longherone', 'Asse_', 'Asta_Specchietto'),   # i passaruota restano: coprono le ruote che bucherebbero il pianale
    3: ('Specchietto', 'Coprimozzo', 'Cassetta', 'Frecce', 'Porta_', 'Ralla', 'Pedana', 'Griglia_Motore', 'Fascia'),   # il pavimento resta: si vede dai finestrini
}
# parametri di semplificazione per livello
LIV = {
    1: dict(tol=0.0,  step=0.20, rough=0.010, nick=0.030, warp=0.012, buco_min=0.0,   dischi=2, lugs=18),
    2: dict(tol=0.03, step=0.50, rough=0.008, nick=0.020, warp=0.010, buco_min=0.012, dischi=1, lugs=12),
    3: dict(tol=0.08, step=50.0, rough=0.0,   nick=0.0,   warp=0.0,   buco_min=0.09,  dischi=1, lugs=0),
}

# ---------- semplificazione dei contorni ----------
def _dp(pts, tol):
    if len(pts) < 3: return pts
    a = Vector(pts[0]); b = Vector(pts[-1]); ab = b - a; L = ab.length
    best, idx = -1.0, 0
    for i in range(1, len(pts) - 1):
        p = Vector(pts[i])
        d = (p - a).length if L < 1e-9 else abs(ab.x*(p - a).y - ab.y*(p - a).x)/L
        if d > best: best, idx = d, i
    if best <= tol: return [pts[0], pts[-1]]
    return _dp(pts[:idx + 1], tol)[:-1] + _dp(pts[idx:], tol)

def semplifica(loop, tol, min_n=4):
    if tol <= 0 or len(loop) <= min_n: return list(loop)
    c = Vector(loop[0]); j = max(range(len(loop)), key=lambda i: (Vector(loop[i]) - c).length)
    out = _dp(list(loop[:j + 1]), tol)[:-1] + _dp(list(loop[j:]) + [loop[0]], tol)[:-1]
    if len(out) < min_n:
        n = len(loop); out = [loop[int(i*n/min_n)] for i in range(min_n)]
    return out

def _area(loop):
    s = 0.0
    for i in range(len(loop)):
        x0, y0 = loop[i]; x1, y1 = loop[(i + 1) % len(loop)]
        s += x0*y1 - x1*y0
    return abs(s)/2

# ---------- ruote ----------
def ruota_lod(pd0, cfg, L):
    # ricostruisce la ruota: stessi centro e lato, meno dischi e meno tasselli
    w = cfg['wheel']; M = pd0['M']; c = M.translation; s = 1 if M.col[2].y > 0 else -1
    n = LIV[L]['dischi']; t = w['DT']*4/n; out = []
    for k in range(n):
        if LIV[L]['lugs']: outl = tread(w['RW'], w['RW'] - 0.035, LIV[L]['lugs'])
        else: outl = circle(0, 0, w['RW'], 10)
        holes = [circle(0, 0, 0.065, 10)] if L == 1 else []
        out.append(part(outl, frame((c.x, s*(w['YW0'] + k*t), c.z), (1, 0, 0), (0, 0, 1), (0, s, 0)), holes,
                        t=t, rough=LIV[L]['rough']*0.5, nick=0.0, step=LIV[L]['step']))
    return out

# ---------- pezzi per livello ----------
def pezzi_lod(PCS, cfg, L, extra_togli=()):
    via = sum((TOGLI[k] for k in range(1, L + 1)), ()) + tuple(extra_togli)
    p = LIV[L]; out = []
    for pc in PCS:
        if pc['stage'] > cfg['final_stage'] or pc['until'] < cfg['final_stage']: continue
        if pc['kind'] == 'tape' or any(pc['name'].startswith(v) for v in via): continue
        q = dict(pc)
        if pc['name'].startswith('Ruota_'):
            q['parts'] = ruota_lod(pc['parts'][0], cfg, L); out.append(q); continue
        parts = []
        for pd in pc['parts']:
            if 'geo' in pd: continue
            kw = dict(pd['kw'])
            kw['rough'] = min(kw.get('rough', 0.012), p['rough']); kw['nick'] = min(kw.get('nick', 0.035), p['nick'])
            kw['warp'] = min(kw.get('warp', 0.012), p['warp']); kw['step'] = max(kw.get('step', 0.09), p['step'])
            holes = [semplifica(h, p['tol']) for h in pd['holes'] if _area(h) >= p['buco_min']]
            parts.append(dict(outline=semplifica(pd['outline'], p['tol']), holes=holes, M=pd['M'], t=pd['t'], kw=kw))
        if parts:
            q['parts'] = parts; out.append(q)
    return out

# ---------- costruzione ----------
def triangoli(objs):
    return sum(len(f.vertices) - 2 for o in objs if o.type == 'MESH' for f in o.data.polygons)

def costruisci(PCS, MAT, cfg, coll, loc, pref, unisci=False):
    s = cfg['final_stage']; objs = []
    if not unisci:
        for pc in PCS:
            geos = [(geo_of(pc, i, pd), pd['M']) for i, pd in enumerate(pc['parts'])]
            objs.append(make_object(f"{pref}_{pc['name']}", geos, piece_mats(pc, s, MAT, cfg), coll, loc))
        return objs
    # un solo oggetto: i pezzi con materiali diversi vanno su slot diversi
    slots = []; geos = []
    for pc in PCS:
        mats = piece_mats(pc, s, MAT, cfg)
        idx = []
        for m in mats:
            if m not in slots: slots.append(m)
            idx.append(slots.index(m))
        for i, pd in enumerate(pc['parts']):
            V, F, M_, U, S = geo_of(pc, i, pd)
            geos.append(((V, F, [idx[m] for m in M_], U, S), pd['M']))
    return [make_object(f'{pref}_Mezzo', geos, slots, coll, loc)]

def reset_coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c:
        for ch in list(c.children_recursive) + [c]:
            for o in list(ch.objects):
                d = o.data; bpy.data.objects.remove(o, do_unlink=True)
                if d is not None and d.users == 0:
                    if isinstance(d, bpy.types.Mesh): bpy.data.meshes.remove(d)
                    elif isinstance(d, bpy.types.Armature): bpy.data.armatures.remove(d)   # LOD snodabili
                    else: bpy.data.curves.remove(d)
        for ch in list(c.children_recursive): bpy.data.collections.remove(ch)
        bpy.data.collections.remove(c)
    c = bpy.data.collections.new(name)
    (parent.children if parent else bpy.context.scene.collection.children).link(c)
    return c


# ---------- mattoni per LOD4 e LOD5 (disegnati nel file del mezzo) ----------
def quad(p0, p1, p2, p3):
    # rettangolo senza spessore (2 triangoli): finestrini, luci, strati del gettone
    return ([tuple(p0), tuple(p1), tuple(p2), tuple(p3)], [(0, 1, 2, 3)], [0], [[(0, 0), (1, 0), (1, 1), (0, 1)]], [])

def estruso(profilo, y0, y1):
    # profilo nel piano x-z estruso lungo y: volume a blocchi, bordi dritti
    g = build_panel(profilo, t=y1 - y0, rough=0.0, warp=0.0, nick=0.0, step=50.0)
    return g, frame((0, y0, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0))

def lastra(x0, x1, y0, y1, z, t):
    # lastra orizzontale (tetti, coperchi)
    return build_panel(rect(x0, y0, x1, y1), t=t, rough=0, warp=0, nick=0, step=50.0), frame((0, 0, z), (1, 0, 0), (0, 1, 0))

def disco_piatto(cx, cy, r, z, n=6):
    V = [(cx, cy, z)] + [(cx + r*math.cos(2*math.pi*i/n), cy + r*math.sin(2*math.pi*i/n), z) for i in range(n)]
    F = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
    return (V, F, [0]*n, [[(0, 0), (1, 0), (1, 1)]]*n, [])

def ruote_ottagono(MAT, assi, raggio, za, y_out, larg=0.30):
    out = []
    for cx in assi:
        for s in (-1, 1):
            y0, y1 = sorted((s*(y_out - larg), s*(y_out + 0.02)))
            out.append((build_panel(circle(0, 0, raggio, 8, math.pi/8), t=y1 - y0, rough=0, warp=0, nick=0, step=50),
                        frame((cx, y0, za), (1, 0, 0), (0, 0, 1), (0, 1, 0))))
    return [MAT['kraft'], MAT['bordo'], MAT['kraft']], out

def gettone(MAT, x0, x1, w, strati, punta=0.55, r=0.35, zt=0.15):
    # LOD5: gettone di cartone con la punta a freccia sul muso (verso di marcia)
    # strati: lista di (materiale, [geo,...]) disegnati sopra, in ordine
    out = arc(x0 + r, -w + r, r, math.pi, 1.5*math.pi, 3) + [(x1 - punta, -w), (x1, 0.0), (x1 - punta, w)] + arc(x0 + r, w - r, r, 0.5*math.pi, math.pi, 3)
    chip = build_panel(out, t=zt, rough=0.0, warp=0.0, nick=0.0, step=50.0)
    g = [([MAT['kraft'], MAT['bordo'], MAT['interno']], [(chip, Matrix())])]
    for k, (m, geos) in enumerate(strati):
        z = zt + 0.004*(k + 1)
        g.append(([m]*3, [(gg(z) if callable(gg) else gg, Matrix()) for gg in geos]))
    return g

def rettangolo_a(x0, x1, y0, y1):
    return lambda z: quad((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z))

def unisci(nome, gruppi, coll, loc):
    # gruppi: lista di (materiali [faccia, bordo, retro], [(geo, matrice), ...]) -> un solo oggetto
    slots = []; geos = []
    for mats, items in gruppi:
        idx = []
        for m in mats:
            if m not in slots: slots.append(m)
            idx.append(slots.index(m))
        for (V, F, M_, U, S), Mx in items:
            geos.append(((V, F, [idx[m] for m in M_], U, S), Mx))
    return make_object(nome, geos, slots, coll, loc)

# ---------- fila di confronto ----------
VISTE = {0: 'a bordo, a piedi', 1: 'zoom e modellino sul tavolo', 2: "volo d'uccello",
         3: '3D tabellone vicino', 4: '3D tabellone lontano', 5: "2D dall'alto"}

def fila_lod(root_nome, cfg, PCS, lod4, lod5, riga_y, x0, passo, extra=None):
    # costruisce LOD0..LOD5 in fila con il cartellino "LODn · vista · triangoli".
    # LOD0 = copia del mezzo finito del tutorial; extra(L, coll, MAT, loc) aggiunge
    # pezzi speciali (es. la scritta della linea) ai LOD0-2
    MAT = make_materials(); root = reset_coll(root_nome)
    fs = cfg['final_stage']; src = None
    for c in bpy.data.collections:
        if c.name.startswith(f'Fase_{fs}_') and any(o.name.startswith(f'F{fs}_') for o in c.objects): src = c
    conteggi = {}
    for L in range(6):
        c = reset_coll(f'{root_nome}_{L}', root); loc = Vector((x0 + L*passo, riga_y, 0.0)); objs = []
        if L == 0:
            org = next(o.location for o in src.objects if o.type == 'MESH' and o.name.startswith(f'F{fs}_'))
            for o in src.objects:
                if o.name.startswith(f'F{fs}_') and o.type in ('MESH', 'FONT'):
                    n = o.copy(); n.name = 'L0_' + o.name[len(f'F{fs}_'):]
                    n.matrix_world = Matrix.Translation(loc - org) @ o.matrix_world; c.objects.link(n); objs.append(n)
        elif L <= 3:
            objs = costruisci(pezzi_lod(PCS, cfg, L), MAT, cfg, c, loc, f'L{L}', unisci=(L == 3))
            if extra and L <= 2: extra(L, c, MAT, loc)
        elif L == 4: objs = lod4(MAT, c, loc)
        else: objs = lod5(MAT, c, loc)
        n = triangoli(objs); conteggi[L] = n
        cartellino(f'LOD{L} · {VISTE[L]} · {n:,} tri'.replace(',', '.'), (loc.x, riga_y - cfg['label_dy'], 0.0), c, MAT)
    return conteggi
