# =====================================================================
# cb_palina.py — Corsa Bis · la palina della fermata con il nodo dello spago
# Cosa fa: costruisce il pin della fermata come lo vede il GDD da vicino:
#   bacchetta di legno, cartellino esagonale di cartone "FERMATA" e il
#   nodo dello spago della linea attorno all'asta, con due spezzoni che si
#   collegano allo spago disegnato dal codice.
#   - metri reali (in gioco ×5,2), origine alla base dell'asta, a Z = 0;
#   - la strada corre lungo X (verso di marcia +X): lo spago entra da −X ed
#     esce verso +X, il cartellino è perpendicolare (piano Y-Z), leggibile
#     da chi arriva in bus;
#   - nodo a 3,67 m (19,1 unità di gioco, sopra il tetto del bus 16,6);
#   - spezzoni: finiscono a ±RACCORDO dal centro dell'asta, a quota NODO_Z,
#     sull'asse dell'asta (y = 0) e tangenti a X: lì il codice riprende lo
#     spago con lo stesso raggio (RAGGIO_SPAGO).
#   - spago a tre capi attorcigliati (sezione a 12 lati con tre lobi che
#     ruotano), colore neutro chiaro: il colore della linea lo dà il codice;
#   - LOD0 / LOD1 / LOD2, una mesh per LOD con tre materiali.
# Uso: apri il file nel Text Editor e premi Run Script.
# =====================================================================
import bpy, math, os
from mathutils import Vector, Matrix

def _carica(nome):
    t = bpy.data.texts.get(nome)
    if t is not None: return t.as_string()
    raise FileNotFoundError(nome + ': aprilo nel Text Editor')

if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))

ALTEZZA = 5.6            # asta: finisce dentro il cartellino a sandwich
R_ASTA = 0.085
INCLINAZIONE = 3.0       # gradi, verso −Y (lontano dalla strada): fatta a mano
NODO_Z = 3.67            # quota dello spago
RAGGIO_SPAGO = 0.28      # 1,46 unità di gioco
RACCORDO = 1.5           # fine degli spezzoni (7,8 unità): oltre, lo spago lo disegna il codice
GIRI_CAPI = 2.2          # giri dei tre capi per metro di spago
CARTELLO_Z = 5.25        # centro del cartellino: il bordo basso (4,38) libera il nodo (4,26)
LOC = Vector((0.0, -6.0, 0.0))

def asse(z):
    # punto dell'asta inclinata all'altezza z
    return Vector((0.0, -math.tan(math.radians(INCLINAZIONE))*z, z))

# ---------- percorso dello spago ----------
def percorso(n_curva=48):
    # entra da −X, fa un giro e mezzo attorno all'asta (sale di un diametro per non
    # attraversarsi), esce verso +X; estremità a y = 0, z = NODO_Z, tangenti a X
    c = asse(NODO_Z); a = R_ASTA + RAGGIO_SPAGO*1.05; h = RAGGIO_SPAGO*1.1
    pts = [Vector((-RACCORDO, 0, NODO_Z)), Vector((-RACCORDO*0.6, 0, NODO_Z)), Vector((-a*1.9, c.y*0.5, NODO_Z - h*0.7))]
    for i in range(n_curva + 1):
        t = i/n_curva; ang = math.pi + 3*math.pi*t          # da π a 4π: un giro e mezzo (antiorario visto dall'alto)
        pts.append(c + Vector((a*math.cos(ang), a*math.sin(ang), -h + 2*h*t)))
    pts += [Vector((a*1.9, c.y*0.5, NODO_Z + h*0.7)), Vector((RACCORDO*0.6, 0, NODO_Z)), Vector((RACCORDO, 0, NODO_Z))]
    return catmull(pts, 4)

def catmull(P, k):
    out = []
    for i in range(len(P) - 1):
        p0 = P[max(i - 1, 0)]; p1 = P[i]; p2 = P[i + 1]; p3 = P[min(i + 2, len(P) - 1)]
        for j in range(k):
            t = j/k; t2 = t*t; t3 = t2*t
            out.append(0.5*((2*p1) + (-p0 + p2)*t + (2*p0 - 5*p1 + 4*p2 - p3)*t2 + (-p0 + 3*p1 - 3*p2 + p3)*t3))
    out.append(P[-1]); return out

def ricampiona(pts, passo):
    L = [0.0]
    for i in range(1, len(pts)): L.append(L[-1] + (pts[i] - pts[i-1]).length)
    n = max(2, int(L[-1]/passo)); out = []; j = 0
    for k in range(n + 1):
        s = L[-1]*k/n
        while j < len(L) - 2 and L[j + 1] < s: j += 1
        f = (s - L[j])/max(1e-9, L[j + 1] - L[j]); out.append((pts[j].lerp(pts[j + 1], f), s))
    return out

def tubo(pts, lati, passo, capi=True):
    # tubo lungo pts con trasporto parallelo del riferimento; i tre capi sono lobi del raggio
    # che ruotano con la lunghezza. Estremità tangenti a X: le sezioni finali sono nel piano Y-Z.
    P = ricampiona(pts, passo); V = []; F = []; UV = []
    T0 = (P[1][0] - P[0][0]).normalized(); N = Vector((0, 0, 1)); N = (N - T0*N.dot(T0)).normalized()
    for k, (p, s) in enumerate(P):
        T = (P[min(k + 1, len(P) - 1)][0] - P[max(k - 1, 0)][0]).normalized()
        N = (N - T*N.dot(T)).normalized(); B = T.cross(N)
        for i in range(lati):
            a = 2*math.pi*i/lati
            r = RAGGIO_SPAGO*(1 + (0.09*math.cos(3*(a - 2*math.pi*GIRI_CAPI*s)) if capi else 0.0))
            V.append(tuple(p + (N*math.cos(a) + B*math.sin(a))*r))
    for k in range(len(P) - 1):
        for i in range(lati):
            a0 = k*lati + i; a1 = k*lati + (i + 1) % lati
            F.append((a0, a1, a1 + lati, a0 + lati)); UV.append([(i/lati, P[k][1]), ((i + 1)/lati, P[k][1]), ((i + 1)/lati, P[k + 1][1]), (i/lati, P[k + 1][1])])
    # tappi alle estremità: nascosti dallo spago del codice, ma evitano il buco visto da vicino
    n = len(P)
    F.append(tuple(reversed(range(lati)))); UV.append([(0.5, 0.0)]*lati)
    F.append(tuple((n - 1)*lati + i for i in range(lati))); UV.append([(0.5, P[-1][1])]*lati)
    return V, F, UV

# ---------- costruzione ----------
def mesh_da(nome, parti, coll):
    # parti: lista di (V, F, UV, indice materiale)
    V = []; F = []; MI = []; UV = []
    for v, f, uv, mi in parti:
        o = len(V); V += v; F += [tuple(i + o for i in ff) for ff in f]; MI += [mi]*len(f); UV += uv
    me = bpy.data.meshes.new(nome); me.from_pydata(V, [], F)
    uvl = me.uv_layers.new(name='UVMap')
    for p, mi, uu in zip(me.polygons, MI, UV):
        p.material_index = mi; p.use_smooth = (mi == 2)
        for k, li in enumerate(p.loop_indices): uvl.data[li].uv = uu[k]
    me.update(); ob = bpy.data.objects.new(nome, me); coll.objects.link(ob); return ob

def da_panel(g, M, mi_map):
    V, F, Mi, U, S = g
    return [tuple(M @ Vector(x)) for x in V], F, U, mi_map, Mi

def asta(lati):
    V = []; F = []; UV = []
    for z in (0.0, ALTEZZA):
        c = asse(z)
        for i in range(lati):
            a = 2*math.pi*i/lati; V.append(tuple(c + Vector((R_ASTA*math.cos(a), R_ASTA*math.sin(a), 0))))
    for i in range(lati):
        j = (i + 1) % lati; F.append((i, j, j + lati, i + lati)); UV.append([(i/lati, 0), ((i + 1)/lati, 0), ((i + 1)/lati, 1), (i/lati, 1)])
    F.append(tuple(range(lati, 2*lati))); UV.append([(0.5, 0.5)]*lati)
    return V, F, UV

def esagono_yz(r, x, z, dettaglio, seed, y=0.0):
    # cartellino di cartone nel piano Y-Z, punte a destra e a sinistra
    pts = [(r*math.cos(math.radians(60*k)), r*math.sin(math.radians(60*k))) for k in range(6)]
    if dettaglio: g = build_panel(pts, t=0.05, rough=0.004, warp=0.0, nick=0.03, step=0.12, seed=seed, scala=1.0)
    else: g = build_panel(pts, t=0.05, rough=0, warp=0, nick=0, step=50.0)
    return g, frame((x, y, z), (0, 1, 0), (0, 0, 1), (1, 0, 0))

def materiali():
    return {'legno': mat_legno('CB_Palina_Legno'), 'kraft': mat_kraft('CB_Palina_Kraft', 1.0, 0.3), 'bordo': mat_bordo('CB_Palina_Bordo', 0.25),
            'crema': mat_vernice('CB_Palina_Crema', (0.88, 0.84, 0.72, 1), 0.70, 0.3), 'spago': mat_plain('CB_Palina_Spago', (0.86, 0.82, 0.74, 1), 0.95),
            'inchiostro': mat_plain('CB_Palina_Inchiostro', (0.03, 0.03, 0.03, 1), 0.6)}

def palina(L, coll, M, loc):
    det = L == 0
    lati_asta, lati_spago, passo = ((10, 16, 0.04), (6, 6, 0.15), (4, 4, 0.4))[L]
    slots = [M['legno'], M['kraft'], M['spago'], M['bordo'], M['crema']]
    parti = []
    v, f, uv = asta(lati_asta); parti.append((v, f, uv, 0))
    v, f, uv = tubo(percorso(), lati_spago, passo, capi=(L < 2)); parti.append((v, f, uv, 2))
    # cartellino a sandwich: due fogli esagonali incollati ai due lati dell'asta (l'asta
    # finisce in mezzo, nascosta), ognuno con la sua targa crema: si legge sia da chi
    # arriva (faccia −X) sia da chi riparte (faccia +X), senza l'asta davanti alla scritta
    yc = asse(CARTELLO_Z).y
    for sx, seed in ((1, 3), (-1, 5)):
        x0 = R_ASTA + 0.005 if sx > 0 else -R_ASTA - 0.055      # il foglio va da x0 a x0 + 0,05
        g, M4 = esagono_yz(1.0, x0, CARTELLO_Z, det, seed, yc)
        V, F, Mi, U, S = g
        parti.append(([tuple(M4 @ Vector(x_)) for x_ in V], F, U, [(1, 3, 1)[m] for m in Mi]))
        # targa: tengo solo la faccia esterna, appoggiata 2 mm sopra il foglio
        xt = x0 + 0.002 if sx > 0 else x0 - 0.002          # Ant: tengo la faccia alta; Post: quella bassa, a x0 − 2 mm
        g, M4 = esagono_yz(0.78, xt, CARTELLO_Z, False, 4, yc)
        V, F, Mi, U, S = g
        keep = [k for k, m in enumerate(Mi) if m == (0 if sx > 0 else 2)]
        parti.append(([tuple(M4 @ Vector(x_)) for x_ in V], [F[k] for k in keep], [U[k] for k in keep], 4))
    # fusione con indici di materiale per faccia
    V = []; F = []; MI = []; UV = []
    for v, f, uv, mi in parti:
        o = len(V); V += v; F += [tuple(i + o for i in ff) for ff in f]; UV += uv
        MI += (mi if isinstance(mi, list) else [mi]*len(f))
    me = bpy.data.meshes.new(f'Palina_LOD{L}'); me.from_pydata(V, [], F)
    uvl = me.uv_layers.new(name='UVMap')
    for p, mi, uu in zip(me.polygons, MI, UV):
        p.material_index = mi; p.use_smooth = (mi == 2 and L < 2)
        for k, li in enumerate(p.loop_indices): uvl.data[li].uv = uu[k] if k < len(uu) else uu[-1]
    for m in slots: me.materials.append(m)
    me.update(); ob = bpy.data.objects.new(f'Palina_LOD{L}', me); ob.location = loc; coll.objects.link(ob)
    # scritta FERMATA sulle due facce (solo LOD0)
    if det:
        for sx in (1, -1):
            cu = bpy.data.curves.new('Fermata', 'FONT'); cu.body = 'FERMATA'; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
            cu.size = 0.30; cu.extrude = 0.004; cu.materials.append(M['inchiostro'])
            t = bpy.data.objects.new(f'Palina_LOD0_Scritta_{"Ant" if sx > 0 else "Post"}', cu); coll.objects.link(t)
            xx = (R_ASTA + 0.067)*sx
            # figlia della palina: matrice locale, così segue l'oggetto ovunque lo sposti
            t.parent = ob; t.matrix_parent_inverse = Matrix.Identity(4)
            t.matrix_basis = Matrix.Translation(Vector((xx, asse(CARTELLO_Z).y, CARTELLO_Z))) @ frame((0, 0, 0), (0, sx, 0), (0, 0, 1), (sx, 0, 0))
    return ob

def run():
    coll = bpy.data.collections.get('Palina_Cartone')
    if coll:
        for o in list(coll.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0:
                (bpy.data.meshes if isinstance(d, bpy.types.Mesh) else bpy.data.curves).remove(d)
    else:
        coll = bpy.data.collections.new('Palina_Cartone'); bpy.context.scene.collection.children.link(coll)
    M = materiali(); out = {}
    for L in range(3):
        ob = palina(L, coll, M, LOC + Vector((0, -5.0*L, 0)))
        out[L] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    return out

if __name__ == '__main__':
    print(run())
