# =====================================================================
# cb_export_monumenti.py — Corsa Bis · export delle statue delle rotonde
# Cosa fa (file PERSONAGGI aperto, statue costruite con cb_statue.py):
#   per ogni Monumento_<nome> (Oratore, Pensatore, Fiaccola, Poeta,
#   Equestre) prepara una copia con:
#   - le facce sotto il basamento tolte (non si vedono mai);
#   - un atlante UV nuovo e il cartone (bronzo/marmo, pietra, targa,
#     bordi ondulati) cotto in UNA immagine (bake Diffuse, solo colore);
#   - LOD0 = tutto il dettaglio; LOD1 = la stessa mesh ridotta a circa un
#     quarto dei triangoli, con le stesse UV e lo stesso materiale (da
#     lontano, viste dall'alto e di media distanza).
#   Scrive packages/web/public/models/arredo/monumenti.glb (JPEG, Draco):
#   nodi Monumento_<nome>_LOD0 e Monumento_<nome>_LOD1, tutti con
#   l'origine al centro della base del basamento (Z = 0), davanti +X,
#   metri reali (nel gioco scala 5,2 come mezzi e palina).
# Uso: Run Script, oppure passo per passo: prepara(); bake('Oratore') ...;
#   esporta().
# =====================================================================
import bpy, bmesh, math, os

NOMI = ('Oratore', 'Pensatore', 'Fiaccola', 'Poeta', 'Equestre')
RISOLUZIONE = 2048
CAMPIONI = 8
RIDUZIONE = 0.25           # LOD1: frazione dei triangoli del LOD0

def cartella():
    t = bpy.data.texts.get('cb_export_monumenti.py')
    radice = os.path.dirname(os.path.dirname(os.path.dirname(bpy.path.abspath(t.filepath))))
    return os.path.join(radice, 'packages', 'web', 'public', 'models', 'arredo')

def prepara():
    c = bpy.data.collections.get('Export_Monumenti')
    if c:
        for o in list(c.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d and d.users == 0: bpy.data.meshes.remove(d)
    else:
        c = bpy.data.collections.new('Export_Monumenti'); bpy.context.scene.collection.children.link(c)
    for im in [i for i in bpy.data.images if i.name.startswith('Monumento_')]: bpy.data.images.remove(im)
    for n in NOMI:
        src = bpy.data.objects[f'Monumento_{n}']
        me = src.data.copy(); me.name = f'X_Monumento_{n}_LOD0'
        bm = bmesh.new(); bm.from_mesh(me)
        sotto = [f for f in bm.faces if f.normal.z < -0.99 and max(v.co.z for v in f.verts) < 0.01]
        bmesh.ops.delete(bm, geom=sotto, context='FACES'); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(me.name, me); c.objects.link(ob); ob.location = src.location
        me.uv_layers[0].name = 'UVMap'
        at = me.uv_layers.new(name='Atlante'); me.uv_layers.active = at; me.uv_layers['UVMap'].active_render = True
        for o in bpy.context.view_layer.objects: o.select_set(False)
        bpy.context.view_layer.objects.active = ob; ob.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003, area_weight=0.0, scale_to_bounds=True)
        bpy.ops.object.mode_set(mode='OBJECT')
    return [o.name for o in c.objects]

def bake(n):
    ob = bpy.data.objects[f'X_Monumento_{n}_LOD0']; sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = CAMPIONI
    sc.render.bake.margin = 6; sc.render.bake.use_clear = True
    im = bpy.data.images.new(f'Monumento_{n}_colore', RISOLUZIONE, RISOLUZIONE); nodi = []
    for m in ob.data.materials:
        nd = m.node_tree.nodes.new('ShaderNodeTexImage'); nd.image = im
        for x in m.node_tree.nodes: x.select = False
        nd.select = True; m.node_tree.nodes.active = nd; nodi.append((m, nd))
    for o in bpy.context.view_layer.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
    for m, nd in nodi: m.node_tree.nodes.remove(nd)
    im.pack()
    mat = bpy.data.materials.get(f'Monumento_{n}') or bpy.data.materials.new(f'Monumento_{n}'); mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = im
    nt.links.new(t.outputs['Color'], b.inputs['Base Color']); nt.links.new(b.outputs[0], out.inputs['Surface'])
    b.inputs['Roughness'].default_value = 0.85
    me = ob.data; me.materials.clear(); me.materials.append(mat)
    for p in me.polygons: p.material_index = 0; p.use_smooth = False
    me.uv_layers.remove(me.uv_layers['UVMap']); me.uv_layers['Atlante'].name = 'UVMap'
    # LOD1: copia ridotta (collapse tiene le UV)
    l1 = ob.copy(); l1.data = me.copy(); l1.name = l1.data.name = f'X_Monumento_{n}_LOD1'
    ob.users_collection[0].objects.link(l1)
    md = l1.modifiers.new('Riduci', 'DECIMATE'); md.ratio = RIDUZIONE
    bpy.context.view_layer.objects.active = l1
    for o in bpy.context.view_layer.objects: o.select_set(False)
    l1.select_set(True); bpy.ops.object.modifier_apply(modifier='Riduci')
    l1.data.validate()                     # la riduzione lascia facce degeneri: via
    return n

def esporta():
    c = bpy.data.collections['Export_Monumenti']; obs = list(c.objects); vecchi = {}
    for o in obs:
        vecchi[o.name] = (o.location.copy(), o.name)
        o.location = (0, 0, 0); o.name = o.name[2:]          # nel .glb: Monumento_<nome>_LODn nell'origine
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in obs: o.select_set(True)
    d = cartella(); os.makedirs(d, exist_ok=True); p = os.path.join(d, 'monumenti.glb')
    bpy.ops.export_scene.gltf(filepath=p, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
                              export_animations=False, export_lights=False, export_cameras=False,
                              export_image_format='JPEG', export_jpeg_quality=88,
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
    tri = {}
    for o in obs:
        tri[o.name] = sum(len(f.vertices) - 2 for f in o.data.polygons)
        o.name = 'X_' + o.name
        o.location = vecchi[o.name][0]
    c.hide_viewport = True
    return p, round(os.path.getsize(p)/1e6, 2), tri

def run():
    prepara()
    for n in NOMI: bake(n)
    return esporta()

if __name__ == '__main__':
    print(run())
