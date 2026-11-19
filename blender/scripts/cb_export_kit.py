# =====================================================================
# cb_export_kit.py — Corsa Bis · export del KIT degli edifici per il codice
# Scelta del 18 novembre (strada 3, ibrida): da vicino il gioco monta gli
#   edifici con i pezzi del kit e il seme, da lontano usa gusci semplici con
#   una texture di facciata. Questo script esporta i pezzi.
# Cosa fa (file EDIFICI aperto, kit costruito da cb_edifici.py nella
#   collezione Kit_Borgo):
#   - una copia di ogni pezzo nell'origine, col nome del pezzo (lo stesso
#     usato da cb_edifici.py e dal codice), normali piatte;
#   - i materiali diventano SEGNAPOSTO con un nome fisso, che il codice
#     sostituisce con le texture ripetibili (come GLB_Faccia per le tessere):
#       EDI_Intonaco  facciata, da tingere per istanza (colore della casa,
#                     stucco per cornici e cornicioni)
#       EDI_Bordo     taglio del cartone (u = lunghezza in m, v 0..1 sullo
#                     spessore: la texture bordo_ondulato delle tessere)
#       EDI_Interno   cartone in ombra dentro le aperture
#       EDI_Kraft     kraft nudo (tetti, scale, ringhiere, persiane)
#       EDI_Legno, EDI_Carta, EDI_Spago, EDI_Tenda (da tingere, a strisce),
#       EDI_Coppi (tetti delle villette, rosso), EDI_Vetro_Gr (carta azzurrina delle finestre dei grattacieli),
#       EDI_Vetro (vetri di androni, vetrocemento e divisori dei palazzoni),
#       EDI_Insegna_<nome>, EDI_Scritta_<nome> (colori già giusti)
#     UV delle facce in metri (1 unità UV = 1 m reale);
#   - models/edifici/kit_edifici.glb (Draco, senza immagini) e
#     kit_edifici.json: costanti del kit, aperture dei moduli, pezzi con
#     misure, triangoli e materiali, per riscrivere il generatore nel codice.
#   Metri reali (gioco ×5,2); origine di ogni pezzo all'angolo in basso a
#   destra della facciata, davanti +X, un modulo occupa y da 0 a -2.
# Uso: Run Script (dopo cb_edifici.py), oppure esporta().
# =====================================================================
import bpy, os, json, math

SEGNAPOSTO = {   # materiale di Blender -> (segnaposto, colore di prova nel .glb)
    'KIT_Intonaco': ('EDI_Intonaco', (1.0, 1.0, 1.0)), 'CB_B_Bordo': ('EDI_Bordo', (0.55, 0.40, 0.25)),
    'CB_B_Interno': ('EDI_Interno', (0.20, 0.14, 0.09)), 'CB_B_Kraft': ('EDI_Kraft', (0.62, 0.45, 0.28)),
    'CB_B_Legno': ('EDI_Legno', (0.55, 0.38, 0.22)), 'CB_B_Carta': ('EDI_Carta', (0.90, 0.88, 0.82)),
    'CB_B_Spago': ('EDI_Spago', (0.62, 0.52, 0.38)), 'KIT_Tenda': ('EDI_Tenda', (1.0, 1.0, 1.0)),
    'CB_P_Vetro': ('EDI_Vetro', (0.52, 0.60, 0.60)), 'CB_V_Coppi': ('EDI_Coppi', (0.72, 0.25, 0.15)),
    'CB_G_Vetro': ('EDI_Vetro_Gr', (0.66, 0.78, 0.88)),
}

def cartella():
    t = bpy.data.texts.get('cb_export_kit.py')
    radice = os.path.dirname(os.path.dirname(os.path.dirname(bpy.path.abspath(t.filepath))))
    return os.path.join(radice, 'packages', 'web', 'public', 'models', 'edifici')

def segnaposto(m):
    # materiale piatto col nome fisso; insegne e scritte tengono il loro colore
    if m.name in SEGNAPOSTO: nome, col = SEGNAPOSTO[m.name]
    else:
        nome = 'EDI_' + m.name.replace('CB_B_', '').replace('CB_S_', 'Speciale_')
        b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if m.use_nodes else None
        col = tuple(b.inputs['Base Color'].default_value[:3]) if b else (0.8, 0.8, 0.8)
    e = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
    e.use_nodes = True; bs = e.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*col, 1); bs.inputs['Roughness'].default_value = 0.9
    return e

def costanti(ns):
    # le regole del kit che il generatore nel codice deve conoscere
    k = ('MODULO', 'T', 'H_TERRA', 'H_PIANO', 'ONDA', 'AMP', 'FALDA_A', 'TETTO_A', 'GRONDA', 'VICOLO')
    c = {n: round(ns[n], 4) for n in k if n in ns}
    c['FINESTRA_PIANO'] = list(ns['FINESTRA_PIANO'])
    c['INTONACI'] = {n: [round(x, 3) for x in v] for n, v in ns['INTONACI'].items()}
    c['INTONACI_CORTE'] = {n: [round(x, 3) for x in v] for n, v in ns['INTONACI_CORTE'].items()}
    c['STUCCO'] = [0.92, 0.88, 0.78]
    c['INTONACI_PALAZZONI'] = {n: [round(x, 3) for x in v] for n, v in ns['INTONACI_PALAZZONI'].items()}
    c['CEMENTO_CHIARO'] = list(ns['CEMENTO_CHIARO'])
    c['INTONACI_VILLE'] = {n: [round(x, 3) for x in v] for n, v in ns['INTONACI_VILLE'].items()}
    c['COPPI'] = list(ns['COPPI']); c['TETTO_V'] = round(ns['TETTO_V'], 4)
    c['INTONACI_CAPANNONI'] = {n: [round(x, 3) for x in v] for n, v in ns['INTONACI_CAPANNONI'].items()}
    c['UFFICI'] = {n: [round(x, 3) for x in v] for n, v in ns['UFFICI'].items()}
    c['ROSSO_CIM'] = list(ns['ROSSO_CIM']); c['SHED_L'] = ns['SHED_L']; c['SHED_A'] = round(ns['SHED_A'], 4)
    c['INTONACI_GRATTACIELI'] = {n: [round(x, 3) for x in v] for n, v in ns['INTONACI_GRATTACIELI'].items()}
    c['VETRO_GR'] = list(ns['VETRO_GR'])
    c['COMUNE_COLORI'] = {n: [round(x, 3) for x in v] for n, v in ns['COMUNE_COLORI'].items()}
    c['TENDE'] = [[list(a), list(b)] for a, b in ns['TENDE']]
    ap = {n: {'altezza': h, 'buchi': [[[round(x, 3), round(y, 3)] for x, y in poly] for poly in b]} for n, (h, b) in ns['APERTURE'].items()}
    return c, ap

def esporta():
    ns = {'__name__': 'cb_edifici'}; exec(bpy.data.texts['cb_edifici.py'].as_string(), ns)
    pezzi = [o for o in bpy.data.collections['Kit_Borgo'].objects if o.type == 'MESH']
    coll = bpy.data.collections.get('Export_Kit') or bpy.data.collections.new('Export_Kit')
    if coll.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(coll)
    for o in list(coll.objects):
        d = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(d)
    coll.hide_viewport = False
    copie, info = [], {}
    for o in pezzi:
        nome = o.name; o.name = nome + '__kit'                  # l'originale cede il nome alla copia
        me = o.data.copy(); me.name = 'EDI_' + nome
        mats = [segnaposto(m) for m in o.data.materials]
        for i, m in enumerate(mats): me.materials[i] = m       # sostituiti al loro posto (clear() azzererebbe gli indici)
        for p in me.polygons: p.use_smooth = False
        c = bpy.data.objects.new(nome, me); coll.objects.link(c); copie.append((c, o, nome))
        bb = [v.co for v in me.vertices]
        info[nome] = {'triangoli': sum(len(p.vertices) - 2 for p in me.polygons), 'materiali': [m.name for m in mats],
                      'min': [round(min(v[i] for v in bb), 3) for i in range(3)], 'max': [round(max(v[i] for v in bb), 3) for i in range(3)]}
    for x in bpy.context.view_layer.objects: x.select_set(False)
    for c, _, _ in copie: c.select_set(True)
    d = cartella(); os.makedirs(d, exist_ok=True); p = os.path.join(d, 'kit_edifici.glb')
    try:
        bpy.ops.export_scene.gltf(filepath=p, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
                                  export_animations=False, export_lights=False, export_cameras=False, export_materials='EXPORT',
                                  export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
    finally:
        for c, o, nome in copie: c.name = nome + '__exp'; o.name = nome      # gli originali riprendono il nome
    cst, ap = costanti(ns)
    with open(os.path.join(d, 'kit_edifici.json'), 'w', encoding='utf-8') as f:
        json.dump({'costanti': cst, 'aperture': ap, 'pezzi': info}, f, ensure_ascii=False, indent=1)
    coll.hide_viewport = True
    return p, round(os.path.getsize(p)/1e6, 2), len(info), sum(v['triangoli'] for v in info.values())

if __name__ == '__main__':
    print(esporta())
