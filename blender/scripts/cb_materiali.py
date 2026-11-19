# =====================================================================
# cb_materiali.py — Corsa Bis · materiali ripetibili per le tessere
# Cosa fa: nel file MATERIALI_ERBA (scena "Materiali") crea, accanto a
#   MAT_Erba_Flock, due materiali costruiti allo stesso modo:
#   - MAT_Cemento   cemento da plastico: grigio caldo, macchie larghe,
#                   segni di frattazzo, inerti fini, pori scuri e giunti
#                   tra le lastre ogni GIUNTI unità (32/GIUNTI intero, così
#                   la griglia si richiude; GIUNTI = 0 li toglie)
#   - MAT_Selciato  cubetti di porfido (~0,6 unità = 12 cm reali) con le
#                   fughe di sabbia, pietre di tinte diverse, spigoli
#                   smussati nel rilievo
#   - MAT_Asfalto   asfalto da plastico: grigio scuro a grana di carta
#                   vetrata, inerti chiari, toppe più scure e lisce,
#                   crepe sottili solo a tratti (piastrella a x = 120)
#   - MAT_Bordo_Ondulato  il taglio del cartone ondulato sul bordo degli
#                   strati: copertine e onda ogni 16 unità, cavità scure;
#                   piastrella 32 x 12 a x = 160, immagine 2048 x 512
#   Tutte le texture sono Noise/Voronoi in 4D collegate al gruppo
#   CB_Coord_Tileable (Lato 32): l'immagine cotta si ripete senza cuciture.
#   Ogni materiale ha il nodo "BAKE: destinazione" con la sua immagine
#   2048 x 2048 (<Nome>_Colore) e una piastrella di prova 32 x 32
#   (MAT_Piastrella_Cemento a x = 40, MAT_Piastrella_Selciato a x = 80).
# Uso: Run Script; poi il bake come scritto in MAT_Istruzioni,
#   selezionando la piastrella del materiale.
# =====================================================================
import bpy

GIUNTI = 8.0            # lato della lastra in unità (8 = 4 x 4 lastre per piastrella, 1,5 m reali)
LARGHEZZA_GIUNTO = 0.08 # unità (≈ 1,5 cm reali, ~5 pixel nell'immagine 2048)

class Nodi:
    # piccolo aiuto per costruire un albero di nodi con etichette e posizioni
    def __init__(self, m):
        self.nt = m.node_tree; self.nt.nodes.clear()
    def n(self, tipo, x, y, etichetta='', **imp):
        nodo = self.nt.nodes.new(tipo); nodo.location = (x, y); nodo.label = etichetta
        for k, v in imp.items():
            if hasattr(nodo, k) and not k[0].isupper(): setattr(nodo, k, v)
            else: nodo.inputs[k].default_value = v
        return nodo
    def l(self, a, b):
        self.nt.links.new(a, b)
    def math(self, op, x, y, a=None, b=None, c=None, etichetta=''):
        m = self.n('ShaderNodeMath', x, y, etichetta); m.operation = op
        for i, v in enumerate((a, b, c)):
            if v is None: continue
            if isinstance(v, (int, float)): m.inputs[i].default_value = v
            else: self.l(v, m.inputs[i])
        return m.outputs[0]
    def rampa(self, x, y, punti, fattore, etichetta=''):
        r = self.n('ShaderNodeValToRGB', x, y, etichetta); el = r.color_ramp.elements
        while len(el) > 1: el.remove(el[-1])
        el[0].position, el[0].color = punti[0][0], (*punti[0][1], 1)
        for p, c in punti[1:]:
            e = el.new(p); e.color = (*c, 1)
        self.l(fattore, r.inputs['Fac']); return r.outputs['Color']
    def intervallo(self, x, y, val, a, b, c, d, etichetta='', liscio=False):
        r = self.n('ShaderNodeMapRange', x, y, etichetta)
        if liscio: r.interpolation_type = 'SMOOTHERSTEP'
        for k, v in zip(('From Min', 'From Max', 'To Min', 'To Max'), (a, b, c, d)): r.inputs[k].default_value = v
        self.l(val, r.inputs['Value']); return r.outputs['Result']
    def mix(self, x, y, a, b, f, modo='MIX', etichetta='', tipo='RGBA'):
        m = self.n('ShaderNodeMix', x, y, etichetta); m.data_type = tipo; m.blend_type = modo
        ia, ib = (6, 7) if tipo == 'RGBA' else (2, 3)
        for s, v in ((ia, a), (ib, b)):
            if isinstance(v, tuple): m.inputs[s].default_value = (*v, 1) if len(v) == 3 else v
            elif isinstance(v, (int, float)): m.inputs[s].default_value = v
            else: self.l(v, m.inputs[s])
        if isinstance(f, (int, float)): m.inputs[0].default_value = f
        else: self.l(f, m.inputs[0])
        return m.outputs[2 if tipo == 'RGBA' else 0]
    def tex(self, tipo, x, y, g, etichetta='', **imp):
        t = self.n(tipo, x, y, etichetta)
        if tipo.endswith('Voronoi'): t.voronoi_dimensions = '4D'
        else: t.noise_dimensions = '4D'
        for k, v in imp.items():
            if k in ('feature', 'distance'): setattr(t, k, v)
            else: t.inputs[k].default_value = v
        self.l(g.outputs['Vettore'], t.inputs['Vector']); self.l(g.outputs['W'], t.inputs['W'])
        return t
    def fine(self, colore, rugosita, altezza, forza, distanza, immagine):
        b = self.n('ShaderNodeBsdfPrincipled', 900, 0)
        b.inputs['Specular IOR Level'].default_value = 0.2
        self.l(colore, b.inputs['Base Color']); self.l(rugosita, b.inputs['Roughness'])
        bu = self.n('ShaderNodeBump', 650, -450, Strength=forza, Distance=distanza); self.l(altezza, bu.inputs['Height'])
        self.l(bu.outputs['Normal'], b.inputs['Normal'])
        o = self.n('ShaderNodeOutputMaterial', 1200, 0); self.l(b.outputs[0], o.inputs['Surface'])
        t = self.n('ShaderNodeTexImage', 1200, -250, 'BAKE: destinazione'); t.image = immagine
        for x in self.nt.nodes: x.select = False
        t.select = True; self.nt.nodes.active = t

def immagine(nome):
    im = bpy.data.images.get(nome) or bpy.data.images.new(nome, 2048, 2048)
    im.colorspace_settings.name = 'sRGB'; return im

def gruppo(N):
    g = N.n('ShaderNodeGroup', -1600, 0, 'Coordinate ripetibili'); g.node_tree = bpy.data.node_groups['CB_Coord_Tileable']
    g.inputs['Lato'].default_value = 32.0; return g

# ---------- cemento ----------
def mat_cemento():
    m = bpy.data.materials.get('MAT_Cemento') or bpy.data.materials.new('MAT_Cemento'); m.use_nodes = True
    N = Nodi(m); g = gruppo(N)
    macchie = N.tex('ShaderNodeTexNoise', -1200, 450, g, 'Macchie larghe', Scale=0.10, Detail=3.0, Roughness=0.55)
    fratt = N.tex('ShaderNodeTexNoise', -1200, 150, g, 'Frattazzo', Scale=0.45, Detail=6.0, Roughness=0.62, Distortion=0.35)
    inerti = N.tex('ShaderNodeTexVoronoi', -1200, -150, g, 'Inerti fini', Scale=14.0)
    pori = N.tex('ShaderNodeTexVoronoi', -1200, -450, g, 'Pori', Scale=3.0)
    maschera = N.tex('ShaderNodeTexNoise', -1200, -750, g, 'Dove ci sono i pori', Scale=0.8, Detail=2.0)
    tinta = N.rampa(-900, 450, [(0.25, (0.255, 0.246, 0.226)), (0.45, (0.350, 0.340, 0.315)), (0.60, (0.405, 0.395, 0.368)), (0.78, (0.470, 0.460, 0.430))], macchie.outputs['Fac'], 'Tinta del cemento')
    bw = N.n('ShaderNodeRGBToBW', -950, -150); N.l(inerti.outputs['Color'], bw.inputs['Color'])
    ti = N.rampa(-750, -150, [(0.0, (0.250, 0.240, 0.222)), (0.5, (0.380, 0.370, 0.345)), (1.0, (0.500, 0.488, 0.455))], bw.outputs[0], 'Tinta degli inerti')
    base = N.mix(-450, 300, tinta, ti, 0.30, etichetta='Cemento + inerti')
    fr = N.intervallo(-750, 150, fratt.outputs['Fac'], 0.25, 0.75, 0.86, 1.08, 'Segni del frattazzo')
    poro = N.intervallo(-900, -450, pori.outputs['Distance'], 0.07, 0.13, 0.35, 1.0, 'Poro (scuro al centro)', liscio=True)
    msk = N.intervallo(-900, -750, maschera.outputs['Fac'], 0.30, 0.45, 0.0, 1.0, 'Maschera dei pori')
    poro_m = N.mix(-650, -550, 1.0, poro, msk, tipo='FLOAT', etichetta='Pori solo a chiazze')
    scuro = N.math('MULTIPLY', -400, -100, fr, poro_m, etichetta='Luce x pori')
    giunto = None
    if GIUNTI > 0:
        # griglia dalle UV (0-1 = 32 unità): distanza dalla linea più vicina, in unità
        uv = N.n('ShaderNodeTexCoord', -1600, -1050)
        sep = N.n('ShaderNodeSeparateXYZ', -1400, -1050); N.l(uv.outputs['UV'], sep.inputs[0])
        dist = []
        for i, asse in enumerate(('X', 'Y')):
            q = N.math('MULTIPLY', -1200, -1000 - 150*i, sep.outputs[asse], 32.0/GIUNTI)
            f = N.math('FRACT', -1050, -1000 - 150*i, q)
            g = N.math('PINGPONG', -900, -1000 - 150*i, f, 0.5)        # 0 sulla linea, 0,5 a metà lastra
            dist.append(g)
        # ogni lastra ha una tinta appena diversa (gettate in giorni diversi)
        cx = N.math('FLOOR', -1050, -1350, N.math('MULTIPLY', -1200, -1350, sep.outputs['X'], 32.0/GIUNTI))
        cy = N.math('FLOOR', -1050, -1450, N.math('MULTIPLY', -1200, -1450, sep.outputs['Y'], 32.0/GIUNTI))
        cxy = N.n('ShaderNodeCombineXYZ', -900, -1400); N.l(cx, cxy.inputs['X']); N.l(cy, cxy.inputs['Y'])
        wn = N.n('ShaderNodeTexWhiteNoise', -750, -1400, 'Tinta per lastra'); wn.noise_dimensions = '3D'
        N.l(cxy.outputs[0], wn.inputs['Vector'])
        lastra = N.intervallo(-600, -1400, wn.outputs['Value'], 0.0, 1.0, 0.94, 1.05, 'Variazione della lastra')
        d = N.math('MINIMUM', -750, -1050, dist[0], dist[1])
        d = N.math('MULTIPLY', -600, -1050, d, GIUNTI, etichetta='Distanza dal giunto (unità)')
        mezzo = LARGHEZZA_GIUNTO/2
        giunto = N.intervallo(-450, -1050, d, mezzo*0.6, mezzo*1.4, 0.0, 1.0, 'Giunto (0) / lastra (1)', liscio=True)
        # il giunto è più scuro e un po' irregolare (sporco che ci si deposita)
        ombra = N.mix(-300, -850, 0.50, 0.68, fratt.outputs['Fac'], tipo='FLOAT', etichetta='Tinta del giunto')
        fatt = N.mix(-150, -850, ombra, lastra, giunto, tipo='FLOAT')
        scuro = N.math('MULTIPLY', -100, -300, scuro, fatt, etichetta='Luce x giunti')
    comb = N.n('ShaderNodeCombineColor', -200, -100)
    for c in ('Red', 'Green', 'Blue'): N.l(scuro, comb.inputs[c])
    colore = N.mix(100, 200, base, comb.outputs[0], 1.0, 'MULTIPLY', 'Colore finale')
    rug = N.intervallo(400, -200, fratt.outputs['Fac'], 0.3, 0.7, 0.95, 0.84, 'Rugosità')
    alt = N.math('MULTIPLY_ADD', 300, -450, fratt.outputs['Fac'], 0.35, poro_m, etichetta='Altezza')
    if giunto is not None:
        alt = N.math('MULTIPLY_ADD', 450, -600, giunto, 1.2, alt, etichetta='Altezza + scanalatura')
        rug = N.mix(600, -250, 0.98, rug, giunto, tipo='FLOAT', etichetta='Giunto più opaco')
    N.fine(colore, rug, alt, 0.30, 0.06, immagine('Cemento_Colore'))
    return m

# ---------- selciato ----------
def mat_selciato():
    m = bpy.data.materials.get('MAT_Selciato') or bpy.data.materials.new('MAT_Selciato'); m.use_nodes = True
    N = Nodi(m); g = gruppo(N)
    SC, RND = 1.6, 0.55                                  # ~1,6 cubetti per unità (12 cm reali), posa irregolare
    pietre = N.tex('ShaderNodeTexVoronoi', -1200, 450, g, 'Cubetti (tinta)', Scale=SC, Randomness=RND)
    fughe = N.tex('ShaderNodeTexVoronoi', -1200, 100, g, 'Fughe', Scale=SC, Randomness=RND, feature='DISTANCE_TO_EDGE')
    grana = N.tex('ShaderNodeTexNoise', -1200, -200, g, 'Grana della pietra', Scale=3.0, Detail=6.0, Roughness=0.65)
    sporco = N.tex('ShaderNodeTexNoise', -1200, -500, g, 'Sporco a chiazze', Scale=0.14, Detail=3.0)
    bw = N.n('ShaderNodeRGBToBW', -950, 450); N.l(pietre.outputs['Color'], bw.inputs['Color'])
    tinta = N.rampa(-750, 450, [(0.00, (0.120, 0.055, 0.032)), (0.30, (0.200, 0.095, 0.050)), (0.60, (0.300, 0.160, 0.075)),
                                 (0.80, (0.230, 0.170, 0.130)), (1.00, (0.290, 0.230, 0.180))], bw.outputs[0], 'Tinte del porfido')
    gr = N.intervallo(-900, -200, grana.outputs['Fac'], 0.3, 0.7, 0.86, 1.10, 'Grana')
    sp = N.intervallo(-900, -500, sporco.outputs['Fac'], 0.35, 0.65, 0.88, 1.06, 'Sporco')
    luce = N.math('MULTIPLY', -650, -350, gr, sp)
    bordo = N.intervallo(-900, 100, fughe.outputs['Distance'], 0.012, 0.14, 0.72, 1.0, 'Spigoli consumati', liscio=True)
    luce = N.math('MULTIPLY', -450, -150, luce, bordo)
    comb = N.n('ShaderNodeCombineColor', -250, -150)
    for c in ('Red', 'Green', 'Blue'): N.l(luce, comb.inputs[c])
    pietra = N.mix(-100, 350, tinta, comb.outputs[0], 1.0, 'MULTIPLY', 'Pietra')
    pietra_si = N.intervallo(-650, 100, fughe.outputs['Distance'], 0.012, 0.028, 0.0, 1.0, 'Pietra o fuga')
    sabbia = N.mix(-100, 50, (0.085, 0.075, 0.062), (0.130, 0.115, 0.095), grana.outputs['Fac'], etichetta='Sabbia delle fughe')
    colore = N.mix(200, 250, sabbia, pietra, pietra_si, etichetta='Colore finale')
    rug = N.intervallo(400, -200, pietra_si, 0.0, 1.0, 0.97, 0.78, 'Rugosità')
    cupola = N.intervallo(-650, -650, fughe.outputs['Distance'], 0.012, 0.12, 0.0, 1.0, 'Cubetto bombato', liscio=True)
    alt = N.math('MULTIPLY_ADD', 300, -500, grana.outputs['Fac'], 0.12, cupola, etichetta='Altezza')
    N.fine(colore, rug, alt, 0.60, 0.10, immagine('Selciato_Colore'))
    return m

# ---------- asfalto ----------
def mat_asfalto():
    # asfalto da plastico: cartone grigio scuro passato con la carta vetrata, grana fine,
    # inerti chiari, toppe di rattoppo più scure e lisce, crepe sottili solo a tratti
    m = bpy.data.materials.get('MAT_Asfalto') or bpy.data.materials.new('MAT_Asfalto'); m.use_nodes = True
    N = Nodi(m); g = gruppo(N)
    macchie = N.tex('ShaderNodeTexNoise', -1200, 600, g, 'Macchie larghe', Scale=0.09, Detail=3.0, Roughness=0.55)
    grana = N.tex('ShaderNodeTexVoronoi', -1200, 300, g, 'Grana (carta vetrata)', Scale=11.0)
    inerti = N.tex('ShaderNodeTexVoronoi', -1200, 0, g, 'Inerti chiari', Scale=4.0)
    toppe = N.tex('ShaderNodeTexNoise', -1200, -300, g, 'Toppe', Scale=0.16, Detail=2.0, Roughness=0.4)
    crepe = N.tex('ShaderNodeTexVoronoi', -1200, -600, g, 'Crepe', Scale=0.35, Randomness=1.0, feature='DISTANCE_TO_EDGE')
    dove = N.tex('ShaderNodeTexNoise', -1200, -900, g, 'Dove ci sono le crepe', Scale=0.25, Detail=2.0)
    tinta = N.rampa(-900, 600, [(0.30, (0.060, 0.060, 0.064)), (0.50, (0.085, 0.084, 0.088)), (0.72, (0.110, 0.108, 0.110))], macchie.outputs['Fac'], 'Grigio dell asfalto')
    bw = N.n('ShaderNodeRGBToBW', -950, 300); N.l(grana.outputs['Color'], bw.inputs['Color'])
    gr = N.intervallo(-750, 300, bw.outputs[0], 0.0, 1.0, 0.80, 1.18, 'Grana chiara/scura')
    ine = N.intervallo(-900, 0, inerti.outputs['Distance'], 0.06, 0.13, 2.6, 1.0, 'Inerto (chiaro al centro)', liscio=True)
    tp = N.intervallo(-900, -300, toppe.outputs['Fac'], 0.60, 0.64, 0.0, 1.0, 'Toppa (1 dentro)', liscio=True)
    tp_luce = N.mix(-650, -300, 1.0, 0.70, tp, tipo='FLOAT', etichetta='Toppa più scura')
    ine_t = N.mix(-650, 0, ine, 1.0, tp, tipo='FLOAT', etichetta='Niente inerti nelle toppe')
    cr = N.intervallo(-900, -600, crepe.outputs['Distance'], 0.004, 0.012, 0.35, 1.0, 'Crepa', liscio=True)
    cm = N.intervallo(-900, -900, dove.outputs['Fac'], 0.56, 0.62, 0.0, 1.0, 'Maschera delle crepe')
    cr_m = N.mix(-650, -700, 1.0, cr, cm, tipo='FLOAT', etichetta='Crepe solo a tratti')
    luce = N.math('MULTIPLY', -450, 100, gr, ine_t)
    luce = N.math('MULTIPLY', -300, 0, luce, tp_luce)
    luce = N.math('MULTIPLY', -150, -150, luce, cr_m, etichetta='Luce totale')
    comb = N.n('ShaderNodeCombineColor', 0, -150)
    for c in ('Red', 'Green', 'Blue'): N.l(luce, comb.inputs[c])
    colore = N.mix(200, 300, tinta, comb.outputs[0], 1.0, 'MULTIPLY', 'Colore finale')
    rug = N.mix(400, -200, 0.93, 0.80, tp, tipo='FLOAT', etichetta='Rugosità (toppe più lisce)')
    alt = N.math('MULTIPLY_ADD', 200, -500, bw.outputs[0], 0.25, cr_m, etichetta='Altezza')
    alt = N.math('MULTIPLY_ADD', 350, -600, tp, -0.15, alt, etichetta='Toppa appena incassata')
    N.fine(colore, rug, alt, 0.35, 0.05, immagine('Asfalto_Colore'))
    return m

# ---------- bordo ondulato degli strati ----------
ONDA = 16.0      # passo dell'onda in unità sugli strati (come CB_T_Strato_Bordo: PITCH x scala 100)
def mat_bordo_ondulato():
    # taglio del cartone ondulato visto di lato: due copertine (sotto e sopra) e l'onda in
    # mezzo, cavità scure. UV della piastrella: u 0-1 = 32 unità lungo il bordo (2 onde),
    # v 0-1 = tutto lo spessore (come le UV del bordo di strato e cima: v da 0 a 1).
    m = bpy.data.materials.get('MAT_Bordo_Ondulato') or bpy.data.materials.new('MAT_Bordo_Ondulato'); m.use_nodes = True
    N = Nodi(m); g = gruppo(N)
    uv = N.n('ShaderNodeTexCoord', -1600, -500)
    sep = N.n('ShaderNodeSeparateXYZ', -1400, -500); N.l(uv.outputs['UV'], sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    ang = N.math('MULTIPLY', -1200, -400, u, 2*3.141592653589793*32.0/ONDA)
    ondulina = N.math('MULTIPLY_ADD', -1000, -400, N.math('SINE', -1100, -400, ang), 0.34, 0.5, etichetta='Centro dell onda')
    d = N.math('ABSOLUTE', -850, -400, N.math('SUBTRACT', -900, -400, v, ondulina))
    fl = N.intervallo(-700, -400, d, 0.045, 0.085, 1.0, 0.0, 'Onda (carta)')
    lo = N.intervallo(-700, -600, v, 0.11, 0.15, 1.0, 0.0, 'Copertina sotto')
    hi = N.intervallo(-700, -800, v, 0.85, 0.89, 0.0, 1.0, 'Copertina sopra')
    carta = N.math('MAXIMUM', -450, -600, N.math('MAXIMUM', -550, -500, fl, lo), hi, etichetta='Carta (1) / cavità (0)')
    # kraft ripetibile: fibre e macchie con il gruppo 4D (si richiude ogni 32 unità lungo u)
    fibre = N.tex('ShaderNodeTexNoise', -1200, 300, g, 'Fibre', Scale=1.2, Detail=8.0, Roughness=0.6)
    macchie = N.tex('ShaderNodeTexNoise', -1200, 0, g, 'Macchie', Scale=0.15, Detail=2.0)
    kraft = N.rampa(-900, 300, [(0.30, (0.330, 0.200, 0.095)), (0.50, (0.430, 0.280, 0.140)), (0.70, (0.520, 0.355, 0.190))], fibre.outputs['Fac'], 'Kraft')
    mc = N.intervallo(-900, 0, macchie.outputs['Fac'], 0.35, 0.65, 0.88, 1.05, 'Macchie')
    kraft = N.mix(-600, 200, kraft, (1, 1, 1), 1.0, 'MULTIPLY', 'Kraft')
    combm = N.n('ShaderNodeCombineColor', -700, 0)
    for c in ('Red', 'Green', 'Blue'): N.l(mc, combm.inputs[c])
    kraft = N.mix(-450, 200, kraft, combm.outputs[0], 1.0, 'MULTIPLY', 'Kraft con macchie')
    # nella cavità si intravede il retro dell'onda: scuro ma non nero
    colore = N.mix(-200, 100, (0.030, 0.017, 0.008), kraft, carta, etichetta='Colore finale')
    rug = N.mix(0, -300, 0.97, 0.90, carta, tipo='FLOAT', etichetta='Rugosità')
    N.fine(colore, rug, carta, 0.6, 0.02, immagine('Bordo_Ondulato_Colore'))
    return m

def piastrella_bordo():
    # piano 32 x 12 con UV 0-1 (come la striscia del bordo di uno strato aperta in piano)
    import bmesh
    nome = 'MAT_Piastrella_Bordo'
    ob = bpy.data.objects.get(nome)
    if ob is None:
        me = bpy.data.meshes.new(nome); bm = bmesh.new()
        vs = [bm.verts.new(p) for p in ((-16, -6, 0), (16, -6, 0), (16, 6, 0), (-16, 6, 0))]
        f = bm.faces.new(vs); lay = bm.loops.layers.uv.new('UVMap')
        for l, uvv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): l[lay].uv = uvv
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(nome, me); [c.objects.link(ob) for c in bpy.data.objects['MAT_Piastrella'].users_collection]
    ob.location = (160, 0, 0)
    if not ob.data.materials: ob.data.materials.append(mat_bordo_ondulato())
    else: ob.data.materials[0] = mat_bordo_ondulato()
    return ob

# ---------- piastrelle di prova ----------
def piastrella(nome, mat, x):
    base = bpy.data.objects['MAT_Piastrella']
    ob = bpy.data.objects.get(nome)
    if ob is None:
        ob = bpy.data.objects.new(nome, base.data); [c.objects.link(ob) for c in base.users_collection]
    ob.location = (x, 0, 0)
    ob.material_slots[0].link = 'OBJECT'; ob.material_slots[0].material = mat   # la mesh resta condivisa
    return ob

def run():
    c = mat_cemento(); s = mat_selciato(); a = mat_asfalto()
    piastrella('MAT_Piastrella_Cemento', c, 40.0); piastrella('MAT_Piastrella_Selciato', s, 80.0)
    piastrella('MAT_Piastrella_Asfalto', a, 120.0)
    piastrella_bordo()
    return [c.name, s.name, a.name, 'MAT_Bordo_Ondulato']

# ---------- export delle immagini per il gioco ----------
# Scrive in packages/web/public/textures/tessere/ (stessa radice di cb_export.py):
#   <nome>_colore.jpg   bake Diffuso solo colore, sRGB, JPEG qualità 90
#   <nome>_normale.png  bake Normale in spazio tangente, Non-Color, PNG 8 bit
# e restituisce la rugosità media (nel gioco è un valore fisso del materiale).
import os
TEXTURE = {   # nome file: (materiale, piastrella)
    'erba_flock': ('MAT_Erba_Flock', 'MAT_Piastrella'),
    'cemento':    ('MAT_Cemento', 'MAT_Piastrella_Cemento'),
    'selciato':   ('MAT_Selciato', 'MAT_Piastrella_Selciato'),
    'asfalto':    ('MAT_Asfalto', 'MAT_Piastrella_Asfalto'),
    'bordo_ondulato': ('MAT_Bordo_Ondulato', 'MAT_Piastrella_Bordo'),
}
DIMENSIONI = {'bordo_ondulato': (2048, 512)}   # 32 unità x tutto lo spessore; le altre 2048 x 2048

def cartella_texture():
    t = bpy.data.texts.get('cb_materiali.py')
    radice = os.path.dirname(os.path.dirname(os.path.dirname(bpy.path.abspath(t.filepath))))
    return os.path.join(radice, 'packages', 'web', 'public', 'textures', 'tessere')

def _bake(ob, mat, nome_img, tipo, colore, lato=2048, **kw):
    w, h = lato if isinstance(lato, tuple) else (lato, lato)
    im = bpy.data.images.get(nome_img)
    if im is None or tuple(im.size) != (w, h):
        if im: bpy.data.images.remove(im)
        im = bpy.data.images.new(nome_img, w, h)
    im.colorspace_settings.name = colore
    nodo = next(n for n in mat.node_tree.nodes if n.label == 'BAKE: destinazione')
    nodo.image = im
    for n in mat.node_tree.nodes: n.select = False
    nodo.select = True; mat.node_tree.nodes.active = nodo
    for o in bpy.context.view_layer.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.bake(type=tipo, margin=0, use_clear=True, **kw)
    return im

def esporta_texture(nome):
    mn, pn = TEXTURE[nome]; mat = bpy.data.materials[mn]; ob = bpy.data.objects[pn]
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 4
    cart = cartella_texture(); os.makedirs(cart, exist_ok=True)
    # colore
    dim = DIMENSIONI.get(nome, 2048)
    im = _bake(ob, mat, f'{nome}_colore', 'DIFFUSE', 'sRGB', lato=dim, pass_filter={'COLOR'})
    im.filepath_raw = os.path.join(cart, f'{nome}_colore.jpg'); im.file_format = 'JPEG'
    sc.render.image_settings.quality = 90; im.save(quality=90)
    # normale
    im = _bake(ob, mat, f'{nome}_normale', 'NORMAL', 'Non-Color', lato=dim, normal_space='TANGENT')
    im.filepath_raw = os.path.join(cart, f'{nome}_normale.png'); im.file_format = 'PNG'; im.save()
    # rugosità media (immagine piccola, non salvata)
    im = _bake(ob, mat, f'{nome}_rugosita', 'ROUGHNESS', 'Non-Color', lato=256)
    px = im.pixels[:]; rug = sum(px[0::4])/(len(px)//4)
    nodo = next(n for n in mat.node_tree.nodes if n.label == 'BAKE: destinazione')
    # il nodo del bake torna sull'immagine di lavoro del materiale (Erba_Flock_Colore, Cemento_Colore, ...)
    nodo.image = bpy.data.images.get(mn.replace('MAT_', '') + '_Colore') or nodo.image
    return {f: round(os.path.getsize(os.path.join(cart, f))/1e6, 2) for f in (f'{nome}_colore.jpg', f'{nome}_normale.png')}, round(rug, 3)

if __name__ == '__main__':
    print(run())
