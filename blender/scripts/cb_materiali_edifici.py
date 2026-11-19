# =====================================================================
# cb_materiali_edifici.py — Corsa Bis · texture ripetibili del kit degli edifici
# Cosa fa: nel file MATERIALI_ERBA (scena "Materiali"), con lo stesso metodo
#   delle texture delle tessere (Noise/Voronoi in 4D sul gruppo
#   CB_Coord_Tileable, si ripetono senza cuciture), crea e cuoce i materiali
#   che il codice mette al posto dei segnaposto di kit_edifici.glb:
#   - EDI_T_Intonaco  tempera chiara quasi bianca, da TINGERE nel codice
#                     (colore × texture): pennellate, fibre della carta,
#                     sporco largo, qualche scrostatura
#   - EDI_T_Kraft     kraft nudo: fibre, macchie, chiazze più scure
#                     (anche per EDI_Interno, scurito nel codice)
#   - EDI_T_Legno     bacchette di legno chiaro con le venature lungo v
#   - EDI_T_Tenda     maschera delle strisce (bianco = colore 1, nero =
#                     colore 2) con la trama della tela
#   Periodo LATO = 4 m: le UV del kit sono in metri, quindi nel gioco
#   repeat = 1/4. Immagini 1024 x 1024 (256 pixel per metro).
#   Il taglio del cartone (EDI_Bordo) usa bordo_ondulato delle tessere.
# Uso: Run Script (crea materiali e piastrelle), poi esporta('intonaco') ...
#   oppure esporta_tutto(). Richiede cb_materiali.py nel Text Editor.
# =====================================================================
import bpy, os, math

_m = {'__name__': 'cb_materiali'}
exec(bpy.data.texts['cb_materiali.py'].as_string(), _m)
Nodi, _bake = _m['Nodi'], _m['_bake']

LATO = 4.0                 # metri reali per periodo
LATO_IMG = 1024
STRISCE = 13               # strisce della tenda per periodo (4/13 = 0,31 m, come le tende del kit)

def gruppo(N):
    g = N.n('ShaderNodeGroup', -1600, 0, 'Coordinate ripetibili'); g.node_tree = bpy.data.node_groups['CB_Coord_Tileable']
    g.inputs['Lato'].default_value = LATO; return g

def immagine(nome):
    im = bpy.data.images.get(nome) or bpy.data.images.new(nome, LATO_IMG, LATO_IMG)
    im.colorspace_settings.name = 'sRGB'; return im

def uv_xy(N, x, y):
    uv = N.n('ShaderNodeTexCoord', x, y); sep = N.n('ShaderNodeSeparateXYZ', x + 200, y); N.l(uv.outputs['UV'], sep.inputs[0])
    return sep.outputs['X'], sep.outputs['Y']

def grigio(N, x, y, val):
    c = N.n('ShaderNodeCombineColor', x, y)
    for k in ('Red', 'Green', 'Blue'): N.l(val, c.inputs[k])
    return c.outputs[0]

def materiale(nome):
    m = bpy.data.materials.get(nome) or bpy.data.materials.new(nome); m.use_nodes = True; return m

# ---------- intonaco da tingere ----------
def mat_intonaco():
    m = materiale('EDI_T_Intonaco'); N = Nodi(m); g = gruppo(N)
    pennellate = N.tex('ShaderNodeTexNoise', -1200, 500, g, 'Pennellate', Scale=2.5, Detail=6.0, Roughness=0.55)
    fibre = N.tex('ShaderNodeTexNoise', -1200, 250, g, 'Fibre della carta', Scale=30.0, Detail=4.0, Roughness=0.7)
    sporco = N.tex('ShaderNodeTexNoise', -1200, 0, g, 'Sporco largo', Scale=0.6, Detail=3.0)
    sc_ = N.tex('ShaderNodeTexVoronoi', -1200, -300, g, 'Scrostature', Scale=2.2, Randomness=1.0)
    bordo_sc = N.tex('ShaderNodeTexNoise', -1200, -550, g, 'Bordo frastagliato', Scale=9.0, Detail=5.0)
    # base quasi bianca: il codice la moltiplica per il colore della casa
    p = N.intervallo(-900, 500, pennellate.outputs['Fac'], 0.25, 0.75, 0.80, 1.0, 'Tempera')
    f = N.intervallo(-900, 250, fibre.outputs['Fac'], 0.3, 0.7, 0.92, 1.0, 'Fibre')
    s = N.intervallo(-900, 0, sporco.outputs['Fac'], 0.40, 0.72, 1.0, 0.84, 'Sporco')
    base = N.math('MULTIPLY', -650, 300, N.math('MULTIPLY', -750, 300, p, f), s, etichetta='Tempera chiara')
    # scrostature: macchie piccole e rare dove la vernice è saltata (sotto si vede il kraft, che col colore diventa bruno)
    d = N.math('ADD', -900, -400, N.math('MULTIPLY_ADD', -1000, -500, bordo_sc.outputs['Fac'], 0.3, -0.15), sc_.outputs['Distance'], etichetta='Distanza frastagliata')
    scr = N.intervallo(-700, -400, d, 0.12, 0.15, 1.0, 0.0, 'Scrostatura (1)')
    col_base = grigio(N, -450, 300, base)
    colore = N.mix(-200, 200, col_base, (0.80, 0.66, 0.50), scr, etichetta='Colore (da tingere)')
    rug = N.mix(0, -300, 0.88, 0.95, scr, tipo='FLOAT', etichetta='Rugosità')
    alt = N.math('MULTIPLY_ADD', -300, -600, p, 0.4, N.math('MULTIPLY', -450, -650, scr, -1.0), etichetta='Altezza')
    N.fine(colore, rug, alt, 0.25, 0.01, immagine('EDI_Intonaco_Colore'))
    return m

# ---------- kraft nudo ----------
def mat_kraft():
    m = materiale('EDI_T_Kraft'); N = Nodi(m); g = gruppo(N)
    fibre = N.tex('ShaderNodeTexNoise', -1200, 400, g, 'Fibre', Scale=18.0, Detail=8.0, Roughness=0.65)
    macchie = N.tex('ShaderNodeTexNoise', -1200, 100, g, 'Macchie', Scale=0.9, Detail=3.0)
    chiazze = N.tex('ShaderNodeTexVoronoi', -1200, -200, g, 'Chiazze di umido', Scale=1.3, Randomness=1.0)
    kraft = N.rampa(-900, 400, [(0.30, (0.40, 0.25, 0.11)), (0.50, (0.52, 0.34, 0.16)), (0.72, (0.61, 0.42, 0.22))], fibre.outputs['Fac'], 'Kraft')
    mc = N.intervallo(-900, 100, macchie.outputs['Fac'], 0.35, 0.65, 0.86, 1.04, 'Macchie')
    ch = N.intervallo(-900, -200, chiazze.outputs['Distance'], 0.05, 0.22, 0.80, 1.0, 'Chiazze', liscio=True)
    k = N.mix(-600, 300, kraft, grigio(N, -750, 100, mc), 1.0, 'MULTIPLY', 'Con macchie')
    colore = N.mix(-350, 250, k, grigio(N, -600, -200, ch), 1.0, 'MULTIPLY', 'Colore')
    N.fine(colore, N.intervallo(-300, -350, fibre.outputs['Fac'], 0, 1, 0.86, 0.96, 'Rugosità'), fibre.outputs['Fac'], 0.2, 0.01,
           immagine('EDI_Kraft_Colore'))
    return m

# ---------- legno delle bacchette ----------
def mat_legno():
    m = materiale('EDI_T_Legno'); N = Nodi(m); g = gruppo(N)
    u, v = uv_xy(N, -1600, -600)
    storto = N.tex('ShaderNodeTexNoise', -1200, 300, g, 'Venature storte', Scale=3.0, Detail=4.0)
    # venature: un numero intero di strisce per periodo lungo u (si richiude); il rumore le piega
    ang = N.math('MULTIPLY_ADD', -950, 0, storto.outputs['Fac'], 1.5, N.math('MULTIPLY', -1100, 0, u, 2*math.pi*60.0), etichetta='Fase')
    ven = N.intervallo(-700, 0, N.math('SINE', -850, 0, ang), -1.0, 1.0, 0.0, 1.0, 'Venature')
    legno = N.rampa(-450, 200, [(0.0, (0.55, 0.37, 0.20)), (0.6, (0.70, 0.52, 0.32)), (1.0, (0.76, 0.58, 0.37))], ven, 'Legno chiaro')
    N.fine(legno, N.math('ADD', -300, -350, 0.8, 0.0, etichetta='Rugosità'), ven, 0.15, 0.01, immagine('EDI_Legno_Colore'))
    return m

# ---------- strisce della tenda (maschera) ----------
def mat_tenda():
    m = materiale('EDI_T_Tenda'); N = Nodi(m); g = gruppo(N)
    u, v = uv_xy(N, -1600, -600)
    fase = N.math('FRACT', -1100, 0, N.math('MULTIPLY', -1250, 0, u, float(STRISCE)))
    striscia = N.intervallo(-900, 0, fase, 0.47, 0.53, 1.0, 0.0, 'Striscia (1 = colore 1)')
    trama = N.tex('ShaderNodeTexNoise', -1200, 300, g, 'Trama della tela', Scale=60.0, Detail=2.0)
    t = N.intervallo(-900, 300, trama.outputs['Fac'], 0.3, 0.7, 0.9, 1.0, 'Trama')
    val = N.math('MULTIPLY', -650, 150, N.math('MULTIPLY_ADD', -750, 0, striscia, 0.92, 0.04), t, etichetta='Maschera')
    N.fine(grigio(N, -450, 150, val), N.math('ADD', -300, -350, 0.9, 0.0, etichetta='Rugosità'), trama.outputs['Fac'], 0.1, 0.01, immagine('EDI_Tenda_Colore'))
    return m

# ---------- piastrelle di prova (UV 0-1 = un periodo) ----------
MATERIALI = {'intonaco': mat_intonaco, 'kraft': mat_kraft, 'legno': mat_legno, 'tenda': mat_tenda}
def piastrella(nome, mat, x):
    base = bpy.data.objects['MAT_Piastrella']
    ob = bpy.data.objects.get(nome)
    if ob is None:
        ob = bpy.data.objects.new(nome, base.data); [c.objects.link(ob) for c in base.users_collection]
    ob.location = (x, -60.0, 0)
    ob.material_slots[0].link = 'OBJECT'; ob.material_slots[0].material = mat
    return ob

def run():
    return [piastrella('EDI_Piastrella_' + n.capitalize(), f(), 40.0*i).name for i, (n, f) in enumerate(MATERIALI.items())]

# ---------- export: packages/web/public/textures/edifici/ ----------
def cartella_texture():
    t = bpy.data.texts.get('cb_materiali_edifici.py')
    radice = os.path.dirname(os.path.dirname(os.path.dirname(bpy.path.abspath(t.filepath))))
    return os.path.join(radice, 'packages', 'web', 'public', 'textures', 'edifici')

def esporta(nome):
    mat = bpy.data.materials['EDI_T_' + nome.capitalize()]; ob = bpy.data.objects['EDI_Piastrella_' + nome.capitalize()]
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 4
    cart = cartella_texture(); os.makedirs(cart, exist_ok=True); file = {}
    im = _bake(ob, mat, f'edi_{nome}_colore', 'DIFFUSE', 'sRGB', lato=LATO_IMG, pass_filter={'COLOR'})
    im.filepath_raw = os.path.join(cart, f'{nome}_colore.jpg'); im.file_format = 'JPEG'; im.save(quality=90)
    file[f'{nome}_colore.jpg'] = im.filepath_raw
    if nome != 'tenda':                                   # la tenda è solo una maschera
        im = _bake(ob, mat, f'edi_{nome}_normale', 'NORMAL', 'Non-Color', lato=LATO_IMG, normal_space='TANGENT')
        im.filepath_raw = os.path.join(cart, f'{nome}_normale.png'); im.file_format = 'PNG'; im.save()
        file[f'{nome}_normale.png'] = im.filepath_raw
    im = _bake(ob, mat, f'edi_{nome}_rugosita', 'ROUGHNESS', 'Non-Color', lato=128)
    px = im.pixels[:]; rug = sum(px[0::4])/(len(px)//4)
    return {k: round(os.path.getsize(v)/1e6, 2) for k, v in file.items()}, round(rug, 3)

def esporta_tutto():
    return {n: esporta(n) for n in MATERIALI}

if __name__ == '__main__':
    print(run())
