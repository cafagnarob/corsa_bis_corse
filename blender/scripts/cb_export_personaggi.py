# =====================================================================
# cb_export_personaggi.py — Corsa Bis · export dell'omino e dei personaggi con il rig
# Cosa fa (file PERSONAGGI aperto, omino di cb_omino.py e personaggi di
#   cb_personaggi.py già costruiti):
#   - per ogni personaggio una copia del rig nell'origine ("Rig", 11 ossa:
#     Root, Busto, Testa, Braccio_Sup_/Avambraccio_ Sx e Dx, Coscia_/Gamba_
#     Sx e Dx) e UNA mesh con la pelle rigida: ogni pezzo segue al 100%
#     l'osso a cui era agganciato (come i mezzi);
#   - colore dei cartoni cotto in un'immagine su un atlante nuovo (Diffuso
#     solo colore), un materiale, normali piatte;
#   - omino: LOD0 (1.500 triangoli) e LOD1 (200) sullo stesso Rig; i vestiti
#     escono chiari e l'attributo di colore "Tinta" (COLOR_0, 1 sui vestiti,
#     0 su pelle, scarpe, legno) dice al codice dove tingere per istanza:
#     colore = texel × mix(1, coloreVestiti, Tinta);
#   - clip: "Cammina" (fotogrammi 1-25 = un passo destro + uno sinistro,
#     in loop) e "Seduto" (slider: 1 = in piedi, 2 = seduto, il bacino scende
#     di 0,33 m e i piedi restano a terra). Una clip sola per tutti: stesse
#     ossa, le misure diverse le fa la scala del rig.
#   File: models/personaggi/omino.glb e models/personaggi/<nome>.glb
#   (Pina, Marco, Rinaldi, Ferretti, Giulia, Tommaso). Metri reali (gioco
#   ×5,2), davanti +X, origine in mezzo ai piedi.
# Uso: Run Script, oppure prepara(); azioni(); bake('Omino'); bake('Pina')...;
#   esporta('Omino'); esporta('Pina')...
# =====================================================================
import bpy, bmesh, math, os

PERSONAGGI = ('Pina', 'Marco', 'Rinaldi', 'Ferretti', 'Giulia', 'Tommaso')
RIS = {'Omino_LOD0': 512, 'Omino_LOD1': 256}          # i personaggi: 1024
CAMPIONI = 8

def cartella():
    t = bpy.data.texts.get('cb_export_personaggi.py')
    radice = os.path.dirname(os.path.dirname(os.path.dirname(bpy.path.abspath(t.filepath))))
    return os.path.join(radice, 'packages', 'web', 'public', 'models', 'personaggi')

def coll():
    c = bpy.data.collections.get('Export_Personaggi')
    if c is None: c = bpy.data.collections.new('Export_Personaggi'); bpy.context.scene.collection.children.link(c)
    return c

def rig_copia(src, nome, c):
    r = src.copy(); r.data = src.data.copy(); r.name = r.data.name = nome
    c.objects.link(r); r.location = (0, 0, 0); r.rotation_euler = (0, 0, 0)
    r.animation_data_clear()
    return r

def unisci_skin(nome, pezzi, src, rig, c, tinta=None):
    # pezzi agganciati alle ossa di src -> una mesh nello spazio del rig, un gruppo di vertici per osso
    inv = src.matrix_world.inverted(); copie = []
    for o in pezzi:
        me = o.data.copy(); me.materials.clear()
        for sl in o.material_slots: me.materials.append(sl.material)
        me.transform(inv @ o.matrix_world)
        if me.uv_layers: me.uv_layers[0].name = 'UVMap'
        else: me.uv_layers.new(name='UVMap')
        x = bpy.data.objects.new('tmp', me); c.objects.link(x)
        g = x.vertex_groups.new(name=o.parent_bone); g.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
        if tinta:                                         # 1 sulle facce coi materiali da tingere
            a = me.color_attributes.new('Tinta', 'BYTE_COLOR', 'CORNER')
            for p in me.polygons:
                v = 1.0 if (me.materials[p.material_index] and me.materials[p.material_index].name in tinta) else 0.0
                for li in p.loop_indices: a.data[li].color = (v, v, v, 1)
        copie.append(x)
    for x in bpy.context.view_layer.objects: x.select_set(False)
    for x in copie: x.select_set(True)
    bpy.context.view_layer.objects.active = copie[0]; bpy.ops.object.join()
    ob = copie[0]; ob.name = ob.data.name = nome
    ob.parent = rig; ob.matrix_parent_inverse.identity(); ob.matrix_world = rig.matrix_world.copy()
    m = ob.modifiers.new('Rig', 'ARMATURE'); m.object = rig
    # atlante nuovo
    at = ob.data.uv_layers.new(name='Atlante'); ob.data.uv_layers.active = at
    for x in bpy.context.view_layer.objects: x.select_set(False)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, area_weight=0.0, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob

def prepara():
    c = coll()
    for o in list(c.objects):
        d = o.data; bpy.data.objects.remove(o, do_unlink=True)
        if d is not None and d.users == 0:
            (bpy.data.meshes if isinstance(d, bpy.types.Mesh) else bpy.data.armatures).remove(d)
    c.hide_viewport = False
    out = {}
    # omino: LOD0 e LOD1 sullo stesso rig (le ossa dei due rig sono identiche)
    r0, r1 = bpy.data.objects['OM0_Rig'], bpy.data.objects['OM1_Rig']
    rig = rig_copia(r0, 'X_Omino_Rig', c); rig.location = (0, 12, 0)
    for src, lod in ((r0, 0), (r1, 1)):
        pz = [o for o in src.children if o.type == 'MESH' and o.parent_type == 'BONE']
        ob = unisci_skin(f'X_Omino_LOD{lod}', pz, src, rig, c, tinta={'CB_P_Vestiti'})
        out[ob.name] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    for i, n in enumerate(PERSONAGGI):
        src = bpy.data.objects[f'PG_{n}_Rig']
        rig = rig_copia(src, f'X_{n}_Rig', c); rig.location = (2.0*(i + 1), 12, 0)
        pz = [o for o in src.children if o.type == 'MESH' and o.parent_type == 'BONE']
        ob = unisci_skin(f'X_{n}_LOD0', pz, src, rig, c)
        out[ob.name] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    return out

# ---------- clip ----------
def _chiave(rig, f, pose):
    for b, (asse, gradi) in pose.items():
        pb = rig.pose.bones[b]; pb.rotation_mode = 'XYZ'
        e = [0.0, 0.0, 0.0]; e['XYZ'.index(asse)] = math.radians(gradi); pb.rotation_euler = e
        pb.keyframe_insert('rotation_euler', frame=f)

def azioni():
    # le ossa hanno l'asse X locale verso -Y del mondo (il Busto verso +Y): una rotazione positiva
    # attorno a X porta il piede (o la mano) in avanti, verso +X
    rig = bpy.data.objects['X_Omino_Rig']; ad = rig.animation_data_create()
    for nome in ('Cammina', 'Seduto'):
        a = bpy.data.actions.get(nome)
        if a: bpy.data.actions.remove(a)
    TUTTE = ('Coscia_Sx', 'Coscia_Dx', 'Gamba_Sx', 'Gamba_Dx', 'Braccio_Sup_Sx', 'Braccio_Sup_Dx', 'Avambraccio_Sx', 'Avambraccio_Dx', 'Busto', 'Testa')
    # Cammina: 1 = destra avanti, 13 = sinistra avanti, 25 = come 1
    a = bpy.data.actions.new('Cammina'); a.use_fake_user = True; ad.action = a
    for f, s in ((1, 1), (7, 0), (13, -1), (19, 0), (25, 1)):
        pose = {b: ('X', 0.0) for b in TUTTE}
        pose.update({'Coscia_Dx': ('X', 24*s), 'Coscia_Sx': ('X', -24*s),
                     'Gamba_Dx': ('X', -6 if s > 0 else (-38 if s < 0 else -20)), 'Gamba_Sx': ('X', -6 if s < 0 else (-38 if s > 0 else -20)),
                     'Braccio_Sup_Dx': ('X', -20*s), 'Braccio_Sup_Sx': ('X', 20*s),
                     'Avambraccio_Dx': ('X', 12), 'Avambraccio_Sx': ('X', 12), 'Busto': ('X', 0.0)})
        _chiave(rig, f, pose)
        pr = rig.pose.bones['Root']; pr.location = (0, 0, 0.0 if s != 0 else 0.025); pr.keyframe_insert('location', frame=f)
    # Seduto: 1 = in piedi, 2 = seduto
    a = bpy.data.actions.new('Seduto'); a.use_fake_user = True; ad.action = a
    for f, k in ((1, 0.0), (2, 1.0)):
        pose = {b: ('X', 0.0) for b in TUTTE}
        pose.update({'Coscia_Dx': ('X', 88*k), 'Coscia_Sx': ('X', 88*k), 'Gamba_Dx': ('X', -88*k), 'Gamba_Sx': ('X', -88*k),
                     'Braccio_Sup_Dx': ('X', 25*k), 'Braccio_Sup_Sx': ('X', 25*k), 'Avambraccio_Dx': ('X', 30*k), 'Avambraccio_Sx': ('X', 30*k)})
        _chiave(rig, f, pose)
        pr = rig.pose.bones['Root']; pr.location = (0, 0, -0.33*k); pr.keyframe_insert('location', frame=f)
    ad.action = None
    for pb in rig.pose.bones: pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
    return [x.name for x in bpy.data.actions]

# ---------- bake ----------
def bake(nome):
    obs = [bpy.data.objects[f'X_{nome}_LOD0']] + ([bpy.data.objects['X_Omino_LOD1']] if nome == 'Omino' else [])
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = CAMPIONI
    sc.render.bake.margin = 4; sc.render.bake.use_clear = True; sc.render.bake.use_selected_to_active = False
    for ob in obs:
        n = ob.name[2:]; ris = RIS.get(n, 1024)
        im = bpy.data.images.new(f'{n}_colore', ris, ris); nodi = []
        me = ob.data; me.uv_layers.active = me.uv_layers['Atlante']; me.uv_layers['UVMap'].active_render = True
        for m in me.materials:
            nd = m.node_tree.nodes.new('ShaderNodeTexImage'); nd.image = im
            for x in m.node_tree.nodes: x.select = False
            nd.select = True; m.node_tree.nodes.active = nd; nodi.append((m, nd))
        ob.modifiers['Rig'].show_render = False
        for x in bpy.context.view_layer.objects: x.select_set(False)
        bpy.context.view_layer.objects.active = ob; ob.select_set(True)
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
        ob.modifiers['Rig'].show_render = True
        for m, nd in nodi: m.node_tree.nodes.remove(nd)
        im.pack()
        mat = bpy.data.materials.get(n) or bpy.data.materials.new(n); mat.use_nodes = True
        nt = mat.node_tree; nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial'); b = nt.nodes.new('ShaderNodeBsdfPrincipled')
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = im
        nt.links.new(t.outputs['Color'], b.inputs['Base Color']); nt.links.new(b.outputs[0], out.inputs['Surface'])
        b.inputs['Roughness'].default_value = 0.85
        me.materials.clear(); me.materials.append(mat)
        for p in me.polygons: p.material_index = 0; p.use_smooth = False
        me.uv_layers.remove(me.uv_layers['UVMap']); me.uv_layers['Atlante'].name = 'UVMap'
    return nome

# ---------- export ----------
def esporta(nome):
    rig = bpy.data.objects[f'X_{nome}_Rig']; obs = [rig] + [o for o in rig.children]
    vecchi = {o: o.name for o in obs}; loc = rig.location.copy(); rig.location = (0, 0, 0)
    rig.name = 'Rig'
    for o in obs[1:]: o.name = o.name[2:]
    ad = rig.animation_data_create(); ad.action = None
    for x in bpy.context.view_layer.objects: x.select_set(False)
    for o in obs: o.select_set(True)
    d = cartella(); os.makedirs(d, exist_ok=True); p = os.path.join(d, f'{nome.lower()}.glb')
    try:
        bpy.ops.export_scene.gltf(filepath=p, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
                                  export_skins=True, export_animations=True, export_animation_mode='ACTIONS',
                                  export_force_sampling=True, export_frame_step=1, export_def_bones=False,
                                  export_lights=False, export_cameras=False, export_attributes=True,
                                  export_vertex_color='ACTIVE', export_active_vertex_color_when_no_material=True,
                                  export_image_format='JPEG', export_jpeg_quality=88,
                                  export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
    finally:
        for o, n in vecchi.items(): o.name = n
        rig.location = loc
    return p, round(os.path.getsize(p)/1e6, 2)

def run():
    prepara(); azioni()
    out = {}
    for n in ('Omino',) + PERSONAGGI: bake(n); out[n] = esporta(n)
    coll().hide_viewport = True
    return out

if __name__ == '__main__':
    print(run())
