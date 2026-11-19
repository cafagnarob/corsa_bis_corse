# =====================================================================
# cb_edifici.py — Corsa Bis · centro storico: il borgo arrampicato di cartone
# Cosa fa: il kit del borgo (moduli di facciata da 2 m, bottega, tetti,
#   scale, balconi, panni), il generatore genera_palazzina(seme), l'isolato
#   con vicolo isolato() e le funzioni di prova run_campioni() e run_isolato().
#   L'export per il gioco è in cb_export_borgo.py.
#   Regola del colore: facciate (intonaco) dipinte a tempera, con la
#   vernice scrostata sugli spigoli; kraft nudo per tutto ciò che è
#   aggiunto o strutturale (tetti ondulati, sopraelevazioni, scale,
#   ballatoi, ringhiere, pali, persiane, serbatoi).
#   Metri reali (gioco ×5,2), modulo 2 m in larghezza, piano terra 4 m,
#   piani superiori 3 m; davanti verso +X (la strada), origine all'angolo
#   in basso a destra della facciata, Z = 0; nomi dei pezzi espliciti.
#   Le funzioni del primo campione (volume, falda, persiane, scala, panni)
#   restano: il kit le riusa.
# Uso: Run Script (richiede cb_lib.py nel Text Editor), oppure
#   run_campioni() / run_isolato() dalla console.
# =====================================================================
import bpy, math, random
from mathutils import Vector, Matrix

def _carica(nome):
    t = bpy.data.texts.get(nome)
    if t is not None: return t.as_string()
    raise FileNotFoundError(nome + ': aprilo nel Text Editor')

if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))

MODULO, PIANO = 2.0, 3.0          # GDD: modulo 2 x 3 m
T = 0.08                          # spessore del cartone delle pareti
SC = 1.5                          # scala del cartone (onda del bordo, scrostature)
FIN = (0.9, 1.35, 1.0)            # finestra: larghezza, altezza, davanzale dal pavimento
PORTA = (1.0, 2.2)
BOTTEGA = (1.6, 2.4)
INTONACI = {'ocra': (0.74, 0.45, 0.14), 'terracotta': (0.66, 0.26, 0.13), 'siena': (0.82, 0.58, 0.20),
            'rosa': (0.80, 0.45, 0.38), 'crema': (0.86, 0.74, 0.52)}

def materiali():
    M = {k: mat_vernice('CB_B_Intonaco_' + k, (*c, 1), 0.66, SC*0.3) for k, c in INTONACI.items()}
    M['kraft'] = mat_kraft('CB_B_Kraft', 1.0, SC*0.3)
    M['bordo'] = mat_bordo('CB_B_Bordo', SC*0.25)
    M['interno'] = mat_kraft('CB_B_Interno', 0.30, SC*0.3)        # dentro le finestre: cartone in ombra
    M['legno'] = mat_legno('CB_B_Legno')
    M['carta'] = mat_plain('CB_B_Carta', (0.90, 0.88, 0.82, 1), 0.85)
    M['spago'] = mat_plain('CB_B_Spago', (0.62, 0.52, 0.38, 1), 0.9)
    return M

def kw(seed):
    return dict(rough=0.015, warp=0.0, nick=0.03, step=0.25, seed=seed, scala=1.0)

# ---------- pezzo 1: volume con le aperture ----------
def aperture_parete(larg, alt, piani, terra=None, lato_fin=True):
    # buchi di una parete larga "larg" (moduli centrati) per "piani" piani; terra = lista per modulo
    # del piano terra: 'porta', 'bottega', 'finestra' o None
    n = max(1, int(round(larg/MODULO))); x0 = -larg/2 + (larg - n*MODULO)/2 + MODULO/2
    holes = []
    for p in range(piani):
        for k in range(n):
            cx = x0 + k*MODULO; z0 = p*PIANO
            tipo = (terra[k] if terra and k < len(terra) else 'finestra') if p == 0 else 'finestra'
            if tipo == 'porta': w, h, s = PORTA[0], PORTA[1], 0.0
            elif tipo == 'bottega': w, h, s = BOTTEGA[0], BOTTEGA[1], 0.0
            elif tipo == 'finestra' and lato_fin: w, h, s = FIN
            else: continue
            if z0 + s + h > alt - 0.3: continue
            holes.append(rect(cx - w/2, z0 + s + 0.02, cx + w/2, z0 + s + h))
    return holes

def volume(nome, coll, M, centro, larg, prof, piani, intonaco, terra=None, finestre_lati=True, seed=0, alt=None):
    # scatola: larg lungo Y (facciata), prof lungo X; facciata davanti verso +X
    alt = alt or piani*PIANO + 0.4
    c = Vector(centro); geos = []
    def parete(outline, holes, fr, s):
        V, F, Mi, U, S = build_panel(outline, holes=holes, t=T, **kw(s))
        geos.append(((V, F, Mi, U, S), fr))
    hx, hy = prof/2, larg/2
    # davanti (+X) e dietro (-X): pannelli larghi tutta la facciata
    parete(rect(-hy, 0, hy, alt), aperture_parete(larg, alt, piani, terra), frame((c.x + hx - T, c.y, c.z), (0, 1, 0), (0, 0, 1), (1, 0, 0)), seed + 1)
    parete(rect(-hy, 0, hy, alt), aperture_parete(larg, alt, piani, None, finestre_lati), frame((c.x - hx + T, c.y, c.z), (0, -1, 0), (0, 0, 1), (-1, 0, 0)), seed + 2)
    # fianchi (+Y, -Y): tra le due facciate
    for s, sd in ((1, 3), (-1, 4)):
        parete(rect(-(hx - T), 0, hx - T, alt), aperture_parete(prof - 2*T, alt, piani, None, finestre_lati),
               frame((c.x, c.y + s*(hy - T), c.z), (-s, 0, 0), (0, 0, 1), (0, s, 0)), seed + sd)
    # solaio di copertura (sotto il tetto) e pavimento
    for z, n, sd in ((alt - T, 1, 5), (0.0, -1, 6)):
        V, F, Mi, U, S = build_panel(rect(-hx + T, -hy + T, hx - T, hy - T), t=T, **kw(seed + sd))
        geos.append(((V, F, Mi, U, S), frame((c.x, c.y, c.z + z + (T if n < 0 else 0)), (1, 0, 0), (0, n, 0), (0, 0, n))))
    return make_object(nome, geos, [M[intonaco], M['bordo'], M['interno']], coll)

# ---------- pezzo 2: tetti, sopraelevazioni, serbatoi ----------
ONDA, AMP, TO = 0.20, 0.045, 0.025      # 10 onde per modulo da 2 m: i moduli di falda si saldano      # passo e ampiezza dell'onda, spessore del foglio ondulato

CAMPIONI_ONDA = 4      # punti per onda: 4 bastano a leggere l'ondulato e dimezzano i triangoli
def ondulato(L, W, pendenza=0.0, seed=0, campioni=None):
    # foglio ondulato senza copertina: lungo X (L, in discesa), onde lungo Y (W).
    # Restituisce la geometria nel formato di build_panel: facce 0 = sopra (kraft), 1 = bordi, 2 = sotto
    rng = random.Random(seed); n = max(4, int(W/ONDA*(campioni or CAMPIONI_ONDA))); m = max(2, int(L/1.0) + 1)
    V, F, Mi, U, S = [], [], [], [], []
    def z_onda(j): return AMP*math.sin(2*math.pi*(j/n)*W/ONDA)
    # griglia sopra e sotto
    for strato, dz in ((0, 0.0), (1, -TO)):
        for i in range(m + 1):
            x = -L/2 + L*i/m + rng.uniform(-0.01, 0.01)*(0 < i < m)
            for j in range(n + 1):
                y = -W/2 + W*j/n
                V.append((x, y, z_onda(j) + dz - math.tan(pendenza)*x))
    off = (m + 1)*(n + 1); idx = lambda s_, i, j: s_*off + i*(n + 1) + j
    for i in range(m):
        for j in range(n):
            a, b, c, d = idx(0, i, j), idx(0, i + 1, j), idx(0, i + 1, j + 1), idx(0, i, j + 1)
            F.append((a, b, c, d)); Mi.append(0); U.append([(V[k][0], V[k][1]) for k in (a, b, c, d)])
            a, b, c, d = idx(1, i, j), idx(1, i, j + 1), idx(1, i + 1, j + 1), idx(1, i + 1, j)
            F.append((a, b, c, d)); Mi.append(2); U.append([(V[k][0], V[k][1]) for k in (a, b, c, d)])
    # bordi: davanti e dietro mostrano il profilo dell'onda
    for i in (0, m):
        for j in range(n):
            q = (idx(0, i, j), idx(0, i, j + 1), idx(1, i, j + 1), idx(1, i, j))
            F.append(q if i == m else q[::-1]); Mi.append(1); U.append([(V[k][1], V[k][2]) for k in q])
    for j in (0, n):
        for i in range(m):
            q = (idx(0, i, j), idx(0, i + 1, j), idx(1, i + 1, j), idx(1, i, j))
            F.append(q[::-1] if j == n else q); Mi.append(1); U.append([(V[k][0], V[k][2]) for k in q])
    return V, F, Mi, U, S

def falda(nome, coll, M, centro, L, W, pendenza_gradi=10, sporto=0.3, seed=0):
    # tetto a una falda che scende verso -X (dietro), appoggiato sul volume; centro = centro del bordo alto del volume
    g = ondulato(L + 2*sporto, W + 2*sporto, math.radians(pendenza_gradi), seed)
    z = Vector(centro).z + AMP + 0.02 + math.tan(math.radians(pendenza_gradi))*(L/2)   # il bordo basso appoggia sul muro di dietro
    geos = [(g, Matrix.Translation((centro[0], centro[1], z)) @ Matrix.Rotation(math.pi, 4, 'Z'))]
    # la falda sale verso il davanti (+X): chiudo lo spazio sopra il muro con due triangoli sui fianchi
    # e una striscia sul davanti, di kraft (sono pezzi aggiunti)
    h = math.tan(math.radians(pendenza_gradi))*L; cx, cy, cz = centro
    for sgn in (1, -1):
        tri = [(-L/2, 0.0), (L/2, 0.0), (L/2, h)]
        geos.append((build_panel(tri, t=T, **kw(seed + 3 + sgn)), frame((cx, cy + sgn*W/2 - (T if sgn > 0 else 0), cz), (1, 0, 0), (0, 0, 1), (0, sgn, 0) if False else (0, 1, 0))))
    geos.append((build_panel(rect(-W/2, 0.0, W/2, h), t=T, **kw(seed + 6)), frame((cx + L/2 - T, cy, cz), (0, 1, 0), (0, 0, 1), (1, 0, 0))))
    return make_object(nome, geos, [M['kraft'], M['bordo'], M['interno']], coll)

def serbatoio(nome, coll, M, base, r=0.55, h=1.0, n_onde=22):
    # ondulato arrotolato: cilindro con le costole verticali, coperchio piatto, kraft
    k = n_onde*4; V, F, Mi, U = [], [], [], []
    for z in (0.0, h):
        for i in range(k):
            a = 2*math.pi*i/k; rr = r + 0.025*math.sin(n_onde*a)
            V.append((base[0] + rr*math.cos(a), base[1] + rr*math.sin(a), base[2] + z))
    for i in range(k):
        j = (i + 1) % k; F.append((i, j, j + k, i + k)); Mi.append(0)
        U.append([(i/k*2*math.pi*r, 0), ((i + 1)/k*2*math.pi*r, 0), ((i + 1)/k*2*math.pi*r, h), (i/k*2*math.pi*r, h)])
    c = len(V); V.append((base[0], base[1], base[2] + h + 0.06))
    for i in range(k):
        j = (i + 1) % k; F.append((i + k, j + k, c)); Mi.append(1); U.append([(0, 0)]*3)
    me = bpy.data.meshes.new(nome); me.from_pydata(V, [], F); uvl = me.uv_layers.new(name='UVMap')
    for p, mi, uu in zip(me.polygons, Mi, U):
        p.material_index = mi; p.use_smooth = mi == 0
        for q, li in enumerate(p.loop_indices): uvl.data[li].uv = uu[q]
    me.materials.append(M['kraft']); me.materials.append(M['interno']); me.update()
    o = bpy.data.objects.new(nome, me); coll.objects.link(o); return o

# ---------- pezzo 3: facciata ----------
def finestre(larg, piani, terra=None):
    # (centro lungo la facciata, quota del fondo, larghezza, altezza, tipo) di ogni apertura
    n = max(1, int(round(larg/MODULO))); x0 = -larg/2 + (larg - n*MODULO)/2 + MODULO/2; out = []
    for p in range(piani):
        for k in range(n):
            tipo = (terra[k] if terra and k < len(terra) else 'finestra') if p == 0 else 'finestra'
            w, h, sd = {'porta': (PORTA[0], PORTA[1], 0.0), 'bottega': (BOTTEGA[0], BOTTEGA[1], 0.0)}.get(tipo, FIN)
            if tipo: out.append((x0 + k*MODULO, p*PIANO + sd + 0.02, w, h, tipo, p))
    return out

def persiane(nome, coll, M, faccia_x, cy, larg, piani, terra, prob=0.7, seed=0):
    # due ante di kraft per finestra, incernierate ai lati, aperte di 100-150 gradi (socchiuse verso fuori)
    rng = random.Random(seed); geos = []
    for c, zb, w, h, tipo, p in finestre(larg, piani, terra):
        if tipo != 'finestra' or rng.random() > prob: continue
        for lato in (1, -1):
            a = math.radians(rng.uniform(100, 150))
            u = Vector((math.sin(a), -lato*math.cos(a), 0)) if lato > 0 else Vector((math.sin(a), math.cos(a), 0))
            u = Vector((math.sin(a), lato*(-math.cos(a)) if False else 0, 0)) if False else u
            hinge = Vector((faccia_x + 0.01, cy + c + lato*w/2, zb))
            g = build_panel(rect(0, 0, w/2, h), t=0.03, **kw(rng.randrange(999)))
            v = Vector((0, 0, 1)); n = u.cross(v)
            geos.append((g, frame(tuple(hinge), tuple(u), tuple(v), tuple(n))))
            # tre listelli orizzontali dipinti dal taglio (righe del bordo): un foglietto sottile sopra
            for q in (0.25, 0.5, 0.75):
                gl = build_panel(rect(0.04, h*q - 0.03, w/2 - 0.04, h*q + 0.03), t=0.012, rough=0, warp=0, nick=0, step=50.0)
                geos.append((gl, frame(tuple(hinge + n*0.03), tuple(u), tuple(v), tuple(n))))
    return make_object(nome, geos, [M['kraft'], M['bordo'], M['kraft']], coll)

def palo(p0, h, r=0.055):
    return build_panel(circle(0, 0, r, 8), t=h, rough=0, warp=0, nick=0, step=50.0), Matrix.Translation(p0)

def ringhiera(geos, p0, direzione, lung, alt=0.9, seed=0, campioni=None):
    # striscia di ondulato in piedi (costole verticali) lungo "direzione" (asse X o Y del mondo)
    g = ondulato(alt, lung, 0.0, seed, campioni)
    d = Vector(direzione).normalized(); z = Vector((0, 0, 1)); n = z.cross(d)
    # colonne: x locale -> alto, y locale -> lungo la ringhiera, z locale -> normale
    m = Matrix(((z.x, d.x, -n.x if False else z.cross(d).x * -1, 0), (z.y, d.y, -z.cross(d).y, 0), (z.z, d.z, -z.cross(d).z, 0), (0, 0, 0, 1)))
    m.translation = Vector(p0) + d*lung/2 + z*alt/2
    geos.append((g, m))

def balcone(nome, coll, M, faccia_x, cy, z, larg=2.6, prof=0.9, pali=True, seed=0):
    geos = []
    geos.append((build_panel(rect(faccia_x, cy - larg/2, faccia_x + prof, cy + larg/2), t=0.12, **kw(seed)), Matrix.Translation((0, 0, z - 0.12))))
    ringhiera(geos, (faccia_x + prof - 0.03, cy - larg/2, z), (0, 1, 0), larg, seed=seed + 1)
    for sgn in (1, -1): ringhiera(geos, (faccia_x, cy + sgn*(larg/2 - 0.03), z), (1, 0, 0), prof - 0.03, seed=seed + 2)
    o = make_object(nome, geos, [M['kraft'], M['bordo'], M['interno']], coll)
    if pali:
        gp = [palo((faccia_x + prof - 0.1, cy + sgn*(larg/2 - 0.1), 0.0), z - 0.12) for sgn in (1, -1)]
        make_object(nome + '_Pali', gp, [M['legno']]*3, coll)
    return o

def pensilina(nome, coll, M, faccia_x, cy, z, larg=1.4, prof=0.7, seed=0):
    g = ondulato(prof, larg, math.radians(18), seed)
    m = Matrix.Translation((faccia_x + prof/2, cy, z + math.tan(math.radians(18))*prof/2*0))
    return make_object(nome, [(g, m)], [M['kraft'], M['bordo'], M['interno']], coll)

# ---------- pezzo 4: scala esterna e panni ----------
def scala(nome, coll, M, x0, y0, n=10, alzata=0.3, pedata=0.3, larg=0.9, t=0.06, seed=0):
    # striscia ondulata piegata a gradini, sale verso -X; i gradini mostrano l'onda del cartone sul taglio
    up = [(0.0, 0.0)]
    for i in range(n):
        up += [(i*pedata, (i + 1)*alzata), ((i + 1)*pedata, (i + 1)*alzata)]
    lo = [(max(0.0, x) + t, max(0.0, z - t)) for x, z in up]
    lo[0] = (t, 0.0)
    prof = up + list(reversed(lo))
    g = build_panel(prof, t=larg, **kw(seed))
    return make_object(nome, [(g, frame((x0, y0, 0), (-1, 0, 0), (0, 0, 1), (0, 1, 0)))], [M['kraft'], M['bordo'], M['interno']], coll)

def filo_panni(nome, coll, M, x, y0, y1, z, n=4, seed=0):
    rng = random.Random(seed); pts = []
    for k in range(21):
        f = k/20; pts.append((x, y0 + (y1 - y0)*f, z - 0.18*math.sin(math.pi*f)))
    cu = bpy.data.curves.new(nome, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.012; cu.bevel_resolution = 0
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (*p, 1)
    ob = bpy.data.objects.new(nome + '_tmp', cu); coll.objects.link(ob)
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu); me.name = nome; me.materials.append(M['spago'])
    fo = bpy.data.objects.new(nome, me); coll.objects.link(fo)
    # bacchette ai due capi, piantate nel muro
    make_object(nome + '_Bacchette', [(build_panel(circle(0, 0, 0.025, 6), t=0.5, rough=0, warp=0, nick=0, step=50.0),
                                       frame((x - 0.45, yy, z), (0, 1, 0), (0, 0, 1), (1, 0, 0))) for yy in (y0, y1)], [M['legno']]*3, coll)
    # panni: magliette e teli di carta appesi al filo, nel piano Y-Z
    maglia = [(-0.28, 0.0), (-0.10, 0.0), (-0.07, -0.08), (0.07, -0.08), (0.10, 0.0), (0.28, 0.0), (0.33, -0.18), (0.20, -0.22),
              (0.20, -0.62), (-0.20, -0.62), (-0.20, -0.22), (-0.33, -0.18)]
    telo = [(-0.26, 0.0), (0.26, 0.0), (0.24, -0.55), (-0.24, -0.55)]
    geos = []
    for k in range(n):
        f = (k + 0.7)/(n + 0.4); yy = y0 + (y1 - y0)*f; zz = z - 0.18*math.sin(math.pi*f) - 0.01
        forma = maglia if rng.random() < 0.6 else telo
        rot = Matrix.Rotation(math.radians(rng.uniform(-6, 6)), 4, 'X')
        geos.append((build_panel(forma, t=0.01, rough=0.004, warp=0, nick=0.006, step=0.1, seed=k, bottom_mat=0), frame((x - 0.005, yy, zz), (0, 1, 0), (0, 0, 1), (1, 0, 0)) @ rot))
    make_object(nome + '_Panni', geos, [M['carta'], M['carta'], M['carta']], coll)
    return fo

# =====================================================================
# KIT DEL BORGO (regole del GDD, "Regole del kit"):
#   - cella base 2 x 2 m, piano terra alto 4 m, piani superiori 3 m;
#   - ogni pezzo ha l'origine sull'angolo in basso a destra guardando la
#     facciata: il modulo occupa y da 0 a -2 (cresce verso sinistra), z da 0
#     all'altezza, x da -T a 0 (lo spessore va verso l'interno), davanti +X;
#   - nomi espliciti, gli stessi che userà il codice (Terra_Vetrina,
#     Modulo_Finestra, Persiana...); i pezzi stanno nella collezione Kit_Borgo;
#   - slot 0 = intonaco (segnaposto KIT_Intonaco): il colore lo dà ogni
#     palazzo (qui con il materiale per oggetto, nel gioco per istanza);
#     slot 1 = bordo ondulato, slot 2 = interno scuro, slot 3 = kraft.
# =====================================================================
H_TERRA, H_PIANO = 4.0, 3.0
APERTURE = {   # tipo: (altezza del modulo, buchi in coordinate (u lungo la facciata, z))
    'Terra_Parete': (H_TERRA, []),
    'Terra_Porta': (H_TERRA, [rect(0.5, 0.02, 1.5, 2.4)]),
    'Terra_Vetrina': (H_TERRA, [rect(0.2, 0.02, 1.8, 2.9)]),
    'Terra_Serranda': (H_TERRA, [rect(0.2, 0.02, 1.8, 2.9)]),
    'Terra_Portone': (H_TERRA, [[(0.4, 0.02), (1.6, 0.02)] + [(1.0 + 0.6*math.cos(a), 2.4 + 0.6*math.sin(a)) for a in [math.pi*k/12 for k in range(13)]]]),
    'Modulo_Parete': (H_PIANO, []),
    'Modulo_Finestra': (H_PIANO, [rect(0.55, 1.0, 1.45, 2.35)]),
    'Modulo_Portafinestra': (H_PIANO, [rect(0.55, 0.02, 1.45, 2.35)]),
}
FINESTRA_PIANO = (0.55, 1.45, 1.0, 2.35)       # u0, u1, z0, z1 della finestra (per le persiane)

def mat_kit():
    m = bpy.data.materials.get('KIT_Intonaco') or mat_plain('KIT_Intonaco', (0.9, 0.9, 0.9, 1), 0.8)
    return m

def m_modulo():
    # dal piano del foglio (u, z) al modulo: u -> -Y, z -> +Z, spessore verso +X da -T a 0
    return frame((-T, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))

def costruisci_kit(M):
    coll = bpy.data.collections.get('Kit_Borgo')
    if coll:
        for o in list(coll.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0: bpy.data.meshes.remove(d)
    else:
        coll = bpy.data.collections.new('Kit_Borgo'); bpy.context.scene.collection.children.link(coll)
    for me in [m for m in bpy.data.meshes if m.name.startswith(('Terra_', 'Modulo_', 'Persiana', 'Marcapiano', 'Cornicione')) and m.users == 0]:
        bpy.data.meshes.remove(me)
    mats = [mat_kit(), M['bordo'], M['interno'], M['kraft']]; kit = {}
    for i, (nome, (h, buchi)) in enumerate(APERTURE.items()):
        geos = [(build_panel(rect(0, 0, MODULO, h), holes=buchi, t=T, **kw(100 + i)), m_modulo())]
        if nome == 'Terra_Serranda':
            g = ondulato(1.6, 2.86, 0.0, 7)
            V, F, Mi, U, S = g
            geos.append(((V, F, [3 if x == 0 else x for x in Mi], U, S),
                         Matrix(((0, 0, 1, -0.05), (1, 0, 0, -1.0), (0, 1, 0, 1.45), (0, 0, 0, 1)))))   # coste orizzontali, dentro il vano
        kit[nome] = make_object(nome, geos, mats, coll)
    # fasce: marcapiano (sottile) e cornicione (più sporgente), lunghe un modulo, dipinte come l'intonaco
    for nome, h, sp in (('Marcapiano', 0.16, 0.06), ('Cornicione', 0.30, 0.16)):
        g = build_panel(rect(0, 0, MODULO, h), t=sp, **kw(len(nome)))
        kit[nome] = make_object(nome, [(g, frame((0, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0)))], mats, coll)
    # persiana: un'anta incernierata nell'origine, chiusa copre verso -Y; ruotata attorno a Z si apre
    w, h = (FINESTRA_PIANO[1] - FINESTRA_PIANO[0])/2, FINESTRA_PIANO[3] - FINESTRA_PIANO[2]
    geos = [(build_panel(rect(0, 0, w, h), t=0.03, **kw(77)), frame((0.005, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0)))]
    for q in (0.25, 0.5, 0.75):
        geos.append((build_panel(rect(0.04, h*q - 0.03, w - 0.04, h*q + 0.03), t=0.012, rough=0, warp=0, nick=0, step=50.0),
                     frame((0.035, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
    kit['Persiana'] = make_object('Persiana', geos, [M['kraft'], M['bordo'], M['kraft']], coll)
    for i, o in enumerate(kit.values()):
        o.location = (-30.0, 30.0 - 3.0*i, 0)          # in fila, per guardarli
    return kit

# =====================================================================
# KIT, seconda parte: bottega, tetti e vita come pezzi riusabili
#   (stessa origine dei moduli: angolo in basso a destra, y da 0 a -2)
# =====================================================================
FALDA_A = math.radians(10)          # pendenza delle falde
def mat_strisce(nome, c1, c2, passo=0.3):
    # tela della tenda a strisce: dalla vernice di cb_lib, con le strisce lungo la U del foglio
    m = mat_vernice('CB_B_Tenda_' + nome, (*c1, 1), 0.78, SC*0.3); nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'); sorg = b.inputs['Base Color'].links[0].from_socket
    uv = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(uv.outputs['UV'], sep.inputs[0])
    d = nt.nodes.new('ShaderNodeMath'); d.operation = 'DIVIDE'; nt.links.new(sep.outputs['X'], d.inputs[0]); d.inputs[1].default_value = passo
    f = nt.nodes.new('ShaderNodeMath'); f.operation = 'PINGPONG'; nt.links.new(d.outputs[0], f.inputs[0]); f.inputs[1].default_value = 1.0
    st = nt.nodes.new('ShaderNodeMath'); st.operation = 'GREATER_THAN'; nt.links.new(f.outputs[0], st.inputs[0]); st.inputs[1].default_value = 0.5
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; nt.links.new(st.outputs[0], mx.inputs[0])
    nt.links.new(sorg, mx.inputs[6]); mx.inputs[7].default_value = (*c2, 1); nt.links.new(mx.outputs[2], b.inputs['Base Color'])
    return m

def rimappa(g, mappa):
    V, F, Mi, U, S = g
    return V, F, [mappa.get(m, m) for m in Mi], U, S

def testo_mesh(testo, size, estrudi=0.01):
    cu = bpy.data.curves.new('tmp_testo', 'FONT'); cu.body = testo; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    cu.size = size; cu.extrude = estrudi; cu.resolution_u = 2
    ob = bpy.data.objects.new('tmp_testo', cu); bpy.context.scene.collection.objects.link(ob)
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    V = [tuple(v.co) for v in me.vertices]; F = [tuple(p.vertices) for p in me.polygons]
    bpy.data.meshes.remove(me)
    return V, F, [0]*len(F), [[(V[i][0], V[i][1]) for i in f] for f in F], []

def costruisci_kit2(M, kit, coll):
    mats = [mat_kit(), M['bordo'], M['interno'], M['kraft']]
    MK = [M['kraft'], M['bordo'], M['interno'], M['legno']]
    def pezzo(nome, geos, mm):
        o = bpy.data.objects.get(nome)
        if o: d = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(d)
        kit[nome] = make_object(nome, geos, mm, coll); return kit[nome]
    # ---- bottega: tenda a strisce sopra la vetrina (tela inclinata + mantovana a smerlo) ----
    a = math.radians(28); L = 0.95; z0 = 3.25
    v = Vector((math.cos(a), 0, -math.sin(a))); u = Vector((0, -1, 0)); n = u.cross(v)
    tela = build_panel(rect(0.1, 0, 1.9, L), t=0.012, **kw(301))
    fine = Vector((0, 0, z0)) + v*L
    sm = [(0.1, 0.0), (1.9, 0.0), (1.9, -0.22)] + [(1.9 - 0.15*k - 0.075, -0.22 - (0.05 if k % 2 == 0 else 0.0)) for k in range(12)] + [(0.1, -0.22)]
    sm = [(0.1, 0.0), (1.9, 0.0)] + [(1.9 - 1.8*k/12, -0.22 + 0.05*math.sin(math.pi*k)) for k in range(13)]
    smerlo = [(0.1, 0.0), (1.9, 0.0)] + [(1.9 - 0.15*k, -0.17 - 0.06*abs(math.sin(math.pi*k/2))) for k in range(13)]
    pezzo('Tenda', [(rimappa(tela, {2: 0}), frame((0.01, 0, z0), tuple(u), tuple(v), tuple(n))),
                    (rimappa(build_panel(smerlo, t=0.012, **kw(302)), {2: 0}), frame(tuple(fine), (0, -1, 0), (0, 0, 1), (1, 0, 0)))],
          [bpy.data.materials.get('KIT_Tenda') or mat_plain('KIT_Tenda', (0.8, 0.2, 0.15, 1), 0.8), M['bordo'], M['interno']])
    # ---- insegne: tavoletta dipinta con la scritta, sopra la vetrina ----
    for nome, scritta, fondo, ink in (('Bar', 'BAR', (0.70, 0.16, 0.12), (0.95, 0.92, 0.82)),
                                      ('Farmacia', 'FARMACIA', (0.15, 0.48, 0.25), (0.95, 0.95, 0.90)),
                                      ('Tabacchi', 'TABACCHI', (0.12, 0.20, 0.42), (0.95, 0.92, 0.82))):
        mf = mat_vernice('CB_B_Insegna_' + nome, (*fondo, 1), 0.80, SC*0.3); mi = mat_plain('CB_B_Scritta_' + nome, (*ink, 1), 0.6)
        tav = build_panel(rect(0.25, 0, 1.75, 0.42), t=0.04, **kw(310 + len(nome)))
        txt = testo_mesh(scritta, 0.26 if len(scritta) > 3 else 0.32)
        pezzo('Insegna_' + nome, [(tav, frame((0.0, 0, 3.02), (0, -1, 0), (0, 0, 1), (1, 0, 0))),
                                  (rimappa(txt, {0: 3}), frame((0.04, -1.0, 3.23), (0, 1, 0), (0, 0, 1), (1, 0, 0)))], [mf, M['bordo'], M['interno'], mi])   # verso +Y: si legge da sinistra a destra
    # ---- tetti: falda di ondulato larga un modulo, fronte rialzato e timpano, per profondità di 1-3 moduli ----
    for nd in (1, 2, 3):
        D = nd*MODULO + 2*T; Lf = D + 0.6; h = math.tan(FALDA_A)*D
        g = ondulato(Lf, MODULO, FALDA_A, 400 + nd)
        pezzo(f'Falda_{nd}', [(g, Matrix.Translation((-D/2, -MODULO/2, AMP + 0.02 + math.tan(FALDA_A)*D/2)) @ Matrix.Rotation(math.pi, 4, 'Z'))], MK[:3])
        pezzo(f'Falda_{nd}_Fronte', [(build_panel(rect(0, 0, MODULO, h), t=T, **kw(410 + nd)), m_modulo())], MK[:3])
        pezzo(f'Falda_{nd}_Timpano', [(build_panel([(-D, 0.0), (0.0, 0.0), (0.0, h)], t=T, **kw(420 + nd)), frame((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0)))], MK[:3])
    # ---- terrazzo: parapetto (un modulo), solaio (una cella 2 x 2) ----
    pezzo('Parapetto', [(build_panel(rect(0, 0, MODULO, 0.9), t=T, **kw(430)), m_modulo())], mats)
    pezzo('Solaio', [(build_panel(rect(-MODULO, -MODULO, 0, 0), t=T, **kw(431)), Matrix())], mats)
    # ---- comignolo (intonaco con il cappello di kraft) e antenna di bacchette ----
    pezzo('Comignolo', [(build_panel(rect(-0.25, -0.25, 0.25, 0.25), t=0.9, **kw(440)), Matrix()),
                        (rimappa(build_panel(rect(-0.34, -0.34, 0.34, 0.34), t=0.07, **kw(441)), {0: 3}), Matrix.Translation((0, 0, 0.9)))], mats)
    pa = [palo((0, 0, 0), 1.7, 0.025)]
    for z, l in ((1.35, 0.9), (1.6, 0.55)):
        pa.append((build_panel(circle(0, 0, 0.015, 6), t=l, rough=0, warp=0, nick=0, step=50.0), frame((0, -l/2, z), (1, 0, 0), (0, 0, 1), (0, 1, 0))))
    pezzo('Antenna', [(rimappa(g, {0: 3, 1: 3, 2: 3}), m) for g, m in pa], MK)
    # ---- serbatoio ----
    o = serbatoio('Serbatoio', coll, M, (0, 0, 0)); kit['Serbatoio'] = o
    # ---- scala esterna fino al primo piano e pianerottolo su pali ----
    nst = 13
    o = scala('Scala_Terra', coll, M, 0.0, 0.0, n=nst, alzata=H_TERRA/nst, pedata=0.3, seed=450); kit['Scala_Terra'] = o
    geos = [(build_panel(rect(-1.3, 0, 0, 0.9), t=0.12, **kw(451)), Matrix.Translation((0, 0, H_TERRA - 0.12)))]
    ringhiera(geos, (-1.3, 0.87, H_TERRA), (1, 0, 0), 1.3, seed=452)
    geos += [(rimappa(g, {0: 3, 1: 3, 2: 3}), m) for g, m in (palo((-xx, 0.8, 0.0), H_TERRA - 0.12) for xx in (0.1, 1.2))]
    pezzo('Pianerottolo', geos, MK)
    # ---- balcone (un modulo, sporge 0,9) e pali per il balcone del primo piano ----
    geos = [(build_panel(rect(0, -1.0 - 1.2, 0.9, -1.0 + 1.2), t=0.12, **kw(460)), Matrix.Translation((0, 0, -0.12)))]
    ringhiera(geos, (0.87, -2.2, 0), (0, 1, 0), 2.4, seed=461)
    for sg in (1, -1): ringhiera(geos, (0, -1.0 + sg*1.17, 0), (1, 0, 0), 0.87, seed=462)
    pezzo('Balcone', geos, MK[:3])
    pezzo('Balcone_Pali', [(rimappa(g, {0: 3, 1: 3, 2: 3}), m) for g, m in (palo((0.8, -1.0 + sg*1.1, -H_TERRA), H_TERRA - 0.12) for sg in (1, -1))], MK)
    # ---- pensilina sopra la porta ----
    g = ondulato(0.7, 1.4, math.radians(18), 470)
    pezzo('Pensilina', [(g, Matrix.Translation((0.35, -1.0, 2.55)))], MK[:3])
    # ---- filo di panni lungo 4 m (dalla facciata verso -Y, bacchette nel muro) ----
    fo = filo_panni('Panni_4m', coll, M, 0.4, 0.0, -4.0, 0.0, seed=480)
    parti = [fo, bpy.data.objects['Panni_4m_Bacchette'], bpy.data.objects['Panni_4m_Panni']]
    for o in parti: o.select_set(False)
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in parti: o.select_set(True)
    bpy.context.view_layer.objects.active = fo; bpy.ops.object.join(); kit['Panni_4m'] = fo
    for i, o in enumerate(kit.values()):
        o.location = (-30.0 - 6.0*(i // 12), 30.0 - 3.5*(i % 12), 0)
    return kit

# ---------- composizione di un palazzo con i pezzi del kit ----------
def istanza(nome, me, coll, parent, loc, rot_z, colore=None):
    o = bpy.data.objects.new(nome, me); coll.objects.link(o)
    o.parent = parent; o.location = loc; o.rotation_euler = (0, 0, rot_z)
    if colore is not None:
        o.material_slots[0].link = 'OBJECT'; o.material_slots[0].material = colore
    return o

def pareti(volume):
    # le 4 pareti di un volume largo n_w moduli e profondo n_d moduli, in coordinate del palazzo
    # (origine = angolo in basso a destra della facciata): (nome, origine, rotazione, n moduli, dir. sinistra)
    W, D = volume['n_w']*MODULO, volume['n_d']*MODULO + 2*T
    return [('Fronte', Vector((0, 0, 0)), 0.0, volume['n_w'], Vector((0, -1, 0))),
            ('Destra', Vector((-D + T, 0, 0)), math.pi/2, volume['n_d'], Vector((1, 0, 0))),
            ('Sinistra', Vector((-T, -W, 0)), -math.pi/2, volume['n_d'], Vector((-1, 0, 0))),
            ('Retro', Vector((-D, -W, 0)), math.pi, volume['n_w'], Vector((0, 1, 0)))]

def palazzo(nome, coll, kit, M, origine, n_w, n_d, piani, colore, fronte=None, lati=None, terra=True,
            fasce=True, persiane_prob=0.7, seed=0, rot=0.0, persiane_retro=True):
    # piani = piani sopra il terra (0, 1, 2...); fronte = {piano: [tipo per colonna]} (piano 0 = terra)
    # lati[(parete, piano, k)] = None: modulo non costruito (parete nascosta contro un'altra ala)
    # persiane_retro = False: niente persiane sul retro (lato cortile)
    rng = random.Random(seed)
    radice = bpy.data.objects.new(nome, None); coll.objects.link(radice)
    radice.location = origine; radice.rotation_euler = (0, 0, rot); radice.empty_display_size = 1.0
    vol = {'n_w': n_w, 'n_d': n_d}; quote = ([0.0] if terra else []) + [(H_TERRA if terra else 0.0) + H_PIANO*k for k in range(piani)]
    H = quote[-1] + (H_PIANO if piani else H_TERRA); finestre = []
    for parete, o, r, n, sx in pareti(vol):
        for li, z in enumerate(quote):
            e_terra = terra and li == 0
            for k in range(n):
                if parete == 'Fronte' and fronte and li in fronte: tipo = fronte[li][k]
                elif lati and (parete, li, k) in lati: tipo = lati[(parete, li, k)]
                elif e_terra: tipo = 'Terra_Porta' if (parete == 'Retro' and k == 0) else ('Terra_Parete' if rng.random() < 0.6 else 'Terra_Vetrina') if parete == 'Fronte' else 'Terra_Parete'
                else: tipo = 'Modulo_Finestra' if rng.random() < 0.8 else 'Modulo_Parete'
                if tipo is None: continue
                p = o + sx*MODULO*k + Vector((0, 0, z))
                istanza(f'{nome}_{parete}_{li}_{k}', kit[tipo].data, coll, radice, p, r, M[colore])
                if tipo == 'Modulo_Finestra' and (persiane_retro or parete != 'Retro'): finestre.append((p, r))
        # fasce: marcapiano sopra il terra, cornicione in cima
        if fasce:
            for k in range(n):
                p = o + sx*MODULO*k
                if terra and piani: istanza(f'{nome}_{parete}_Marcapiano_{k}', kit['Marcapiano'].data, coll, radice, p + Vector((0, 0, H_TERRA - 0.08)), r, M['crema'])
                istanza(f'{nome}_{parete}_Cornicione_{k}', kit['Cornicione'].data, coll, radice, p + Vector((0, 0, H - 0.30)), r, M['crema'])
    # solaio di copertura e pavimento (un foglio ciascuno)
    W, D = n_w*MODULO, n_d*MODULO + 2*T
    for z, sd in ((H - T, 1), (0.0, 2)):
        g = build_panel(rect(-D + T, -W + T, -T, -T), t=T, **kw(seed + sd))
        o = make_object(f'{nome}_Solaio_{sd}', [(g, Matrix.Translation((0, 0, z)))], [M[colore], M['bordo'], M['interno']], coll)
        o.parent = radice
    # persiane sulle finestre (due ante, socchiuse in modo diverso)
    for i, (p, r) in enumerate(finestre):
        if rng.random() > persiane_prob: continue
        u0, u1, z0, z1 = FINESTRA_PIANO
        for lato, u, base in (('Dx', u0, 0.0), ('Sx', u1, math.pi)):
            a = math.radians(rng.uniform(100, 150))
            ang = a if lato == 'Dx' else math.pi - a
            cerniera = p + Matrix.Rotation(r, 3, 'Z') @ Vector((0.0, -u, z0))
            istanza(f'{nome}_Persiana_{i}_{lato}', kit['Persiana'].data, coll, radice, cerniera, r + ang)
    return radice, H, W, D

def coll_borgo():
    c = bpy.data.collections.get('Borgo_Campione')
    if c:
        for o in list(c.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0: bpy.data.meshes.remove(d)
    else:
        c = bpy.data.collections.new('Borgo_Campione'); bpy.context.scene.collection.children.link(c)
    return c

# =====================================================================
# GENERATORE: una palazzina del borgo da un seme
#   stesse regole del kit; tutto è istanza dei pezzi, colore per oggetto
# =====================================================================
TENDE = (((0.78, 0.18, 0.14), (0.93, 0.89, 0.78)), ((0.16, 0.42, 0.26), (0.93, 0.89, 0.78)), ((0.17, 0.27, 0.52), (0.93, 0.89, 0.78)))
def mat_tende():
    return [bpy.data.materials.get(f'CB_B_Tenda_{i}') or mat_strisce(str(i), a, b) for i, (a, b) in enumerate(TENDE)]

def genera_palazzina(nome, coll, kit, M, origine, seed, rot=0.0, n_w=None, n_d=None, piani=None):
    # restituisce (radice, info) con info = larghezza/profondità/altezza, per affiancare le case nell'isolato
    rng = random.Random(seed); tende = mat_tende()
    n_w = n_w or rng.choice((1, 2, 2, 3)); n_d = n_d or rng.choice((2, 3)); piani = piani if piani is not None else rng.choice((1, 2, 2, 3))
    colore = rng.choice(list(INTONACI))
    # --- terra: almeno un ingresso, il resto botteghe o muro ---
    terra = [rng.choice(('Terra_Vetrina', 'Terra_Vetrina', 'Terra_Serranda', 'Terra_Parete')) for _ in range(n_w)]
    terra[rng.randrange(n_w)] = rng.choice(('Terra_Porta', 'Terra_Porta', 'Terra_Portone'))
    # --- piani: colonne coerenti (stessa apertura su tutti i piani), balcone al primo piano ---
    colonne = ['Modulo_Finestra' if rng.random() < 0.85 else 'Modulo_Parete' for _ in range(n_w)]
    k_balc = rng.randrange(n_w) if (piani and rng.random() < 0.5) else None
    fronte = {0: terra}
    for p in range(1, piani + 1):
        fronte[p] = [('Modulo_Portafinestra' if (k == k_balc and p == 1) else c) for k, c in enumerate(colonne)]
    scala = piani >= 1 and n_d == 3 and rng.random() < 0.5
    lati = {('Destra', 1, 0): 'Modulo_Portafinestra'} if scala else None
    radice, H, W, D = palazzo(nome, coll, kit, M, origine, n_w, n_d, piani, colore, fronte=fronte, lati=lati, seed=seed, rot=rot)
    def metti(pezzo, loc, r=0.0, col=None, suff=''):
        return istanza(f'{nome}_{pezzo}{suff}', kit[pezzo].data, coll, radice, Vector(loc), r, col)
    # --- bottega: tenda o insegna sulle vetrine, pensilina su qualche porta ---
    for k, tipo in enumerate(terra):
        y = -MODULO*k
        if tipo == 'Terra_Vetrina':
            if rng.random() < 0.6: metti('Tenda', (0, y, 0), col=rng.choice(tende), suff=f'_{k}')
            elif rng.random() < 0.7: metti(rng.choice(('Insegna_Bar', 'Insegna_Farmacia', 'Insegna_Tabacchi')), (0, y, 0), suff=f'_{k}')
        elif tipo == 'Terra_Porta' and rng.random() < 0.5: metti('Pensilina', (0, y, 0), suff=f'_{k}')
    if k_balc is not None:
        metti('Balcone', (0, -MODULO*k_balc, H_TERRA))
        if rng.random() < 0.5: metti('Balcone_Pali', (0, -MODULO*k_balc, H_TERRA))
    # --- scala esterna sul fianco destro fino al pianerottolo del primo piano ---
    if scala:
        metti('Scala_Terra', (-0.3, 0, 0)); metti('Pianerottolo', (-0.3 - 13*0.3, 0, 0))
    # --- tetto: falda di ondulato (con fronte e timpani) oppure terrazzo con parapetto ---
    cima = H; falda = rng.random() < 0.55
    if falda:
        for k in range(n_w):
            metti(f'Falda_{n_d}', (0, -MODULO*k, H), suff=f'_{k}')
            metti(f'Falda_{n_d}_Fronte', (0, -MODULO*k, H), col=M[colore], suff=f'_{k}')
        metti(f'Falda_{n_d}_Timpano', (0, 0, H), col=M[colore], suff='_Dx')
        metti(f'Falda_{n_d}_Timpano', (0, -W + T, H), col=M[colore], suff='_Sx')
        cima = H + math.tan(FALDA_A)*D
        if rng.random() < 0.7:
            xc = -D*rng.uniform(0.35, 0.7)
            metti('Comignolo', (xc, -rng.uniform(0.4, W - 0.4), H + math.tan(FALDA_A)*(D + xc) - 0.1), col=M[colore])
    else:
        for parete, o, r, n, sx in pareti({'n_w': n_w, 'n_d': n_d}):
            for k in range(n): metti('Parapetto', o + sx*MODULO*k + Vector((0, 0, H)), r, M[colore], f'_{parete}_{k}')
        # sopraelevazione abusiva in cartone grezzo nell'angolo posteriore sinistro
        if rng.random() < 0.6:
            Ds = MODULO + 2*T
            so, Hs, Ws, _ = palazzo(nome + '_Sopra', coll, kit, M, Vector((-D + Ds, -W + MODULO, H)), 1, 1, 1, 'kraft',
                                    terra=False, fasce=False, persiane_prob=0.0, seed=seed + 7)
            so.parent = radice
            metti('Falda_1', (-D + Ds, -W + MODULO, H + Hs), suff='_Sopra')
            cima = H + Hs
        if rng.random() < 0.7: metti('Serbatoio', (-D*0.3, -min(W*0.5, 1.2), H))
    if rng.random() < 0.5:
        metti('Antenna', (-D*rng.uniform(0.2, 0.5), -rng.uniform(0.5, max(0.6, W - 0.5)), cima - (0.15 if falda else 0)))
    # --- panni stesi davanti alla facciata (solo case di almeno 2 moduli) ---
    if n_w >= 2 and piani and rng.random() < 0.5:
        metti('Panni_4m', (0, 0, H_TERRA + H_PIANO*rng.randrange(piani) + 2.3))
    return radice, {'W': W, 'D': D, 'H': cima, 'n_w': n_w, 'n_d': n_d, 'piani': piani, 'colore': colore}

def run_campioni(semi=range(1, 9)):
    # una fila di palazzine generate, per controllare la varietà
    coll = coll_borgo(); M = materiali(); kit = costruisci_kit(M); kit = costruisci_kit2(M, kit, bpy.data.collections['Kit_Borgo'])
    y = 0.0
    for s in semi:
        r, info = genera_palazzina(f'P{s}', coll, kit, M, Vector((12.0, y, 0)), seed=s)
        y -= info['W'] + 2.0

# =====================================================================
# ISOLATO CON VICOLO: due file di palazzine faccia a faccia, panni tesi sopra il vicolo
#   fila A: facciate verso +X sul filo x = 0; fila B: facciate verso -X sul filo x = VICOLO
# =====================================================================
VICOLO = 4.0
def isolato(nome, coll, kit, M, origine, lunghezza=16.0, seme=100):
    rng = random.Random(seme); case = []
    for fila, x, rot, verso in (('A', 0.0, 0.0, -1), ('B', VICOLO, math.pi, 1)):
        y = 0.0 if verso < 0 else -lunghezza; i = 0
        while abs(y - (0.0 if verso < 0 else -lunghezza)) < lunghezza - 1.0:
            rientro = rng.uniform(0.0, 0.35)                      # facciate non allineate
            o = origine + Vector((x - rientro if verso < 0 else x + rientro, y, 0))
            r, info = genera_palazzina(f'{nome}_{fila}{i}', coll, kit, M, o, seed=seme*10 + len(case), rot=rot)
            case.append((fila, y, info)); y += verso*info['W']; i += 1
    # panni da una facciata all'altra, ad altezze diverse
    for j in range(3):
        yy = -rng.uniform(1.5, lunghezza - 1.5); z = H_TERRA + rng.uniform(1.8, 4.5)
        o = istanza(f'{nome}_Panni_{j}', kit['Panni_4m'].data, coll, None, origine + Vector((0.0, yy, z)), math.pi/2)
    return case

def run_isolato():
    c = bpy.data.collections.get('Borgo_Isolato')
    if c:
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    else:
        c = bpy.data.collections.new('Borgo_Isolato'); bpy.context.scene.collection.children.link(c)
    M = materiali(); kit = {o.name: o for o in bpy.data.collections['Kit_Borgo'].objects}
    return isolato('I', c, kit, M, Vector((45.0, 0.0, 0.0)))

# =====================================================================
# PALAZZI A CORTE (residenziale vicino al centro)
#   quattro ali attorno a un cortile: due ali lunghe (strada davanti e dietro)
#   e due ali corte sui fianchi; a filo strada, balconi in fila, cornicioni e
#   cornici delle finestre color stucco, tetti a due falde di ondulato kraft,
#   ballatoi con la ringhiera sul cortile (casa di ringhiera)
# =====================================================================
INTONACI_CORTE = {'rosa_antico': (0.80, 0.55, 0.48), 'salvia': (0.58, 0.64, 0.48), 'polvere': (0.56, 0.64, 0.70),
                  'paglia': (0.86, 0.72, 0.44), 'perla': (0.78, 0.76, 0.70)}
TETTO_A = math.radians(24)          # pendenza delle due falde
GRONDA = 0.35                       # sporgenza della falda oltre il muro

def materiali_corte(M):
    for k, c in INTONACI_CORTE.items(): M[k] = mat_vernice('CB_C_Intonaco_' + k, (*c, 1), 0.66, SC*0.3)
    M['stucco'] = mat_vernice('CB_C_Stucco', (0.92, 0.88, 0.78, 1), 0.66, SC*0.3)
    M['pietra'] = mat_plain('CB_C_Pietra', (0.56, 0.54, 0.50, 1), 0.9)
    return M

def costruisci_kit_corte(M, kit, coll):
    mats = [mat_kit(), M['bordo'], M['interno'], M['kraft']]; MK = [M['kraft'], M['bordo'], M['interno']]
    def pezzo(nome, geos, mm):
        o = bpy.data.objects.get(nome)
        if o: d = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(d)
        kit[nome] = make_object(nome, geos, mm, coll); return kit[nome]
    fuori = lambda x=0.0, z=0.0: frame((x, 0, z), (0, -1, 0), (0, 0, 1), (1, 0, 0))    # foglio sulla facciata, sporge verso +X
    b = AMP + 0.02
    # ---- tetto a due falde, un modulo largo 2 m, per ali profonde 2 o 3 moduli: falde con gronda + colmo ----
    for nd in (2, 3):
        D = nd*MODULO + 2*T; Lf = D/2 + GRONDA; xc = GRONDA - Lf/2; zc = b - math.tan(TETTO_A)*xc; hr = b + math.tan(TETTO_A)*D/2
        geos = [(ondulato(Lf, MODULO, TETTO_A, 500 + nd), Matrix.Translation((xc, -MODULO/2, zc))),
                (ondulato(Lf, MODULO, TETTO_A, 510 + nd), Matrix.Translation((-D - xc, -MODULO/2, zc)) @ Matrix.Rotation(math.pi, 4, 'Z'))]
        ca, sa = math.cos(TETTO_A), math.sin(TETTO_A)
        for sg in (1, -1):        # colmo: una striscia piegata a cavallo delle due falde
            geos.append((build_panel(rect(0, 0, MODULO, 0.24), t=0.02, **kw(520 + nd)),
                         frame((-D/2, 0, hr + AMP + 0.015), (0, -1, 0), (sg*ca, 0, -sa), Vector((0, -1, 0)).cross(Vector((sg*ca, 0, -sa))))))
        pezzo(f'Tetto_{nd}', geos, MK)
        pezzo(f'Testata_{nd}', [(build_panel([(-D, 0.0), (0.0, 0.0), (-D/2, hr)], t=T, **kw(530 + nd)), frame((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0)))], mats)
    # ---- cornicione con le mensole (stucco), lungo un modulo ----
    geos = [(build_panel(rect(0, 0.22, MODULO, 0.40), t=0.45, **kw(540)), fuori()),
            (build_panel(rect(0, 0.0, MODULO, 0.22), t=0.10, **kw(541)), fuori())]
    for k in range(4):
        u = 0.19 + 0.5*k
        geos.append((build_panel(rect(u, 0.02, u + 0.12, 0.22), t=0.36, **kw(542 + k)), fuori()))
    pezzo('Cornicione_Corte', geos, mats)
    # ---- cornici delle finestre e delle portefinestre: telaio, cappello, davanzale (stucco) ----
    u0, u1, z0, z1 = FINESTRA_PIANO; e = 0.12
    cappello = (build_panel(rect(u0 - e - 0.05, z1 + e, u1 + e + 0.05, z1 + e + 0.14), t=0.09, **kw(550)), fuori())
    pezzo('Cornice_Finestra', [(build_panel(rect(u0 - e, z0 - 0.08, u1 + e, z1 + e), holes=[rect(u0, z0, u1, z1)], t=0.04, **kw(551)), fuori()),
                               cappello, (build_panel(rect(u0 - e, z0 - 0.12, u1 + e, z0), t=0.08, **kw(552)), fuori())], mats)
    ferro = [(u0 - e, 0.02), (u0, 0.02), (u0, z1), (u1, z1), (u1, 0.02), (u1 + e, 0.02), (u1 + e, z1 + e), (u0 - e, z1 + e)]
    pezzo('Cornice_Portafinestra', [(build_panel(ferro, t=0.04, **kw(553)), fuori()), cappello], mats)
    # ---- ballatoio sul cortile: soletta di un modulo, ringhiera davanti, due mensole sotto; testata = ringhiera di chiusura ----
    #   versione leggera (il cortile si vede poco): bordi meno frastagliati, ringhiera con 2 punti per onda
    P = 1.1; liscio = dict(rough=0.01, warp=0.0, nick=0.0, step=1.0, scala=1.0)
    geos = [(build_panel(rect(0, -MODULO, P, 0), t=0.10, seed=560, **liscio), Matrix.Translation((0, 0, -0.10)))]
    ringhiera(geos, (P - 0.03, -MODULO, 0), (0, 1, 0), MODULO, seed=561, campioni=2)
    for y in (-0.35, -1.65):
        geos.append((build_panel([(0.0, 0.0), (0.85, 0.0), (0.0, -0.5)], t=0.06, seed=562, **liscio), frame((0, y + 0.03, -0.10), (1, 0, 0), (0, 0, 1), (0, -1, 0))))
    pezzo('Ballatoio', geos, MK)
    # ---- pareti del cortile: stessi buchi dei moduli, bordi lisci (molti meno triangoli) ----
    for nome in ('Terra_Parete', 'Terra_Porta', 'Terra_Portone', 'Modulo_Parete', 'Modulo_Finestra', 'Modulo_Portafinestra'):
        h, buchi = APERTURE[nome]
        pezzo('Cortile_' + nome, [(build_panel(rect(0, 0, MODULO, h), holes=buchi, t=T, seed=570, **liscio), m_modulo())], mats)
    g2 = []; ringhiera(g2, (0, -0.03, 0), (1, 0, 0), P - 0.03, seed=563, campioni=2)
    pezzo('Ballatoio_Testa', g2, MK)
    for i, n in enumerate([n for n in kit if n.startswith(('Tetto_', 'Testata_', 'Cornicione_Corte', 'Cornice_', 'Ballatoio', 'Cortile_'))]):
        kit[n].location = (-60.0, 30.0 - 4.0*i, 0)
    return kit

def palazzo_corte(nome, coll, kit, M, origine, seed=0, rot=0.0, n_l=None, n_s=None, n_d=None, piani=None):
    # Blocco a corte generato dal seme. origine = angolo in basso a destra della facciata principale.
    # Le due ali lunghe sono una CORTINA di palazzi (2-5 moduli ciascuno) con colori, altezze, balconi e
    # cornici diversi; le ali corte prendono l'altezza più bassa dei palazzi a cui si appoggiano.
    # Restituisce (radice, info).
    rng = random.Random(seed); tende = mat_tende()
    n_d = n_d or rng.choice((2, 2, 3)); Dw = n_d*MODULO + 2*T
    nc = math.ceil(Dw/MODULO - 0.1)                       # colonne del lato cortile coperte dalle ali corte
    n_l = n_l or rng.randint(2*nc + 3, 2*nc + 5); n_s = n_s or rng.randint(2, 4)
    base = piani if piani is not None else rng.choice((2, 3, 3, 4))
    L = n_l*MODULO; B = 2*Dw + n_s*MODULO; c_and = (n_l - 1)//2
    zp = lambda p: H_TERRA + H_PIANO*(p - 1)              # quota del pavimento del piano p
    radice = bpy.data.objects.new(nome, None); coll.objects.link(radice)
    radice.location = origine; radice.rotation_euler = (0, 0, rot); radice.empty_display_size = 2.0
    cnt = [0]
    def metti(padre, pezzo, loc, r=0.0, col=None):
        cnt[0] += 1
        return istanza(f'{nome}_{pezzo}_{cnt[0]}', kit[pezzo].data, coll, padre, Vector(loc), r, col)
    def vuoto(n, padre, loc, r):
        e = bpy.data.objects.new(n, None); coll.objects.link(e); e.parent = padre; e.location = loc; e.rotation_euler = (0, 0, r)
        e.empty_display_size = 0.5; return e
    def cortina(n):
        # divide n colonne in palazzi di 2-5 moduli, ognuno col suo carattere
        segs, k, prec = [], 0, None
        while k < n:
            w = rng.randint(2, 4)
            if n - (k + w) == 1: w += 1
            w = min(w, n - k)
            col = rng.choice([c for c in INTONACI_CORTE if c != prec]); prec = col
            segs.append({'s0': k, 'w': w, 'colore': col, 'piani': max(2, min(4, base + rng.choice((-1, 0, 0, 1)))),
                         'balconi': rng.choice(('alterni', 'alterni', 'tutti', 'nessuno')), 'cornici': rng.random() < 0.75,
                         'persiane': rng.uniform(0.5, 0.95)})
            k += w
        return segs
    def ala_lunga(nome_ala, o, r, sd, piani_corte, segs):
        ala = vuoto(nome_ala, radice, o, r)
        for i, g in enumerate(segs):
            s0, w, pz, colore = g['s0'], g['w'], g['piani'], g['colore']
            vicino_dx = segs[i - 1]['piani'] if i > 0 else None              # verso y = 0
            vicino_sx = segs[i + 1]['piani'] if i < len(segs) - 1 else None  # verso -L
            ka = c_and - s0 if s0 <= c_and < s0 + w else None
            terra = [('Terra_Portone' if k == ka else rng.choice(('Terra_Vetrina', 'Terra_Vetrina', 'Terra_Serranda', 'Terra_Parete'))) for k in range(w)]
            balc = {'alterni': [k for k in range(w) if (s0 + k) % 2 == 1], 'tutti': list(range(w)), 'nessuno': []}[g['balconi']]
            balc = [k for k in balc if k != ka]
            fronte = {0: terra}
            for p in range(1, pz + 1):
                fronte[p] = [('Modulo_Portafinestra' if (k in balc and p <= 2) else 'Modulo_Finestra') for k in range(w)]
            lati = {}
            for li in range(pz + 1):
                for k in range(w):                                    # lato cortile, k contato da -W
                    gc = s0 + (w - 1 - k)                             # colonna dell'ala
                    if gc < nc or gc >= n_l - nc:                     # dietro un'ala corta
                        tipo = None if li <= piani_corte[0 if gc < nc else 1] else 'Cortile_Modulo_Parete'
                    elif li == 0: tipo = 'Cortile_' + ('Terra_Portone' if gc == c_and else ('Terra_Porta' if gc % 3 == 0 else 'Terra_Parete'))
                    else: tipo = 'Cortile_Modulo_Portafinestra'
                    lati[('Retro', li, k)] = tipo
                for parete, vic in (('Destra', vicino_dx), ('Sinistra', vicino_sx)):   # confine con il palazzo accanto: muro cieco
                    if vic is None: continue
                    for k in range(n_d): lati[(parete, li, k)] = None if li <= vic else 'Modulo_Parete'
            seg, H, W, D = palazzo(f'{nome_ala}_{i}', coll, kit, M, Vector((0, -MODULO*s0, 0)), w, n_d, pz, colore, fronte=fronte, lati=lati,
                                   fasce=False, persiane_prob=g['persiane'], seed=sd*10 + i, rot=0.0, persiane_retro=False)
            seg.parent = ala
            for k in range(w):
                metti(seg, 'Marcapiano', (0, -MODULO*k, H_TERRA - 0.08), 0, M['stucco'])
                metti(seg, 'Cornicione_Corte' if g['cornici'] else 'Cornicione', (0, -MODULO*k, H - (0.40 if g['cornici'] else 0.30)), 0, M['stucco'])
                metti(seg, 'Cornicione', (-D, -W + MODULO*k, H - 0.30), math.pi, M['stucco'])
                metti(seg, f'Tetto_{n_d}', (0, -MODULO*k, H))
            for lato, vic, y, rr in (('dx', vicino_dx, 0.0, math.pi/2), ('sx', vicino_sx, -W, -math.pi/2)):
                if vic is None:                                       # testa dell'ala, sull'incrocio delle strade
                    for k in range(n_d):
                        metti(seg, 'Cornicione_Corte', ((-D + T + MODULO*k) if lato == 'dx' else (-T - MODULO*k), y, H - 0.40), rr, M['stucco'])
                if vic is None or vic < pz:
                    metti(seg, f'Testata_{n_d}', (0, y if lato == 'dx' else y + T, H), 0, M[colore])
            if g['cornici']:
                for p in range(1, pz + 1):
                    for k, tipo in enumerate(fronte[p]):
                        metti(seg, 'Cornice_Portafinestra' if tipo == 'Modulo_Portafinestra' else 'Cornice_Finestra', (0, -MODULO*k, zp(p)), 0, M['stucco'])
            for p in (1, 2):
                for k in balc: metti(seg, 'Balcone', (0, -MODULO*k, zp(p)))
            for k, tipo in enumerate(terra):
                if tipo == 'Terra_Vetrina':
                    if rng.random() < 0.5: metti(seg, 'Tenda', (0, -MODULO*k, 0), 0, rng.choice(tende))
                    elif rng.random() < 0.3: metti(seg, rng.choice(('Insegna_Bar', 'Insegna_Farmacia', 'Insegna_Tabacchi')), (0, -MODULO*k, 0))
            # ballatoi sul cortile, a tutti i piani, tra le due ali corte
            for p in range(1, pz + 1):
                for k in range(w):
                    gc = s0 + (w - 1 - k)
                    if nc <= gc < n_l - nc: metti(seg, 'Ballatoio', (-D, -W + MODULO*k, zp(p)), math.pi)
        # chiusure dei ballatoi e panni stesi (sull'ala, che ha la stessa geometria di un palazzo unico)
        Dl = n_d*MODULO + 2*T
        for p in range(1, max(g['piani'] for g in segs) + 1):
            if all(g['piani'] >= p for g in segs if g['s0'] < n_l - nc and g['s0'] + g['w'] > nc):
                metti(ala, 'Ballatoio_Testa', (-Dl, -L + MODULO*nc + 0.06, zp(p)), math.pi)
                metti(ala, 'Ballatoio_Testa', (-Dl, -L + MODULO*(n_l - nc), zp(p)), math.pi)
        for _ in range(rng.randint(0, 2)):
            p = rng.randint(1, min(g['piani'] for g in segs)); k0 = rng.randint(nc, n_l - nc - 2)
            metti(ala, 'Panni_4m', (-Dl, -L + MODULO*k0, zp(p) + 2.2), math.pi)
        return segs
    def ala_corta(nome_ala, o, r, sd, pz, colore):
        terra = [rng.choice(('Terra_Parete', 'Terra_Vetrina', 'Terra_Serranda')) for _ in range(n_s)]
        fronte = {0: terra}
        for p in range(1, pz + 1): fronte[p] = ['Modulo_Finestra']*n_s
        lati = {}
        for li in range(pz + 1):
            for parete in ('Destra', 'Sinistra'):           # contro le ali lunghe: non si vede
                for k in range(n_d): lati[(parete, li, k)] = None
            for k in range(n_s): lati[('Retro', li, k)] = 'Cortile_' + (('Terra_Porta' if k == n_s//2 else 'Terra_Parete') if li == 0 else 'Modulo_Finestra')
        ala, H, W, D = palazzo(nome_ala, coll, kit, M, o, n_s, n_d, pz, colore, fronte=fronte, lati=lati, fasce=False,
                               persiane_prob=0.8, seed=sd, rot=r, persiane_retro=False)
        ala.parent = radice
        for k in range(n_s):
            metti(ala, 'Marcapiano', (0, -MODULO*k, H_TERRA - 0.08), 0, M['stucco'])
            metti(ala, 'Cornicione_Corte', (0, -MODULO*k, H - 0.40), 0, M['stucco'])
            metti(ala, 'Cornicione', (-D, -W + MODULO*k, H - 0.30), math.pi, M['stucco'])
            metti(ala, f'Tetto_{n_d}', (0, -MODULO*k, H))
            for p in range(1, pz + 1): metti(ala, 'Cornice_Finestra', (0, -MODULO*k, zp(p)), 0, M['stucco'])
        metti(ala, f'Testata_{n_d}', (0, 0, H), 0, M[colore]); metti(ala, f'Testata_{n_d}', (0, -W + T, H), 0, M[colore])
    # le ali corte sono alte quanto il più basso dei palazzi d'angolo: prima si decidono le cortine
    sf, sr = cortina(n_l), cortina(n_l)          # fronte (colonna 0 a y = 0) e retro (colonna 0 a y = -L)
    pc_dx = max(2, min(sf[0]['piani'], sr[-1]['piani']) - rng.choice((0, 0, 1)))
    pc_sx = max(2, min(sf[-1]['piani'], sr[0]['piani']) - rng.choice((0, 0, 1)))
    f = ala_lunga(nome + '_AlaFronte', Vector((0, 0, 0)), 0.0, seed + 1, (pc_sx, pc_dx), sf)
    rr = ala_lunga(nome + '_AlaRetro', Vector((-B, -L, 0)), math.pi, seed + 2, (pc_dx, pc_sx), sr)
    ala_corta(nome + '_AlaDx', Vector((-B + Dw, 0, 0)), math.pi/2, seed + 3, pc_dx, rng.choice((f[0]['colore'], rr[-1]['colore'])))
    ala_corta(nome + '_AlaSx', Vector((-Dw, -L, 0)), -math.pi/2, seed + 4, pc_sx, rng.choice((f[-1]['colore'], rr[0]['colore'])))
    # cortile lastricato
    g = build_panel(rect(-B + Dw, -L + Dw, -Dw, -Dw), t=0.02, **kw(seed + 9))
    o = make_object(nome + '_Cortile', [(g, Matrix())], [M['pietra'], M['bordo'], M['interno']], coll); o.parent = radice
    Hmax = max(zp(g['piani'] + 1) for g in f + rr)
    return radice, {'L': L, 'B': B, 'H': Hmax + math.tan(TETTO_A)*Dw/2, 'n_l': n_l, 'n_s': n_s, 'n_d': n_d}

def run_corte(semi=range(1, 5)):
    # fila di blocchi a corte generati, per controllare la varietà
    c = bpy.data.collections.get('Corte_Campione')
    if c:
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    else:
        c = bpy.data.collections.new('Corte_Campione'); bpy.context.scene.collection.children.link(c)
    M = materiali_corte(materiali()); kit = {o.name: o for o in bpy.data.collections['Kit_Borgo'].objects}
    kit = costruisci_kit_corte(M, kit, bpy.data.collections['Kit_Borgo'])
    y, out = 0.0, []
    for sd in semi:
        r, info = palazzo_corte(f'C{sd}', c, kit, M, Vector((80.0, y, 0.0)), seed=sd)
        out.append(info); y -= info['L'] + 6.0
    return out

# =====================================================================
# PALAZZONI ANNI '60-'70 (residenziale popolare, più esterno, T02)
#   stecche lunghe e torri regolari: balconi a nastro con il parapetto pieno,
#   finestre larghe con le tapparelle (ondulato a costole orizzontali, abbassate
#   a caso), vani scala con il vetrocemento, androni vetrati, tetto piano di
#   kraft con il parapetto, i torrini delle scale e le antenne. Toni spenti.
# =====================================================================
INTONACI_PALAZZONI = {'cemento': (0.60, 0.58, 0.54), 'beige': (0.74, 0.66, 0.53), 'giallino': (0.78, 0.70, 0.47),
                      'verdino': (0.56, 0.60, 0.52), 'mattone': (0.58, 0.32, 0.23), 'azzurrino': (0.58, 0.64, 0.68)}
CEMENTO_CHIARO = (0.78, 0.76, 0.71)          # frontalini dei solai e parapetti dei balconi (quando non sono del colore della casa)
APERTURE_PAL = {
    'Pal_Finestra': (H_PIANO, [rect(0.3, 0.9, 1.7, 2.4)]),                              # finestra larga 1,4 m
    'Pal_Portafinestra': (H_PIANO, [rect(0.25, 0.02, 0.95, 2.4), rect(1.15, 0.9, 1.75, 2.4)]),   # porta sul balcone + finestrella
    'Pal_Vano_Scala': (H_PIANO, [rect(0.7, 0.35, 1.3, 2.75)]),                          # feritoia del vano scala
    'Pal_Terra_Androne': (H_TERRA, [rect(0.25, 0.02, 1.75, 2.9)]),                      # ingresso vetrato del condominio
}
APERTURE.update(APERTURE_PAL)                 # così l'export del kit e il kit di base li conoscono

def materiali_palazzoni(M):
    for k, c in INTONACI_PALAZZONI.items(): M[k] = mat_vernice('CB_P_Intonaco_' + k, (*c, 1), 0.66, SC*0.3)
    M['cemento_chiaro'] = mat_vernice('CB_P_Cemento_Chiaro', (*CEMENTO_CHIARO, 1), 0.66, SC*0.3)
    M['vetro'] = mat_plain('CB_P_Vetro', (0.52, 0.60, 0.60, 1), 0.35)
    return M

def costruisci_kit_palazzoni(M, kit, coll):
    mats = [mat_kit(), M['bordo'], M['interno'], M['kraft']]; MK = [M['kraft'], M['bordo'], M['interno']]
    def pezzo(nome, geos, mm):
        o = bpy.data.objects.get(nome)
        if o: d = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(d)
        kit[nome] = make_object(nome, geos, mm, coll); return kit[nome]
    # ---- pareti con le aperture dei palazzoni (stesso foglio dei moduli del borgo) ----
    for i, (nome, (h, buchi)) in enumerate(APERTURE_PAL.items()):
        geos = [(build_panel(rect(0, 0, MODULO, h), holes=buchi, t=T, **kw(600 + i)), m_modulo())]
        if nome == 'Pal_Vano_Scala':          # vetrocemento: lastra verdina arretrata con la griglia dei mattoncini
            geos.append((rimappa(build_panel(rect(0.7, 0.35, 1.3, 2.75), t=0.02, rough=0, warp=0, nick=0, step=50.0), {0: 4}), frame((-T - 0.02, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
            for zz in [0.35 + 0.2*k for k in range(1, 12)]:
                geos.append((build_panel(rect(0.7, zz - 0.012, 1.3, zz + 0.012), t=0.01, rough=0, warp=0, nick=0, step=50.0), frame((-T + 0.0, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
            for uu in (0.9, 1.1):
                geos.append((build_panel(rect(uu - 0.012, 0.35, uu + 0.012, 2.75), t=0.01, rough=0, warp=0, nick=0, step=50.0), frame((-T + 0.0, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
        if nome == 'Pal_Terra_Androne':       # vetrata dell'ingresso con il montante
            geos.append((rimappa(build_panel(rect(0.25, 0.02, 1.75, 2.9), t=0.02, rough=0, warp=0, nick=0, step=50.0), {0: 4}), frame((-T/2 - 0.01, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
            geos.append((build_panel(rect(0.97, 0.02, 1.03, 2.9), t=0.05, rough=0, warp=0, nick=0, step=50.0), frame((-T/2, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
        pezzo(nome, geos, mats + [M['vetro']])
    # ---- tapparelle: ondulato a costole orizzontali, alto quanto l'apertura, origine in ALTO (il codice la alza, non la scala) ----
    for nome, u0, u1, z1, h in (('Tapparella_Finestra', 0.3, 1.7, 2.4, 1.5), ('Tapparella_Porta', 0.25, 0.95, 2.4, 2.38), ('Tapparella_Piccola', 1.15, 1.75, 2.4, 1.5)):
        w = u1 - u0; g = ondulato(w, h, 0.0, 620 + int(w*10), campioni=2)
        # x locale (larghezza) -> -Y, y locale (le onde) -> Z, z locale -> +X; in alto a z = 0
        m = Matrix(((0, 0, 1, -T/2), (-1, 0, 0, -(u0 + u1)/2), (0, 1, 0, -h/2), (0, 0, 0, 1)))
        pezzo(nome, [(g, m)], MK)
    # ---- balcone a nastro: soletta di un modulo, parapetto pieno davanti (colore per oggetto) ----
    P = 1.2
    geos = [(build_panel(rect(0, -MODULO, P, 0), t=0.16, **kw(630)), Matrix.Translation((0, 0, -0.16))),
            (build_panel(rect(0, -0.16, MODULO, 1.0), t=0.06, **kw(631)), frame((P - 0.06, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0)))]
    pezzo('Pal_Balcone', geos, mats)
    pezzo('Pal_Balcone_Testa', [(build_panel(rect(0, -0.16, P, 1.0), t=0.06, **kw(632)), frame((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0)))], mats)
    # divisorio tra due appartamenti sul balcone: pannello di vetro smerigliato in una cornice
    pezzo('Pal_Divisorio', [(rimappa(build_panel(rect(0.05, 0.0, P - 0.1, 2.3), t=0.02, rough=0, warp=0, nick=0, step=50.0), {0: 4}), frame((0, 0.01, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0)))],
          mats + [M['vetro']])
    # ---- tetto piano: copertura di kraft (una cella 2 x 2) e cornice bassa del parapetto ----
    pezzo('Pal_Copertura', [(build_panel(rect(-MODULO, -MODULO, 0, 0), t=0.03, **kw(640)), Matrix())], MK)
    pezzo('Pal_Parapetto', [(build_panel(rect(0, 0, MODULO, 0.6), t=T, **kw(641)), m_modulo()),
                            (build_panel(rect(0, 0.6, MODULO, 0.72), t=0.16, **kw(642)), fuori_pal())], mats)
    for i, n in enumerate([n for n in kit if n.startswith(('Pal_', 'Tapparella_'))]):
        kit[n].location = (-90.0, 30.0 - 4.0*i, 0)
    return kit

def fuori_pal():
    # cimasa del parapetto: sporge un poco da entrambi i lati del muro
    return frame((-T - 0.04, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))

def palazzone(nome, coll, kit, M, origine, seed=0, rot=0.0, tipo=None, n_w=None, piani=None):
    # stecca (9-14 moduli, profonda 4, 4-5 piani, più scale) o torre (5-6 x 5 moduli, 6-7 piani, una scala). Restituisce (radice, info)
    rng = random.Random(f'palazzone-{seed}')     # seme in stringa: con 1, 2, 3... i primi numeri di Random si somigliano
    tipo = tipo or rng.choice(('stecca', 'stecca', 'torre'))
    if tipo == 'stecca': n_w = n_w or rng.randint(9, 14); piani = piani or rng.randint(4, 5); n_d = 4
    else: n_w = n_w or rng.randint(5, 6); piani = piani or rng.randint(6, 7); n_d = 5   # torre quasi quadrata
    colore = rng.choice(list(INTONACI_PALAZZONI))
    col_balc = M['cemento_chiaro'] if rng.random() < 0.6 else M[colore]
    zp = lambda p: H_TERRA + H_PIANO*(p - 1)
    # vani scala: uno ogni 5-6 colonne nella stecca, al centro nella torre
    if tipo == 'stecca':
        passo = rng.randint(5, 6); vani = list(range(passo//2, n_w, passo))
        if n_w - 1 - vani[-1] < 2 and len(vani) > 1: vani[-1] = n_w - 3
    else: vani = [n_w//2]
    negozi = tipo == 'stecca' and rng.random() < 0.5
    terra = []
    for k in range(n_w):
        if k in vani: terra.append('Pal_Terra_Androne')
        elif negozi: terra.append(rng.choice(('Terra_Vetrina', 'Terra_Vetrina', 'Terra_Serranda')))
        else: terra.append('Terra_Parete')
    # appartamenti: tra due vani si alternano portafinestra (sul balcone) e finestra
    piano = [('Pal_Vano_Scala' if k in vani else ('Pal_Portafinestra' if (k + seed) % 2 == 0 else 'Pal_Finestra')) for k in range(n_w)]
    fronte = {0: terra}
    for p in range(1, piani + 1): fronte[p] = list(piano)
    lati = {}
    for li in range(1, piani + 1):
        for k in range(n_w): lati[('Retro', li, k)] = 'Pal_Vano_Scala' if (n_w - 1 - k) in vani else 'Pal_Finestra'
        for parete in ('Destra', 'Sinistra'):
            for k in range(n_d): lati[(parete, li, k)] = 'Pal_Finestra' if (k == 1 and rng.random() < 0.5) else 'Modulo_Parete'
    for k in range(n_w): lati[('Retro', 0, k)] = 'Pal_Terra_Androne' if (n_w - 1 - k) in vani else 'Terra_Parete'
    radice, H, W, D = palazzo(nome, coll, kit, M, origine, n_w, n_d, piani, colore, fronte=fronte, lati=lati, fasce=False,
                              persiane_prob=0.0, seed=seed, rot=rot)
    cnt = [0]
    def metti(pezzo, loc, r=0.0, col=None):
        cnt[0] += 1
        return istanza(f'{nome}_{pezzo}_{cnt[0]}', kit[pezzo].data, coll, radice, Vector(loc), r, col)
    # balconi a nastro sul fronte (fra i vani), divisori fra gli appartamenti, testate alle estremità
    for p in range(1, piani + 1):
        tratti, cur = [], []
        for k in range(n_w):
            if k in vani:
                if cur: tratti.append(cur); cur = []
            else: cur.append(k)
        if cur: tratti.append(cur)
        for tr in tratti:
            for k in tr: metti('Pal_Balcone', (0, -MODULO*k, zp(p)), 0, col_balc)
            metti('Pal_Balcone_Testa', (0, -MODULO*tr[0], zp(p)), 0, col_balc)
            metti('Pal_Balcone_Testa', (0, -MODULO*(tr[-1] + 1) + 0.06, zp(p)), 0, col_balc)
            for k in tr[1:]:
                if (k + seed) % 2 == 0: metti('Pal_Divisorio', (0, -MODULO*k, zp(p)))
    # tapparelle abbassate a caso su tutte le finestre (fronte e retro)
    # la tapparella NON si scala (le costole si schiaccerebbero): si alza, e la parte sopra l'apertura resta
    # nascosta dentro lo spessore del muro (al massimo 1,45 m, il muro fino alla finestra di sopra)
    ALT = {'Tapparella_Finestra': 1.5, 'Tapparella_Porta': 2.38, 'Tapparella_Piccola': 1.5}
    def tapparelle(tipo_mod, base, r):
        z1 = 2.4
        if tipo_mod == 'Pal_Finestra': pezzi = ['Tapparella_Finestra']
        elif tipo_mod == 'Pal_Portafinestra': pezzi = ['Tapparella_Porta', 'Tapparella_Piccola']
        else: return
        for pz in pezzi:
            h = ALT[pz]; f = rng.choice((0.0, 0.0, 0.25, 0.5, 0.7, 1.0)); su = min((1 - f)*h, 1.45)   # f = quanto è abbassata
            if su >= h - 0.02: continue                                                         # tutta su: non si vede
            metti(pz, base + Matrix.Rotation(r, 3, 'Z') @ Vector((0, 0, z1 + su)), r)
    for p in range(1, piani + 1):
        for k, tp in enumerate(fronte[p]): tapparelle(tp, Vector((0, -MODULO*k, zp(p))), 0.0)
        for k in range(n_w): tapparelle(lati[('Retro', p, k)], Vector((-D, -W + MODULO*k, zp(p))), math.pi)
    # frontalini dei solai sulle testate e sui vani scala
    for parete, o, r, n, sx in pareti({'n_w': n_w, 'n_d': n_d}):
        for p in range(1, piani + 1):
            for k in range(n):
                vano = parete == 'Fronte' and k in vani
                if parete in ('Destra', 'Sinistra') or vano:
                    metti('Marcapiano', o + sx*MODULO*k + Vector((0, 0, zp(p) - 0.08)), r, M['cemento_chiaro'])
    # tetto piano: copertura di kraft, parapetto tutto attorno, torrini delle scale, antenne
    for i in range(n_w):
        for j in range(n_d): metti('Pal_Copertura', (-T - MODULO*j, -T - MODULO*i, H + 0.005))
    for parete, o, r, n, sx in pareti({'n_w': n_w, 'n_d': n_d}):
        for k in range(n): metti('Pal_Parapetto', o + sx*MODULO*k + Vector((0, 0, H)), r, M[colore])
    for v in vani:
        tr, Ht, _, _ = palazzo(f'{nome}_Torrino_{v}', coll, kit, M, Vector((-MODULO, -MODULO*v, H)), 1, 1, 1, colore,
                               fronte={0: ['Modulo_Parete']}, lati={(pp, 0, 0): 'Modulo_Parete' for pp in ('Destra', 'Sinistra', 'Retro')},
                               terra=False, fasce=False, persiane_prob=0.0, seed=seed + v)
        tr.parent = radice
        metti('Pal_Copertura', (-MODULO - T, -MODULO*v - T + 0.0, H + Ht + 0.005))
    for _ in range(rng.randint(3, 7)):
        metti('Antenna', (-rng.uniform(0.6, D - 0.6), -rng.uniform(0.6, W - 0.6), H))
    if rng.random() < 0.5: metti('Serbatoio', (-D*0.5, -rng.uniform(1.5, W - 1.5), H))
    return radice, {'tipo': tipo, 'W': W, 'D': D, 'H': H, 'n_w': n_w, 'piani': piani, 'colore': colore}

def run_palazzoni(semi=range(1, 5)):
    c = bpy.data.collections.get('Palazzoni_Campione')
    if c:
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    else:
        c = bpy.data.collections.new('Palazzoni_Campione'); bpy.context.scene.collection.children.link(c)
    M = materiali_palazzoni(materiali()); kit = {o.name: o for o in bpy.data.collections['Kit_Borgo'].objects}
    kit = costruisci_kit_palazzoni(M, kit, bpy.data.collections['Kit_Borgo'])
    y, out = 0.0, []
    for sd in semi:
        r, info = palazzone(f'PZ{sd}', c, kit, M, Vector((130.0, y, 0.0)), seed=sd)
        out.append(info); y -= info['W'] + 8.0
    return out

# =====================================================================
# VILLETTE (periferia, T03)
#   casetta di 1-2 piani (tutti da 3 m) in un lotto con il giardino davanti,
#   recinzione col muretto e la ringhiera, cancello in asse con la porta,
#   vialetto, portico d'ingresso; tetto a due falde "a coppi" di ondulato rosso
#   (onde più larghe e alte); a volte il garage. Colori vivaci.
# =====================================================================
INTONACI_VILLE = {'giallo': (0.92, 0.74, 0.30), 'arancio': (0.90, 0.52, 0.28), 'rosa': (0.90, 0.58, 0.58),
                  'azzurro': (0.50, 0.70, 0.84), 'menta': (0.58, 0.80, 0.66), 'lilla': (0.72, 0.62, 0.82),
                  'bianco': (0.92, 0.90, 0.86)}
COPPI = (0.72, 0.25, 0.15)                   # rosso dei coppi
TETTO_V = math.radians(28)                   # pendenza del tetto della villetta
ONDA_COPPI, AMP_COPPI = 0.25, 0.07           # 8 coppi per modulo da 2 m
APERTURE_VILLA = {
    'Villa_Porta': (H_PIANO, [rect(0.55, 0.02, 1.45, 2.3)]),
    'Villa_Garage': (H_PIANO, [rect(0.15, 0.02, 1.85, 2.3)]),
}
APERTURE.update(APERTURE_VILLA)

def materiali_ville(M):
    for k, c in INTONACI_VILLE.items(): M[k] = mat_vernice('CB_V_Intonaco_' + k, (*c, 1), 0.66, SC*0.3)
    M['coppi'] = mat_vernice('CB_V_Coppi', (*COPPI, 1), 0.70, SC*0.3)
    M['pietra'] = M.get('pietra') or mat_plain('CB_C_Pietra', (0.56, 0.54, 0.50, 1), 0.9)
    return M

def ondulato_coppi(L, W, pendenza, seed):
    # come ondulato(), con le onde larghe e alte dei coppi
    global ONDA, AMP
    vecchi = (ONDA, AMP); ONDA, AMP = ONDA_COPPI, AMP_COPPI
    try: return ondulato(L, W, pendenza, seed)
    finally: ONDA, AMP = vecchi

def costruisci_kit_ville(M, kit, coll):
    mats = [mat_kit(), M['bordo'], M['interno'], M['kraft']]; MK = [M['kraft'], M['bordo'], M['interno']]
    MC = [M['coppi'], M['bordo'], M['interno']]
    def pezzo(nome, geos, mm):
        o = bpy.data.objects.get(nome)
        if o: d = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(d)
        kit[nome] = make_object(nome, geos, mm, coll); return kit[nome]
    for i, (nome, (h, buchi)) in enumerate(APERTURE_VILLA.items()):
        geos = [(build_panel(rect(0, 0, MODULO, h), holes=buchi, t=T, **kw(700 + i)), m_modulo())]
        if nome == 'Villa_Garage':          # basculante di kraft, un poco arretrata
            geos.append((rimappa(build_panel(rect(0.15, 0.02, 1.85, 2.3), t=0.02, **kw(705)), {0: 3}), frame((-T - 0.03, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
            for zz in (0.6, 1.2, 1.8):
                geos.append((rimappa(build_panel(rect(0.2, zz - 0.02, 1.8, zz + 0.02), t=0.01, rough=0, warp=0, nick=0, step=50.0), {0: 3}), frame((-T - 0.01, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
        pezzo(nome, geos, mats)
    # ---- tetto a coppi a due falde (gronda, colmo) e testata, per profondità di 3 e 4 moduli ----
    b = AMP_COPPI + 0.02
    for nd in (3, 4):
        D = nd*MODULO + 2*T; Lf = D/2 + GRONDA; xc = GRONDA - Lf/2; zc = b - math.tan(TETTO_V)*xc; hr = b + math.tan(TETTO_V)*D/2
        geos = [(ondulato_coppi(Lf, MODULO, TETTO_V, 710 + nd), Matrix.Translation((xc, -MODULO/2, zc))),
                (ondulato_coppi(Lf, MODULO, TETTO_V, 715 + nd), Matrix.Translation((-D - xc, -MODULO/2, zc)) @ Matrix.Rotation(math.pi, 4, 'Z'))]
        ca, sa = math.cos(TETTO_V), math.sin(TETTO_V)
        for sg in (1, -1):
            geos.append((build_panel(rect(0, 0, MODULO, 0.26), t=0.03, **kw(720 + nd)),
                         frame((-D/2, 0, hr + AMP_COPPI + 0.02), (0, -1, 0), (sg*ca, 0, -sa), Vector((0, -1, 0)).cross(Vector((sg*ca, 0, -sa))))))
        pezzo(f'Villa_Tetto_{nd}', geos, MC)
        pezzo(f'Villa_Testata_{nd}', [(build_panel([(-D, 0.0), (0.0, 0.0), (-D/2, hr)], t=T, **kw(725 + nd)), frame((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0)))], mats)
    # ---- portico d'ingresso: tettuccio a coppi su due pali di legno, davanti a un modulo ----
    Pp, a = 1.3, math.radians(20)
    geos = [(ondulato_coppi(Pp + 0.2, 2.2, a, 730), Matrix.Translation((Pp/2, -1.0, 2.75 + math.tan(a)*(Pp/2))))]
    pali = [palo((Pp - 0.1, -1.0 + sg*0.95, 0.0), 2.75) for sg in (1, -1)]
    pezzo('Villa_Portico', geos + [(rimappa(g, {0: 3, 1: 3, 2: 3}), m) for g, m in pali], MC + [M['legno']])
    # ---- recinzione: muretto (colore della casa) con la ringhiera ondulata e il pilastrino; cancello ----
    def recinzione(cancello):
        geos = []
        if not cancello:
            geos.append((build_panel(rect(0, 0, MODULO, 0.5), t=0.2, **kw(740)), frame((-0.1, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
            r = []; ringhiera(r, (0.0, -MODULO + 0.1, 0.5), (0, 1, 0), MODULO - 0.2, alt=0.7, seed=741, campioni=2)
            geos += [(rimappa(g, {0: 3, 1: 1, 2: 2}), m) for g, m in r]
        else:                                # cancello di legno a stecche, un poco aperto
            for k in range(7):
                u = 0.25 + 0.22*k
                geos.append((rimappa(build_panel(rect(u, 0.08, u + 0.12, 1.05), t=0.03, **kw(742 + k)), {0: 4, 1: 4, 2: 4}), frame((-0.02, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
            for zz in (0.25, 0.85):
                geos.append((rimappa(build_panel(rect(0.2, zz, 1.8, zz + 0.08), t=0.03, **kw(750)), {0: 4, 1: 4, 2: 4}), frame((0.01, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
        geos.append((build_panel(rect(-0.14, -0.14, 0.14, 0.14), t=1.3, **kw(745)), Matrix.Translation((0, -0.0, 0))))   # pilastrino all'origine
        return geos
    pezzo('Recinzione', recinzione(False), mats + [M['legno']])
    pezzo('Recinzione_Cancello', recinzione(True), mats + [M['legno']])
    # ---- vialetto di lastre di pietra, lungo 2 m verso -X, largo 1 m centrato in y = 0 ----
    geos = []
    for k in range(3):
        x0 = -0.08 - 0.66*k
        geos.append((build_panel(rect(x0 - 0.58, -0.5, x0, 0.5), t=0.04, **kw(760 + k)), Matrix()))
    pezzo('Vialetto', geos, [M['pietra'], M['bordo'], M['interno']])
    for i, n in enumerate([n for n in kit if n.startswith(('Villa_', 'Recinzione', 'Vialetto'))]):
        kit[n].location = (-110.0, 30.0 - 4.0*i, 0)
    return kit

def villetta(nome, coll, kit, M, origine, seed=0, rot=0.0):
    # origine = angolo in basso a destra del LOTTO sulla strada (filo della recinzione), davanti +X.
    # Restituisce (radice, info) con le misure del lotto e della casa.
    rng = random.Random(f'villetta-{seed}')
    n_w = rng.randint(3, 5); n_d = rng.choice((3, 4)); livelli = rng.choice((1, 2, 2))
    colore = rng.choice(list(INTONACI_VILLE))
    garage = n_w >= 4 and rng.random() < 0.5
    kd = rng.randint(1 if garage else 0, n_w - 2 if garage else n_w - 1)        # colonna della porta
    W, D = n_w*MODULO, n_d*MODULO + 2*T
    m = rng.choice((2, 4)); sx = rng.choice((4, 6))                              # fianchi e giardino davanti
    Lw = int(W) + 2*m; Lp = sx + n_d*int(MODULO) + 4                             # lotto (multipli di 2 m, interi)
    radice = bpy.data.objects.new(nome, None); coll.objects.link(radice)
    radice.location = origine; radice.rotation_euler = (0, 0, rot); radice.empty_display_size = 1.5
    # la casa
    fronte = {0: [('Villa_Garage' if (garage and k == n_w - 1) else ('Villa_Porta' if k == kd else 'Modulo_Finestra')) for k in range(n_w)]}
    balc = livelli == 2 and rng.random() < 0.6
    if livelli == 2: fronte[1] = [('Modulo_Portafinestra' if (balc and k == kd) else 'Modulo_Finestra') for k in range(n_w)]
    lati = {}
    for li in range(livelli):
        for parete in ('Destra', 'Sinistra'):
            for k in range(n_d): lati[(parete, li, k)] = 'Modulo_Finestra' if rng.random() < 0.6 else 'Modulo_Parete'
        for k in range(n_w): lati[('Retro', li, k)] = 'Villa_Porta' if (li == 0 and k == n_w//2) else 'Modulo_Finestra'
    casa, H, _, _ = palazzo(nome + '_Casa', coll, kit, M, Vector((-sx, -m, 0)), n_w, n_d, livelli, colore, fronte=fronte, lati=lati,
                            terra=False, fasce=False, persiane_prob=0.85, seed=seed)
    casa.parent = radice
    cnt = [0]
    def metti(padre, pezzo, loc, r=0.0, col=None):
        cnt[0] += 1
        return istanza(f'{nome}_{pezzo}_{cnt[0]}', kit[pezzo].data, coll, padre, Vector(loc), r, col)
    for k in range(n_w):
        metti(casa, 'Cornicione', (0, -MODULO*k, H - 0.30), 0, M['bianco'])
        metti(casa, f'Villa_Tetto_{n_d}', (0, -MODULO*k, H))
    metti(casa, f'Villa_Testata_{n_d}', (0, 0, H), 0, M[colore]); metti(casa, f'Villa_Testata_{n_d}', (0, -W + T, H), 0, M[colore])
    xc = -D*rng.uniform(0.25, 0.4)
    metti(casa, 'Comignolo', (xc, -rng.uniform(0.6, W - 0.6), H + math.tan(TETTO_V)*(-xc) + AMP_COPPI - 0.1), 0, M[colore])
    if rng.random() < 0.6: metti(casa, 'Antenna', (-D/2, -rng.uniform(0.5, W - 0.5), H + math.tan(TETTO_V)*D/2))
    if balc: metti(casa, 'Balcone', (0, -MODULO*kd, H_PIANO)); metti(casa, 'Balcone_Pali', (0, -MODULO*kd, H_PIANO))   # il balcone fa da portico
    else: metti(casa, 'Villa_Portico', (0, -MODULO*kd, 0))
    # recinzione: davanti (col cancello in asse con la porta), sui fianchi e dietro
    g = m//2 + kd; col_m = M[colore] if rng.random() < 0.5 else M['bianco']
    for k in range(Lw//2):
        metti(radice, 'Recinzione_Cancello' if k == g else 'Recinzione', (0, -MODULO*k, 0), 0, col_m)
    for k in range(Lp//2):
        metti(radice, 'Recinzione', (-Lp + MODULO*k, 0, 0), math.pi/2, col_m)                 # fianco destro (y = 0)
        metti(radice, 'Recinzione', (-MODULO*k, -Lw, 0), -math.pi/2, col_m)                   # fianco sinistro
    for k in range(Lw//2): metti(radice, 'Recinzione', (-Lp, -Lw + MODULO*k, 0), math.pi, col_m)
    # vialetto dal cancello alla porta
    yd = -m - MODULO*kd - 1.0
    for i in range(sx//2): metti(radice, 'Vialetto', (-MODULO*i, yd, 0))
    return radice, {'lotto_larghezza': Lw, 'lotto_profondita': Lp, 'W': W, 'D': D, 'H': H + math.tan(TETTO_V)*D/2,
                    'livelli': livelli, 'colore': colore, 'garage': garage}

def run_ville(semi=range(1, 7)):
    c = bpy.data.collections.get('Ville_Campione')
    if c:
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    else:
        c = bpy.data.collections.new('Ville_Campione'); bpy.context.scene.collection.children.link(c)
    M = materiali_ville(materiali_corte(materiali())); kit = {o.name: o for o in bpy.data.collections['Kit_Borgo'].objects}
    kit = costruisci_kit_ville(M, kit, bpy.data.collections['Kit_Borgo'])
    y, out = 0.0, []
    for sd in semi:
        r, info = villetta(f'V{sd}', c, kit, M, Vector((170.0, y, 0.0)), seed=sd)
        out.append(info); y -= info['lotto_larghezza']
    return out

# =====================================================================
# CAPANNONI (zona industriale, T05)
#   scatoloni bassi e lunghi (7 m alla gronda) con le pareti di lamiera, cioè
#   ondulato a costole verticali (grigio lamiera, verde, azzurro o kraft nudo),
#   portoni sezionali con la tettoia, nastro di finestre in alto, tetto a SHED
#   (denti di ondulato kraft con la vetrata verticale) o piano; palazzina degli
#   uffici in muratura sul fronte, ciminiera di tubo di cartone, silos, pallet.
# =====================================================================
INTONACI_CAPANNONI = {'lamiera': (0.56, 0.58, 0.59), 'lamiera_scura': (0.40, 0.42, 0.44), 'verde_ind': (0.38, 0.49, 0.41),
                      'azzurro_ind': (0.46, 0.56, 0.63)}
UFFICI = {'uff_bianco': (0.86, 0.85, 0.81), 'uff_grigio': (0.70, 0.70, 0.68)}
ROSSO_CIM = (0.70, 0.20, 0.14)
SHED_L, SHED_A = 3.6, math.radians(23)       # dente dello shed: falda lunga 3,6 m + canale 0,4 m = 4 m (2 moduli)

def materiali_capannoni(M):
    for k, c in list(INTONACI_CAPANNONI.items()) + list(UFFICI.items()): M[k] = mat_vernice('CB_I_' + k, (*c, 1), 0.66, SC*0.3)
    M['rosso_cim'] = mat_vernice('CB_I_Rosso', (*ROSSO_CIM, 1), 0.66, SC*0.3)
    M['vetro'] = M.get('vetro') or mat_plain('CB_P_Vetro', (0.52, 0.60, 0.60, 1), 0.35)
    return M

def cilindro(r, h, n=16, z0=0.0):
    # tubo aperto (formato di build_panel): facce 0 = esterno; UV u = arco in m, v = z
    V, F, Mi, U = [], [], [], []
    for z in (z0, z0 + h):
        for i in range(n): a = 2*math.pi*i/n; V.append((r*math.cos(a), r*math.sin(a), z))
    for i in range(n):
        j = (i + 1) % n; F.append((i, j, j + n, i + n)); Mi.append(0)
        U.append([(2*math.pi*r*i/n, z0), (2*math.pi*r*(i + 1)/n, z0), (2*math.pi*r*(i + 1)/n, z0 + h), (2*math.pi*r*i/n, z0 + h)])
    return V, F, Mi, U, []

def costruisci_kit_capannoni(M, kit, coll):
    mats = [mat_kit(), M['bordo'], M['interno'], M['kraft']]; MK = [M['kraft'], M['bordo'], M['interno']]
    liscio = dict(rough=0.0, warp=0.0, nick=0.0, step=50.0)
    def pezzo(nome, geos, mm):
        o = bpy.data.objects.get(nome)
        if o: d = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(d)
        kit[nome] = make_object(nome, geos, mm, coll); return kit[nome]
    def lamiera(w, h, u0=0.0, z0=0.0, seed=0):
        # foglio di ondulato a costole verticali sulla facciata (tinta per oggetto), in coordinate del modulo
        g = ondulato(h, w, 0.0, seed, campioni=2)
        # x locale (altezza) -> Z, y locale (onde) -> -Y, z locale -> +X
        return (g, Matrix(((0, 0, 1, -T/2), (0, -1, 0, -(u0 + w/2)), (1, 0, 0, z0 + h/2), (0, 0, 0, 1))))
    # ---- pareti di lamiera: terra (4 m) e fascia alta (3 m) ----
    pezzo('Cap_Parete', [lamiera(MODULO, H_TERRA, seed=800)], mats)
    pezzo('Cap_Parete_Alta', [lamiera(MODULO, H_PIANO, seed=801)], mats)
    # ---- nastro di finestre in alto: lamiera sotto e sopra, vetrata con i montanti ----
    geos = [lamiera(MODULO, 0.8, seed=802), lamiera(MODULO, 0.5, z0=2.5, seed=803),
            (rimappa(build_panel(rect(0, 0.8, MODULO, 2.5), t=0.02, **liscio), {0: 4}), frame((-T/2, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0)))]
    for u in (0.02, 0.98, 1.96):
        geos.append((rimappa(build_panel(rect(u - 0.03 if u > 0.02 else 0, 0.8, u + 0.03 if u < 1.96 else 2.0, 2.5), t=0.05, **liscio), {0: 3}), frame((-T/2 + 0.02, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
    geos.append((rimappa(build_panel(rect(0, 1.63, MODULO, 1.67), t=0.05, **liscio), {0: 3}), frame((-T/2 + 0.02, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
    pezzo('Cap_Finestrata', geos, mats + [M['vetro']])
    # ---- porta di servizio: lamiera ai lati e sopra, anta di kraft ----
    geos = [lamiera(0.5, H_TERRA, seed=804), lamiera(0.5, H_TERRA, u0=1.5, seed=805), lamiera(1.0, 1.7, u0=0.5, z0=2.3, seed=806),
            (rimappa(build_panel(rect(0.5, 0.0, 1.5, 2.3), t=0.04, **kw(807)), {0: 3}), frame((-T/2 - 0.02, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0)))]
    pezzo('Cap_Porta', geos, mats)
    # ---- portone sezionale largo due moduli (4 m): telaio di lamiera, pannelli a costole orizzontali ----
    geos = [lamiera(0.3, H_TERRA, seed=808), lamiera(0.3, H_TERRA, u0=3.7, seed=809), lamiera(3.4, 0.4, u0=0.3, z0=3.6, seed=810)]
    g = ondulato(3.4, 3.6, 0.0, 811, campioni=2)                       # costole orizzontali (come la serranda)
    geos.append((rimappa(g, {0: 0}), Matrix(((0, 0, 1, -T - 0.03), (1, 0, 0, -2.0), (0, 1, 0, 1.8), (0, 0, 0, 1)))))
    for zz in (0.9, 1.8, 2.7):
        geos.append((rimappa(build_panel(rect(0.3, zz - 0.03, 3.7, zz + 0.03), t=0.03, **liscio), {0: 3}), frame((-T + 0.02, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
    pezzo('Cap_Portone', geos, mats)
    # tettoia sopra il portone: ondulato kraft su due mensole
    geos = [(ondulato(1.4, 4.6, math.radians(12), 812), Matrix.Translation((0.7, -2.0, 4.15 + math.tan(math.radians(12))*0.7)))]
    for y in (-0.1, -3.9):
        geos.append((build_panel([(0.0, 0.0), (1.3, 0.0), (0.0, -0.6)], t=0.06, **kw(813)), frame((0, y + 0.03, 4.1), (1, 0, 0), (0, 0, 1), (0, -1, 0))))
    pezzo('Cap_Tettoia', geos, MK)
    # ---- shed: un dente lungo 4 m (y da 0 a -4), per profondità di 6, 8 o 10 moduli ----
    hs = math.tan(SHED_A)*SHED_L
    for nd in (6, 8, 10):
        D = nd*MODULO + 2*T
        g = ondulato(SHED_L, D, SHED_A, 820 + nd)
        geos = [(g, Matrix.Translation((-D/2, -SHED_L/2, AMP + 0.02 + hs/2)) @ Matrix.Rotation(math.pi/2, 4, 'Z'))]
        geos.append((rimappa(build_panel(rect(0, 0.02, D, hs + 0.02), t=0.02, **liscio), {0: 4}), frame((0, -SHED_L, 0), (-1, 0, 0), (0, 0, 1), (0, 1, 0))))
        for k in range(1, nd):
            geos.append((build_panel(rect(MODULO*k - 0.03, 0.02, MODULO*k + 0.03, hs), t=0.04, **liscio), frame((0, -SHED_L - 0.01, 0), (-1, 0, 0), (0, 0, 1), (0, 1, 0))))
        geos.append((build_panel(rect(-D, -4.0, 0, -SHED_L), t=0.03, **kw(830)), Matrix()))          # canale
        pezzo(f'Shed_{nd}', geos, MK + [M['kraft'], M['vetro']])
    # testata del dente (triangolo nel colore della lamiera), sul fianco
    pezzo('Shed_Testa', [(build_panel([(0.0, 0.0), (SHED_L, 0.0), (SHED_L, hs)], t=T, **kw(831)), frame((0, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0)))], mats)
    # ---- ciminiera di tubo di cartone (16 m) con due fasce rosse (tinta per oggetto) e la cuffia ----
    geos = [(rimappa(cilindro(0.55, 16.0), {0: 3}), Matrix())]
    for z0, h in ((12.6, 0.9), (14.6, 0.9)): geos.append((cilindro(0.565, h, z0=z0), Matrix()))
    geos.append((rimappa(cilindro(0.7, 0.25, z0=15.9), {0: 1}), Matrix()))
    geos.append((build_panel(circle(0, 0, 0.9, 16), t=0.6, **kw(840)), Matrix()))                   # basamento
    pezzo('Ciminiera', geos, mats)
    # ---- pallet: tre tavole sopra, tre traversi sotto (1,2 x 0,8 m), e una pila di casse di kraft ----
    geos = []
    for k in range(5): geos.append((build_panel(rect(-0.8, -0.04 - 0.29*k - 0.1, 0, -0.04 - 0.29*k), t=0.025, **kw(850 + k)), Matrix.Translation((0, 0, 0.12))))
    for x in (-0.75, -0.45, -0.15): geos.append((build_panel(rect(x, -1.2, x + 0.1, 0), t=0.12, **kw(856)), Matrix()))
    pezzo('Pallet', [(rimappa(g, {0: 3, 1: 3, 2: 3}), m) for g, m in geos], [M['kraft'], M['bordo'], M['interno'], M['legno']])
    pezzo('Casse', [(build_panel(rect(-0.75, -1.15, -0.05, -0.05), t=0.6, **kw(860)), Matrix.Translation((0, 0, 0.145))),
                    (build_panel(rect(-0.7, -1.1, -0.1, -0.4), t=0.4, **kw(861)), Matrix.Translation((0, 0, 0.745)))], MK)
    for i, n in enumerate([n for n in kit if n.startswith(('Cap_', 'Shed_', 'Ciminiera', 'Pallet', 'Casse'))]):
        kit[n].location = (-130.0, 30.0 - 5.0*i, 0)
    return kit

def capannone(nome, coll, kit, M, origine, seed=0, rot=0.0):
    # origine = angolo in basso a destra del fronte (lungo, sulla strada), davanti +X. Restituisce (radice, info)
    rng = random.Random(f'capannone-{seed}')
    n_l = 2*rng.randint(5, 10); n_d = rng.choice((6, 8, 10))                  # lunghezza pari: denti da 2 moduli
    colore = rng.choice(list(INTONACI_CAPANNONI) + ['kraft', 'kraft'])
    shed = rng.random() < 0.7
    W, D = n_l*MODULO, n_d*MODULO + 2*T; H = H_TERRA + H_PIANO
    # fronte: portoni da 4 m (due colonne), porte di servizio, lamiera; in alto il nastro di finestre
    terra = ['Cap_Parete']*n_l; k = 1
    while k < n_l - 2:
        if rng.random() < 0.55: terra[k] = 'Cap_Portone'; terra[k + 1] = None; k += 3
        elif rng.random() < 0.3: terra[k] = 'Cap_Porta'; k += 2
        else: k += 1
    alto = ['Cap_Finestrata' if rng.random() < 0.8 else 'Cap_Parete_Alta']*n_l if rng.random() < 0.7 else ['Cap_Parete_Alta']*n_l
    lati = {}
    for parete, n in (('Destra', n_d), ('Sinistra', n_d), ('Retro', n_l)):
        for kk in range(n):
            lati[(parete, 0, kk)] = 'Cap_Parete'; lati[(parete, 1, kk)] = 'Cap_Finestrata' if (parete == 'Retro' and rng.random() < 0.5) else 'Cap_Parete_Alta'
    if rng.random() < 0.5: lati[('Destra', 0, n_d//2)] = 'Cap_Porta'
    radice, H, W, D = palazzo(nome, coll, kit, M, origine, n_l, n_d, 1, colore, fronte={0: terra, 1: alto}, lati=lati,
                              fasce=False, persiane_prob=0.0, seed=seed, rot=rot)
    cnt = [0]
    def metti(padre, pezzo, loc, r=0.0, col=None):
        cnt[0] += 1
        return istanza(f'{nome}_{pezzo}_{cnt[0]}', kit[pezzo].data, coll, padre, Vector(loc), r, col)
    for kk, tp in enumerate(terra):
        if tp == 'Cap_Portone': metti(radice, 'Cap_Tettoia', (0, -MODULO*kk, 0))
    # tetto
    if shed:
        for i in range(n_l//2):
            metti(radice, f'Shed_{n_d}', (0, -2*MODULO*i, H))
            metti(radice, 'Shed_Testa', (0, -2*MODULO*i, H), 0, M[colore])
            metti(radice, 'Shed_Testa', (-D + T, -2*MODULO*i, H), 0, M[colore])
    else:
        for i in range(n_l):
            for j in range(n_d): metti(radice, 'Pal_Copertura', (-T - MODULO*j, -T - MODULO*i, H + 0.005))
        for parete, o, r, n, sx in pareti({'n_w': n_l, 'n_d': n_d}):
            for kk in range(n): metti(radice, 'Pal_Parapetto', o + sx*MODULO*kk + Vector((0, 0, H)), r, M[colore])
    # palazzina degli uffici sul fronte, a filo strada, all'estremità destra
    if rng.random() < 0.7:
        nu = rng.randint(2, 3); cu = rng.choice(list(UFFICI))
        uf, Hu, Wu, Du = palazzo(nome + '_Uffici', coll, kit, M, Vector((2.4, 0, 0)), nu, 1, 1, cu,
                                 fronte={0: ['Terra_Porta'] + ['Terra_Vetrina']*(nu - 1), 1: ['Modulo_Finestra']*nu},
                                 lati={(p_, li, kk): ('Modulo_Finestra' if li == 1 else 'Terra_Parete') for p_ in ('Destra', 'Sinistra', 'Retro') for li in (0, 1) for kk in range(3)},
                                 fasce=True, persiane_prob=0.0, seed=seed + 5)
        uf.parent = radice
        for kk in range(nu):
            for j in range(1): metti(uf, 'Pal_Copertura', (-T - MODULO*j, -T - MODULO*kk, Hu + 0.005))
    # ciminiera e silos dietro, pallet nel piazzale
    if rng.random() < 0.6: metti(radice, 'Ciminiera', (-D - 1.5, -rng.uniform(2, W - 2), 0), 0, M['rosso_cim'] if rng.random() < 0.6 else M['bianco'] if 'bianco' in M else None)
    for _ in range(rng.randint(0, 2)):
        o = metti(radice, 'Serbatoio', (-D - 2.0, -rng.uniform(2, W - 2), 0)); o.scale = (2.4, 2.4, 3.0)
    for _ in range(rng.randint(2, 6)):
        p = rng.choice(('Pallet', 'Pallet', 'Casse')); x = rng.uniform(1.0, 3.0); y = -rng.uniform(0.5, W - 1.5)
        o = metti(radice, p, (x + 0.8, y, 0), rng.choice((0, math.pi/2)))
        if p == 'Pallet' and rng.random() < 0.5: metti(radice, 'Casse', (x + 0.8, y, 0.145 - 0.145))
    return radice, {'W': W, 'D': D, 'H': H + (math.tan(SHED_A)*SHED_L if shed else 0.7), 'n_l': n_l, 'n_d': n_d, 'shed': shed, 'colore': colore}

def run_capannoni(semi=range(1, 5)):
    c = bpy.data.collections.get('Capannoni_Campione')
    if c:
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    else:
        c = bpy.data.collections.new('Capannoni_Campione'); bpy.context.scene.collection.children.link(c)
    M = materiali_capannoni(materiali_ville(materiali_palazzoni(materiali()))); kit = {o.name: o for o in bpy.data.collections['Kit_Borgo'].objects}
    kit = costruisci_kit_capannoni(M, kit, bpy.data.collections['Kit_Borgo'])
    y, out = 0.0, []
    for sd in semi:
        r, info = capannone(f'CP{sd}', c, kit, M, Vector((220.0, y, 0.0)), seed=sd)
        out.append(info); y -= info['W'] + 10.0
    return out

# =====================================================================
# GRATTACIELI (uffici e commercio, T04)
#   torri sottili fino a 10 piani (terra 4 m + fino a 9 piani da 3 m, circa
#   31 m): 2-3 scatole impilate e arretrate, ognuna col suo colore, come
#   scatole di cereali una sull'altra; finestre a nastro (strisce di carta
#   azzurrina) o facciate tutte vetrate a griglia; atrio vetrato al terra;
#   in cima il coronamento oppure le alette della scatola aperte, il locale
#   macchine e il pennone. Grigi e azzurri, pochissimo kraft.
# =====================================================================
INTONACI_GRATTACIELI = {'grigio_gr': (0.66, 0.68, 0.70), 'grigio_scuro_gr': (0.42, 0.45, 0.49), 'azzurro_gr': (0.55, 0.68, 0.80),
                        'blu_gr': (0.30, 0.42, 0.58), 'argento_gr': (0.80, 0.81, 0.82), 'petrolio_gr': (0.26, 0.44, 0.48)}
VETRO_GR = (0.66, 0.78, 0.88)                 # carta azzurrina delle finestre

def materiali_grattacieli(M):
    for k, c in INTONACI_GRATTACIELI.items(): M[k] = mat_vernice('CB_G_' + k, (*c, 1), 0.66, SC*0.3)
    M['vetro_gr'] = mat_plain('CB_G_Vetro', (*VETRO_GR, 1), 0.45)
    return M

def costruisci_kit_grattacieli(M, kit, coll):
    mats = [mat_kit(), M['bordo'], M['interno'], M['kraft'], M['vetro_gr']]
    liscio = dict(rough=0.0, warp=0.0, nick=0.0, step=50.0)
    def pezzo(nome, geos, mm=mats):
        o = bpy.data.objects.get(nome)
        if o: d = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(d)
        kit[nome] = make_object(nome, geos, mm, coll); return kit[nome]
    def foglio(r, t_=T, x=0.0, sd=0, vetro=False):
        g = build_panel(r, t=t_, **(liscio if vetro else kw(sd)))
        return (rimappa(g, {0: 4}) if vetro else g), frame((x - T if not vetro else x, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))
    # ---- nastro: parapetto pieno sotto e sopra, striscia di carta azzurrina in mezzo, montanti ogni metro ----
    geos = [foglio(rect(0, 0, MODULO, 0.9), sd=900), foglio(rect(0, 2.4, MODULO, H_PIANO), sd=901),
            foglio(rect(0, 0.9, MODULO, 2.4), 0.02, -T/2, vetro=True)]
    for u in (0.0, 1.0):
        geos.append((build_panel(rect(u, 0.9, u + 0.05, 2.4), t=0.06, **liscio), frame((-T/2 - 0.02, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
    geos.append((rimappa(build_panel(rect(0, 1.62, MODULO, 1.66), t=0.01, **liscio), {0: 1}), frame((-T/2 + 0.005, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))   # giunta della striscia di carta
    pezzo('Gr_Nastro', geos)
    # ---- facciata vetrata: tutta carta azzurrina con la griglia ----
    geos = [foglio(rect(0, 0, MODULO, H_PIANO), 0.02, -T/2, vetro=True)]
    for r in (rect(0, 0, 0.06, H_PIANO), rect(0.97, 0, 1.03, H_PIANO), rect(0, 0, MODULO, 0.18), rect(0, 1.45, MODULO, 1.5)):
        geos.append((build_panel(r, t=0.06, **liscio), frame((-T/2 - 0.02, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
    pezzo('Gr_Vetrata', geos)
    # ---- atrio vetrato del piano terra (4 m) con la fascia in alto e la porta ----
    geos = [foglio(rect(0, 0, MODULO, 3.4), 0.02, -T/2, vetro=True), foglio(rect(0, 3.4, MODULO, H_TERRA), sd=902)]
    for r in (rect(0, 0, 0.06, 3.4), rect(0.97, 0, 1.03, 3.4), rect(0, 2.55, MODULO, 2.6)):
        geos.append((build_panel(r, t=0.06, **liscio), frame((-T/2 - 0.02, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))))
    pezzo('Gr_Terra_Vetrata', geos)
    # ---- coronamento (1 m con la cimasa) e aletta della scatola aperta (inclinata in fuori di 25°) ----
    pezzo('Gr_Coronamento', [(build_panel(rect(0, 0, MODULO, 1.0), t=T, **kw(903)), m_modulo()),
                             (build_panel(rect(0, 1.0, MODULO, 1.12), t=0.18, **kw(904)), frame((-T - 0.05, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0)))])
    a = math.radians(25); v = Vector((math.sin(a), 0, math.cos(a))); u = Vector((0, -1, 0))
    pezzo('Gr_Aletta', [(build_panel(rect(0, 0, MODULO, 1.1), t=0.03, **kw(905)), frame((-T/2, 0, 0), tuple(u), tuple(v), tuple(u.cross(v))))])
    # ---- pennone sul tetto (tinta per oggetto) ----
    geos = [palo((0, 0, 0), 6.0, 0.06)]
    for z, l in ((4.6, 1.2), (5.4, 0.8)):
        geos.append((build_panel(circle(0, 0, 0.025, 6), t=l, **liscio), frame((0, -l/2, z), (1, 0, 0), (0, 0, 1), (0, 1, 0))))
    pezzo('Gr_Pennone', geos)
    for i, n in enumerate([n for n in kit if n.startswith('Gr_')]):
        kit[n].location = (-150.0, 30.0 - 4.0*i, 0)
    return kit

def grattacielo(nome, coll, kit, M, origine, seed=0, rot=0.0):
    # origine = angolo in basso a destra della facciata della scatola di base, davanti +X. Restituisce (radice, info)
    rng = random.Random(f'grattacielo-{seed}')
    n_w, n_d = rng.randint(3, 4), rng.randint(3, 4)
    tot = rng.randint(7, 9)                                       # piani sopra il terra: 8-10 piani in tutto
    n_vol = rng.choice((2, 3, 3))
    tagli = sorted(rng.sample(range(2, tot), n_vol - 1)); piani = [b - a for a, b in zip([0] + tagli, tagli + [tot])]
    radice = bpy.data.objects.new(nome, None); coll.objects.link(radice)
    radice.location = origine; radice.rotation_euler = (0, 0, rot); radice.empty_display_size = 2.0
    cnt = [0]
    def metti(padre, pezzo, loc, r=0.0, col=None):
        cnt[0] += 1
        return istanza(f'{nome}_{pezzo}_{cnt[0]}', kit[pezzo].data, coll, padre, Vector(loc), r, col)
    o = Vector((0, 0, 0)); w, d = n_w, n_d; prec = None; vols = []
    for i, p in enumerate(piani):
        if i > 0:                                                 # la scatola sopra è più stretta e spostata
            nw, nd = max(2, w - rng.choice((0, 1, 1))), max(2, d - rng.choice((0, 1, 1)))
            if (nw, nd) == (w, d): nw = max(2, w - 1)
            o = o + Vector((-MODULO*rng.randint(0, d - nd), -MODULO*rng.randint(0, w - nw), 0)); w, d = nw, nd
        colore = rng.choice([c for c in INTONACI_GRATTACIELI if c != prec]); prec = colore
        modulo = rng.choice(('Gr_Nastro', 'Gr_Nastro', 'Gr_Vetrata'))
        terra = i == 0
        fronte = {li: [modulo]*w for li in range(1 if terra else 0, p + (1 if terra else 0))}
        if terra: fronte[0] = ['Gr_Terra_Vetrata']*w
        lati = {}
        for parete, n in (('Destra', d), ('Sinistra', d), ('Retro', w)):
            for li in range(p + (1 if terra else 0)):
                for k in range(n): lati[(parete, li, k)] = ('Terra_Parete' if parete == 'Retro' else 'Gr_Terra_Vetrata') if (terra and li == 0) else modulo
        v, H, W, D = palazzo(f'{nome}_Scatola_{i}', coll, kit, M, o.copy(), w, d, p, colore, fronte=fronte, lati=lati, terra=terra,
                             fasce=False, persiane_prob=0.0, seed=seed*10 + i)
        v.parent = radice; vols.append((v, H, W, D, w, d, colore))
        o = o + Vector((0, 0, H))
    # bordo in cima a ogni scatola: coronamento, o le alette aperte sull'ultima
    for i, (v, H, W, D, w, d, colore) in enumerate(vols):
        alette = i == len(vols) - 1 and rng.random() < 0.5
        for parete, oo, r, n, sx in pareti({'n_w': w, 'n_d': d}):
            for k in range(n): metti(v, 'Gr_Aletta' if alette else 'Gr_Coronamento', oo + sx*MODULO*k + Vector((0, 0, H)), r, M[colore])
    # locale macchine e pennone sull'ultima scatola
    v, H, W, D, w, d, colore = vols[-1]
    lm, Hl, _, _ = palazzo(f'{nome}_Macchine', coll, kit, M, Vector((-MODULO*rng.randint(0, d - 2) - 0.5, -0.5 - MODULO*rng.randint(0, w - 2), H)), 1, 1, 1,
                           'grigio_scuro_gr', fronte={0: ['Modulo_Parete']}, lati={(pp, 0, 0): 'Modulo_Parete' for pp in ('Destra', 'Sinistra', 'Retro')},
                           terra=False, fasce=False, persiane_prob=0.0, seed=seed + 77)
    lm.parent = v
    if rng.random() < 0.7: metti(v, 'Gr_Pennone', (-D*0.7, -W*0.3, H), 0, M['argento_gr'])
    Htot = vols[-1][0].location.z + vols[-1][1] + 1.12
    return radice, {'W': n_w*MODULO, 'D': n_d*MODULO + 2*T, 'H': Htot, 'piani': tot + 1, 'scatole': len(vols)}

def run_grattacieli(semi=range(1, 6)):
    c = bpy.data.collections.get('Grattacieli_Campione')
    if c:
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    else:
        c = bpy.data.collections.new('Grattacieli_Campione'); bpy.context.scene.collection.children.link(c)
    M = materiali_grattacieli(materiali()); kit = {o.name: o for o in bpy.data.collections['Kit_Borgo'].objects}
    kit = costruisci_kit_grattacieli(M, kit, bpy.data.collections['Kit_Borgo'])
    y, out = 0.0, []
    for sd in semi:
        r, info = grattacielo(f'GR{sd}', c, kit, M, Vector((260.0, y, 0.0)), seed=sd)
        out.append(info); y -= info['W'] + 8.0
    return out

# =====================================================================
# EDIFICI SPECIALI — 1. IL COMUNE (palazzo comunale, piazza del centro storico)
#   blocco di 6 x 5 moduli (12 x 10 m) e torre civica di 2 x 2 moduli sul
#   fianco sinistro: in tutto circa 16 x 10 m. Piano terra a loggiato (archi
#   alti 3,6 m, loggia profonda 2,3 m con porte e vetrine dietro), piano nobile
#   con le bifore e l'arengario al centro (portefinestre ad arco, bandiere),
#   secondo piano con le finestre incorniciate e lo stemma, merli guelfi in
#   cima. Torre: feritoie, orologio su due lati, cella campanaria ad archi,
#   merli e cuspide di coppi; circa 28 m, il punto più alto del centro storico.
#   Stesse misure del kit: modulo 2 m, terra 4 m, piani 3 m.
# =====================================================================
def arco(u0, u1, z0, zi, n=10):
    # contorno di un'apertura ad arco a tutto sesto: rettangolo fino all'imposta zi, poi mezzo cerchio
    c, r = (u0 + u1)/2, (u1 - u0)/2
    return [(u0, z0), (u1, z0)] + [(c + r*math.cos(math.pi*k/n), zi + r*math.sin(math.pi*k/n)) for k in range(n + 1)]

APERTURE_COMUNE = {
    'Com_Arco': (H_TERRA, [arco(0.3, 1.7, 0.02, 2.9)]),
    'Com_Bifora': (H_PIANO, [arco(0.45, 0.95, 1.0, 2.15, 6), arco(1.05, 1.55, 1.0, 2.15, 6)]),
    'Com_Portafinestra_Arco': (H_PIANO, [arco(0.5, 1.5, 0.02, 2.0)]),
    'Com_Cella': (H_PIANO, [arco(0.35, 1.65, 0.6, 2.0)]),
    'Com_Feritoia': (H_PIANO, [rect(0.85, 1.0, 1.15, 2.2)]),
}
APERTURE.update(APERTURE_COMUNE)
COMUNE_COLORI = {'pietra_com': (0.80, 0.70, 0.54), 'mattone_com': (0.62, 0.36, 0.25)}

def materiali_comune(M):
    for k, c in COMUNE_COLORI.items(): M[k] = mat_vernice('CB_S_' + k, (*c, 1), 0.70, SC*0.3)
    M['stucco'] = M.get('stucco') or mat_vernice('CB_C_Stucco', (0.92, 0.88, 0.78, 1), 0.66, SC*0.3)
    M['coppi'] = M.get('coppi') or mat_vernice('CB_V_Coppi', (0.72, 0.25, 0.15, 1), 0.70, SC*0.3)
    for k, c in (('Rosso', (0.72, 0.12, 0.12)), ('Bianco', (0.95, 0.94, 0.90)), ('Verde', (0.10, 0.50, 0.25)), ('Oro', (0.80, 0.62, 0.22))):
        M['s_' + k.lower()] = mat_plain('CB_S_' + k, (*c, 1), 0.7)
    return M

def costruisci_kit_comune(M, kit, coll):
    mats = [mat_kit(), M['bordo'], M['interno'], M['kraft']]
    liscio = dict(rough=0.0, warp=0.0, nick=0.0, step=50.0)
    fuori = lambda x=0.0: frame((x, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))
    def pezzo(nome, geos, mm=mats):
        o = bpy.data.objects.get(nome)
        if o: d = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(d)
        kit[nome] = make_object(nome, geos, mm, coll); return kit[nome]
    # ---- muri con le aperture ----
    for i, (nome, (h, buchi)) in enumerate(APERTURE_COMUNE.items()):
        pezzo(nome, [(build_panel(rect(0, 0, MODULO, h), holes=buchi, t=T, **kw(950 + i)), m_modulo())])
    # ---- cornici di stucco (tinte per oggetto): archivolto con l'imposta, cornici di bifora e portafinestra ----
    def anello(u0, u1, z0, zi, e, sd):
        est = arco(u0 - e, u1 + e, z0, zi, 10); inn = arco(u0, u1, z0 + 0.001, zi, 10)
        return build_panel(est, holes=[inn], t=0.05, **kw(sd))
    pezzo('Com_Arco_Cornice', [(anello(0.3, 1.7, 2.9, 2.9, 0.12, 960), fuori()),
                               (build_panel(rect(0, 2.8, 0.3, 2.95), t=0.07, **kw(961)), fuori()),
                               (build_panel(rect(1.7, 2.8, MODULO, 2.95), t=0.07, **kw(962)), fuori())])
    pezzo('Com_Bifora_Cornice', [(anello(0.45, 1.55, 2.15, 2.15, 0.1, 963), fuori()),
                                 (build_panel(rect(0.3, 0.86, 1.7, 1.0), t=0.09, **kw(964)), fuori()),
                                 (build_panel(rect(0.95, 1.0, 1.05, 2.15), t=0.06, **liscio), fuori())])            # colonnina
    pezzo('Com_Portafinestra_Cornice', [(anello(0.5, 1.5, 2.0, 2.0, 0.12, 965), fuori()),
                                        (build_panel(rect(0.38, 0.0, 0.5, 2.0), t=0.05, **kw(966)), fuori()),
                                        (build_panel(rect(1.5, 0.0, 1.62, 2.0), t=0.05, **kw(967)), fuori())])
    # ---- merli guelfi (un modulo, due merli), soffitto della loggia, cuspide di coppi della torre ----
    merlo = [(0, 0), (2, 0), (2, 0.55), (1.75, 0.55), (1.75, 1.1), (1.25, 1.1), (1.25, 0.55), (0.75, 0.55), (0.75, 1.1), (0.25, 1.1), (0.25, 0.55), (0, 0.55)]
    pezzo('Com_Merlo', [(build_panel(merlo, t=T, **kw(970)), m_modulo())])
    pezzo('Com_Soffitto_Loggia', [(build_panel(rect(-2.3, -MODULO, 0, 0), t=T, **kw(971)), Matrix.Translation((0, 0, H_TERRA - T)))])
    L, hc = 4.0 + 2*T, 2.8                                      # cuspide su 4 x 4 m, origine all'angolo come i moduli
    tri = lambda a, b: [(a[0], a[1]), (b[0], b[1]), (0.0, hc)]
    geos = []
    for i in range(4):
        ang = math.pi/2*i; d = Vector((math.cos(ang), math.sin(ang), 0)); u = Vector((-math.sin(ang), math.cos(ang), 0))
        c = Vector((-L/2, -L/2, 0)) + d*L/2
        n = d.copy(); v = (Vector((0, 0, hc)) - d*L/2).normalized()
        geos.append((rimappa(build_panel([(-L/2, 0.0), (L/2, 0.0), (0.0, (Vector((0, 0, hc)) - d*L/2).length)], t=0.03, **kw(972 + i)), {0: 3}),
                     frame(tuple(c), tuple(u), tuple(v), tuple(u.cross(v)))))
    pezzo('Com_Cuspide', geos, [M['coppi'], M['bordo'], M['interno'], M['coppi']])
    # ---- orologio (quadrante di stucco, lancette e tacche scure), stemma, bandiere ----
    geos = [(build_panel(circle(0, 0, 0.8, 24), t=0.06, **kw(976)), fuori()),
            (rimappa(build_panel(circle(0, 0, 0.9, 24), holes=[circle(0, 0, 0.8, 24)], t=0.08, **kw(977)), {0: 3}), fuori())]
    for r_ in (rect(-0.03, 0.0, 0.03, 0.6), rect(0.0, -0.035, 0.42, 0.035)) + tuple(rect(x - 0.03, y - 0.03, x + 0.03, y + 0.03) for x, y in ((0, 0.7), (0.7, 0), (0, -0.7), (-0.7, 0))):
        geos.append((rimappa(build_panel(r_, t=0.02, **liscio), {0: 2}), fuori(0.06)))
    pezzo('Com_Orologio', geos)
    scudo = [(-0.45, 0.45), (0.45, 0.45), (0.45, -0.15), (0.0, -0.65), (-0.45, -0.15)]
    pezzo('Com_Stemma', [(build_panel(scudo, t=0.05, **kw(980)), fuori()),
                         (rimappa(build_panel(rect(-0.08, -0.5, 0.08, 0.38), t=0.02, **liscio), {0: 3}), fuori(0.05)),
                         (rimappa(build_panel(rect(-0.38, 0.05, 0.38, 0.2), t=0.02, **liscio), {0: 3}), fuori(0.05)),
                         (rimappa(build_panel([(-0.3, 0.45), (-0.3, 0.62), (-0.15, 0.52), (0.0, 0.68), (0.15, 0.52), (0.3, 0.62), (0.3, 0.45)], t=0.04, **kw(981)), {0: 4}), fuori())],
          [M['s_rosso'], M['bordo'], M['interno'], M['s_bianco'], M['s_oro']])
    a = math.radians(35); d = Vector((math.cos(a), 0, math.sin(a)))       # asta inclinata in fuori dalla facciata
    geos = [(rimappa(build_panel(circle(0, 0, 0.03, 6), t=2.6, **liscio), {0: 4, 1: 4, 2: 4}), frame((0, 0, 0), (0, 1, 0), (0, 0, 1).__class__((d.z*0, 1, 0)) if False else (0, 1, 0), (0, 0, 1)))] if False else []
    asta = build_panel(circle(0, 0, 0.03, 6), t=2.6, **liscio)
    geos.append((rimappa(asta, {0: 4, 1: 4, 2: 4}), Matrix.Rotation(math.pi/2 - a, 4, 'Y')))
    top = d*2.6
    for k, col in enumerate((3, 5, 6)):                           # tricolore lungo l'asta: verde, bianco, rosso
        u0 = 1.5 + 0.35*k
        geos.append((rimappa(build_panel(rect(u0, -0.75, u0 + 0.35, 0.0), t=0.01, **liscio), {0: col}),
                     frame((0, 0.005, 0), tuple(d), (math.sin(a)*-1*0, 0, 0) if False else tuple(Vector((-math.sin(a), 0, math.cos(a)))), (0, 1, 0))))
    pezzo('Com_Bandiera', geos, [M['bordo'], M['bordo'], M['interno'], M['s_verde'], M['legno'], M['s_bianco'], M['s_rosso']])
    # ---- arengario: balcone di pietra largo due moduli, parapetto pieno con la cimasa, mensole sotto ----
    P = 1.0; W2 = 2*MODULO
    geos = [(build_panel(rect(0, -W2, P, 0), t=0.14, **kw(985)), Matrix.Translation((0, 0, -0.14))),
            (build_panel(rect(0, 0, W2, 0.95), t=0.1, **kw(986)), frame((P - 0.1, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))),
            (build_panel(rect(0, 0.95, W2 + 0.0, 1.07), t=0.18, **kw(987)), frame((P - 0.14, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0)))]
    for y in (0.0, -W2 + 0.1):
        geos.append((build_panel(rect(0, 0, P, 1.0), t=0.1, **kw(988)), frame((0, y, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))))
    for y in (-0.3, -2.0, -3.7):
        geos.append((build_panel([(0.0, 0.0), (0.85, 0.0), (0.0, -0.7)], t=0.14, **kw(989)), frame((0, y + 0.07, -0.14), (1, 0, 0), (0, 0, 1), (0, -1, 0))))
    pezzo('Com_Arengario', geos)
    for i, n in enumerate([n for n in kit if n.startswith('Com_')]):
        kit[n].location = (-170.0, 30.0 - 4.0*i, 0)
    return kit

def comune(nome, coll, kit, M, origine, rot=0.0, n_w=6, n_d=5, seed=1):
    # origine = angolo in basso a destra della facciata del blocco, davanti +X (la piazza). Restituisce (radice, info)
    rng = random.Random(f'comune-{seed}')
    W, D = n_w*MODULO, n_d*MODULO + 2*T; zp = lambda p: H_TERRA + H_PIANO*(p - 1)
    kc = n_w//2 - 1                                                   # le due colonne dell'arengario
    radice = bpy.data.objects.new(nome, None); coll.objects.link(radice)
    radice.location = origine; radice.rotation_euler = (0, 0, rot); radice.empty_display_size = 2.0
    cnt = [0]
    def metti(padre, pezzo, loc, r=0.0, col=None):
        cnt[0] += 1
        return istanza(f'{nome}_{pezzo}_{cnt[0]}', kit[pezzo].data, coll, padre, Vector(loc), r, col)
    # ---- blocco: loggiato, piano nobile, secondo piano ----
    fronte = {0: ['Com_Arco']*n_w,
              1: [('Com_Portafinestra_Arco' if k in (kc, kc + 1) else 'Com_Bifora') for k in range(n_w)],
              2: [('Modulo_Parete' if k in (kc, kc + 1) else 'Modulo_Finestra') for k in range(n_w)]}
    lati = {('Destra', 0, n_d - 1): 'Com_Arco'}
    for li in range(3):
        for k in (0, 1): lati[('Sinistra', li, k)] = None                    # contro la torre
        for k in range(n_d):
            if ('Destra', li, k) not in lati: lati[('Destra', li, k)] = {0: 'Terra_Parete', 1: 'Com_Bifora', 2: 'Modulo_Finestra'}[li]
        for k in range(n_w): lati[('Retro', li, k)] = {0: ('Terra_Portone' if k == n_w//2 else 'Terra_Parete'), 1: 'Modulo_Finestra', 2: 'Modulo_Finestra'}[li]
        for k in range(2, n_d): lati[('Sinistra', li, k)] = {0: 'Terra_Parete', 1: 'Com_Bifora', 2: 'Modulo_Finestra'}[li]
    blocco, H, _, _ = palazzo(nome + '_Blocco', coll, kit, M, Vector((0, 0, 0)), n_w, n_d, 2, 'pietra_com', fronte=fronte, lati=lati,
                              fasce=False, persiane_prob=0.0, seed=seed)
    blocco.parent = radice
    # loggia: parete interna con porte e vetrine, soffitto
    for k in range(n_w):
        tp = 'Terra_Portone' if k in (kc, kc + 1) and k == kc else ('Terra_Porta' if k == kc + 1 else 'Terra_Vetrina')
        metti(blocco, tp, (-2.3, -MODULO*k, 0), 0, M['pietra_com'])
        metti(blocco, 'Com_Soffitto_Loggia', (0, -MODULO*k, 0), 0, M['stucco'])
        metti(blocco, 'Com_Arco_Cornice', (0, -MODULO*k, 0), 0, M['stucco'])
    metti(blocco, 'Com_Arco_Cornice', (-D + T + MODULO*(n_d - 1), 0, 0), math.pi/2, M['stucco'])
    # fasce, cornici, arengario, stemma, bandiere
    for parete, o, r, n, sx in pareti({'n_w': n_w, 'n_d': n_d}):
        for k in range(n):
            if parete == 'Sinistra' and k < 2: continue
            for z in (H_TERRA - 0.08, zp(2) - 0.08): metti(blocco, 'Marcapiano', o + sx*MODULO*k + Vector((0, 0, z)), r, M['stucco'])
            metti(blocco, 'Com_Merlo', o + sx*MODULO*k + Vector((0, 0, H)), r, M['pietra_com'])
            tp1 = fronte[1][k] if parete == 'Fronte' else lati.get((parete, 1, k))
            tp2 = fronte[2][k] if parete == 'Fronte' else lati.get((parete, 2, k))
            if tp1 == 'Com_Bifora': metti(blocco, 'Com_Bifora_Cornice', o + sx*MODULO*k + Vector((0, 0, zp(1))), r, M['stucco'])
            if tp1 == 'Com_Portafinestra_Arco': metti(blocco, 'Com_Portafinestra_Cornice', o + sx*MODULO*k + Vector((0, 0, zp(1))), r, M['stucco'])
            if tp2 == 'Modulo_Finestra': metti(blocco, 'Cornice_Finestra', o + sx*MODULO*k + Vector((0, 0, zp(2))), r, M['stucco'])
    for i in range(n_w):
        for j in range(n_d): metti(blocco, 'Pal_Copertura', (-T - MODULO*j, -T - MODULO*i, H - 0.2))
    metti(blocco, 'Com_Arengario', (0, -MODULO*kc, zp(1)), 0, M['pietra_com'])
    metti(blocco, 'Com_Stemma', (0, -MODULO*(kc + 1), zp(2) + 1.6))
    for y in (-MODULO*kc - 0.15, -MODULO*(kc + 2) + 0.15):
        metti(blocco, 'Com_Bandiera', (0.95, y, zp(1) + 1.0))
    # ---- torre civica: 2 x 2 moduli sul fianco sinistro, terra + 6 piani + cella campanaria ----
    n_t = 6
    ft = {0: ['Terra_Portone', 'Terra_Parete']}
    for p in range(1, n_t + 1): ft[p] = ['Com_Feritoia' if p % 2 == 1 else 'Modulo_Parete']*2
    ft[n_t + 1] = ['Com_Cella']*2
    lt = {}
    for li in range(n_t + 2):
        for parete in ('Destra', 'Sinistra', 'Retro'):
            for k in range(2):
                if parete == 'Destra' and li <= 2: lt[(parete, li, k)] = None                # contro il blocco
                elif li == n_t + 1: lt[(parete, li, k)] = 'Com_Cella'
                elif li == 0: lt[(parete, li, k)] = 'Terra_Parete'
                else: lt[(parete, li, k)] = 'Com_Feritoia' if (li % 2 == 1 and k == 0) else 'Modulo_Parete'
    torre, Ht, Wt, Dt = palazzo(nome + '_Torre', coll, kit, M, Vector((0, -W, 0)), 2, 2, n_t + 1, 'mattone_com', fronte=ft, lati=lt,
                                fasce=False, persiane_prob=0.0, seed=seed + 3)
    torre.parent = radice
    for parete, o, r, n, sx in pareti({'n_w': 2, 'n_d': 2}):
        for k in range(n):
            metti(torre, 'Com_Merlo', o + sx*MODULO*k + Vector((0, 0, Ht)), r, M['mattone_com'])
            metti(torre, 'Marcapiano', o + sx*MODULO*k + Vector((0, 0, zp(n_t + 1) - 0.08)), r, M['stucco'])
            if not (parete == 'Destra'): metti(torre, 'Marcapiano', o + sx*MODULO*k + Vector((0, 0, zp(3) - 0.08)), r, M['stucco'])
    metti(torre, 'Com_Cuspide', (0, 0, Ht - 0.1))
    zo = zp(n_t - 1) + 1.5
    metti(torre, 'Com_Orologio', (0, -MODULO, zo))                                       # sulla piazza
    metti(torre, 'Com_Orologio', (-Dt/2 - 0.0, -2*MODULO - T, zo), -math.pi/2)            # sul fianco
    return radice, {'W': W + 2*MODULO, 'D': D, 'H': Ht + 2.8, 'blocco_H': H}

def run_comune():
    c = bpy.data.collections.get('Speciali_Campione')
    if c:
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    else:
        c = bpy.data.collections.new('Speciali_Campione'); bpy.context.scene.collection.children.link(c)
    M = materiali_comune(materiali_palazzoni(materiali_corte(materiali()))); kit = {o.name: o for o in bpy.data.collections['Kit_Borgo'].objects}
    kit = costruisci_kit_comune(M, kit, bpy.data.collections['Kit_Borgo'])
    return comune('Comune', c, kit, M, Vector((300.0, 40.0, 0.0)))

# =====================================================================
# EDIFICI SPECIALI — 2. IL DUOMO (ispirato alla cattedrale di Trani)
#   romanico pugliese in pietra bianco-rosata, ridotto alla scala del gioco:
#   - chiesa a tre navate larga 16 m (centrale 8 m, laterali 4 m) e lunga
#     22 m più l'abside; la chiesa superiore poggia sulla cripta (4 m), con
#     la terrazza davanti alla facciata e la scalinata a doppia rampa che sale
#     al pianerottolo davanti al portale; sotto, l'arco vetrato della cripta;
#   - facciata a capanna con le spalle inclinate delle navate laterali:
#     arcate cieche su colonnine, portale con l'archivolto e la porta di
#     bronzo, due porte laterali, tre finestre ad arco, il rosone, la
#     finestrella in alto, la cornice lungo i bordi, la croce in cima;
#   - campanile a destra, staccato: arco ogivale alla base (si passa sotto),
#     poi bifore, trifora, quadrifora e pentafora salendo, cornici a ogni
#     piano, belvedere con la ringhiera, tamburo ad archi e guglia: circa
#     30 m, sotto i grattacieli (32 m) e più alto della torre del Comune.
#   Origine all'angolo in basso a destra dell'ingombro (davanti al campanile),
#   davanti +X (la piazza), metri reali. Pezzi propri, non del kit: è unico.
# =====================================================================
PIETRA_TRANI = (0.90, 0.84, 0.74)

def materiali_duomo(M):
    M['pietra_trani'] = mat_vernice('CB_S_Pietra_Trani', (*PIETRA_TRANI, 1), 0.72, SC*0.3)
    M['tetto_pietra'] = mat_vernice('CB_S_Tetto_Pietra', (0.70, 0.64, 0.56, 1), 0.72, SC*0.3)
    M['vetro_chiesa'] = mat_plain('CB_S_Vetro_Chiesa', (0.55, 0.66, 0.58, 1), 0.4)
    M['bronzo'] = mat_plain('CB_S_Bronzo', (0.36, 0.24, 0.15, 1), 0.6)
    M['ferro'] = mat_plain('CB_S_Ferro', (0.18, 0.18, 0.19, 1), 0.6)
    return M

def ogiva(u0, u1, z0, zi, n=6):
    # arco a sesto acuto (equilatero): due archi di raggio pari alla luce
    w = u1 - u0; pts = [(u0, z0), (u1, z0)]
    pts += [(u0 + w*math.cos(math.radians(60*k/n)), zi + w*math.sin(math.radians(60*k/n))) for k in range(n + 1)]
    pts += [(u1 + w*math.cos(math.radians(120 + 60*k/n)), zi + w*math.sin(math.radians(120 + 60*k/n))) for k in range(1, n + 1)]
    return pts

def duomo(nome, coll, M, origine, rot=0.0, seed=1):
    mats = [M['pietra_trani'], M['bordo'], M['interno'], M['tetto_pietra'], M['vetro_chiesa'], M['bronzo'], M['ferro']]
    PI, BO, IN, TE, VE, BR, FE = range(7)
    radice = bpy.data.objects.new(nome, None); coll.objects.link(radice)
    radice.location = origine; radice.rotation_euler = (0, 0, rot); radice.empty_display_size = 3.0
    gruppi = {}
    def gruppo(g):
        if g not in gruppi:
            e = bpy.data.objects.new(f'{nome}_{g}', None); coll.objects.link(e); e.parent = radice; e.empty_display_size = 1.0
            gruppi[g] = e
        return gruppi[g]
    pezzi = {}
    def aggiungi(g, parte, geo, m):
        pezzi.setdefault((g, parte), []).append((geo, m))
    sd = [seed*1000]
    def k():
        sd[0] += 1; return kw(sd[0])
    liscio = dict(rough=0.0, warp=0.0, nick=0.0, step=50.0)
    def lastra(poly, holes, o, u, v, n, t=0.12, mat=PI, ruvido=True):
        g = build_panel(poly, holes=holes or None, t=t, **(k() if ruvido else liscio)) if holes else build_panel(poly, t=t, **(k() if ruvido else liscio))
        if mat != PI: g = rimappa(g, {0: mat})
        return g, frame(tuple(o), tuple(u), tuple(v), tuple(n))
    def poli3d(P, t=0.06, mat=PI):
        # lastra piana da punti 3D complanari (triangoli dei tetti, guglie)
        A = Vector(P[0]); u = (Vector(P[1]) - A).normalized(); nn = u.cross(Vector(P[2]) - A).normalized(); v = nn.cross(u)
        pts = [((Vector(p) - A).dot(u), (Vector(p) - A).dot(v)) for p in P]
        g = build_panel(pts, t=t, **k())
        if mat != PI: g = rimappa(g, {0: mat})
        return g, frame(tuple(A), tuple(u), tuple(v), tuple(nn))
    def scatola(x0, y0, z0, dx, dy, dz, mat=PI):
        g = build_panel(rect(x0, y0, x0 + dx, y0 + dy), t=dz, **k())
        if mat != PI: g = rimappa(g, {0: mat})
        return g, Matrix.Translation((0, 0, z0))
    def anello(est, inn, t=0.1):
        return build_panel(est, holes=[inn], t=t, **k())
    # ---------------- geometria principale ----------------
    S = 4.4; XT = -1.5                          # campanile: lato e fronte
    YR = -S - 0.6                               # bordo destro della chiesa
    XF = -3.0; LUN = 22.0; XB = XF - LUN        # facciata e fondo
    Y = lambda u: YR - u                         # u lungo la facciata (0 = destra, 16 = sinistra)
    FAC = dict(u=(0, -1, 0), v=(0, 0, 1), n=(1, 0, 0))
    tf = 0.14
    def in_facciata(x, z=0.0): return Vector((x, YR, z))
    # facciata in tre lastre (spalle e parte centrale), dalla terrazza (z 4) in su
    sx_dx = [(0, 4), (4, 4), (4, 13.5), (0, 11)]
    centro = [(4, 4), (12, 4), (12, 15.5), (8, 19.5), (4, 15.5)]
    sx_sx = [(12, 4), (16, 4), (16, 11), (12, 13.5)]
    aggiungi('Lato_Dx', 'Facciata', lastra(sx_dx, [rect(2.4, 4.02, 3.6, 5.8), arco(2.45, 3.55, 9.2, 10.4)], in_facciata(XF - tf), **FAC, t=tf), None)
    aggiungi('Lato_Sx', 'Facciata', lastra(sx_sx, [rect(12.4, 4.02, 13.6, 5.8), arco(12.45, 13.55, 9.2, 10.4)], in_facciata(XF - tf), **FAC, t=tf), None)
    buchi_c = [arco(7.0, 9.0, 4.02, 6.6), arco(7.35, 8.65, 9.0, 10.6), circle(8.0, 13.3, 0.95, 24), arco(7.75, 8.25, 16.3, 16.9, 6)]
    aggiungi('Centrale', 'Facciata', lastra(centro, buchi_c, in_facciata(XF - tf), **FAC, t=tf), None)
    # porte di bronzo e vetri dietro le aperture
    for poly, mat in ((arco(7.0, 9.0, 4.0, 6.6), BR), (rect(2.4, 4.0, 3.6, 5.8), BR), (rect(12.4, 4.0, 13.6, 5.8), BR),
                      (arco(7.35, 8.65, 9.0, 10.6), VE), (arco(2.45, 3.55, 9.2, 10.4), VE), (arco(12.45, 13.55, 9.2, 10.4), VE),
                      (circle(8.0, 13.3, 0.95, 24), VE), (arco(7.75, 8.25, 16.3, 16.9, 6), VE)):
        aggiungi('Dett', 'Dett_Porte_Vetri', lastra(poly, None, in_facciata(XF - tf - 0.05), **FAC, t=0.03, mat=mat, ruvido=False), None)
    # portale: archivolto a tre ghiere, stipiti
    for e in (0.18, 0.34, 0.5):
        aggiungi('Dett', 'Dett_Portale', (anello(arco(7.0 - e, 9.0 + e, 6.6, 6.6, 12), arco(7.0 - e + 0.16, 9.0 + e - 0.16, 6.6 + 0.001, 6.6, 12), t=0.12 + e*0.3),
                                         frame(tuple(in_facciata(XF)), **FAC)), None)
    for u0, u1 in ((6.5, 7.0), (9.0, 9.5)):
        aggiungi('Dett', 'Dett_Portale', (build_panel(rect(u0, 4.0, u1, 6.6), t=0.25, **k()), frame(tuple(in_facciata(XF)), **FAC)), None)
    # arcate cieche su colonnine, ai due lati del portale
    for a0s in ([0.4 + 1.2*i for i in range(5)], [9.6 + 1.2*i for i in range(5)]):
        for a0 in a0s:
            aggiungi('Dett', 'Dett_Arcata', (anello(arco(a0, a0 + 1.2, 6.1, 6.1, 10), arco(a0 + 0.12, a0 + 1.08, 6.1 + 0.001, 6.1, 10), t=0.1),
                                             frame(tuple(in_facciata(XF)), **FAC)), None)
            aggiungi('Dett', 'Dett_Arcata', (build_panel(rect(a0 - 0.06, 4.0, a0 + 0.06, 6.1), t=0.14, **liscio), frame(tuple(in_facciata(XF)), **FAC)), None)
        a = a0s[-1] + 1.2
        aggiungi('Dett', 'Dett_Arcata', (build_panel(rect(a - 0.06, 4.0, a + 0.06, 6.1), t=0.14, **liscio), frame(tuple(in_facciata(XF)), **FAC)), None)
    # cornici delle finestre (la centrale con le mensole), rosone con i raggi
    for u0, u1, z0, zi, e in ((7.35, 8.65, 9.0, 10.6, 0.22), (2.45, 3.55, 9.2, 10.4, 0.16), (12.45, 13.55, 9.2, 10.4, 0.16), (7.75, 8.25, 16.3, 16.9, 0.1)):
        aggiungi('Dett', 'Dett_Cornici', (anello(arco(u0 - e, u1 + e, z0, zi, 10), arco(u0, u1, z0 + 0.001, zi, 10), t=0.1), frame(tuple(in_facciata(XF)), **FAC)), None)
    for u0 in (6.85, 8.85):
        aggiungi('Dett', 'Dett_Cornici', (build_panel(rect(u0, 8.6, u0 + 0.3, 11.6), t=0.2, **k()), frame(tuple(in_facciata(XF)), **FAC)), None)
    aggiungi('Dett', 'Dett_Rosone', (anello(circle(8.0, 13.3, 1.25, 24), circle(8.0, 13.3, 0.95, 24), t=0.14), frame(tuple(in_facciata(XF)), **FAC)), None)
    aggiungi('Dett', 'Dett_Rosone', (build_panel(circle(8.0, 13.3, 0.22, 12), t=0.1, **liscio), frame(tuple(in_facciata(XF)), **FAC)), None)
    for i in range(12):
        a = 2*math.pi*i/12; ca, sa = math.cos(a), math.sin(a); w = 0.035
        q = [(8.0 + ca*r_ - sa*s_, 13.3 + sa*r_ + ca*s_) for r_, s_ in ((0.2, -w), (0.96, -w), (0.96, w), (0.2, w))]
        aggiungi('Dett', 'Dett_Rosone', (build_panel(q, t=0.08, **liscio), frame(tuple(in_facciata(XF - 0.02)), **FAC)), None)
    # cornice lungo i bordi alti della facciata
    bordo = [(0, 11), (4, 13.5), (4, 15.5), (8, 19.5), (12, 15.5), (12, 13.5), (16, 11)]
    for (u0, v0), (u1, v1) in zip(bordo, bordo[1:]):
        if abs(u1 - u0) < 1e-6: continue
        d = Vector((u1 - u0, v1 - v0)).normalized(); nn = Vector((d.y, -d.x)) if d.x > 0 else Vector((-d.y, d.x))
        nn = nn if nn.y < 0 else -nn
        q = [(u0, v0), (u1, v1), (u1 + nn.x*0.22, v1 + nn.y*0.22), (u0 + nn.x*0.22, v0 + nn.y*0.22)]
        aggiungi('Dett', 'Dett_Cornici', (build_panel(q, t=0.16, **k()), frame(tuple(in_facciata(XF)), **FAC)), None)
    # croce in cima e pinnacoli sulle spalle
    for r_ in (rect(7.94, 19.4, 8.06, 20.6), rect(7.65, 20.1, 8.35, 20.22)):
        aggiungi('Dett', 'Dett_Croce', (rimappa(build_panel(r_, t=0.06, **liscio), {0: FE}), frame(tuple(in_facciata(XF - tf/2)), **FAC)), None)
    for u in (0.35, 15.65):
        y = Y(u); aggiungi('Dett', 'Dett_Pinnacolo', scatola(XF - 0.45, y - 0.2, 11.0, 0.4, 0.4, 0.9), None)
        ap = (XF - 0.25, y, 12.6); b = [(XF - 0.45, y - 0.2, 11.9), (XF - 0.05, y - 0.2, 11.9), (XF - 0.05, y + 0.2, 11.9), (XF - 0.45, y + 0.2, 11.9)]
        for i in range(4): aggiungi('Dett', 'Dett_Pinnacolo', poli3d([b[i], b[(i + 1) % 4], ap], 0.04), None)
    # ---------------- corpo della chiesa ----------------
    for lato, yw, sgn, g in (('Dx', YR, 1, 'Lato_Dx'), ('Sx', YR - 16, -1, 'Lato_Sx')):
        # muro della navata laterale (da terra a 11 m): finestre ad arco e finestrelle della cripta
        holes = []
        for kk in range(6):
            uc = 2.4 + 3.6*kk; holes += [arco(uc - 0.5, uc + 0.5, 6.4, 8.0), rect(uc - 0.4, 1.3, uc + 0.4, 2.2)]
        if sgn > 0: o, uu, nn = Vector((XF, yw - 0.12, 0)), (-1, 0, 0), (0, 1, 0)
        else: o, uu, nn = Vector((XB, yw + 0.12, 0)), (1, 0, 0), (0, -1, 0)
        aggiungi(g, 'Muro', lastra(rect(0, 0, LUN, 11.0), holes, o, uu, (0, 0, 1), nn), None)
        for kk in range(6):
            uc = 2.4 + 3.6*kk
            for poly in (arco(uc - 0.5, uc + 0.5, 6.4, 8.0), rect(uc - 0.4, 1.3, uc + 0.4, 2.2)):
                aggiungi('Dett', 'Dett_Porte_Vetri', lastra(poly, None, o - Vector(nn)*0.05, uu, (0, 0, 1), nn, t=0.02, mat=VE, ruvido=False), None)
        # cleristorio (muro della navata centrale sopra il tetto laterale)
        yc = YR - 4 if sgn > 0 else YR - 12
        holes = [arco(1.9 + 3.6*kk - 0.35, 1.9 + 3.6*kk + 0.35, 13.8, 14.6, 6) for kk in range(6)]
        o2 = Vector((XF, yc - 0.1, 0)) if sgn > 0 else Vector((XB, yc + 0.1, 0))
        aggiungi('Centrale', 'Cleristorio', lastra(rect(0, 11.0, LUN, 15.5), holes, o2, uu, (0, 0, 1), nn, t=0.1), None)
        # tetto della navata laterale: dal muro esterno (11 m) al cleristorio (13,5 m)
        p0, p1 = Vector((XF + 0.3, yw + sgn*0.3, 10.8)), Vector((XF + 0.3, yc, 13.5))
        q = [tuple(p0), (XB - 0.3, p0.y, p0.z), (XB - 0.3, p1.y, p1.z), tuple(p1)]
        aggiungi(g, 'Tetto', poli3d(q if sgn > 0 else q[::-1], 0.08, TE), None)
    # tetto della navata centrale (due falde) e muro di fondo
    yc0, yc1, ym = YR - 4, YR - 12, YR - 8
    for ye in (yc0 + 0.3, yc1 - 0.3):
        q = [(XF + 0.3, ye, 15.2), (XB - 0.3, ye, 15.2), (XB - 0.3, ym, 19.6), (XF + 0.3, ym, 19.6)]
        aggiungi('Centrale', 'Tetto', poli3d(q if ye > ym else q[::-1], 0.08, TE), None)
    fondo = [(0, 0), (16, 0), (16, 11), (12, 13.5), (12, 15.5), (8, 19.5), (4, 15.5), (4, 13.5), (0, 11)]
    aggiungi('Centrale', 'Fondo', lastra(fondo, None, Vector((XB + 0.12, YR - 16, 0)), (0, 1, 0), (0, 0, 1), (-1, 0, 0)), None)
    # ---------------- terrazza, cripta e scalinata ----------------
    aggiungi('Terrazza', 'Piano', scatola(XF, YR - 16, 3.84, -XF, 16, 0.16), None)
    cripta = [arco(6.6, 9.4, 0.02, 1.9), arco(1.0, 1.8, 0.02, 1.4), arco(14.2, 15.0, 0.02, 1.4)]
    aggiungi('Terrazza', 'Cripta', lastra(rect(0, 0, 16, 4.0), cripta, in_facciata(-0.14), **FAC, t=0.14), None)
    for poly in cripta:
        aggiungi('Dett', 'Dett_Porte_Vetri', lastra(poly, None, in_facciata(-0.2), **FAC, t=0.02, mat=VE, ruvido=False), None)
    aggiungi('Dett', 'Dett_Portale', (anello(arco(6.4, 9.6, 1.9, 1.9, 12), arco(6.6, 9.4, 1.901, 1.9, 12), t=0.12), frame(tuple(in_facciata(0.0)), **FAC)), None)
    for yw, nn in ((YR, (0, 1, 0)), (YR - 16, (0, -1, 0))):
        o = Vector((0.0, yw - 0.12*nn[1], 0)); aggiungi('Terrazza', 'Cripta', lastra(rect(0, 0, -XF, 4.0), None, o, (-1, 0, 0), (0, 0, 1), nn), None)
    # rampe: piene, con i gradini, dal suolo ai lati fino al pianerottolo in mezzo (davanti al portale)
    n, rise, run, P = 19, 4.0/20, 0.3, 1.7
    # la rampa destra sale da u = 0,7 al pianerottolo (u = 6,4); la sinistra è la sua copia SPECCHIATA attorno
    # all'asse della facciata (u = 8): sale da u = 15,3 verso il pianerottolo (u = 9,6)
    u_basso = 6.4 - n*run
    prof = [(u_basso, 0.0)] + sum(([(u_basso + run*i, rise*(i + 1)), (u_basso + run*(i + 1), rise*(i + 1))] for i in range(n)), []) + [(6.4, 0.0)]
    prof = [p for idx, p in enumerate(prof) if idx == 0 or p != prof[idx - 1]]
    parap = [(u_basso, 0.2), (6.4, 4.0), (6.4, 4.85), (u_basso, 1.05)]
    specchio = lambda pts: [(16.0 - u, z) for u, z in reversed(pts)]           # stesso verso del contorno
    for pr, pa in ((prof, parap), (specchio(prof), specchio(parap))):
        aggiungi('Terrazza', 'Scalinata', (build_panel(pr, t=P, **k()), frame(tuple(in_facciata(0.0)), **FAC)), None)
        aggiungi('Terrazza', 'Scalinata', (build_panel(pa, t=0.16, **k()), frame(tuple(in_facciata(P - 0.16)), **FAC)), None)
    aggiungi('Terrazza', 'Scalinata', scatola(0.0, Y(9.6), 3.8, P, 3.2, 0.2), None)                       # pianerottolo
    aggiungi('Terrazza', 'Scalinata', (build_panel(rect(6.4, 3.4, 9.6, 4.0), t=0.16, **k()), frame(tuple(in_facciata(P)), **FAC)), None)   # sopra l'arco della cripta
    aggiungi('Terrazza', 'Scalinata', (build_panel(rect(6.4, 4.0, 9.6, 4.85), t=0.16, **k()), frame(tuple(in_facciata(P - 0.16)), **FAC)), None)
    # ---------------- abside ----------------
    cx, cy, R = XB, YR - 8, 4.0; segs = 8
    pts = [Vector((cx + R*math.cos(math.radians(90 + 180*i/segs)), cy + R*math.sin(math.radians(90 + 180*i/segs)), 0)) for i in range(segs + 1)]
    for i in range(segs):
        a, b = pts[i], pts[i + 1]; L_ = (b - a).length; u = (b - a).normalized()
        holes = [arco(L_/2 - 0.35, L_/2 + 0.35, 5.0, 8.0, 6)] if 2 <= i <= 5 else None
        aggiungi('Abside', 'Muro', lastra(rect(0, 0, L_, 13.0), holes, a, u, (0, 0, 1), u.cross(Vector((0, 0, 1))), t=0.12), None)
        if holes: aggiungi('Dett', 'Dett_Porte_Vetri', lastra(holes[0], None, a - u.cross(Vector((0, 0, 1)))*0.05, u, (0, 0, 1), u.cross(Vector((0, 0, 1))), t=0.02, mat=VE, ruvido=False), None)
        ap = Vector((cx, cy, 15.4))
        aggiungi('Abside', 'Tetto', poli3d([tuple(a + (a - Vector((cx, cy, 0))).normalized()*0.3 + Vector((0, 0, 12.85))), tuple(b + (b - Vector((cx, cy, 0))).normalized()*0.3 + Vector((0, 0, 12.85))), tuple(ap)][::-1], 0.06, TE), None)
    # ---------------- campanile ----------------
    XBt = XT - S
    def muri(g, parte, z0, h, buchi_fn, t=0.14):
        for o, uu, nn in ((Vector((XT - t, 0, z0)), (0, -1, 0), (1, 0, 0)), (Vector((XBt + t, -S, z0)), (0, 1, 0), (-1, 0, 0)),
                          (Vector((XBt, -t, z0)), (1, 0, 0), (0, 1, 0)), (Vector((XT, -S + t, z0)), (-1, 0, 0), (0, -1, 0))):
            hb = buchi_fn()
            aggiungi(g, parte, lastra(rect(0, 0, S, h), hb, o, uu, (0, 0, 1), nn, t=t), None)
            for poly in hb:
                aggiungi('Dett', 'Dett_Porte_Vetri', lastra(poly, None, o - Vector(nn)*0.25, uu, (0, 0, 1), nn, t=0.02, mat=IN, ruvido=False), None)
    def polifora(nl, zb=0.9, zi=2.3, larg=2.6):
        gap = 0.14; w = (larg - gap*(nl - 1))/nl; u0 = (S - larg)/2
        return [arco(u0 + i*(w + gap), u0 + i*(w + gap) + w, zb, zi, 8) for i in range(nl)]
    muri('Campanile', 'Base', 0.0, 7.5, lambda: [ogiva(0.8, 3.6, 0.02, 4.4)], t=0.3)
    piani = [(7.5, 1), (11.0, 2), (14.5, 3), (18.0, 4), (21.5, 5)]
    for z0, nl in piani:
        muri('Campanile', f'Piano_{nl}', z0, 3.5, (lambda nl=nl: polifora(nl) if nl > 1 else [arco(1.85, 2.55, 1.0, 2.4)]))
    for z, sp in ((7.5, 0.25), (11.0, 0.12), (14.5, 0.12), (18.0, 0.12), (21.5, 0.12), (25.0, 0.35)):
        aggiungi('Dett', 'Dett_Cornici_Campanile', scatola(XBt - sp, -S - sp, z - 0.1, S + 2*sp, S + 2*sp, 0.2 + (0.1 if sp > 0.3 else 0)), None)
    # belvedere: ringhiera di ferro, tamburo ad archi, guglia, croce
    for o, uu, nn, L_ in ((Vector((XT + 0.25, 0.3, 25.2)), (0, -1, 0), (1, 0, 0), S + 0.6), (Vector((XBt - 0.25, -S - 0.3, 25.2)), (0, 1, 0), (-1, 0, 0), S + 0.6),
                          (Vector((XBt - 0.3, 0.25, 25.2)), (1, 0, 0), (0, 1, 0), S + 0.6), (Vector((XT + 0.3, -S - 0.25, 25.2)), (-1, 0, 0), (0, -1, 0), S + 0.6)):
        hb = [rect(0.1 + 0.25*i, 0.12, 0.1 + 0.25*i + 0.17, 0.78) for i in range(int((L_ - 0.2)/0.25))]
        aggiungi('Dett', 'Dett_Ringhiera', lastra(rect(0, 0, L_, 0.9), hb, o, uu, (0, 0, 1), nn, t=0.03, mat=FE, ruvido=False), None)
    S2 = 3.0; d2 = (S - S2)/2
    XT2, YT2 = XT - d2, -d2
    for o, uu, nn in ((Vector((XT2 - 0.12, YT2, 25.2)), (0, -1, 0), (1, 0, 0)), (Vector((XT2 - S2 + 0.12, YT2 - S2, 25.2)), (0, 1, 0), (-1, 0, 0)),
                      (Vector((XT2 - S2, YT2 - 0.12, 25.2)), (1, 0, 0), (0, 1, 0)), (Vector((XT2, YT2 - S2 + 0.12, 25.2)), (-1, 0, 0), (0, -1, 0))):
        aggiungi('Guglia', 'Tamburo', lastra(rect(0, 0, S2, 1.7), [arco(1.15, 1.85, 0.2, 1.05, 6)], o, uu, (0, 0, 1), nn, t=0.12), None)
    aggiungi('Dett', 'Dett_Cornici_Campanile', scatola(XT2 - S2 - 0.15, YT2 - S2 - 0.15, 26.85, S2 + 0.3, S2 + 0.3, 0.15), None)
    ap = (XT2 - S2/2, YT2 - S2/2, 30.0)
    b = [(XT2 + 0.05, YT2 + 0.05, 27.0), (XT2 + 0.05, YT2 - S2 - 0.05, 27.0), (XT2 - S2 - 0.05, YT2 - S2 - 0.05, 27.0), (XT2 - S2 - 0.05, YT2 + 0.05, 27.0)]
    for i in range(4): aggiungi('Guglia', 'Guglia', poli3d([b[(i + 1) % 4], b[i], ap], 0.06), None)
    for r_ in (rect(-0.05, 30.0, 0.05, 30.9), rect(-0.28, 30.5, 0.28, 30.6)):
        aggiungi('Dett', 'Dett_Croce', (rimappa(build_panel(r_, t=0.05, **liscio), {0: FE}), frame((ap[0], ap[1] + 0.0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0))), None)
    # ---------------- oggetti ----------------
    for (g, parte), geos in pezzi.items():
        o = make_object(f'{nome}_{parte}_{g}' if not parte.startswith('Dett') else f'{nome}_{parte}', [x[0] for x in geos], mats, coll)
        o.parent = gruppo('Dettagli' if g == 'Dett' else g)
    return radice, {'W': S + 0.6 + 16.0, 'D': -XB + R, 'H': 30.9}

def run_duomo():
    c = bpy.data.collections.get('Speciali_Campione') or bpy.data.collections.new('Speciali_Campione')
    if c.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(c)
    vecchio = bpy.data.objects.get('Duomo')
    if vecchio:
        for o in [vecchio] + list(vecchio.children_recursive):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0: bpy.data.meshes.remove(d)
    M = materiali_duomo(materiali())
    return duomo('Duomo', c, M, Vector((300.0, 0.0, 0.0)))

# =====================================================================
# EDIFICI SPECIALI — 3. LA ROCCA DI CASTELFIUME (ispirata a Castel del Monte, Andria)
#   tutto è ottagono: pianta ottagonale, otto torri ottagonali sugli spigoli,
#   cortile ottagonale. Misure reali ridotte a circa 0,6 per restare nella
#   scala della città (il vero è largo 56 m e alto 24 m):
#   - corpo: lato 10 m (circonferenza circoscritta 13,1 m), due piani da 6 m,
#     muri esterni alti 12,3 m; cortile largo 10,8 m tra i lati, con i muri
#     che sporgono 0,8 m sopra il tetto (il parapetto del cortile);
#   - torri: lato 1,6 m (larghe 4,2 m), alte 14,4 m, con lo zoccolo, la fascia
#     a metà, il cappello e il torrino in cima;
#   - fronte (+X): portale di breccia rosa con il timpano e la porta di bronzo,
#     scalinata a due rampe specchiate con le ringhiere, bifora sopra;
#     sugli altri lati monofora al terra e bifora al piano nobile, una sola
#     trifora sul retro (a Castel del Monte è quella verso Andria);
#   - cortile: porte al terra e portefinestre ad arco al piano nobile;
#   - piattaforma lastricata rotonda tutto attorno.
#   Circa 33 m di diametro con le torri; la Rocca sta in cima all'altura: il
#   codice la posa sulla quota più alta della tessera. Origine all'angolo in
#   basso a destra dell'ingombro (come gli altri), davanti +X, metri reali.
# =====================================================================
def materiali_rocca(M):
    M['pietra_monte'] = mat_vernice('CB_S_Pietra_Monte', (0.86, 0.78, 0.66, 1), 0.72, SC*0.3)
    M['breccia'] = mat_vernice('CB_S_Breccia', (0.76, 0.52, 0.47, 1), 0.72, SC*0.3)
    M['tetto_monte'] = mat_vernice('CB_S_Tetto_Monte', (0.62, 0.60, 0.56, 1), 0.72, SC*0.3)
    M['lastricato'] = mat_vernice('CB_S_Lastricato', (0.80, 0.76, 0.69, 1), 0.72, SC*0.3)
    M['bronzo'] = M.get('bronzo') or mat_plain('CB_S_Bronzo', (0.36, 0.24, 0.15, 1), 0.6)
    M['ferro'] = M.get('ferro') or mat_plain('CB_S_Ferro', (0.18, 0.18, 0.19, 1), 0.6)
    return M

def rocca(nome, coll, M, origine, rot=0.0, seed=1):
    mats = [M['pietra_monte'], M['bordo'], M['interno'], M['tetto_monte'], M['breccia'], M['bronzo'], M['ferro'], M['lastricato']]
    PI, BO, IN, TE, BR, BZ, FE, LA = range(8)
    c22 = math.cos(math.radians(22.5)); s22 = math.sin(math.radians(22.5))
    Lm = 10.0; Rm = Lm/(2*s22); am = Rm*c22                 # corpo
    ai = 5.4; ri = ai/c22; Li = 2*ri*s22                     # cortile
    Lt = 1.6; rt = Lt/(2*s22)                                # torri
    Hp = 6.0; Hw = 2*Hp; Ht = 14.4; Hc = Hw + 0.8; Z0 = 1.2 # piani, muri, torri, cortile, zoccolo
    Rtot = Rm + rt
    C = Vector((-Rtot - 0.5, -Rtot - 0.5, 0.0))              # centro: l'ingombro parte dall'origine
    radice = bpy.data.objects.new(nome, None); coll.objects.link(radice)
    radice.location = origine; radice.rotation_euler = (0, 0, rot); radice.empty_display_size = 3.0
    sd = [seed*2000]
    def k():
        sd[0] += 1; return kw(sd[0])
    liscio = dict(rough=0.0, warp=0.0, nick=0.0, step=50.0)
    gruppi = {}
    def add(g, geo, mat=PI):
        if mat != PI: geo = (rimappa(geo[0], {0: mat}), geo[1])
        gruppi.setdefault(g, []).append(geo)
    def ott(cx, cy, R, off=0.0):
        return [(cx + R*math.cos(math.radians(off + 22.5 + 45*j)), cy + R*math.sin(math.radians(off + 22.5 + 45*j))) for j in range(8)]
    def anello(Re, Ri, z, t, cx=None, cy=None, off=0.0, mat=PI, g='Fasce'):
        cx = C.x if cx is None else cx; cy = C.y if cy is None else cy
        geo = build_panel(ott(cx, cy, Re, off), holes=[ott(cx, cy, Ri, off)[::-1]], t=t, **k())
        add(g, (rimappa(geo, {1: mat}) if t > 0.2 else geo, Matrix.Translation((0, 0, z))), mat)   # fasce alte: fianchi in pietra
    def muro(o, u, n, L, h, holes, t=0.25, g='Muri', z0=0.0, scuro=True):
        v = Vector((0, 0, 1)); oo = o - n*t + v*z0
        add(g, (build_panel(rect(0, 0, L, h), holes=holes, t=t, **k()) if holes else build_panel(rect(0, 0, L, h), t=t, **k()), frame(tuple(oo), tuple(u), tuple(v), tuple(n))))
        if scuro:
            for hb in holes:                                    # fondo scuro dietro le aperture
                add('Dettagli', (build_panel(hb, t=0.02, **liscio), frame(tuple(oo - n*0.6), tuple(u), tuple(v), tuple(n))), IN)
    def bifora(uc, z0, zi, w=0.55, gap=0.14):
        return [arco(uc - gap/2 - w, uc - gap/2, z0, zi, 8), arco(uc + gap/2, uc + gap/2 + w, z0, zi, 8)]
    def trifora(uc, z0, zi, w=0.45, gap=0.12):
        return [arco(uc - 1.5*w - gap + j*(w + gap), uc - 0.5*w - gap + j*(w + gap), z0, zi, 8) for j in range(3)]
    # ---------------- muri esterni del corpo ----------------
    for kk in range(8):
        phi = math.radians(45*kk); n = Vector((math.cos(phi), math.sin(phi), 0)); u = Vector((math.sin(phi), -math.cos(phi), 0))
        o = C + Rm*Vector((math.cos(phi + math.radians(22.5)), math.sin(phi + math.radians(22.5)), 0))
        uc = Lm/2
        if kk == 0:   holes = [rect(uc - 0.75, Z0, uc + 0.75, Z0 + 2.6)] + bifora(uc, Hp + 1.3, Hp + 2.7)
        elif kk == 4: holes = [arco(uc - 0.3, uc + 0.3, 3.2, 4.1, 6)] + trifora(uc, Hp + 1.3, Hp + 2.7)
        else:         holes = [arco(uc - 0.3, uc + 0.3, 3.2, 4.1, 6)] + bifora(uc, Hp + 1.3, Hp + 2.7)
        muro(o, u, n, Lm, Hw, holes, g=f'Muro_{kk}')       # un oggetto per lato: il LOD1 fa un guscio per pezzo
        # cornici delle bifore/trifore e delle monofore
        oo = o; fr = frame(tuple(oo), tuple(u), (0, 0, 1), tuple(n))
        w_ = 1.55 if kk == 4 else 1.25
        add('Dettagli', (build_panel(arco(uc - w_/2 - 0.12, uc + w_/2 + 0.12, Hp + 1.15, Hp + 2.7, 10),
                                     holes=[arco(uc - w_/2, uc + w_/2, Hp + 1.15 + 0.001, Hp + 2.7, 10)], t=0.08, **k()), fr))
        add('Dettagli', (build_panel(rect(uc - w_/2 - 0.15, Hp + 1.05, uc + w_/2 + 0.15, Hp + 1.3), t=0.12, **k()), fr))
        # tamponature di vetro scuro nelle bifore: già il fondo scuro
        if kk == 0:   # portale di breccia rosa con il timpano, porta di bronzo, bifora del fronte
            add('Dettagli', (build_panel(rect(uc - 1.25, Z0, uc + 1.25, Z0 + 3.1), holes=[rect(uc - 0.75, Z0 + 0.001, uc + 0.75, Z0 + 2.6)], t=0.1, **k()), fr), BR)
            add('Dettagli', (build_panel([(uc - 1.5, Z0 + 3.1), (uc + 1.5, Z0 + 3.1), (uc, Z0 + 4.0)], t=0.14, **k()), fr), BR)
            for uu in (uc - 1.45, uc + 1.15):
                add('Dettagli', (build_panel(rect(uu, Z0, uu + 0.3, Z0 + 3.1), t=0.2, **liscio), fr), BR)       # paraste
            add('Dettagli', (build_panel(rect(uc - 0.75, Z0, uc + 0.75, Z0 + 2.6), t=0.03, **liscio), frame(tuple(oo - n*0.2), tuple(u), (0, 0, 1), tuple(n))), BZ)
    # zoccolo a scarpa e fascia del piano nobile, cornice in cima (anelli attorno al corpo)
    anello(Rm + 0.3, Rm - 0.4, 0.0, Z0)
    anello(Rm + 0.12, Rm - 0.3, Hp - 0.12, 0.24)
    anello(Rm + 0.15, Rm - 0.3, Hw - 0.2, 0.3)
    # ---------------- cortile ----------------
    for kk in range(8):
        phi = math.radians(45*kk); n = -Vector((math.cos(phi), math.sin(phi), 0)); u = Vector((n.y, -n.x, 0))
        o = C + ri*Vector((math.cos(phi - math.radians(22.5)), math.sin(phi - math.radians(22.5)), 0))
        uc = Li/2
        holes = [rect(uc - 0.55, 0.02, uc + 0.55, 2.6), arco(uc - 0.5, uc + 0.5, Hp + 0.02, Hp + 1.9, 8)]
        muro(o, u, n, Li, Hc, holes, t=0.25, g=f'Cortile_{kk}')
    anello(ri + 0.45, ri, Hc - 0.1, 0.25, g='Fasce')                    # cimasa del muro del cortile
    # ---------------- tetto a terrazza e solai (visti dalle finestre) ----------------
    est, inn = ott(C.x, C.y, Rm - 0.05), ott(C.x, C.y, ri + 0.1)
    for j in range(8):                                                     # otto spicchi, così il cortile resta aperto anche nel LOD1
        q = [inn[j], inn[(j + 1) % 8], est[(j + 1) % 8], est[j]]
        add(f'Tetto_{j}', (build_panel(q, t=0.2, **k()), Matrix.Translation((0, 0, Hw - 0.2))), TE)
    anello(Rm + 0.05, Rm - 0.3, Hw, 0.55, g='Fasce')                      # parapetto basso
    # ---------------- otto torri ----------------
    for kk in range(8):
        th = 22.5 + 45*kk; cx = C.x + Rm*math.cos(math.radians(th)); cy = C.y + Rm*math.sin(math.radians(th))
        g = f'Torre_{kk}'
        add(g, (rimappa(build_panel(ott(cx, cy, rt, th), t=Ht, **k()), {1: PI}), Matrix()))   # i fianchi del prisma sono la facciata, non un taglio
        anello(rt + 0.3, rt - 0.2, 0.0, Z0 + 0.3, cx, cy, th, g=g)                  # zoccolo
        anello(rt + 0.12, rt - 0.1, Hp - 0.12, 0.24, cx, cy, th, g=g)              # fascia
        add(g, (rimappa(build_panel(ott(cx, cy, rt + 0.15, th), t=0.3, **k()), {1: TE}), Matrix.Translation((0, 0, Ht))), TE)   # cappello
        anello(0.95, 0.8, Ht + 0.3, 0.7, cx, cy, th, mat=PI, g=g)                   # torrino in cima
        # feritoie sui lati verso l'esterno (rettangoli scuri leggermente in fuori)
        for j in (-1, 0, 1):
            a = math.radians(th + 45*j); nn = Vector((math.cos(a), math.sin(a), 0)); uu = Vector((math.sin(a), -math.cos(a), 0))
            p = Vector((cx, cy, 0)) + nn*(rt*c22 + 0.01) - uu*0.06
            for z in (3.0, 9.0):
                add('Dettagli', (build_panel(rect(0, z, 0.12, z + 0.9), t=0.02, **liscio), frame(tuple(p), tuple(uu), (0, 0, 1), tuple(nn))), IN)
    # ---------------- scalinata del portale: pianerottolo e due rampe specchiate ----------------
    Pf = Vector((C.x + am + 0.3, C.y, 0)); u = Vector((0, -1, 0)); n = Vector((1, 0, 0)); P = 1.5
    fr = frame(tuple(Pf), tuple(u), (0, 0, 1), tuple(n))
    add('Scalinata', (build_panel(rect(-1.3, 0, 1.3, Z0), t=P, **k()), fr))
    nst, rise, run = 6, Z0/6, 0.32; Ls = nst*run
    rampa = [(1.3, 0.0), (1.3 + Ls, 0.0)]
    for i in range(nst):
        x = 1.3 + Ls - run*i; rampa += [(x, rise*(i + 1)), (x - run, rise*(i + 1))]
    rampa = [p for i, p in enumerate(rampa) if i == 0 or p != rampa[i - 1]]
    if rampa[-1] == (1.3, Z0): pass
    ring = [(1.3 + Ls, 0.15), (1.3 + Ls, 1.05), (1.3, Z0 + 0.95), (1.3, Z0 + 0.05)]
    sp = lambda pts: [(-x, z) for x, z in reversed(pts)]
    for pr, rg in ((rampa, ring), (sp(rampa), sp(ring))):
        add('Scalinata', (build_panel(pr, t=P, **k()), fr))
        add('Scalinata', (build_panel(rg, t=0.03, **liscio), frame(tuple(Pf + n*(P - 0.03)), tuple(u), (0, 0, 1), tuple(n))), FE)
    add('Scalinata', (build_panel(rect(-1.3, Z0, 1.3, Z0 + 0.95), holes=[rect(-1.2, Z0 + 0.1, -0.05, Z0 + 0.85), rect(0.05, Z0 + 0.1, 1.2, Z0 + 0.85)], t=0.03, **liscio),
                      frame(tuple(Pf + n*(P - 0.03)), tuple(u), (0, 0, 1), tuple(n))), FE)
    # ---------------- piattaforma lastricata ----------------
    add('Piattaforma', (build_panel(circle(C.x, C.y, Rtot + 3.0, 48), t=0.15, **k()), Matrix.Translation((0, 0, -0.15))), LA)
    for g, geos in gruppi.items():
        o = make_object(f'{nome}_{g}', geos, mats, coll); o.parent = radice
    return radice, {'W': 2*Rtot + 1.0, 'D': 2*Rtot + 1.0, 'H': Ht + 1.0, 'centro': tuple(round(x, 2) for x in C)}

def run_rocca():
    c = bpy.data.collections.get('Speciali_Campione')
    vecchio = bpy.data.objects.get('Rocca')
    if vecchio:
        for o in [vecchio] + list(vecchio.children_recursive):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0: bpy.data.meshes.remove(d)
    M = materiali_rocca(materiali())
    return rocca('Rocca', c, M, Vector((300.0, -40.0, 0.0)))

def run():
    coll = coll_borgo(); M = materiali(); kit = costruisci_kit(M)
    O = Vector((12.0, 3.0, 0.0))                     # angolo in basso a destra della facciata del corpo
    # corpo: 3 moduli di facciata, 3 di profondità, terra + 2 piani; terra commerciale, balcone al primo
    corpo, H, W, D = palazzo('B_Corpo', coll, kit, M, O, 3, 3, 2, 'ocra',
        fronte={0: ['Terra_Porta', 'Terra_Vetrina', 'Terra_Serranda'], 1: ['Modulo_Finestra', 'Modulo_Portafinestra', 'Modulo_Finestra'],
                2: ['Modulo_Finestra']*3},
        lati={('Destra', 1, 0): 'Modulo_Portafinestra'}, seed=1)
    # casa addossata a sinistra, più bassa (terra + 1) e sfalsata in avanti di 0,6 m
    add, Ha, Wa, Da = palazzo('B_Addossata', coll, kit, M, O + Vector((0.6, -W, 0)), 2, 2, 1, 'terracotta',
        fronte={0: ['Terra_Portone', 'Terra_Parete'], 1: ['Modulo_Finestra']*2}, seed=10)
    # sopraelevazione di kraft arretrata sul tetto del corpo (solo un piano, senza fasce)
    so, Hs, Ws, Ds = palazzo('B_Sopraelevazione', coll, kit, M, O + Vector((-1.0, -0.6, H)), 2, 1, 1, 'kraft', terra=False,
        fronte={0: ['Modulo_Finestra', 'Modulo_Portafinestra']}, fasce=False, persiane_prob=0.4, seed=20)
    out = []
    out.append(falda('B_Tetto_Sopra', coll, M, O + Vector((-1.0 - Ds/2, -0.6 - Ws/2, H + Hs)), Ds, Ws, 10, 0.35, seed=21))
    out.append(falda('B_Tetto_Addossata', coll, M, O + Vector((0.6 - Da/2, -W - Wa/2, Ha)), Da, Wa, 8, 0.3, seed=22))
    out.append(serbatoio('B_Serbatoio', coll, M, O + Vector((-0.9, -W + 0.9, H))))
    # balcone davanti alla portafinestra del primo piano, pensilina sopra la porta del terra
    out.append(balcone('B_Balcone', coll, M, O.x, O.y - 3.0, H_TERRA, seed=33))
    out.append(pensilina('B_Pensilina', coll, M, O.x, O.y - 1.0, 2.55, seed=34))
    # scala lungo il fianco destro (+Y) fino al pianerottolo della portafinestra del primo piano
    n = 13
    out.append(scala('B_Scala', coll, M, O.x - 0.3, O.y, n=n, alzata=H_TERRA/n, pedata=0.3, seed=41))
    x1 = O.x - 0.3 - n*0.3
    pian = [(build_panel(rect(x1 - 1.3, O.y, x1, O.y + 0.9), t=0.12, **kw(42)), Matrix.Translation((0, 0, H_TERRA - 0.12)))]
    ringhiera(pian, (x1 - 1.3, O.y + 0.87, H_TERRA), (1, 0, 0), 1.3, seed=43)
    out.append(make_object('B_Pianerottolo', pian, [M['kraft'], M['bordo'], M['interno']], coll))
    make_object('B_Pianerottolo_Pali', [palo((x1 - xx, O.y + 0.8, 0.0), H_TERRA - 0.12) for xx in (0.1, 1.2)], [M['legno']]*3, coll)
    # panni davanti al primo piano della casa addossata
    out.append(filo_panni('B_Filo', coll, M, O.x + 0.6 + 0.4, O.y - W - Wa + 0.2, O.y - W - 0.2, H_TERRA + 2.6, seed=44))
    tri = sum(len(p.vertices) - 2 for o in coll.objects if o.type == 'MESH' for p in o.data.polygons)
    return {'oggetti': len(coll.objects), 'triangoli': tri, 'pezzi del kit': list(kit)}

if __name__ == '__main__':
    print(run())
