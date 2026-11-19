# =====================================================================
# cb_borgo.py — Corsa Bis · centro storico: il borgo arrampicato di cartone
# Cosa fa: costruisce, a pezzi, la palazzina campione del borgo (GDD,
#   "Edifici: famiglie per zona e stile"); i pezzi diventeranno il kit.
#   Regola del colore: facciate (intonaco) dipinte a tempera, con la
#   vernice scrostata sugli spigoli; kraft nudo per tutto ciò che è
#   aggiunto o strutturale (tetti ondulati, sopraelevazioni, scale,
#   ballatoi, ringhiere, pali, persiane, serbatoi).
#   Metri reali (gioco ×5,2), modulo 2 m in larghezza, piano 3 m;
#   davanti verso +X (la strada), origine al centro della base, Z = 0.
#   Pezzo 1: VOLUME — scatola di cartone con le pareti spesse, finestre e
#            porte ritagliate (buchi: dentro si vede il cartone scuro).
#   Pezzo 2: TETTI E SOPRAELEVAZIONI — falda di cartone ondulato senza
#            copertina (onde vere nella geometria, kraft), sopraelevazione
#            di kraft arretrata sul tetto, serbatoio d'acqua di ondulato
#            arrotolato.
#   Pezzo 3: FACCIATA — persiane di kraft a linguetta socchiuse, balcone
#            con ringhiera di ondulato su pali di legno, pensilina di
#            ondulato sopra la porta.
#   Dal 18 novembre i volumi si compongono con i pezzi del KIT (vedi sotto:
#   piano terra 4 m, origine all'angolo in basso a destra, nomi espliciti).
#   Pezzo 4: VITA — scala esterna di una striscia ondulata piegata a
#            gradini con il pianerottolo su pali, filo di spago con i
#            panni di carta stesi.
# Uso: Run Script (richiede cb_lib.py nel Text Editor).
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

def ondulato(L, W, pendenza=0.0, seed=0):
    # foglio ondulato senza copertina: lungo X (L, in discesa), onde lungo Y (W).
    # Restituisce la geometria nel formato di build_panel: facce 0 = sopra (kraft), 1 = bordi, 2 = sotto
    rng = random.Random(seed); n = max(4, int(W/ONDA*6)); m = max(2, int(L/1.0) + 1)
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

def ringhiera(geos, p0, direzione, lung, alt=0.9, seed=0):
    # striscia di ondulato in piedi (costole verticali) lungo "direzione" (asse X o Y del mondo)
    g = ondulato(alt, lung, 0.0, seed)
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
                                  (rimappa(txt, {0: 3}), frame((0.04, -1.0, 3.23), (0, -1, 0), (0, 0, 1), (1, 0, 0)))], [mf, M['bordo'], M['interno'], mi])
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
            fasce=True, persiane_prob=0.7, seed=0, rot=0.0):
    # piani = piani sopra il terra (0, 1, 2...); fronte = {piano: [tipo per colonna]} (piano 0 = terra)
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
                p = o + sx*MODULO*k + Vector((0, 0, z))
                istanza(f'{nome}_{parete}_{li}_{k}', kit[tipo].data, coll, radice, p, r, M[colore])
                if tipo == 'Modulo_Finestra': finestre.append((p, r))
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
