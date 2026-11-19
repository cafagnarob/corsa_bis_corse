# =====================================================================
# cb_tessera.py — Corsa Bis · tessere esagonali: la pila di strati
# Cosa fa: costruisce i pezzi base di ogni tessera (GDD, "Terreno: il
#   plastico a strati" e "Geometria della tessera"):
#   - disco di STRATO: esagono di cartone ondulato spesso 8 unità, con
#     l'onda sul bordo; è UN solo modello, ripetuto per ogni livello
#     (nel gioco: instancing), colorato per quota assoluta: ogni livello
#     un po' più chiaro di quello sotto, così le colline si leggono come
#     curve di livello;
#   - disco di CIMA: esagono sottile (2 unità) del tipo di terreno:
#     erba, asfalto, selciato;
#   - una tessera = cima + N strati sotto lo zero (origine al centro della
#     faccia superiore, Z = 0, punte lungo Y, raggio 200 unità).
#   Ogni strato della pila è ruotato di un multiplo di 60° (scelto dal
#   seed): l'esagono resta lo stesso ma i bordi storti non si allineano,
#   come in una pila di cartoni tagliati a mano.
# Unità: unità di gioco (come nel GDD per le tessere), non metri reali.
# Uso: apri il file nel Text Editor e premi Run Script: costruisce la fila
#   di prova (pile da 1, 2, 3 strati, le tre cime, una tessera esplosa).
# =====================================================================
import bpy, math, os, random
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

if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))

# ---------- misure (unità di gioco) ----------
RAGGIO = 200.0                 # raggio = lato dell'esagono
STRATO = 12.0                  # spessore grafico di uno strato (in simulazione ~10 m); deciso: 12
CIMA = 2.0                     # spessore del disco di cima
STACCO = 0.2                   # spazio invisibile tra cima e strato e tra uno strato e l'altro:
                               # facce coincidenti sfarfallano (z-fighting); 0,2 su 400 non si vede
CLIP = (1.0, 20000.0)          # inizio e fine taglio della vista per le tessere: con 0,01 (default)
                               # a centinaia di unità la profondità perde precisione e le facce
                               # nascoste bucano la cima (strisce). Nel gioco: camera near >= 1.
S_STRATO, S_CIMA = 100.0, 25.0 # scala del cartone: onda ogni 16 unità sugli strati, ogni 4 sulla cima
MAX_LIVELLI = 8
CIME = {   # tipo di terreno: (nome materiale, colore del cartoncino tinto, scrostature)
    'erba':     ('CB_T_Cima_Erba',     (0.30, 0.42, 0.26, 1), 0.70),
    'asfalto':  ('CB_T_Cima_Asfalto',  (0.20, 0.20, 0.21, 1), 0.72),
    'selciato': ('CB_T_Cima_Selciato', (0.58, 0.40, 0.22, 1), 0.68),
}

def esagono(r=RAGGIO):
    return [(r*math.cos(math.radians(90 + 60*k)), r*math.sin(math.radians(90 + 60*k))) for k in range(6)]

# ---------- materiali alla scala delle tessere ----------
def materiali_tessera():
    M = {'bordo': mat_bordo('CB_T_Strato_Bordo', S_STRATO),
         'bordo_cima': mat_bordo('CB_T_Cima_Bordo', S_CIMA),
         'interno': mat_kraft('CB_T_Interno', 0.42, S_STRATO)}
    for k in range(1, MAX_LIVELLI + 1):
        # livello 1 = il più basso e scuro; ogni livello più chiaro del precedente
        M[f'livello_{k}'] = mat_kraft(f'CB_T_Strato_Livello_{k}', 0.70 + 0.08*(k - 1), S_STRATO)
        # anche il bordo ondulato si schiarisce: è quello che si vede sui gradini delle colline
        M[f'bordo_{k}'] = mat_bordo(f'CB_T_Strato_Bordo_{k}', S_STRATO, 0.70 + 0.08*(k - 1))
    for tipo, (nome, col, chips) in CIME.items():
        M['cima_' + tipo] = mat_vernice(nome, col, chips, S_CIMA)
    return M

# ---------- mesh condivise (una sola per tipo: instancing) ----------
def mesh_strato(M, spessore=STRATO):
    nome = 'Tessera_Strato' if spessore == STRATO else f'Tessera_Strato_{spessore:g}'
    me = bpy.data.meshes.get(nome)
    if me: return me
    g = build_panel(esagono(), t=spessore, warp=0.0, seed=1, scala=S_STRATO)
    ob = make_object('_tmp', [(g, Matrix())], [M['livello_1'], M['bordo'], M['interno']], bpy.context.scene.collection)
    me = ob.data; me.name = nome; bpy.data.objects.remove(ob); return me

def mesh_cima(M, tipo):
    nome = 'Tessera_Cima_' + tipo
    me = bpy.data.meshes.get(nome)
    if me: return me
    g = build_panel(esagono(RAGGIO - 0.6), t=CIMA, warp=0.0, seed=2, step=0.4, scala=S_CIMA)   # bordo ogni 10 unità: più leggero
    ob = make_object('_tmp', [(g, Matrix())], [M['cima_' + tipo], M['bordo_cima'], M['interno']], bpy.context.scene.collection)
    me = ob.data; me.name = nome; bpy.data.objects.remove(ob); return me

def istanza(nome, me, coll, loc, rot_z=0.0, mat_faccia=None, mat_bordo=None):
    ob = bpy.data.objects.new(nome, me); ob.location = loc; ob.rotation_euler = (0, 0, rot_z)
    coll.objects.link(ob)
    # colori per istanza (nel gioco: colore per istanza dell'instancing), la mesh resta una sola
    for slot, mat in ((0, mat_faccia), (1, mat_bordo)):
        if mat is not None:
            ob.material_slots[slot].link = 'OBJECT'; ob.material_slots[slot].material = mat
    return ob

# ---------- una tessera ----------
def tessera(nome, coll, loc, livello=1, tipo='erba', M=None, seed=0, esplosa=0.0, strato=STRATO):
    # livello = numero di strati (quota); la faccia della cima è a Z = loc.z
    M = M or materiali_tessera(); loc = Vector(loc); rng = random.Random(seed); out = []
    out.append(istanza(f'{nome}_Cima', mesh_cima(M, tipo), coll, loc + Vector((0, 0, -CIMA + esplosa)), rng.randrange(6)*math.pi/3))
    for i in range(livello):
        k = livello - i                                       # quota assoluta dello strato
        # la cima resta con la faccia a Z = 0; gli strati scendono di STACCO in più ciascuno
        z = -CIMA - strato*(i + 1) - STACCO*(i + 1) - esplosa*i
        out.append(istanza(f'{nome}_Strato_{k}', mesh_strato(M, strato), coll, loc + Vector((0, 0, z)), rng.randrange(6)*math.pi/3, M[f'livello_{k}'], M[f'bordo_{k}']))
    return out

def cartello(testo, loc, coll, M, size=16.0):
    lab = make_label(testo, (loc[0], loc[1], 0.6), coll, mat_kraft('CB_T_Inchiostro', 0.08, 1.0), size=size)
    bpy.context.view_layer.update()
    w = lab.dimensions.x + size*1.2; h = size*1.8
    g = build_panel(rect(-w/2, -h/2, w/2, h/2), t=0.5, warp=0.0, seed=len(testo), scala=S_CIMA)
    make_object('Cartello_' + testo[:14], [(g, Matrix())], [M['livello_6'], M['bordo_cima'], M['interno']], coll, (loc[0], loc[1] + size*0.25, 0.0))

def vista_tessere():
    # imposta inizio/fine taglio di tutte le viste 3D e della camera di scena
    for scr in bpy.data.screens:
        for a in scr.areas:
            if a.type == 'VIEW_3D':
                a.spaces.active.clip_start, a.spaces.active.clip_end = CLIP
    for c in bpy.data.cameras: c.clip_start, c.clip_end = CLIP

# ---------- fila di prova ----------
def run():
    vista_tessere()
    coll = bpy.data.collections.get('Tessere_Prova')
    if coll:
        for o in list(coll.objects): bpy.data.objects.remove(o, do_unlink=True)
    else:
        coll = bpy.data.collections.new('Tessere_Prova'); bpy.context.scene.collection.children.link(coll)
    M = materiali_tessera(); PASSO = 420.0
    prove = [('1 strato · erba', 1, 'erba', 0), ('2 strati · erba', 2, 'erba', 0), ('3 strati · erba', 3, 'erba', 0),
             ('asfalto', 1, 'asfalto', 0), ('selciato', 1, 'selciato', 0), ('esplosa · 2 strati + cima', 2, 'erba', 25.0)]
    for i, (titolo, liv, tipo, esp) in enumerate(prove):
        x = i*PASSO
        # la faccia di cima sta alla quota della tessera: livello 1 a Z = 0, ogni livello in più sale di uno strato
        z = (liv - 1)*(STRATO + STACCO) if esp == 0 else (liv - 1)*(STRATO + STACCO) + 2*esp
        tessera(f'T{i+1}', coll, (x, 0, z), liv, tipo, M, seed=i, esplosa=esp)
        cartello(titolo, (x, -260.0, 0), coll, M)
    # collina: tre tessere vicine a quote 1, 2, 3 (vicina a est: +346,4 in x; a nord-est: +173,2 x, +300 y)
    cx = len(prove)*PASSO + 200.0; DX = math.sqrt(3)*RAGGIO
    for j, (q, livello) in enumerate((((0, 0), 1), ((DX, 0), 2), ((DX/2, 1.5*RAGGIO), 3))):
        tessera(f'C{j+1}', coll, (cx + q[0], q[1], (livello - 1)*(STRATO + STACCO)), livello, 'erba', M, seed=10 + j)
    cartello('collina · quote 1, 2, 3', (cx + DX/2, -260.0, 0), coll, M)
    return coll

if __name__ == '__main__':
    run()
