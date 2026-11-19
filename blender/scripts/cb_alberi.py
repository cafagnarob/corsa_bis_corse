# =====================================================================
# cb_alberi.py — Corsa Bis · alberi e cespugli di cartone
# Cosa fa: un piccolo set di vegetazione per la città nello stile del
#   plastico, come gli alberelli di cartone fatti a mano: per ogni pianta
#   DUE sagome uguali ritagliate da un cartone spesso, dipinte a tempera
#   e incastrate a croce (taglio fino a metà, uno dall'alto e uno dal
#   basso), con un decoro dipinto in bianco sopra il verde:
#   - Abete            h 10 m, a tre palchi, verde petrolio, strisce verticali
#   - Abete_Festoni    h 8 m, triangolo morbido, verde, festoni bianchi
#   - Albero_Tondo     h 9 m, chioma a nuvola, verde medio, nervature a foglia
#   - Albero_Goccia    h 11 m, chioma a goccia (pioppo), verde acqua, spina di pesce
#   - Cespuglio_Cupola h 1,4 m, cupola, verde lime, puntini
#   - Cespuglio_Nuvola h 1,2 m, tre gobbe, verde scuro, archi
#   - Siepe (run_siepe) modulo da 4 m per i viali, alto 1,1-1,3 m a gobbe,
#                    verde, festoni; due piedini a cupola incastrati di
#                    traverso la tengono in piedi; i moduli si saldano in fila
#   Il tronco è cartone kraft non dipinto, come nelle sagome vere; il bordo
#   mostra l'onda del cartone. Altezze dal GDD (albero di città 8-12 m).
#   Metri reali (gioco ×5,2), origine al piede, a Z = 0. Le piante sono
#   simmetriche: non hanno un davanti, il codice le ruota a caso.
#   LOD0: bordi tagliati a mano; LOD1: bordi dritti, poche facce.
# Uso: Run Script (richiede cb_lib.py nel Text Editor).
# =====================================================================
import bpy, math
from mathutils import Vector, Matrix

def _carica(nome):
    t = bpy.data.texts.get(nome)
    if t is not None: return t.as_string()
    raise FileNotFoundError(nome + ': aprilo nel Text Editor')

if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))

T = 0.12                 # spessore del cartone (alberi da 10 m: cartone "giocattolo")
SCALA = 3.0              # scala del cartone: onda del bordo e scrostature
BIANCO = (0.90, 0.89, 0.84, 1)
LOC = Vector((0.0, -30.0, 0.0)); PASSO = 9.0

# ---------- sagome (metri, x orizzontale, y in alto) ----------
def specchia(destra):
    # destra: punti dal basso verso l'alto sul lato x > 0 -> contorno chiuso simmetrico
    return destra + [(-x, y) for x, y in reversed(destra) if x > 1e-6]

def ellisse(cx, cy, a, b, n=40, lobi=0, amp=0.0, da=-math.pi/2, a_ang=1.5*math.pi):
    pts = []
    for i in range(n + 1):
        t = da + (a_ang - da)*i/n
        r = 1 + amp*math.cos(lobi*(t - math.pi/2))
        pts.append((cx + a*r*math.cos(t), cy + b*r*math.sin(t)))
    return pts

def sagome():
    S = {}
    # abete a tre palchi (lo scalino del palco rientra verso il tronco)
    S['Abete'] = dict(chioma=specchia([(0.0, 1.0), (2.5, 1.0), (1.15, 3.7), (1.95, 3.7), (0.8, 6.5), (1.4, 6.5), (0.0, 10.0)]),
                      tronco=(0.35, 1.0), colore=(0.05, 0.33, 0.40), decoro='strisce')
    # abete morbido: base un po' curva
    destra = [(0.0, 1.2), (1.2, 1.12), (2.3, 0.95)] + [(2.3*(1 - k/10), 0.95 + 7.05*k/10 + 0.08*math.sin(k)) for k in range(1, 10)] + [(0.0, 8.0)]
    S['Abete_Festoni'] = dict(chioma=specchia(destra), tronco=(0.3, 1.2), colore=(0.13, 0.42, 0.22), decoro='festoni')
    # chioma a nuvola: cerchio con tre gobbe, si chiude sul tronco
    c = ellisse(0, 6.0, 2.9, 2.9, 48, lobi=5, amp=0.07, da=-math.pi/2, a_ang=1.5*math.pi)
    S['Albero_Tondo'] = dict(chioma=c, tronco=(0.4, 3.12), colore=(0.18, 0.48, 0.30), decoro='nervature')
    # goccia: ellisse allungata più larga in basso
    g = []
    for i in range(49):
        t = -math.pi/2 + 2*math.pi*i/48
        a = 2.2*(1 + 0.18*(-math.sin(t)))           # più larga sotto
        g.append((a*math.cos(t), 6.8 + 4.2*math.sin(t)))
    S['Albero_Goccia'] = dict(chioma=g, tronco=(0.35, 2.6), colore=(0.10, 0.50, 0.42), decoro='spina')
    # cespugli: senza tronco, appoggiati a terra
    S['Cespuglio_Cupola'] = dict(chioma=[(-1.15, 0.0), (1.15, 0.0)] + [(1.15*math.cos(t), 1.4*math.sin(t)) for t in [math.pi*k/24 for k in range(1, 24)]],
                                 tronco=None, colore=(0.48, 0.66, 0.22), decoro='puntini')
    n = []
    for x0, r, h in ((-0.75, 0.55, 0.8), (0.0, 0.7, 1.2), (0.75, 0.55, 0.85)):
        pass
    gob = [(-1.3, 0.0), (1.3, 0.0)]
    for k in range(1, 40):
        x = 1.3 - 2.6*k/40
        y = max(0.6*math.sqrt(max(0, 1 - ((x - 0.75)/0.55)**2)) + 0.25, 1.2*math.sqrt(max(0, 1 - (x/0.7)**2)) if abs(x) < 0.7 else 0,
                0.6*math.sqrt(max(0, 1 - ((x + 0.75)/0.55)**2)) + 0.25)
        gob.append((x, max(y, 0.05)))
    S['Cespuglio_Nuvola'] = dict(chioma=gob, tronco=None, colore=(0.06, 0.32, 0.20), decoro='archi')
    return S

# ---------- materiali: tempera verde + decoro bianco ----------
def decoro(nt, tipo):
    # maschera 0/1 del decoro bianco dalle UV della faccia (= coordinate del foglio in metri)
    N = lambda t, loc: (lambda n: (setattr(n, 'location', loc), n)[1])(nt.nodes.new(t))
    uv = N('ShaderNodeTexCoord', (-1400, -700)); sep = N('ShaderNodeSeparateXYZ', (-1250, -700))
    nt.links.new(uv.outputs['UV'], sep.inputs[0]); u, v = sep.outputs['X'], sep.outputs['Y']
    def m(op, a, b=None, loc=(0, 0)):
        n = N('ShaderNodeMath', loc); n.operation = op
        for i, x in enumerate((a, b)):
            if x is None: continue
            if isinstance(x, (int, float)): n.inputs[i].default_value = x
            else: nt.links.new(x, n.inputs[i])
        return n.outputs[0]
    def linea(x, passo, larg, loc):
        # 1 dove fract(x / passo) < larg/passo: linea larga "larg" ogni "passo" metri
        f = m('FRACT', m('DIVIDE', x, passo, loc), None, (loc[0] + 120, loc[1]))
        return m('LESS_THAN', f, larg/passo, (loc[0] + 240, loc[1]))
    # tremolio del pennello: rumore che sposta la linea di qualche centimetro
    nz = N('ShaderNodeTexNoise', (-1250, -950)); nt.links.new(uv.outputs['UV'], nz.inputs['Vector'])
    nz.inputs['Scale'].default_value = 0.9
    tre = m('MULTIPLY', m('SUBTRACT', nz.outputs['Fac'], 0.5, (-1100, -950)), 0.12, (-980, -950))
    if tipo == 'strisce':
        return linea(m('ADD', u, tre, (-900, -700)), 0.42, 0.06, (-750, -700))
    if tipo == 'festoni':
        onda = m('MULTIPLY', m('ABSOLUTE', m('SINE', m('MULTIPLY', u, 3.4, (-1100, -800)), None, (-980, -800)), None, (-860, -800)), -0.32, (-740, -800))
        return linea(m('ADD', m('ADD', v, onda, (-620, -700)), tre, (-500, -700)), 0.85, 0.07, (-380, -700))
    if tipo in ('nervature', 'spina'):
        k, passo = (0.9, 0.62) if tipo == 'nervature' else (0.55, 0.45)
        cost = linea(m('ADD', m('ABSOLUTE', u, None, (-1100, -600)), tre, (-980, -600)), 1000.0, 0.05, (-860, -600))   # costa centrale |u| < 0.05
        diag = linea(m('SUBTRACT', v, m('MULTIPLY', m('ABSOLUTE', u, None, (-1100, -500)), k, (-980, -500)), (-860, -500)), passo, 0.05, (-740, -500))
        return m('MAXIMUM', cost, diag, (-400, -550))
    if tipo == 'puntini':
        vo = N('ShaderNodeTexVoronoi', (-1100, -700)); vo.inputs['Scale'].default_value = 4.5; vo.voronoi_dimensions = '2D'
        nt.links.new(uv.outputs['UV'], vo.inputs['Vector'])
        return m('LESS_THAN', vo.outputs['Distance'], 0.24, (-900, -700))
    if tipo == 'archi':
        r = N('ShaderNodeVectorMath', (-1100, -700)); r.operation = 'LENGTH'
        cmb = N('ShaderNodeCombineXYZ', (-1250, -600)); nt.links.new(u, cmb.inputs['X'])
        nt.links.new(m('MULTIPLY', v, 1.25, (-1350, -600)), cmb.inputs['Y']); nt.links.new(cmb.outputs[0], r.inputs[0])
        return linea(m('ADD', r.outputs['Value'], m('MULTIPLY', tre, 0.4, (-950, -800)), (-900, -700)), 0.22, 0.035, (-750, -700))

def mat_pianta(nome, colore, tipo):
    m = mat_vernice('CB_V_' + nome, (*colore, 1), 0.78, SCALA*0.25)
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    sorg = b.inputs['Base Color'].links[0].from_socket
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.location = (b.location.x - 250, b.location.y + 250)
    nt.links.new(decoro(nt, tipo), mix.inputs[0]); nt.links.new(sorg, mix.inputs[6]); mix.inputs[7].default_value = BIANCO
    nt.links.new(mix.outputs[2], b.inputs['Base Color'])
    return m

# ---------- LOD1: contorno ridotto ----------
# punti del contorno nel LOD1 (GDD, "Ottimizzazione: LOD1 della vegetazione"): le curve della chioma
# diventano pochi segmenti dritti; i punti d'angolo (base piatta, scalini) restano
PUNTI_LOD1 = {'Albero_Tondo': 11, 'Albero_Goccia': 11, 'Abete_Festoni': 6, 'Cespuglio_Cupola': 8, 'Cespuglio_Nuvola': 10}

def semplifica(pts, n):
    P = [Vector(p) for p in pts]; m = len(P)
    # angoli: dove il contorno gira di più di 50 gradi
    ang = []
    for i in range(m):
        a = (P[i] - P[i - 1]); b = (P[(i + 1) % m] - P[i])
        ang.append(a.length > 1e-6 and b.length > 1e-6 and a.angle(b) > math.radians(50))
    L = [0.0]
    for i in range(1, m + 1): L.append(L[-1] + (P[i % m] - P[i - 1]).length)
    tot = L[-1]; scelti = {i for i in range(m) if ang[i]}
    resto = max(0, n - len(scelti))
    for k in range(resto):
        s_ = tot*(k + 0.5)/resto
        j = min(range(m), key=lambda i: abs(L[i] - s_)); scelti.add(j)
    return [tuple(P[i]) for i in sorted(scelti)]

# ---------- costruzione ----------
def pianta(nome, d, coll, M, loc, lod):
    det = dict(rough=0.025, nick=0.05, step=0.35, warp=0.0, scala=1.0) if lod == 0 else dict(rough=0, nick=0, step=1000.0, warp=0.0, scala=1.0)
    geos = []
    for i, (u, n) in enumerate((((-1, 0, 0), (0, 1, 0)), ((0, 1, 0), (1, 0, 0)))):
        o = tuple(-T/2*c for c in n)
        fr = frame(o, u, (0, 0, 1), n)
        chioma = semplifica(d['chioma'], PUNTI_LOD1[nome]) if lod == 1 and nome in PUNTI_LOD1 else d['chioma']
        V, F, Mi, U, S = build_panel(chioma, t=T, seed=i + len(nome), bottom_mat=0, **det)
        geos.append(((V, F, Mi, U, S), fr))
        if d['tronco']:
            w, h = d['tronco']
            V, F, Mi, U, S = build_panel(rect(-w/2, 0.0, w/2, h), t=T, seed=9 + i, bottom_mat=0, **det)
            geos.append(((V, F, [3 if x == 0 else x for x in Mi], U, S), fr))
    mats = [M[nome], M['bordo'], M['interno'], M['kraft']]
    return make_object(f'{nome}_LOD{lod}', geos, mats, coll, loc)

def run():
    coll = bpy.data.collections.get('Alberi_Cartone')
    if coll:
        for o in list(coll.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0: bpy.data.meshes.remove(d)
    else:
        coll = bpy.data.collections.new('Alberi_Cartone'); bpy.context.scene.collection.children.link(coll)
    S = sagome()
    M = {'bordo': mat_bordo('CB_V_Bordo', SCALA*0.3), 'interno': mat_kraft('CB_V_Interno', 0.42, SCALA*0.3),
         'kraft': mat_kraft('CB_V_Tronco', 1.0, SCALA*0.3)}
    for nome, d in S.items(): M[nome] = mat_pianta(nome, d['colore'], d['decoro'])
    out = {}
    for i, (nome, d) in enumerate(S.items()):
        for lod in (0, 1):
            ob = pianta(nome, d, coll, M, LOC + Vector((i*PASSO, lod*8.0, 0)), lod)
            out[ob.name] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    return out

# ---------- siepe dei viali ----------
SIEPE_L = 4.0            # modulo: 4 m (20,8 unità), si ripete lungo il viale
SIEPE_H = 1.1            # altezza delle gobbe più basse
GOBBA = 0.8              # una gobba ogni 0,8 m (5 per modulo: il modulo si ripete senza salti)
def siepe_profilo(lod):
    # striscia lunga con il bordo di sopra a gobbe; parte e finisce in una valle alla stessa
    # quota, così due moduli in fila si saldano
    if lod == 1:
        # LOD1: tre gobbe a punta (valle, cima, valle...), stesse quote ai capi
        xs = [SIEPE_L/2 - SIEPE_L*k/6 for k in range(7)]
        top = [(x, SIEPE_H + (0.22 if k % 2 else 0.0)) for k, x in enumerate(xs)]
        return [(-SIEPE_L/2, 0.0), (SIEPE_L/2, 0.0)] + top
    n = 80
    top = [(SIEPE_L/2 - SIEPE_L*k/n, SIEPE_H + 0.22*abs(math.sin(math.pi*(SIEPE_L*k/n)/GOBBA))) for k in range(n + 1)]
    return [(-SIEPE_L/2, 0.0), (SIEPE_L/2, 0.0)] + top

def siepe(coll, M, loc, lod):
    det = dict(rough=0.02, nick=0.04, step=0.3, warp=0.0, scala=1.0) if lod == 0 else dict(rough=0, nick=0, step=1000.0, warp=0.0, scala=1.0)
    geos = []
    # foglio lungo lungo X (verso del viale), spessore lungo Y
    g = build_panel(siepe_profilo(lod), t=T, seed=21, bottom_mat=0, **det)
    geos.append((g, frame((0, -T/2, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0))))
    # due piedini a cupola incastrati di traverso: tengono in piedi la siepe
    piede = [(-0.45, 0.0), (0.45, 0.0)] + [(0.45*math.cos(a), 0.95*math.sin(a)) for a in [math.pi*k/16 for k in range(1, 16)]]
    for i, x in enumerate((-SIEPE_L/4, SIEPE_L/4) if lod == 0 else ()):   # LOD1: senza piedini
        g = build_panel(piede, t=T, seed=22 + i, bottom_mat=0, **det)
        geos.append((g, frame((x - T/2, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0))))
    return make_object(f'Siepe_LOD{lod}', geos, [M['Siepe'], M['bordo'], M['interno']], coll, loc)

def run_siepe():
    coll = bpy.data.collections['Alberi_Cartone']
    for n in ('Siepe_LOD0', 'Siepe_LOD1', 'Siepe_Prova_2', 'Siepe_Prova_3'):
        o = bpy.data.objects.get(n)
        if o: d = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(d)
    M = {'bordo': bpy.data.materials['CB_V_Bordo'], 'interno': bpy.data.materials['CB_V_Interno'],
         'Siepe': mat_pianta('Siepe', (0.10, 0.38, 0.22), 'festoni')}
    base = LOC + Vector((0, -10.0, 0)); out = {}
    for lod in (0, 1):
        ob = siepe(coll, M, base + Vector((0, -3.0*lod, 0)), lod)
        out[ob.name] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    # prova: tre moduli in fila (copie del LOD0) per vedere la giunta
    l0 = bpy.data.objects['Siepe_LOD0']
    for k in (2, 3):
        c = l0.copy(); c.name = f'Siepe_Prova_{k}'; c.location = l0.location + Vector((SIEPE_L*(k - 1), 0, 0)); coll.objects.link(c)
    return out

if __name__ == '__main__':
    print(run(), run_siepe())
