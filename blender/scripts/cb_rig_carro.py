# =====================================================================
# cb_rig_carro.py — Corsa Bis · Rig del carro attrezzi
# Cosa fa: copia il carro attrezzi finito (fase 9 del tutorial) in una
#   collection a parte e lo collega a un'armatura pronta da animare.
#   Comandi (proprietà dell'oggetto "CA_Rig", animabili con I sul campo):
#     percorso_m    metri percorsi: tutte le ruote girano di conseguenza
#     sterzo_gradi  sterzata delle ruote anteriori (+ = sinistra)
#   Ossa da animare a mano (Pose Mode):
#     Root          sposta/ruota tutto il mezzo
#     Braccio       alza (+) e abbassa (-) la gru (rotazione X, da -10° a +10°)
#     CTRL_Gancio   cala (+Y) o solleva (-Y) il gancio, da -0,3 a +0,75 m
#     Porta_Dx/Sx   apre le portiere (rotazione Y, con limiti)
#   Meccanica automatica (collection di ossa nascosta): pistone e cavi di
#   spago si allungano da soli (Stretch To), il gancio resta sempre in verticale.
# Come: i pezzi rigidi sono imparentati alle ossa (parent Bone), senza pesi:
#   è il metodo giusto per un modellino di cartone fatto di parti rigide.
#   Cavo e pistone vengono ricostruiti come oggetti separati per potersi
#   allungare. Le ruote sono guidate da driver (angolo = percorso / raggio).
# Export glTF: l'exporter campiona le pose, quindi driver e vincoli finiscono
#   nell'animazione. Prima di esportare porta "CA_Rig" a location (0, 0, 0).
# Uso: apri il file nel Text Editor e premi Run Script (ricostruisce il tutorial
#   del carro se manca, poi rifà il rig da zero).
# =====================================================================
import bpy, math, os
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

_nome_main = __name__; __name__ = 'cb_rig'          # carica il carro senza lanciarne il tutorial
if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'run_tutorial' not in globals(): exec(_carica('cb_tutorial.py'))
exec(_carica('cb_carro_attrezzi.py'))
__name__ = _nome_main

RIG_LOC = Vector((CFG['STAGE_X'][9], -7.5, 0.0))   # accanto al mezzo finito del tutorial
COLL = 'CarroAttrezzi_Rig'

# ---------- punti della meccanica (stesse formule di cb_carro_attrezzi.py) ----------
def punti():
    d = (P1 - P0).normalized(); up = Vector((d.y, -d.x)) if d.x < 0 else Vector((-d.y, d.x))
    pb = P0 + d*1.5 - up*(HB/2)
    hz = 1.20
    return dict(p0=Vector((P0.x, 0, P0.y)), p1=Vector((P1.x, 0, P1.y)),
                pist_a=Vector((0.20, 0, 1.00)), pist_b=Vector((pb.x, 0, pb.y)),
                ca=Vector((1.15, 0, 1.58)), cb=Vector((P1.x, 0, P1.y - 0.15)),
                hook_top=Vector((P1.x, 0, hz + 0.45)))

# ---------- quale osso guida ogni pezzo ----------
def osso_di(nome):
    for nx in ('Ant', 'Post'):
        for nm in ('Dx', 'Sx'):
            if nome in (f'Ruota_{nx}_{nm}', f'Coprimozzo_{nx}_{nm}'): return f'Ruota_{nx}_{nm}'
    if nome in ('Porta_Dx', 'Porta_Sx'): return nome
    if nome == 'Braccio_Gru': return 'Braccio'
    if nome == 'Gancio': return 'CTRL_Gancio'
    return 'Telaio'

# ---------- pulizia ----------
def reset():
    c = bpy.data.collections.get(COLL)
    if c:
        for o in list(c.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0:
                (bpy.data.armatures if isinstance(d, bpy.types.Armature) else bpy.data.meshes).remove(d)
        bpy.data.collections.remove(c)
    c = bpy.data.collections.new(COLL); bpy.context.scene.collection.children.link(c)
    return c

# ---------- armatura ----------
def crea_armatura(coll):
    K = punti()
    arm_d = bpy.data.armatures.new('CA_Rig'); arm_d.display_type = 'STICK'
    arm = bpy.data.objects.new('CA_Rig', arm_d); arm.location = RIG_LOC; arm.show_in_front = True
    coll.objects.link(arm)
    vl = bpy.context.view_layer; vl.update()
    for o in list(vl.objects):
        if o is not None: o.select_set(False)
    vl.objects.active = arm; arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_d.edit_bones
    def B(name, head, tail, parent=None, roll_up=None):
        b = eb.new(name); b.head = head; b.tail = tail
        if parent: b.parent = eb[parent]
        if roll_up is not None: b.align_roll(Vector(roll_up))
        return b
    B('Root', (0, 0, 0), (1.5, 0, 0), roll_up=(0, 0, 1))
    B('Telaio', (0, 0, ZA), (0, 0, ZA + 0.8), 'Root')
    for cx, nx in ((WR, 'Post'), (WF, 'Ant')):
        for s, nm in ((-1, 'Dx'), (1, 'Sx')):
            c = Vector((cx, s*1.15, ZA))
            par = 'Telaio'
            if nx == 'Ant':
                B(f'Sterzo_{nm}', c, c + Vector((0, 0, 0.6)), 'Telaio', roll_up=(1, 0, 0)); par = f'Sterzo_{nm}'
            B(f'Ruota_{nx}_{nm}', c, c + Vector((0, 0.5, 0)), par, roll_up=(0, 0, 1))
    for s, nm in ((-1, 'Dx'), (1, 'Sx')):
        B(f'Porta_{nm}', (2.66, s*W, 0.62), (2.66, s*W, 2.78), 'Telaio', roll_up=(1, 0, 0))
    B('Braccio', K['p0'], K['p1'], 'Telaio', roll_up=(0, 0, 1))
    B('Attacco_Pistone', K['pist_b'], K['pist_b'] + Vector((0, 0, -0.2)), 'Braccio')
    B('Appeso', K['cb'], K['cb'] + Vector((0, 0, -0.15)), 'Braccio', roll_up=(1, 0, 0)).use_inherit_rotation = False
    B('CTRL_Gancio', K['hook_top'], K['hook_top'] + Vector((0, 0, -0.5)), 'Appeso', roll_up=(1, 0, 0))
    B('Cavo_Verticale', K['cb'], K['hook_top'], 'Appeso')
    B('Cavo_Diagonale', K['ca'], K['cb'], 'Telaio')
    B('Pistone', K['pist_a'], K['pist_b'], 'Telaio')
    bpy.ops.object.mode_set(mode='POSE')
    pb = arm.pose.bones
    for b in pb: b.rotation_mode = 'XYZ'
    def stretch(bone, target, head_tail=0.0):
        c = pb[bone].constraints.new('STRETCH_TO'); c.target = arm; c.subtarget = target
        c.head_tail = head_tail; c.volume = 'NO_VOLUME'; c.keep_axis = 'PLANE_X'
    stretch('Cavo_Verticale', 'CTRL_Gancio')
    stretch('Cavo_Diagonale', 'Appeso')
    stretch('Pistone', 'Attacco_Pistone')
    def limita(bone, axis, lo, hi):
        c = pb[bone].constraints.new('LIMIT_ROTATION'); c.owner_space = 'LOCAL'
        setattr(c, 'use_limit_' + axis, True); setattr(c, 'min_' + axis, math.radians(lo)); setattr(c, 'max_' + axis, math.radians(hi))
    limita('Braccio', 'x', -10, 10)    # + = alza la gru; oltre +10° il gancio rientrerebbe nel cassone; pb['Braccio'].lock_rotation = (False, True, True); pb['Braccio'].lock_location = (True, True, True)
    limita('Porta_Dx', 'y', 0, 80); limita('Porta_Sx', 'y', -80, 0)
    for nm in ('Porta_Dx', 'Porta_Sx'):
        pb[nm].lock_rotation = (True, False, True); pb[nm].lock_location = (True, True, True)
    g = pb['CTRL_Gancio']; g.lock_rotation = (True, True, True); g.lock_location = (True, False, True)
    c = g.constraints.new('LIMIT_LOCATION'); c.owner_space = 'LOCAL'; c.use_min_y = c.use_max_y = True; c.min_y = -0.3; c.max_y = 0.75
    # pavimento: il fondo del gancio (0,65 m sotto l'osso) non scende sotto 5 cm da terra
    c = g.constraints.new('LIMIT_LOCATION'); c.owner_space = 'POSE'; c.use_min_z = True; c.min_z = 0.70
    # proprietà di comando + driver
    for k, v, lo, hi, desc in (('percorso_m', 0.0, -10000.0, 10000.0, 'Metri percorsi: fanno girare le ruote'),
                               ('sterzo_gradi', 0.0, -35.0, 35.0, 'Sterzata delle ruote anteriori (+ = sinistra)')):
        arm[k] = v; arm.id_properties_ui(k).update(min=lo, max=hi, description=desc)
    def driver(bone, expr, var, prop):
        fc = pb[bone].driver_add('rotation_euler', 1); dr = fc.driver; dr.type = 'SCRIPTED'
        vv = dr.variables.new(); vv.name = var; vv.type = 'SINGLE_PROP'
        vv.targets[0].id_type = 'OBJECT'; vv.targets[0].id = arm; vv.targets[0].data_path = f'["{prop}"]'
        dr.expression = expr
    for nx in ('Ant', 'Post'):
        for nm in ('Dx', 'Sx'):
            driver(f'Ruota_{nx}_{nm}', f'd/{RW}', 'd', 'percorso_m'); pb[f'Ruota_{nx}_{nm}'].lock_rotation = (True, True, True)
    for nm in ('Dx', 'Sx'):
        driver(f'Sterzo_{nm}', 'radians(s)', 's', 'sterzo_gradi'); pb[f'Sterzo_{nm}'].lock_rotation = (True, True, True)
    # collezioni di ossa: comandi visibili, meccanica nascosta
    ctrl = arm_d.collections.new('Comandi'); mecc = arm_d.collections.new('Meccanica')
    for b in arm_d.bones:
        (ctrl if b.name in ('Root', 'Braccio', 'CTRL_Gancio', 'Porta_Dx', 'Porta_Sx') else mecc).assign(b)
    mecc.is_visible = False
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm

# ---------- pezzi ----------
def copia_pezzi(coll):
    src = bpy.data.collections.get('Fase_9_Finito')
    if src is None:
        run_tutorial(CFG, pieces()); src = bpy.data.collections['Fase_9_Finito']
    out = []
    for o in src.objects:
        if o.type != 'MESH' or not o.name.startswith('F9_'): continue
        nome = o.name[3:]
        if nome in ('Cavo_Spago', 'Perno_Argano_Pistone'): continue      # ricostruiti separati
        n = o.copy(); n.data = o.data.copy(); n.name = 'CA_' + nome
        n.location = RIG_LOC; coll.objects.link(n); out.append((n, osso_di(nome)))
    MAT = make_materials(); PCS = {p['name']: p for p in pieces()}
    sep = {'Perno_Argano_Pistone': ('Perno_Braccio', 'Perno_Punta', 'Argano', 'Pistone'), 'Cavo_Spago': ('Cavo_Diagonale', 'Cavo_Verticale')}
    ossa = {'Perno_Braccio': 'Braccio', 'Perno_Punta': 'Braccio', 'Argano': 'Telaio', 'Pistone': 'Pistone',
            'Cavo_Diagonale': 'Cavo_Diagonale', 'Cavo_Verticale': 'Cavo_Verticale'}
    for pn, nomi in sep.items():
        pc = PCS[pn]
        for i, (pd, nome) in enumerate(zip(pc['parts'], nomi)):
            ob = make_object('CA_' + nome, [(geo_of(pc, i, pd), pd['M'])], piece_mats(pc, 9, MAT, CFG), coll, RIG_LOC)
            out.append((ob, ossa[nome]))
    return out

def imparenta(arm, pezzi):
    bpy.context.view_layer.update()
    for ob, bone in pezzi:
        mw = ob.matrix_world.copy()
        ob.parent = arm; ob.parent_type = 'BONE'; ob.parent_bone = bone
        bpy.context.view_layer.update()
        ob.matrix_world = mw

def run():
    coll = reset()
    pezzi = copia_pezzi(coll)
    arm = crea_armatura(coll)
    imparenta(arm, pezzi)
    return arm

if __name__ == '__main__':
    run()
