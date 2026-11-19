# =====================================================================
# cb_export.py — Corsa Bis · export dei mezzi in .glb (seconda versione)
# Cosa fa: con il .blend del mezzo aperto (tutorial, rig e LOD già
#   costruiti) scrive packages/web/public/models/mezzi/<mezzo>.glb:
#   - "<mezzo>"  empty radice, davanti verso +X, metri reali (×5,2 nel codice)
#   - "Rig"      armatura del rig (ossa con i nomi del rig del mezzo)
#   - "LOD0" "LOD1" "LOD2"  UNA mesh ciascuno, con pelle (skin) rigida sul Rig:
#                ogni vertice segue al 100% l'osso del suo pezzo (ruote,
#                sterzo, porte). Una mesh e un materiale = una chiamata di disegno.
#                LOD1 e LOD2: ruote e porta anteriore sulle loro ossa; la
#                porta centrale resta ferma (le due ante sono un pezzo solo).
#   - "LOD3" "LOD4" "LOD5"  mesh rigide, figlie della radice
#   - animazioni come slider: Ruota (1-25 = un giro), Sterzo (1 = −35°,
#     2 = 0°, 3 = +35°), Porte (1 = chiuse, 11 = aperte)
#   - carro attrezzi: slider Gru (1 = braccio giù −10°, 6 = riposo,
#     11 = su +10°) e Gancio (1 = alto, ~3,9 = riposo, 11 = basso, +0,75 m);
#     pistone e cavi seguono da soli (STRETCH_TO campionato nell'export)
#   - ogni clip contiene SOLO le ossa che muove (pulisci_animazioni):
#     così nel gioco Ruota, Sterzo, Porte, Gru... si sommano senza
#     annullarsi a vicenda
#   - tram: ogni LOD ha già il suo rig (L1_Rig ... L5_Rig, stesse ossa del
#     TR_Rig): i pezzi vanno sull'osso col loro nome, soffietti e pedane
#     tengono i pesi che hanno. Slider Curva (1 = −20°, 2 = dritto,
#     3 = +20°: piega i due snodi in versi opposti e gira i carrelli di
#     testa e di coda di metà angolo), Lira (1 = abbassata, 11 = alzata
#     +40°), Porte (20 ante), Ruota (12 ruote). Tutti i LOD skinned.
#   - mezzi snodati (bus18): osso Snodo e slider Snodo (1 = −40°, 2 = 0°,
#     3 = +40°; positivo = coda verso destra, −Y: il bus curva a sinistra). TUTTI i LOD sono skinned:
#     davanti sul Telaio, dietro sullo Snodo, il soffietto (e ciò che lo
#     attraversa: fasce, pedana, il gettone del LOD5) sfuma tra i due
#     ossi nella fascia dello snodo; le mesh vengono tagliate ai bordi
#     della fascia, così nessuna faccia lunga si deforma.
# Materiali: per ogni LOD il cartone procedurale viene "cotto" (bake) in
#   un'immagine sola su un atlante UV nuovo:
#   - colore (bake Diffuse, solo colore, senza luci: le luci le fa il gioco)
#   - emissione (bake Emit) solo se il LOD ha fari/fanali: immagine
#     emissiva + intensità (KHR_materials_emissive_strength)
#   Un solo materiale per LOD ("<mezzo>_LOD<n>"), normali piatte.
#   Risoluzione per LOD: 2048, 1024, 512, 256, 128, 128 (immagini nel .glb
#   in JPEG). Compressione delle mesh: Draco.
# Uso: Run Script (fa tutto) oppure, passo per passo dalla console:
#   prepara(); bake(0) ... bake(5); esporta()
# =====================================================================
import bpy, math, os, bmesh
from mathutils import Vector, Matrix

CONFIG = {
    'bus12': dict(rig='B12_Rig', rig_coll='Bus12_Rig', lod='Bus12_LOD_', raggio=0.50,
                  ruote=('Ruota_Ant_Dx', 'Ruota_Ant_Sx', 'Ruota_Post_Dx', 'Ruota_Post_Sx'),
                  sterzo=('Sterzo_Ant_Dx', 'Sterzo_Ant_Sx'),
                  porte=(('Porta_Ant', 1), ('Porta_Cen_A', -1), ('Porta_Cen_B', 1)),
                  ossa_lod={'Porta_Anteriore': 'Porta_Ant'}),
    'minibus': dict(rig='MB_Rig', rig_coll='Minibus_Rig', lod='Minibus_LOD_', raggio=0.50,
                  ruote=('Ruota_Ant_Dx', 'Ruota_Ant_Sx', 'Ruota_Post_Dx', 'Ruota_Post_Sx'),
                  sterzo=('Sterzo_Ant_Dx', 'Sterzo_Ant_Sx'),
                  porte=(('Porta_Dx', 1), ('Porta_Sx', -1)),          # due porte a battente, una per lato
                  ossa_lod={'Porta_Dx': 'Porta_Dx', 'Porta_Sx': 'Porta_Sx'}),
    'carro': dict(rig='CA_Rig', rig_coll='CarroAttrezzi_Rig', lod='LOD', raggio=0.50,
                  ruote=('Ruota_Ant_Dx', 'Ruota_Ant_Sx', 'Ruota_Post_Dx', 'Ruota_Post_Sx'),
                  sterzo=('Sterzo_Dx', 'Sterzo_Sx'),
                  porte=(('Porta_Dx', 1), ('Porta_Sx', -1)),
                  ossa_lod={'Porta_Dx': 'Porta_Dx', 'Porta_Sx': 'Porta_Sx'},   # nei LOD1-2 la gru è ferma (pezzi uniti)
                  extra=[('Gru', 'Braccio', 'rotation_euler', 0, [(1, math.radians(-10)), (11, math.radians(10))]),
                         ('Gancio', 'CTRL_Gancio', 'location', 1, [(1, -0.30), (11, 0.75)])]),
    'utilitaria': dict(rig='UT_Rig', rig_coll='Utilitaria_Rig', lod='Utilitaria_LOD_', raggio=0.30,
                  ruote=('Ruota_Ant_Dx', 'Ruota_Ant_Sx', 'Ruota_Post_Dx', 'Ruota_Post_Sx'),
                  sterzo=('Sterzo_Ant_Dx', 'Sterzo_Ant_Sx'),
                  porte=(('Porta_Ant_Dx', 1), ('Porta_Ant_Sx', -1), ('Porta_Post_Dx', 1), ('Porta_Post_Sx', -1)),
                  ossa_lod={n: n for n in ('Porta_Ant_Dx', 'Porta_Ant_Sx', 'Porta_Post_Dx', 'Porta_Post_Sx')}),
    'tram': dict(rig='TR_Rig', rig_coll='Tram_Rig', lod='Tram_LOD_', raggio=0.33, rig_lod='L{}_Rig',
                  ruote=tuple(f'Ruota_{c}{n}_{l}' for c in 'ABC' for n in '12' for l in ('Dx', 'Sx')),
                  sterzo=(), porte='auto', ossa_lod={},
                  azioni_y=[('Curva', {'Snodo_A': [(1, -20), (2, 0), (3, 20)], 'Snodo_C': [(1, 20), (2, 0), (3, -20)],
                                       'Carrello_A': [(1, 10), (2, 0), (3, -10)], 'Carrello_C': [(1, -10), (2, 0), (3, 10)]}),
                            ('Lira', {'Lira_1': [(1, 0), (11, 40)], 'Lira_2': [(1, 0), (11, 40)]})]),
    'bus18': dict(rig='B18_Rig', rig_coll='Bus18_Rig', lod='Bus18_LOD_', raggio=0.50,
                  ruote=('Ruota_Ant_Dx', 'Ruota_Ant_Sx', 'Ruota_Cen_Dx', 'Ruota_Cen_Sx', 'Ruota_Post_Dx', 'Ruota_Post_Sx'),
                  sterzo=('Sterzo_Ant_Dx', 'Sterzo_Ant_Sx'),
                  porte=(('Porta_Ant', 1), ('Porta_Cen_A', -1), ('Porta_Cen_B', 1), ('Porta_Post_A', -1), ('Porta_Post_B', 1)),
                  ossa_lod={'Porta_Anteriore': 'Porta_Ant', 'Porta_Centrale': 'Telaio', 'Porta_Posteriore': 'Snodo', 'Ralla': 'Telaio'},
                  snodo='Snodo', snodo_x=-2.05, snodo_fascia=0.35, snodo_max=40.0),
}
MEZZO = 'bus18'
RISOLUZIONE = {0: 2048, 1: 1024, 2: 512, 3: 256, 4: 128, 5: 128}
INTENSITA_LUCI = 2.0                 # emissive strength nel .glb (da ricalibrare in gioco)
CAMPIONI = 16                        # campioni Cycles del bake (servono all'occlusione del kraft)

def cartella_glb():
    t = bpy.data.texts.get('cb_export.py')
    sorgente = bpy.path.abspath(t.filepath) if t and t.filepath else bpy.data.filepath
    radice = os.path.dirname(os.path.dirname(os.path.dirname(sorgente)))     # .../blender/scripts -> radice repo
    return os.path.join(radice, 'packages', 'web', 'public', 'models', 'mezzi')

# ---------- unione con i gruppi di vertici (pelle rigida) ----------
def unisci(pezzi, nome, origine, coll, C=None):
    # pezzi: lista di (oggetto, osso o None o 'X'). 'X' = il pezzo sfuma tra Telaio e Snodo
    # secondo la X del vertice (solo mezzi snodati). Tiene i materiali originali (servono al bake)
    dg = bpy.context.evaluated_depsgraph_get()
    V, F, MI, UV, VG, slots = [], [], [], [], [], []
    for o, osso in pezzi:
        if o.type == 'FONT': me = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); tmp = True
        elif o.type == 'MESH': me = o.data; tmp = False
        else: continue
        M = Matrix.Translation(-origine) @ o.matrix_world; b0 = len(V)
        V += [tuple(M @ v.co) for v in me.vertices]
        if osso == 'VG':                                    # pezzo già pesato (soffietti del tram): tengo i suoi pesi
            nomi_g = {g.index: g.name for g in o.vertex_groups}
            VG += [{nomi_g[g.group]: g.weight for g in v.groups if g.weight > 0} for v in me.vertices]
        else: VG += [osso]*len(me.vertices)
        uvl = me.uv_layers.active
        mats = [s.material for s in o.material_slots] if o.material_slots else list(me.materials)
        for p in me.polygons:
            m = mats[p.material_index] if mats else None
            if m not in slots: slots.append(m)
            F.append([b0 + i for i in p.vertices]); MI.append(slots.index(m))
            UV.append([tuple(uvl.data[li].uv) if uvl else (0, 0) for li in p.loop_indices])
        if tmp: bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(nome); me.from_pydata(V, [], F)
    uvl = me.uv_layers.new(name='UVMap')
    for p, mi, uu in zip(me.polygons, MI, UV):
        p.material_index = mi; p.use_smooth = False
        for k, li in enumerate(p.loop_indices): uvl.data[li].uv = uu[k]
    for m in slots: me.materials.append(m)
    me.update(); ob = bpy.data.objects.new(nome, me); coll.objects.link(ob)
    if C and C.get('snodo'):
        _pesi_snodo(ob, VG, C)
        return ob
    gruppi = {}
    def gruppo(n):
        if n not in gruppi: gruppi[n] = ob.vertex_groups.new(name=n)
        return gruppi[n]
    for i, osso in enumerate(VG):
        if osso is None: continue
        if isinstance(osso, dict):
            for n, w in osso.items(): gruppo(n).add([i], w, 'REPLACE')
        else: gruppo(osso).add([i], 1.0, 'REPLACE')
    return ob

def _pesi_snodo(ob, VG, C):
    # 1) etichetta per vertice (indice dell'osso, −1 = sfumato) in un attributo intero,
    # 2) taglio della mesh ai due bordi della fascia (l'attributo e le UV si interpolano),
    # 3) gruppi: osso fisso al 100% oppure Telaio/Snodo secondo X
    nomi = sorted({o for o in VG if o not in (None, 'X')} | {'Telaio', C['snodo']})
    me = ob.data; at = me.attributes.new('osso_i', 'INT', 'POINT')
    at.data.foreach_set('value', [-1 if o == 'X' else (-2 if o is None else nomi.index(o)) for o in VG])
    x0, b = C['snodo_x'], C['snodo_fascia']
    bm = bmesh.new(); bm.from_mesh(me)
    for xp in (x0 - b, x0 + b):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(xp, 0, 0), plane_no=(1, 0, 0))
    bm.to_mesh(me); bm.free(); me.update()
    gr = {n: ob.vertex_groups.new(name=n) for n in nomi}
    et = [0]*len(me.vertices); me.attributes['osso_i'].data.foreach_get('value', et)
    for v, e in zip(me.vertices, et):
        if e >= 0: gr[nomi[e]].add([v.index], 1.0, 'REPLACE'); continue
        if e == -2: e = -1                                  # senza osso: segue la carrozzeria
        w = min(1.0, max(0.0, (x0 + b - v.co.x)/(2*b)))     # 0 davanti alla fascia, 1 dietro
        if w < 1: gr['Telaio'].add([v.index], 1 - w, 'REPLACE')
        if w > 0: gr[C['snodo']].add([v.index], w, 'REPLACE')
    me.attributes.remove(me.attributes['osso_i'])

# ---------- atlante UV ----------
def atlante(ob):
    me = ob.data
    at = me.uv_layers.new(name='Atlante'); me.uv_layers.active = at
    me.uv_layers['UVMap'].active_render = True          # i materiali procedurali leggono ancora le UV vecchie
    for o in bpy.context.view_layer.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, area_weight=0.0, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')

# ---------- bake ----------
def _nodi_bersaglio(ob, img):
    nodi = []
    for m in ob.data.materials:
        if m is None or not m.use_nodes: continue
        n = m.node_tree.nodes.new('ShaderNodeTexImage'); n.image = img; n.name = '_bake'
        for x in m.node_tree.nodes: x.select = False
        n.select = True; m.node_tree.nodes.active = n; nodi.append((m, n))
    return nodi

def _luci(ob):
    return [m for m in ob.data.materials if m and m.name.startswith('CB_Luce')]

def bake(L, mezzo=MEZZO):
    ob = bpy.data.objects[f'{mezzo}_LOD{L}_tmp']; r = RISOLUZIONE[L]
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = CAMPIONI
    sc.render.bake.margin = max(2, r//256); sc.render.bake.use_clear = True
    for o in bpy.context.view_layer.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    col = bpy.data.images.new(f'{mezzo}_LOD{L}_colore', r, r); col.colorspace_settings.name = 'sRGB'
    nodi = _nodi_bersaglio(ob, col)
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
    for m, n in nodi: m.node_tree.nodes.remove(n)
    emi = None
    luci = _luci(ob)
    if luci:
        vecchie = {}
        for m in luci:                                        # intensità 1 durante il bake: l'immagine resta in 0..1
            b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            s = b.inputs['Emission Strength']
            vecchie[m.name] = [l.from_socket for l in s.links]
            for l in list(s.links): m.node_tree.links.remove(l)
            s.default_value = 1.0
        emi = bpy.data.images.new(f'{mezzo}_LOD{L}_emissione', r//2, r//2)
        nodi = _nodi_bersaglio(ob, emi)
        bpy.ops.object.bake(type='EMIT')
        for m, n in nodi: m.node_tree.nodes.remove(n)
        for m in luci:                                        # rimetto i collegamenti originali
            b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            for fs in vecchie[m.name]: m.node_tree.links.new(fs, b.inputs['Emission Strength'])
    _materiale_finale(ob, mezzo, L, col, emi)
    return ob

def _materiale_finale(ob, mezzo, L, col, emi):
    m = bpy.data.materials.get(f'{mezzo}_LOD{L}') or bpy.data.materials.new(f'{mezzo}_LOD{L}')
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(b.outputs[0], out.inputs['Surface'])
    tc = nt.nodes.new('ShaderNodeTexImage'); tc.image = col; tc.interpolation = 'Linear'
    nt.links.new(tc.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.85
    if emi:
        te = nt.nodes.new('ShaderNodeTexImage'); te.image = emi
        nt.links.new(te.outputs['Color'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = INTENSITA_LUCI
    me = ob.data
    me.materials.clear(); me.materials.append(m)
    for p in me.polygons: p.material_index = 0
    me.uv_layers.remove(me.uv_layers['UVMap']); me.uv_layers['Atlante'].name = 'UVMap'
    me.uv_layers['UVMap'].active = True; me.uv_layers['UVMap'].active_render = True

# ---------- preparazione ----------
def _osso_pezzo(nome, C, o=None):
    for k in C['ruote']:
        lato = k.split('_', 1)[1]
        if nome in ('Ruota_' + lato, 'Coprimozzo_' + lato): return k
    if nome in C['ossa_lod']: return C['ossa_lod'][nome]
    if C.get('snodo') and o is not None:                    # snodato: davanti, dietro o a cavallo dello snodo
        xs = [v.co.x for v in o.data.vertices] if o.type == 'MESH' else [o.location.x]
        if max(xs) < C['snodo_x']: return C['snodo']
        if min(xs) > C['snodo_x']: return 'Telaio'
        return 'X'
    return 'Telaio'

def prepara(mezzo=MEZZO):
    C = CONFIG[mezzo]
    if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    for nome in ('Export_' + mezzo,):
        c = bpy.data.collections.get(nome)
        if c:
            for o in list(c.objects):
                d = o.data; bpy.data.objects.remove(o, do_unlink=True)
                if d is not None and d.users == 0:
                    (bpy.data.armatures if isinstance(d, bpy.types.Armature) else bpy.data.meshes).remove(d)
            bpy.data.collections.remove(c)
    for a in [a for a in bpy.data.actions if a.name.split('.')[0] in ('Ruota', 'Sterzo', 'Porte', 'Snodo', 'Gru', 'Gancio', 'Curva', 'Lira')]: bpy.data.actions.remove(a)
    for im in [i for i in bpy.data.images if i.name.startswith(mezzo + '_LOD')]: bpy.data.images.remove(im)
    coll = bpy.data.collections.new('Export_' + mezzo); bpy.context.scene.collection.children.link(coll)
    radice = bpy.data.objects.new(mezzo, None); coll.objects.link(radice)
    rig = bpy.data.objects[C['rig']]; org = rig.location.copy()
    arm = rig.copy(); arm.data = rig.data.copy(); arm.name = 'Rig'; arm.data.name = mezzo + '_Rig'; arm.animation_data_clear()
    for k in ('percorso_m', 'sterzo_gradi', 'snodo_gradi', 'curva_gradi'):
        if k in arm: del arm[k]
    for bc in arm.data.collections: bc.is_visible = True
    arm.location = (0, 0, 0); coll.objects.link(arm); arm.parent = radice
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
        for c in list(pb.constraints):
            if c.type.startswith('LIMIT'): pb.constraints.remove(c)   # i limiti non servono nel .glb
            elif getattr(c, 'target', None) == rig: c.target = arm   # STRETCH_TO (gru): resta, sul rig copiato
    bpy.context.view_layer.update()
    # LOD0: pezzi del rig, ognuno sul suo osso
    # pezzi senza osso ma con i gruppi Telaio/Snodo (soffietto, pedana) sfumano: 'X'
    pezzi = [(o, o.parent_bone or (('X' if C.get('snodo') else 'VG') if o.vertex_groups else 'Telaio'))
             for o in bpy.data.collections[C['rig_coll']].objects if o.type in ('MESH', 'FONT') and o.parent == rig]
    lods = {0: unisci(pezzi, f'{mezzo}_LOD0_tmp', org, coll, C)}
    # LOD1-5 dalla fila dei LOD
    for L in range(1, 6):
        lc = bpy.data.collections[C['lod'] + str(L)]
        if C.get('rig_lod'):                                # tram: i pezzi sono figli del rig del LOD
            rl = bpy.data.objects[C['rig_lod'].format(L)]
            objs = [o for o in lc.all_objects if o.parent == rl and o.type in ('MESH', 'FONT')]
            pezzi = [(o, o.parent_bone or ('VG' if o.vertex_groups else 'Telaio')) for o in objs]
            lods[L] = unisci(pezzi, f'{mezzo}_LOD{L}_tmp', rl.location.copy(), coll, C)
            continue
        objs = [o for o in lc.all_objects if o.type in ('MESH', 'FONT') and not o.name.startswith(('Cartellino', 'Etichetta'))]
        ref = next(o for o in objs if o.type == 'MESH')
        orgL = Vector((round(ref.matrix_world.translation.x, 3), round(ref.matrix_world.translation.y, 3), 0.0))
        if L <= 2: pezzi = [(o, _osso_pezzo(o.name.split('_', 1)[1] if o.name.startswith(f'L{L}_') else '', C, o)) for o in objs]
        else: pezzi = [(o, 'X' if C.get('snodo') else None) for o in objs]
        lods[L] = unisci(pezzi, f'{mezzo}_LOD{L}_tmp', orgL, coll, C)
    for L, ob in lods.items(): atlante(ob)
    return lods

# ---------- export ----------
def _fcurve(act):
    if hasattr(act, 'fcurves'): return list(act.fcurves)
    return [fc for ly in act.layers for st in ly.strips for cb in st.channelbags for fc in cb.fcurves]

def _azione(arm, nome, chiavi):
    act = bpy.data.actions.new(nome); arm.animation_data.action = act
    if hasattr(arm.animation_data, 'action_slot') and arm.animation_data.action_slot is None and act.slots:
        arm.animation_data.action_slot = act.slots[0]
    for osso, kk in chiavi.items():
        pb = arm.pose.bones[osso]
        for f, a in kk:
            pb.rotation_euler = (0, a, 0); pb.keyframe_insert('rotation_euler', frame=f, group=osso)
    for fc in _fcurve(act):
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    tr = arm.animation_data.nla_tracks.new(); tr.name = nome
    tr.strips.new(nome, int(act.frame_range[0]), act); arm.animation_data.action = None
    for pb in arm.pose.bones: pb.rotation_euler = (0, 0, 0)

def _azione_libera(arm, nome, osso, attr, indice, chiavi):
    # una clip su un solo canale (es. rotation_euler[0] del Braccio, location[1] del gancio)
    act = bpy.data.actions.new(nome); arm.animation_data.action = act
    if hasattr(arm.animation_data, 'action_slot') and arm.animation_data.action_slot is None and act.slots:
        arm.animation_data.action_slot = act.slots[0]
    pb = arm.pose.bones[osso]
    for f, v in chiavi:
        getattr(pb, attr)[indice] = v; pb.keyframe_insert(attr, index=indice, frame=f, group=osso)
    for fc in _fcurve(act):
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    tr = arm.animation_data.nla_tracks.new(); tr.name = nome
    tr.strips.new(nome, int(act.frame_range[0]), act); arm.animation_data.action = None
    pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)

def pulisci_animazioni(path, tolleranza=1e-5):
    # Toglie dal .glb i canali costanti: con il campionamento l'export mette in ogni clip
    # TUTTE le ossa (ferme). Nel mixer di three due clip sulla stessa osso si mediano,
    # quindi Ruota + Sterzo insieme darebbero mezze rotazioni. Dopo: ogni clip tocca solo
    # le ossa che muove davvero (incluse quelle mosse dai vincoli, es. pistone e cavi).
    import json, struct
    with open(path, 'rb') as f: b = f.read()
    lj = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + lj]); resto = b[20 + lj:]
    lb = struct.unpack('<I', resto[0:4])[0]; binario = resto[8:8 + lb]
    comp = {5126: ('f', 4)}; ncomp = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}
    def valori(ia):
        a = j['accessors'][ia]; bv = j['bufferViews'][a['bufferView']]
        fmt, sz = comp[a['componentType']]; n = ncomp[a['type']]
        st = bv.get('byteStride', sz*n); o0 = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        return [struct.unpack_from('<' + fmt*n, binario, o0 + k*st) for k in range(a['count'])]
    tolti = 0
    for an in j.get('animations', []):
        tieni = []
        for ch in an['channels']:
            v = valori(an['samplers'][ch['sampler']]['output'])
            if any(abs(x - y) > tolleranza for row in v for x, y in zip(row, v[0])): tieni.append(ch)
            else: tolti += 1
        usati = sorted({c['sampler'] for c in tieni}); nuovo = {s: i for i, s in enumerate(usati)}
        an['samplers'] = [an['samplers'][s] for s in usati]
        for c in tieni: c['sampler'] = nuovo[c['sampler']]
        an['channels'] = tieni
    js = json.dumps(j, separators=(',', ':')).encode('utf-8'); js += b' '*((4 - len(js) % 4) % 4)
    out = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + len(resto)) + struct.pack('<II', len(js), 0x4E4F534A) + js + resto
    with open(path, 'wb') as f: f.write(out)
    return tolti, {a['name']: sorted({j['nodes'][c['target']['node']]['name'] for c in a['channels']}) for a in j.get('animations', [])}

def _porte(C):
    # 'auto': tutte le ossa Porta_* del rig originale, verso preso dal loro limite di rotazione
    if C['porte'] != 'auto': return C['porte']
    out = []
    for pb in bpy.data.objects[C['rig']].pose.bones:
        if not pb.name.startswith('Porta'): continue
        lim = next((c for c in pb.constraints if c.type == 'LIMIT_ROTATION'), None)
        out.append((pb.name, 1 if lim is None or lim.max_y > 0 else -1))
    return out

def esporta(mezzo=MEZZO):
    C = CONFIG[mezzo]; coll = bpy.data.collections['Export_' + mezzo]
    radice = bpy.data.objects[mezzo]; arm = bpy.data.objects['Rig']
    for L in range(6):
        ob = bpy.data.objects[f'{mezzo}_LOD{L}_tmp']; ob.name = f'LOD{L}'; ob.data.name = f'{mezzo}_LOD{L}'
        if L <= 2 or C.get('snodo') or C.get('rig_lod'):
            ob.parent = arm; m = ob.modifiers.new('Rig', 'ARMATURE'); m.object = arm
        else:
            ob.parent = radice
    arm.animation_data_create()
    _azione(arm, 'Ruota', {r: [(1, 0.0), (25, 2*math.pi)] for r in C['ruote']})
    if C['sterzo']: _azione(arm, 'Sterzo', {s: [(1, math.radians(-35)), (2, 0.0), (3, math.radians(35))] for s in C['sterzo']})
    _azione(arm, 'Porte', {p: [(1, 0.0), (11, s*math.radians(85))] for p, s in _porte(C)})
    for nome, chiavi in C.get('azioni_y', []):
        _azione(arm, nome, {o: [(f, math.radians(g)) for f, g in kk] for o, kk in chiavi.items()})
    for nome, osso, attr, i, kk in C.get('extra', []): _azione_libera(arm, nome, osso, attr, i, kk)
    if C.get('snodo'):
        a = math.radians(C['snodo_max'])
        _azione(arm, 'Snodo', {C['snodo']: [(1, -a), (2, 0.0), (3, a)]})
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in coll.objects: o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    cartella = cartella_glb(); os.makedirs(cartella, exist_ok=True)
    path = os.path.join(cartella, mezzo + '.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
                              export_apply=True, export_animations=True, export_animation_mode='ACTIONS',
                              export_force_sampling=True, export_skins=True, export_lights=False, export_cameras=False,
                              export_image_format='JPEG', export_jpeg_quality=85,
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
    pulisci_animazioni(path)
    coll.hide_viewport = True
    tri = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in coll.objects if o.type == 'MESH'}
    return path, os.path.getsize(path), tri

def run(mezzo=MEZZO):
    prepara(mezzo)
    for L in range(6): bake(L, mezzo)
    return esporta(mezzo)

if __name__ == '__main__':
    print(run())
