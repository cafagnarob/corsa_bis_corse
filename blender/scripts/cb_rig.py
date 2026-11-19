# =====================================================================
# cb_rig.py — Corsa Bis · parti comuni dei rig dei mezzi
# Cosa fa: funzioni per riggare un mezzo di cartone finito, uguali per
#   tutti i mezzi:
#   - copia il mezzo finito del tutorial in una collection a parte
#     (i pezzi da muovere separatamente possono essere ricostruiti divisi)
#   - crea l'armatura con Root, Telaio, ruote, sterzo e porte
#   - comandi animabili sull'oggetto armatura:
#       percorso_m    metri percorsi: tutte le ruote girano di conseguenza
#       sterzo_gradi  sterzata delle ruote anteriori (+ = sinistra)
#   - porte: un osso verticale sulla cerniera, rotazione Y con limiti
#     (0 = chiusa, il segno giusto per aprirsi verso l'esterno è già impostato)
#   - collezioni di ossa: "Comandi" visibile, "Meccanica" nascosta
# Come: pezzi rigidi imparentati alle ossa (parent Bone), senza pesi.
#   Le ruote sono guidate da driver (angolo = percorso / raggio).
# Il file del mezzo (es. cb_rig_bus12.py) dice dove stanno assi e porte
#   e aggiunge le sue parti speciali (gru, snodo...).
# =====================================================================
import bpy, math
from mathutils import Vector, Matrix

def rig_reset(nome):
    c = bpy.data.collections.get(nome)
    if c:
        for o in list(c.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0:
                if isinstance(d, bpy.types.Armature): bpy.data.armatures.remove(d)
                elif isinstance(d, bpy.types.Mesh): bpy.data.meshes.remove(d)
                else: bpy.data.curves.remove(d)
        bpy.data.collections.remove(c)
    c = bpy.data.collections.new(nome); bpy.context.scene.collection.children.link(c)
    return c

def copia_finito(src, pref, coll, loc, salta=()):
    # copia i pezzi del mezzo finito (mesh e scritte), tranne quelli in "salta"
    out = []; fs = 'F' + src.name.split('_')[1] + '_'
    for o in src.objects:
        if not o.name.startswith(fs) or o.type not in ('MESH', 'FONT'): continue
        nome = o.name[len(fs):]
        if nome in salta: continue
        n = o.copy(); n.data = o.data.copy(); n.name = pref + nome
        n.matrix_world = Matrix.Translation(Vector(loc) - _origine(src)) @ o.matrix_world   # stessa posa, spostata in loc
        coll.objects.link(n); out.append((n, nome))
    return out

def _origine(src):
    # posizione del mezzo finito nella scena (tutti i pezzi hanno la stessa location)
    for o in src.objects:
        if o.type == 'MESH' and o.name.startswith('F'): return o.location.copy()
    return Vector()

def ricostruisci(pc, nomi, MAT, cfg, coll, loc, pref):
    # crea un oggetto per ogni parte di un pezzo (es. le due ante di una porta)
    out = []
    for i, (pd, nome) in enumerate(zip(pc['parts'], nomi)):
        ob = make_object(pref + nome, [(geo_of(pc, i, pd), pd['M'])], piece_mats(pc, cfg['final_stage'], MAT, cfg), coll, loc)
        out.append((ob, nome))
    return out

# ---------- armatura ----------
def armatura_inizio(nome, coll, loc):
    arm_d = bpy.data.armatures.new(nome); arm_d.display_type = 'STICK'
    arm = bpy.data.objects.new(nome, arm_d); arm.location = loc; arm.show_in_front = True
    coll.objects.link(arm)
    if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    vl = bpy.context.view_layer; vl.update()
    for o in list(vl.objects):
        if o is not None: o.select_set(False)
    vl.objects.active = arm; arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    return arm

def osso(arm, name, head, tail, parent=None, roll_up=None):
    eb = arm.data.edit_bones; b = eb.new(name); b.head = Vector(head); b.tail = Vector(tail)
    if parent: b.parent = eb[parent]
    if roll_up is not None: b.align_roll(Vector(roll_up))
    return b

def ossa_base(arm, lunghezza, za):
    osso(arm, 'Root', (0, 0, 0), (lunghezza*0.2, 0, 0), roll_up=(0, 0, 1))
    osso(arm, 'Telaio', (0, 0, za), (0, 0, za + 0.8), 'Root')

def ossa_ruote(arm, assi, y, za, parent='Telaio'):
    # assi: lista di (x, nome, sterzante); ossa Ruota_<nome>_Dx/Sx (+ Sterzo_<nome>_Dx/Sx)
    for cx, nx, sterza in assi:
        for s, nm in ((-1, 'Dx'), (1, 'Sx')):
            c = Vector((cx, s*y, za)); par = parent
            if sterza:
                par = f'Sterzo_{nx}_{nm}'
                osso(arm, par, c, c + Vector((0, 0, 0.6)), parent, roll_up=(1, 0, 0))
            osso(arm, f'Ruota_{nx}_{nm}', c, c + Vector((0, 0.5, 0)), par, roll_up=(0, 0, 1))

def osso_porta(arm, nome, x, y, z0, z1, parent='Telaio'):
    osso(arm, nome, (x, y, z0), (x, y, z1), parent, roll_up=(1, 0, 0))

def armatura_fine(arm, assi, raggio, porte, comandi_extra=()):
    # porte: lista di (nome, segno): segno +1 se si apre con angoli positivi, -1 se negativi
    bpy.ops.object.mode_set(mode='POSE')
    pb = arm.pose.bones
    for b in pb: b.rotation_mode = 'XYZ'
    for k, v, lo, hi, desc in (('percorso_m', 0.0, -10000.0, 10000.0, 'Metri percorsi: fanno girare le ruote'),
                               ('sterzo_gradi', 0.0, -35.0, 35.0, 'Sterzata delle ruote anteriori (+ = sinistra)')):
        arm[k] = v; arm.id_properties_ui(k).update(min=lo, max=hi, description=desc)
    def driver(bone, expr, var, prop):
        fc = pb[bone].driver_add('rotation_euler', 1); dr = fc.driver; dr.type = 'SCRIPTED'
        vv = dr.variables.new(); vv.name = var; vv.type = 'SINGLE_PROP'
        vv.targets[0].id_type = 'OBJECT'; vv.targets[0].id = arm; vv.targets[0].data_path = f'["{prop}"]'
        dr.expression = expr
    for cx, nx, sterza in assi:
        for nm in ('Dx', 'Sx'):
            driver(f'Ruota_{nx}_{nm}', f'd/{raggio}', 'd', 'percorso_m'); pb[f'Ruota_{nx}_{nm}'].lock_rotation = (True, True, True)
            if sterza:
                driver(f'Sterzo_{nx}_{nm}', 'radians(s)', 's', 'sterzo_gradi'); pb[f'Sterzo_{nx}_{nm}'].lock_rotation = (True, True, True)
    for nome, segno in porte:
        c = pb[nome].constraints.new('LIMIT_ROTATION'); c.owner_space = 'LOCAL'; c.use_limit_y = True
        c.min_y, c.max_y = (0.0, math.radians(85)) if segno > 0 else (math.radians(-85), 0.0)
        pb[nome].lock_rotation = (True, False, True); pb[nome].lock_location = (True, True, True)
    ctrl = arm.data.collections.new('Comandi'); mecc = arm.data.collections.new('Meccanica')
    visibili = {'Root'} | {n for n, _ in porte} | set(comandi_extra)
    for b in arm.data.bones: (ctrl if b.name in visibili else mecc).assign(b)
    mecc.is_visible = False
    bpy.ops.object.mode_set(mode='OBJECT')
    return pb

def imparenta(arm, pezzi):
    # pezzi: lista di (oggetto, nome osso)
    bpy.context.view_layer.update()
    for ob, bone in pezzi:
        mw = ob.matrix_world.copy()
        ob.parent = arm; ob.parent_type = 'BONE'; ob.parent_bone = bone
        bpy.context.view_layer.update()
        ob.matrix_world = mw

def riposo(arm):
    for b in arm.pose.bones:
        b.location = (0, 0, 0); b.rotation_euler = (0, 0, 0); b.scale = (1, 1, 1)
    for k in ('sterzo_gradi', 'percorso_m', 'snodo_gradi'):
        if k in arm: arm[k] = 0.0
    bpy.context.view_layer.update()
