# =====================================================================
# cb_export_vegetazione.py — Corsa Bis · export di alberi, cespugli e siepe
# Cosa fa (file con la collezione Alberi_Cartone, costruita da cb_alberi.py):
#   per ogni pianta e per ogni LOD prepara una copia con un atlante UV
#   nuovo e il cartone (tempera verde, decoro bianco, tronco kraft, bordo
#   ondulato) cotto in UNA immagine (bake Diffuse, solo colore):
#   LOD0 1024 pixel (siepe 1024), LOD1 256.
#   Scrive packages/web/public/models/arredo/vegetazione.glb (JPEG, Draco)
#   con i nodi <Pianta>_LOD0 e <Pianta>_LOD1, tutti nell'origine:
#   origine al piede (Z = 0), metri reali (gioco ×5,2).
#   Piante: Abete, Abete_Festoni, Albero_Tondo, Albero_Goccia,
#   Cespuglio_Cupola, Cespuglio_Nuvola, Siepe (modulo da 4 m lungo X).
# Uso: Run Script, oppure prepara(); bake('Abete', 0) ...; esporta().
# =====================================================================
import bpy, math, os

PIANTE = ('Abete', 'Abete_Festoni', 'Albero_Tondo', 'Albero_Goccia', 'Cespuglio_Cupola', 'Cespuglio_Nuvola', 'Siepe')
RISOLUZIONE = {0: 1024, 1: 256}
CAMPIONI = 8

def cartella():
    t = bpy.data.texts.get('cb_export_vegetazione.py')
    radice = os.path.dirname(os.path.dirname(os.path.dirname(bpy.path.abspath(t.filepath))))
    return os.path.join(radice, 'packages', 'web', 'public', 'models', 'arredo')

def prepara():
    c = bpy.data.collections.get('Export_Vegetazione')
    if c:
        for o in list(c.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d and d.users == 0: bpy.data.meshes.remove(d)
    else:
        c = bpy.data.collections.new('Export_Vegetazione'); bpy.context.scene.collection.children.link(c)
    c.hide_viewport = False                 # nascosta dall'export precedente: deve essere selezionabile per il bake
    for im in [i for i in bpy.data.images if i.name.startswith('Veg_')]: bpy.data.images.remove(im)
    for p in PIANTE:
        for L in (0, 1):
            src = bpy.data.objects[f'{p}_LOD{L}']
            me = src.data.copy(); me.name = f'X_{p}_LOD{L}'
            ob = bpy.data.objects.new(me.name, me); c.objects.link(ob); ob.location = src.location
            me.uv_layers[0].name = 'UVMap'
            at = me.uv_layers.new(name='Atlante'); me.uv_layers.active = at; me.uv_layers['UVMap'].active_render = True
            for o in bpy.context.view_layer.objects: o.select_set(False)
            bpy.context.view_layer.objects.active = ob; ob.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, area_weight=0.0, scale_to_bounds=True)
            bpy.ops.object.mode_set(mode='OBJECT')
    return len(c.objects)

def bake(p, L):
    ob = bpy.data.objects[f'X_{p}_LOD{L}']; sc = bpy.context.scene; r = RISOLUZIONE[L]
    sc.render.engine = 'CYCLES'; sc.cycles.samples = CAMPIONI
    sc.render.bake.margin = max(2, r//256); sc.render.bake.use_clear = True
    im = bpy.data.images.new(f'Veg_{p}_LOD{L}', r, r); nodi = []
    for m in ob.data.materials:
        nd = m.node_tree.nodes.new('ShaderNodeTexImage'); nd.image = im
        for x in m.node_tree.nodes: x.select = False
        nd.select = True; m.node_tree.nodes.active = nd; nodi.append((m, nd))
    for o in bpy.context.view_layer.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
    for m, nd in nodi: m.node_tree.nodes.remove(nd)
    im.pack()
    mat = bpy.data.materials.new(f'{p}_LOD{L}'); mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = im
    nt.links.new(t.outputs['Color'], b.inputs['Base Color']); nt.links.new(b.outputs[0], out.inputs['Surface'])
    b.inputs['Roughness'].default_value = 0.85
    me = ob.data; me.materials.clear(); me.materials.append(mat)
    for f in me.polygons: f.material_index = 0; f.use_smooth = False
    me.uv_layers.remove(me.uv_layers['UVMap']); me.uv_layers['Atlante'].name = 'UVMap'

def esporta():
    c = bpy.data.collections['Export_Vegetazione']; obs = list(c.objects); pos = {}
    # nel .glb i nodi devono chiamarsi <Pianta>_LODn: gli originali lasciano libero il nome per l'export
    originali = []
    for o in obs:
        orig = bpy.data.objects.get(o.name[2:])
        if orig: orig.name = '_src_' + orig.name; originali.append(orig)
    for o in obs:
        pos[o.name[2:]] = o.location.copy(); o.location = (0, 0, 0); o.name = o.name[2:]
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in obs: o.select_set(True)
    d = cartella(); os.makedirs(d, exist_ok=True); path = os.path.join(d, 'vegetazione.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
                              export_animations=False, export_lights=False, export_cameras=False,
                              export_image_format='JPEG', export_jpeg_quality=88,
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
    tri = {}
    for o in obs:
        tri[o.name] = sum(len(f.vertices) - 2 for f in o.data.polygons)
        n = o.name; o.name = 'X_' + n; o.location = pos[n]
    for orig in originali: orig.name = orig.name[5:]
    c.hide_viewport = True
    return path, round(os.path.getsize(path)/1e6, 2), tri

def run():
    prepara()
    for p in PIANTE:
        for L in (0, 1): bake(p, L)
    return esporta()

if __name__ == '__main__':
    print(run())
