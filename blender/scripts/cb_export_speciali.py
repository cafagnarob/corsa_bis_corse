# =====================================================================
# cb_export_speciali.py — Corsa Bis · export degli edifici speciali (modelli cotti)
# Cosa fa (file EDIFICI aperto, edifici speciali costruiti con cb_edifici.py
#   nella collezione Speciali_Campione: per ora il Comune):
#   - prepara(): unisce tutte le istanze del kit in UNA mesh (LOD0) con un
#     atlante UV nuovo; LOD1 = un guscio chiuso per ogni corpo (figli diretti
#     della radice: blocco, torre...), senza bandiere, arengario, cornici.
#   - bake(nome): LOD0 colore in 2048; LOD1 colore del LOD0 proiettato sui
#     gusci (selected to active) in 512.
#   - esporta(): models/edifici/speciali.glb (JPEG, Draco), nodi
#     <Nome>_LOD0 e <Nome>_LOD1, e speciali.json con larghezza, profondità,
#     altezza. Origine all'angolo in basso a destra della facciata principale,
#     davanti +X, metri reali (gioco ×5,2). Uno per mappa: il codice lo posa com'è.
#   Usa le funzioni comuni di cb_export_borgo.py (Text Editor).
# Uso: Run Script, oppure prepara(); bake('Comune'); esporta().
# =====================================================================
import bpy, os, json

_b = {'__name__': 'cb_export_borgo'}
exec(bpy.data.texts['cb_export_borgo.py'].as_string(), _b)
unisci, atlante, guscio, materiale, _bake_su, finisci, discendenti = (
    _b[k] for k in ('unisci', 'atlante', 'guscio', 'materiale', '_bake_su', 'finisci', 'discendenti'))

SPECIALI = ('Comune', 'Duomo', 'Rocca')              # radici nella collezione Speciali_Campione
RIS_LOD0, RIS_LOD1 = 2048, 512
PER_PEZZO = ('Duomo', 'Rocca')
DETTAGLI = ('Bandiera', 'Arengario', 'Cornice', 'Orologio', 'Stemma', 'Marcapiano', 'Soffitto', 'Copertura', 'Cuspide',
            'Dett_', 'Dettagli', 'Scalinata', 'Fasce')

def cartella():
    t = bpy.data.texts.get('cb_export_speciali.py')
    radice = os.path.dirname(os.path.dirname(os.path.dirname(bpy.path.abspath(t.filepath))))
    return os.path.join(radice, 'packages', 'web', 'public', 'models', 'edifici')

def corpo_di(o, r):
    # il figlio diretto della radice da cui discende l'oggetto (blocco, torre...)
    p = o
    while p.parent and p.parent != r: p = p.parent
    return p.name

def prepara():
    c = bpy.data.collections.get('Export_Speciali')
    if c:
        for o in list(c.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d and d.users == 0: bpy.data.meshes.remove(d)
    else:
        c = bpy.data.collections.new('Export_Speciali'); bpy.context.scene.collection.children.link(c)
    c.hide_viewport = False
    for im in [i for i in bpy.data.images if any(i.name.startswith(n + '_') for n in SPECIALI)]: bpy.data.images.remove(im)
    info = {}
    for n in SPECIALI:
        r = bpy.data.objects[n]; inv = r.matrix_world.inverted(); figli = [o for o in discendenti(r) if o.type == 'MESH']
        l0 = unisci(f'X_{n}_LOD0', figli, inv, c); atlante(l0, 0.001)
        gruppi = {}
        for o in figli:
            if any(d in o.name for d in DETTAGLI): continue
            # Comune: un guscio per corpo (blocco, torre); Duomo: un guscio per pezzo (muri, tetti, facciata sono
            # lastre: l'inviluppo di tutta la navata chiuderebbe le spalle e i tetti in una scatola)
            chiave = o.name if n in PER_PEZZO else corpo_di(o, r)
            gruppi.setdefault(chiave, []).append(o)
        l1 = guscio(f'X_{n}_LOD1', list(gruppi.values()), inv, c); atlante(l1, 0.004)
        l0.location = l1.location = r.location
        V = [v.co for v in l1.data.vertices]
        info[n] = {'larghezza': round(-min(v.y for v in V), 2), 'profondita': round(-min(v.x for v in V), 2),
                   'altezza': round(max(v.co.z for v in l0.data.vertices), 2),
                   'triangoli': [sum(len(p.vertices) - 2 for p in o.data.polygons) for o in (l0, l1)]}
    bpy.data.texts['cb_export_speciali.py']['info'] = json.dumps(info)
    return info

def bake(n):
    l0 = bpy.data.objects[f'X_{n}_LOD0']
    me = l0.data; me.uv_layers.active = me.uv_layers['Atlante']; me.uv_layers['UVMap'].active_render = True
    im0 = bpy.data.images.new(f'{n}_colore', RIS_LOD0, RIS_LOD0)
    _bake_su(l0, im0); finisci(l0, materiale(f'{n}_LOD0', im0))
    l1 = bpy.data.objects[f'X_{n}_LOD1']
    r1 = RIS_LOD1*2 if n in PER_PEZZO else RIS_LOD1          # il Duomo ha molti gusci piccoli: serve più risoluzione
    im1 = bpy.data.images.new(f'{n}_LOD1_colore', r1, r1)
    m1 = bpy.data.materials.get(f'{n}_LOD1') or bpy.data.materials.new(f'{n}_LOD1'); m1.use_nodes = True
    nt = m1.node_tree; nt.nodes.clear(); nt.nodes.new('ShaderNodeOutputMaterial')
    nd = nt.nodes.new('ShaderNodeTexImage'); nd.image = im1; nt.nodes.active = nd       # non collegata: niente dipendenza circolare
    l1.data.materials.clear(); l1.data.materials.append(m1)
    _bake_su(l1, im1, sorgente=l0, distanza=1.6)        # i merli tengono il guscio 1,1 m sopra il tetto
    finisci(l1, materiale(f'{n}_LOD1', im1))
    return n

def esporta():
    c = bpy.data.collections['Export_Speciali']; obs = list(c.objects); vecchi = {}
    for o in obs:
        vecchi[o.name[2:]] = o.location.copy(); o.location = (0, 0, 0); o.name = o.name[2:]
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in obs: o.select_set(True)
    d = cartella(); os.makedirs(d, exist_ok=True); p = os.path.join(d, 'speciali.glb')
    try:
        bpy.ops.export_scene.gltf(filepath=p, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
                                  export_animations=False, export_lights=False, export_cameras=False,
                                  export_image_format='JPEG', export_jpeg_quality=85,
                                  export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
    finally:
        for o in obs:
            n = o.name; o.name = 'X_' + n; o.location = vecchi[n]
    with open(os.path.join(d, 'speciali.json'), 'w', encoding='utf-8') as f:
        f.write(bpy.data.texts['cb_export_speciali.py'].get('info', '{}'))
    c.hide_viewport = True
    return p, round(os.path.getsize(p)/1e6, 2)

def run():
    prepara()
    for n in SPECIALI: bake(n)
    return esporta()

if __name__ == '__main__':
    print(run())
