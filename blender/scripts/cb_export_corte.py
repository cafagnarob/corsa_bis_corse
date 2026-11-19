# =====================================================================
# cb_export_corte.py — Corsa Bis · export dei palazzi a corte
# Cosa fa (file EDIFICI aperto, blocchi C1..C4 generati con
#   cb_edifici.run_corte()):
#   - prepara(): per ogni blocco unisce tutte le istanze del kit in UNA mesh
#     (LOD0), origine all'angolo in basso a destra della facciata principale,
#     davanti +X, nuovo atlante UV. LOD1: un guscio chiuso PER PALAZZO
#     (ogni palazzo della cortina, ogni ala corta, il cortile), così il
#     cortile resta aperto; senza balconi, ballatoi, cornici, persiane, tende.
#   - bake(i): LOD0 = colore dei cartoni cotto in un'immagine 2048;
#     LOD1 = colore del LOD0 proiettato sui gusci (selected to active) 512.
#   - esporta(): models/edifici/corte.glb (JPEG, Draco), nodi Corte_<i>_LOD0 e
#     Corte_<i>_LOD1, e corte.json con lunghezza, profondità e altezza.
#   Usa le funzioni comuni di cb_export_borgo.py (unione, atlante, guscio,
#   bake), che deve stare nel Text Editor. Metri reali (gioco ×5,2).
# Uso: Run Script, oppure passo per passo: prepara(); bake(1) ... ; esporta().
# =====================================================================
import bpy, os, json, re

_b = {'__name__': 'cb_export_borgo'}
exec(bpy.data.texts['cb_export_borgo.py'].as_string(), _b)
unisci, atlante, guscio, materiale, _bake_su, finisci, discendenti = (
    _b[k] for k in ('unisci', 'atlante', 'guscio', 'materiale', '_bake_su', 'finisci', 'discendenti'))

SEMI = range(1, 5)                 # blocchi C1..C4 della collezione Corte_Campione
RIS_LOD0, RIS_LOD1 = 2048, 512
DETTAGLI = _b['DETTAGLI'] + ('Ballatoio', 'Cornice_')
RADICE = re.compile(r'_Ala(Fronte|Retro)_\d+$|_Ala(Dx|Sx)$')     # empty di ogni palazzo del blocco

def cartella():
    t = bpy.data.texts.get('cb_export_corte.py')
    radice = os.path.dirname(os.path.dirname(os.path.dirname(bpy.path.abspath(t.filepath))))
    return os.path.join(radice, 'packages', 'web', 'public', 'models', 'edifici')

def palazzo_di(o):
    # il palazzo (segmento della cortina o ala corta) a cui appartiene un oggetto; il cortile fa gruppo da sé
    p = o.parent
    while p and not RADICE.search(p.name): p = p.parent
    return p.name if p else o.name

def prepara():
    c = bpy.data.collections.get('Export_Corte')
    if c:
        for o in list(c.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d and d.users == 0: bpy.data.meshes.remove(d)
    else:
        c = bpy.data.collections.new('Export_Corte'); bpy.context.scene.collection.children.link(c)
    c.hide_viewport = False
    for im in [i for i in bpy.data.images if i.name.startswith('Corte_')]: bpy.data.images.remove(im)
    info = {}
    for i in SEMI:
        r = bpy.data.objects[f'C{i}']; inv = r.matrix_world.inverted(); figli = [o for o in discendenti(r) if o.type == 'MESH']
        l0 = unisci(f'X_Corte_{i}_LOD0', figli, inv, c); atlante(l0, 0.001)
        gruppi = {}
        for o in figli:
            if not any(d in o.name for d in DETTAGLI): gruppi.setdefault(palazzo_di(o), []).append(o)
        l1 = guscio(f'X_Corte_{i}_LOD1', list(gruppi.values()), inv, c); atlante(l1, 0.004)
        l0.location = l1.location = r.location
        V = [v.co for v in l1.data.vertices]
        info[f'Corte_{i}'] = {'lunghezza': round(-min(v.y for v in V), 2), 'profondita': round(-min(v.x for v in V), 2),
                              'altezza': round(max(v.co.z for v in l0.data.vertices), 2), 'palazzi': len(gruppi) - 1}
    bpy.data.texts['cb_export_corte.py']['info'] = json.dumps(info)
    return info

def bake(i):
    l0 = bpy.data.objects[f'X_Corte_{i}_LOD0']
    me = l0.data; me.uv_layers.active = me.uv_layers['Atlante']; me.uv_layers['UVMap'].active_render = True
    im0 = bpy.data.images.new(f'Corte_{i}_colore', RIS_LOD0, RIS_LOD0)
    _bake_su(l0, im0); finisci(l0, materiale(f'Corte_{i}_LOD0', im0))
    # LOD1: l'immagine di destinazione NON è collegata allo shader durante il bake (niente dipendenza circolare)
    l1 = bpy.data.objects[f'X_Corte_{i}_LOD1']
    im1 = bpy.data.images.new(f'Corte_{i}_LOD1_colore', RIS_LOD1, RIS_LOD1)
    m1 = bpy.data.materials.get(f'Corte_{i}_LOD1') or bpy.data.materials.new(f'Corte_{i}_LOD1'); m1.use_nodes = True
    nt = m1.node_tree; nt.nodes.clear(); nt.nodes.new('ShaderNodeOutputMaterial')
    nd = nt.nodes.new('ShaderNodeTexImage'); nd.image = im1; nt.nodes.active = nd
    l1.data.materials.clear(); l1.data.materials.append(m1)
    _bake_su(l1, im1, sorgente=l0)
    finisci(l1, materiale(f'Corte_{i}_LOD1', im1))
    return i

def esporta():
    c = bpy.data.collections['Export_Corte']; obs = list(c.objects); vecchi = {}
    for o in obs:
        vecchi[o.name[2:]] = o.location.copy(); o.location = (0, 0, 0); o.name = o.name[2:]
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in obs: o.select_set(True)
    d = cartella(); os.makedirs(d, exist_ok=True); p = os.path.join(d, 'corte.glb')
    bpy.ops.export_scene.gltf(filepath=p, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
                              export_animations=False, export_lights=False, export_cameras=False,
                              export_image_format='JPEG', export_jpeg_quality=85,
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
    with open(os.path.join(d, 'corte.json'), 'w', encoding='utf-8') as f:
        f.write(bpy.data.texts['cb_export_corte.py'].get('info', '{}'))
    tri = {}
    for o in obs:
        n = o.name; tri[n] = sum(len(f.vertices) - 2 for f in o.data.polygons)
        o.name = 'X_' + n; o.location = vecchi[n]
    c.hide_viewport = True
    return p, round(os.path.getsize(p)/1e6, 2), tri

def run():
    prepara()
    for i in SEMI: bake(i)
    return esporta()

if __name__ == '__main__':
    print(run())
