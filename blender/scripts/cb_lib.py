# =====================================================================
# cb_lib.py — Corsa Bis · libreria "cartone" per Blender
# Cosa fa: costruisce pezzi di cartone come fogli con spessore reale a
#   partire da un contorno 2D (con eventuali fori): bordi tagliati un po'
#   storti, angoli schiacciati, leggera imbarcatura del foglio.
# Come: il contorno viene ricampionato, spostato con un rumore morbido,
#   triangolato con i fori ed estruso. Ogni pezzo ha 3 slot materiale:
#   0 faccia esterna, 1 bordo tagliato (ondulato), 2 faccia interna.
#   UV del bordo: u lungo il perimetro (metri), v attraverso lo spessore
#   (0..1): il materiale del bordo disegna l'onda del cartone ondulato.
# Unità: metri reali (GDD: in Blender si modella in metri reali).
# =====================================================================
import bpy, math, random
from mathutils import Vector, Matrix, geometry, noise

T = 0.08       # spessore del cartone (circa 3 mm sul modellino da 30 cm)
PITCH = 0.16   # passo dell'onda del cartone ondulato

# ---------- contorni 2D ----------
def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

def circle(cx, cy, r, n=32, a0=0.0):
    return [(cx + r*math.cos(a0 + 2*math.pi*i/n), cy + r*math.sin(a0 + 2*math.pi*i/n)) for i in range(n)]

def arc(cx, cy, r, a0, a1, n):
    return [(cx + r*math.cos(a0 + (a1-a0)*i/n), cy + r*math.sin(a0 + (a1-a0)*i/n)) for i in range(n+1)]

def tread(r_out, r_in, lugs=26):
    # disco con il battistrada: tasselli e scanalature alternati
    st = 2*math.pi/lugs; pts = []
    for i in range(lugs):
        a = i*st
        for r, f in ((r_out, 0.0), (r_out, 0.55), (r_in, 0.62), (r_in, 0.93)):
            pts.append((r*math.cos(a + f*st), r*math.sin(a + f*st)))
    return pts

def bbox(loop):
    xs = [p[0] for p in loop]; ys = [p[1] for p in loop]
    return min(xs), min(ys), max(xs), max(ys)

def _area(loop):
    s = 0.0
    for i in range(len(loop)):
        x0, y0 = loop[i]; x1, y1 = loop[(i+1) % len(loop)]
        s += x0*y1 - x1*y0
    return s/2

def _orient(loop, ccw):
    return list(loop) if (_area(loop) > 0) == ccw else list(reversed(loop))

# ---------- matrici di posa ----------
def frame(origin, u, v, n=None):
    # il foglio sta nel piano locale XY e cresce lungo Z locale (n = verso l'esterno)
    u = Vector(u); v = Vector(v); n = Vector(n) if n is not None else u.cross(v); o = Vector(origin)
    return Matrix(((u.x, v.x, n.x, o.x), (u.y, v.y, n.y, o.y), (u.z, v.z, n.z, o.z), (0, 0, 0, 1)))

def frame_dir(p0, d):
    d = Vector(d).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = up.cross(d).normalized(); v = d.cross(u)
    return frame(p0, u, v, d)

# ---------- geometria del foglio ----------
def _prep_loop(loop, step, rough, seed, li, rng, nick=0.035, freq=1.0):
    # ricampiona il contorno, lo rende un po' storto e smussa gli angoli (consumati)
    n = len(loop); pts = []
    for i in range(n):
        a = Vector(loop[i]); b = Vector(loop[(i+1) % n])
        k = max(1, int(round((b-a).length/step)))
        for j in range(k):
            pts.append((a.lerp(b, j/k), j == 0))
    m = len(pts); out = []
    for i, (p, isv) in enumerate(pts):
        pp = pts[i-1][0]; pn = pts[(i+1) % m][0]
        d = pn - pp
        nrm = Vector((d.y, -d.x)).normalized() if d.length > 1e-9 else Vector((0.0, 0.0))
        o = noise.noise(Vector((p.x*2.7*freq + seed*0.37, p.y*2.7*freq - seed*0.21, li*3.3 + seed*0.013)))*rough
        a = p - pp; b = pn - p
        corner = isv and a.length > 1e-9 and b.length > 1e-9 and a.angle(b) > math.radians(40)
        if corner and nick > 0:
            c1 = min(rng.uniform(0.25, 1.0)*nick, a.length*0.45)
            c2 = min(rng.uniform(0.25, 1.0)*nick, b.length*0.45)
            out.append(p - a.normalized()*c1 + nrm*o)
            out.append(p + b.normalized()*c2 + nrm*o)
        else:
            out.append(p + nrm*o)
    return out

def build_panel(outer, holes=(), t=T, rough=0.012, warp=0.012, nick=0.035, seed=0, step=0.09, bottom_mat=2, scala=1.0):
    # scala: per oggetti molto più grandi di un mezzo (es. tessere, scala 100) storture, angoli
    # consumati, imbarcatura e passo dei bordi crescono insieme e il rumore diventa più largo
    rough *= scala; warp *= scala; nick *= scala; step *= scala; freq = 1.0/scala
    rng = random.Random(seed)
    loops = [_orient(outer, True)] + [_orient(h, False) for h in holes]
    P = []; lidx = []
    for li, l in enumerate(loops):
        idx = []
        for p in _prep_loop(l, step, rough*(1.0 if li == 0 else 0.6), seed, li, rng, nick*(1.0 if li == 0 else 0.4), freq):
            idx.append(len(P)); P.append(p)
        lidx.append(idx)
    tris = geometry.tessellate_polygon([[(P[i].x, P[i].y, 0.0) for i in idx] for idx in lidx])
    n = len(P)
    # imbarcatura morbida del foglio (bassa frequenza, stesso valore sopra e sotto)
    wz = [noise.noise(Vector((p.x*0.35*freq + seed, p.y*0.35*freq, 7.7)))*warp for p in P]
    V = [(p.x, p.y, wz[i]) for i, p in enumerate(P)] + [(p.x, p.y, wz[i] + t) for i, p in enumerate(P)]
    F = []; M = []; U = []; S = []
    for a, b, c in tris:
        pa, pb, pc = P[a], P[b], P[c]
        if (pb.x-pa.x)*(pc.y-pa.y) - (pb.y-pa.y)*(pc.x-pa.x) < 0:
            b, c = c, b
        F.append((a+n, b+n, c+n)); M.append(0); U.append([(P[k].x, P[k].y) for k in (a, b, c)])
        F.append((c, b, a)); M.append(bottom_mat); U.append([(P[k].x, P[k].y) for k in (c, b, a)])
    for idx in lidx:
        m = len(idx); acc = 0.0
        for j in range(m):
            i0 = idx[j]; i1 = idx[(j+1) % m]
            L = (P[i1]-P[i0]).length
            F.append((i0, i1, i1+n, i0+n)); M.append(1)
            U.append([(acc, 0.0), (acc+L, 0.0), (acc+L, 1.0), (acc, 1.0)])
            S += [(i0, i1), (i0+n, i1+n), (i0, i0+n)]
            acc += L
    return V, F, M, U, S

def tape_L(p, e, a, na, b, nb, w=0.2, la=0.17, lb=0.17, seed=0):
    # striscia di nastro di carta piegata a L su uno spigolo
    rng = random.Random(seed)
    p, e, a, na, b, nb = (Vector(x) for x in (p, e, a, na, b, nb)); e.normalize()
    c = p + e*rng.uniform(-0.04, 0.04); hw = w*0.5; off = 0.006
    la *= rng.uniform(0.8, 1.25); lb *= rng.uniform(0.8, 1.25); sk = rng.uniform(-0.03, 0.03)
    V = [c-e*hw+na*off, c+e*hw+na*off, c+e*(hw+sk)+a*la+na*off, c-e*(hw-sk)+a*la+na*off,
         c-e*hw+nb*off, c+e*hw+nb*off, c+e*(hw-sk)+b*lb+nb*off, c-e*(hw+sk)+b*lb+nb*off]
    return [tuple(v) for v in V], [(0, 1, 2, 3), (4, 5, 6, 7)], [0, 0], [[(0, 0), (1, 0), (1, 1), (0, 1)]]*2, []

def make_object(name, geos, mats, coll, location=(0, 0, 0)):
    # geos: lista di ((V, F, M, U, S), matrice) -> un solo oggetto.
    # Facce del foglio lisce, bordo tagliato piatto, spigoli del taglio netti.
    V = []; F = []; MI = []; UV = []; SH = set()
    for g, mat4 in geos:
        v, f, m, u, s = g
        o = len(V); flip = mat4.to_3x3().determinant() < 0
        V += [tuple(mat4 @ Vector(x)) for x in v]
        for ff, mi, uu in zip(f, m, u):
            ff = tuple(i+o for i in ff)
            if flip:
                ff = ff[::-1]; uu = uu[::-1]
            F.append(ff); MI.append(mi); UV.append(uu)
        for a, b in s:
            SH.add((min(a, b)+o, max(a, b)+o))
    me = bpy.data.meshes.new(name)
    me.from_pydata(V, [], F)
    uvl = me.uv_layers.new(name="UVMap")
    for poly, mi, uu in zip(me.polygons, MI, UV):
        poly.material_index = mi
        poly.use_smooth = (mi != 1) and bool(SH)
        for k, li in enumerate(poly.loop_indices):
            uvl.data[li].uv = uu[k]
    if SH:
        att = me.attributes.get('sharp_edge') or me.attributes.new('sharp_edge', 'BOOLEAN', 'EDGE')
        for e in me.edges:
            a, b = e.vertices
            att.data[e.index].value = (min(a, b), max(a, b)) in SH
    for m in mats:
        me.materials.append(m)
    me.update()
    ob = bpy.data.objects.new(name, me); ob.location = location
    coll.objects.link(ob)
    return ob

# ---------- materiali ----------
def _N(nt, typ, loc):
    n = nt.nodes.new(typ); n.location = loc; return n

def _mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = _N(nt, 'ShaderNodeOutputMaterial', (1400, 0))
    b = _N(nt, 'ShaderNodeBsdfPrincipled', (1100, 0))
    nt.links.new(b.outputs[0], out.inputs['Surface'])
    return m, nt, b

def _uv(nt, scala=1.0, solo_x=False):
    # coordinate UV divise per la scala: macchie e onde crescono con l'oggetto
    # (solo_x per il bordo: V resta 0..1 attraverso lo spessore)
    uv = _N(nt, 'ShaderNodeTexCoord', (-1600, 0)).outputs['UV']
    if scala == 1.0: return uv
    mp = _N(nt, 'ShaderNodeMapping', (-1450, 0)); nt.links.new(uv, mp.inputs['Vector'])
    mp.inputs['Scale'].default_value = (1.0/scala, 1.0 if solo_x else 1.0/scala, 1.0)
    return mp.outputs['Vector']

def _mix(nt, fac, a, b, loc, blend='MIX'):
    m = _N(nt, 'ShaderNodeMix', loc); m.data_type = 'RGBA'; m.blend_type = blend
    for sock, val in ((m.inputs[0], fac), (m.inputs[6], a), (m.inputs[7], b)):
        if hasattr(val, 'links'): nt.links.new(val, sock)
        else: sock.default_value = val
    return m.outputs[2]

def _maprange(nt, val, f0, f1, t0, t1, loc):
    r = _N(nt, 'ShaderNodeMapRange', loc); r.interpolation_type = 'SMOOTHSTEP'
    nt.links.new(val, r.inputs['Value'])
    r.inputs['From Min'].default_value = f0; r.inputs['From Max'].default_value = f1
    r.inputs['To Min'].default_value = t0; r.inputs['To Max'].default_value = t1
    return r.outputs['Result']

def _math(nt, op, a, b=None, loc=(0, 0), c=None):
    n = _N(nt, 'ShaderNodeMath', loc); n.operation = op
    for i, v in enumerate((a, b, c)):
        if v is None: continue
        if hasattr(v, 'links'): nt.links.new(v, n.inputs[i])
        else: n.inputs[i].default_value = v
    return n.outputs[0]

def _noise(nt, vec, scale, detail, loc):
    n = _N(nt, 'ShaderNodeTexNoise', loc)
    n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
    nt.links.new(vec, n.inputs['Vector']); return n.outputs['Fac']

def _kraft(nt, uv, dark=1.0, stains=True, x=-1000, scala=1.0):
    # colore del kraft: chiazze morbide, macchie di usura, sporco negli angoli
    n1 = _noise(nt, uv, 2.2, 8.0, (x, 300))
    r1 = _N(nt, 'ShaderNodeValToRGB', (x+200, 300)); e = r1.color_ramp.elements
    e[0].position = 0.35; e[1].position = 0.70
    e[0].color = (0.30*dark, 0.16*dark, 0.065*dark, 1); e[1].color = (0.47*dark, 0.28*dark, 0.12*dark, 1)
    nt.links.new(n1, r1.inputs['Fac']); col = r1.outputs['Color']
    if stains:
        n2 = _noise(nt, uv, 0.8, 5.0, (x, 0))
        f2 = _maprange(nt, n2, 0.56, 0.72, 0.0, 0.55, (x+200, 0))
        col = _mix(nt, f2, col, (0.17*dark, 0.09*dark, 0.035*dark, 1), (x+450, 200))
    ao = _N(nt, 'ShaderNodeAmbientOcclusion', (x+450, -200)); ao.inputs['Distance'].default_value = 0.35*scala
    inv = _math(nt, 'SUBTRACT', 1.0, ao.outputs['AO'], (x+650, -200))
    f3 = _math(nt, 'MULTIPLY', inv, 0.75, (x+800, -200))
    return _mix(nt, f3, col, (0.05, 0.03, 0.012, 1), (x+950, 100))

def _face_bump(nt, uv, strength, x=500):
    # righe dell'ondulato che si vedono sotto la copertina + fibre
    w = _N(nt, 'ShaderNodeTexWave', (x-300, -500)); w.wave_type = 'BANDS'; w.bands_direction = 'X'
    w.inputs['Scale'].default_value = 2*math.pi/(20*PITCH)
    w.inputs['Distortion'].default_value = 0.0; w.inputs['Detail'].default_value = 0.0
    nt.links.new(uv, w.inputs['Vector'])
    b1 = _N(nt, 'ShaderNodeBump', (x, -500)); b1.inputs['Strength'].default_value = strength
    b1.inputs['Distance'].default_value = 0.01; nt.links.new(w.outputs['Fac'], b1.inputs['Height'])
    n = _noise(nt, uv, 60.0, 6.0, (x-300, -750))
    b2 = _N(nt, 'ShaderNodeBump', (x+200, -600)); b2.inputs['Strength'].default_value = 0.08
    b2.inputs['Distance'].default_value = 0.005
    nt.links.new(n, b2.inputs['Height']); nt.links.new(b1.outputs['Normal'], b2.inputs['Normal'])
    return b2.outputs['Normal']

def mat_kraft(name='CB_Cartone_Kraft', dark=1.0, scala=1.0):
    m, nt, b = _mat(name); uv = _uv(nt, scala)
    nt.links.new(_kraft(nt, uv, dark, scala=scala), b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.88
    nt.links.new(_face_bump(nt, uv, 0.12), b.inputs['Normal'])
    return m

def mat_bordo(name='CB_Cartone_Bordo', scala=1.0, chiaro=1.0):
    # taglio del cartone ondulato: due copertine + onda, cavità scure
    m, nt, b = _mat(name); uv = _uv(nt, scala, solo_x=True)
    sep = _N(nt, 'ShaderNodeSeparateXYZ', (-1200, -400)); nt.links.new(uv, sep.inputs[0])
    u = sep.outputs['X']; v = sep.outputs['Y']
    s = _math(nt, 'SINE', _math(nt, 'MULTIPLY', u, 2*math.pi/PITCH, (-1000, -400)), None, (-850, -400))
    f = _math(nt, 'MULTIPLY_ADD', s, 0.34, (-700, -400), 0.5)
    d = _math(nt, 'ABSOLUTE', _math(nt, 'SUBTRACT', v, f, (-550, -400)), None, (-400, -400))
    fl = _maprange(nt, d, 0.045, 0.085, 1.0, 0.0, (-250, -400))
    lo = _maprange(nt, v, 0.11, 0.15, 1.0, 0.0, (-250, -600))
    hi = _maprange(nt, v, 0.85, 0.89, 0.0, 1.0, (-250, -800))
    paper = _math(nt, 'MAXIMUM', _math(nt, 'MAXIMUM', fl, lo, (-50, -500)), hi, (100, -500))
    k = _kraft(nt, uv, 1.1*chiaro, stains=False, scala=scala)
    col = _mix(nt, paper, (0.022, 0.012, 0.005, 1), k, (300, 0))
    nt.links.new(col, b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.92
    bp = _N(nt, 'ShaderNodeBump', (600, -400)); bp.inputs['Strength'].default_value = 0.6
    bp.inputs['Distance'].default_value = 0.02; nt.links.new(paper, bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m

def mat_vernice(name, color, chips=0.63, scala=1.0):
    # tempera stesa a pennello sul kraft: pennellate e scrostature
    m, nt, b = _mat(name); uv = _uv(nt, scala)
    k = _kraft(nt, uv, scala=scala)
    nch = _noise(nt, uv, 2.4, 12.0, (-300, 500))
    mask = _maprange(nt, nch, chips, chips + 0.03, 1.0, 0.0, (-100, 500))
    mp = _N(nt, 'ShaderNodeMapping', (-600, 800)); nt.links.new(uv, mp.inputs['Vector'])
    mp.inputs['Scale'].default_value = (1.2, 5.0, 1.0)
    st = _maprange(nt, _noise(nt, mp.outputs['Vector'], 3.0, 4.0, (-400, 800)), 0.3, 0.7, 0.93, 1.03, (-200, 800))
    pc = _mix(nt, 1.0, color, st, (100, 700), 'MULTIPLY')
    col = _mix(nt, mask, k, pc, (400, 400))
    nt.links.new(col, b.inputs['Base Color'])
    nt.links.new(_maprange(nt, mask, 0.0, 1.0, 0.88, 0.55, (400, 100)), b.inputs['Roughness'])
    nt.links.new(_face_bump(nt, uv, 0.07), b.inputs['Normal'])
    return m

def mat_plain(name, color, rough=0.5):
    m, nt, b = _mat(name)
    b.inputs['Base Color'].default_value = color; b.inputs['Roughness'].default_value = rough
    return m

def mat_legno(name='CB_Legno'):
    m, nt, b = _mat(name)
    tc = _N(nt, 'ShaderNodeTexCoord', (-1200, 0)).outputs['Object']
    mp = _N(nt, 'ShaderNodeMapping', (-1000, 0)); nt.links.new(tc, mp.inputs['Vector'])
    mp.inputs['Scale'].default_value = (30.0, 30.0, 2.0)
    n = _noise(nt, mp.outputs['Vector'], 1.5, 6.0, (-800, 0))
    r = _N(nt, 'ShaderNodeValToRGB', (-600, 0)); e = r.color_ramp.elements
    e[0].color = (0.38, 0.22, 0.09, 1); e[1].color = (0.64, 0.44, 0.24, 1)
    nt.links.new(n, r.inputs['Fac']); nt.links.new(r.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.7
    return m

def mat_nastro(name='CB_Nastro_Carta'):
    m, nt, b = _mat(name); uv = _uv(nt)
    n = _noise(nt, uv, 8.0, 6.0, (-600, 0))
    col = _mix(nt, _maprange(nt, n, 0.4, 0.7, 0.0, 0.35, (-400, 0)), (0.80, 0.68, 0.42, 1), (0.55, 0.42, 0.22, 1), (-100, 0))
    nt.links.new(col, b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.72
    return m

def mat_luce(name, color, glow, strength):
    # bottone di plastica acceso: resta un bottone (plastica lucida, forellini),
    # ma emette luce. Più forte dove la faccia guarda verso la camera, più
    # debole sui fianchi (Layer Weight), così si legge ancora il disco.
    # Intensità bassa: il colore resta saturo e non brucia in bianco.
    m, nt, b = _mat(name)
    b.inputs['Base Color'].default_value = color
    b.inputs['Roughness'].default_value = 0.22
    b.inputs['Coat Weight'].default_value = 0.6
    b.inputs['Emission Color'].default_value = glow
    lw = _N(nt, 'ShaderNodeLayerWeight', (-600, -300)); lw.inputs['Blend'].default_value = 0.45
    face = _math(nt, 'SUBTRACT', 1.0, lw.outputs['Facing'], (-400, -300))
    k = _maprange(nt, face, 0.0, 1.0, 0.15, 1.0, (-200, -300))
    nt.links.new(_math(nt, 'MULTIPLY', k, strength, (0, -300)), b.inputs['Emission Strength'])
    return m

def make_materials():
    return {
        'kraft': mat_kraft(),
        'interno': mat_kraft('CB_Cartone_Interno', 0.42),
        'bordo': mat_bordo(),
        'vernice_arancio': mat_vernice('CB_Vernice_Arancio', (0.78, 0.20, 0.02, 1)),
        'vernice_crema': mat_vernice('CB_Vernice_Crema', (0.84, 0.74, 0.50, 1), 0.68),
        'vernice_grigio': mat_vernice('CB_Vernice_Grigio', (0.045, 0.045, 0.05, 1), 0.70),
        'vernice_blu': mat_vernice('CB_Vernice_Blu', (0.08, 0.19, 0.30, 1), 0.72),
        'vernice_rosso': mat_vernice('CB_Vernice_Rosso', (0.55, 0.10, 0.05, 1), 0.66),
        'vernice_azzurro': mat_vernice('CB_Vernice_Azzurro', (0.30, 0.45, 0.52, 1), 0.70),
        'legno': mat_legno(),
        'plastic_giallo': mat_plain('CB_Bottone_Giallo', (0.85, 0.55, 0.06, 1), 0.3),
        'plastic_arancio': mat_plain('CB_Bottone_Arancio', (0.90, 0.25, 0.02, 1), 0.3),
        'plastic_rosso': mat_plain('CB_Bottone_Rosso', (0.55, 0.02, 0.02, 1), 0.3),
        'nastro': mat_nastro(),
        # luci accese (fase finale): fari bianco caldo, frecce e lampeggianti arancio, fanali rossi
        'luce_giallo': mat_luce('CB_Luce_Faro', (0.85, 0.62, 0.15, 1), (1.0, 0.70, 0.30, 1), 2.2),
        'luce_arancio': mat_luce('CB_Luce_Arancio', (0.90, 0.28, 0.02, 1), (1.0, 0.22, 0.0, 1), 1.3),
        'luce_rosso': mat_luce('CB_Luce_Rossa', (0.55, 0.02, 0.02, 1), (1.0, 0.0, 0.0, 1), 1.2),
        'spago': mat_plain('CB_Spago', (0.60, 0.47, 0.30, 1), 0.95),
        'inchiostro': mat_plain('CB_Inchiostro', (0.015, 0.012, 0.01, 1), 0.6),
        'tappetino': mat_plain('CB_Tappetino_Taglio', (0.025, 0.06, 0.05, 1), 0.8),
    }

def make_label(text, loc, coll, mat, size=0.55):
    cu = bpy.data.curves.new('Etichetta', 'FONT'); cu.body = text
    cu.align_x = 'CENTER'; cu.size = size; cu.extrude = 0.01
    ob = bpy.data.objects.new('Etichetta_' + text[:12], cu); ob.location = loc
    cu.materials.append(mat); coll.objects.link(ob); return ob
