# =====================================================================
# cb_rig_bus18.py — Corsa Bis · Rig del bus snodato 18 m
# Cosa fa: copia lo snodato finito (fase 10 del tutorial) accanto al
#   tutorial e lo collega a un'armatura pronta da animare.
#   Comandi (proprietà dell'oggetto "B18_Rig", animabili con I sul campo):
#     percorso_m    metri percorsi: le 6 ruote girano di conseguenza
#     sterzo_gradi  sterzata delle ruote anteriori (+ = sinistra)
#     snodo_gradi   rotazione della cassa posteriore sulla ralla (±30°: oltre,
#                   le casse si toccano sul lato interno della curva;
#                   + = la coda va verso destra, come in una curva a sinistra)
#   Ossa da animare (Pose Mode, rotazione Y, da 0 a ±85°):
#     Root                      sposta/ruota tutto il bus
#     Porta_Ant                 porta anteriore
#     Porta_Cen_A, _Cen_B       ante della porta centrale
#     Porta_Post_A, _Post_B     ante della porta della cassa posteriore
# Come: parti comuni da cb_rig.py. La cassa posteriore è figlia dell'osso
#   Snodo; il soffietto (e la pedana) sono gli unici pezzi deformati:
#   pesi graduali tra Telaio e Snodo, così la fisarmonica si piega.
#   I pezzi che attraversano lo snodo (fasce, corrimano) sono divisi in
#   parti, e ogni parte segue la cassa in cui sta.
# Export glTF: porta "B18_Rig" a location (0, 0, 0) prima di esportare.
# Uso: apri il file nel Text Editor e premi Run Script.
# =====================================================================
import bpy, math, os
from mathutils import Vector

def _carica(nome):
    t = bpy.data.texts.get(nome)
    if t is not None: return t.as_string()
    for tx in bpy.data.texts:
        if tx.filepath:
            p = os.path.join(os.path.dirname(bpy.path.abspath(tx.filepath)), nome)
            if os.path.exists(p):
                with open(p, encoding='utf-8') as f: return f.read()
    raise FileNotFoundError(nome + ': aprilo nel Text Editor o mettilo nella stessa cartella di questo script')

_nome_main = __name__; __name__ = 'cb_rig'          # carica lo snodato senza lanciarne il tutorial
if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'run_tutorial' not in globals(): exec(_carica('cb_tutorial.py'))
exec(_carica('cb_bus18.py'))
exec(_carica('cb_rig.py'))
__name__ = _nome_main

COLL = 'Bus18_Rig'; PREF = 'B18_'
RIG_LOC = Vector((CFG['STAGE_X'][10], -7.5, 0.0))
XP = (XJ1 + XJ2)/2                                  # centro della ralla (perno dello snodo)
ASSI_ANT = ((W2, 'Cen', False), (WF, 'Ant', True))
ASSI_POST = ((WR, 'Post', False),)
YD = -(WI + 0.025)
DEFORMATI = ('Soffietto', 'Pedana_Snodo')            # si piegano tra le due casse
DIVISI = ('Fascia_Dx', 'Fascia_Sx', 'Corrimano_Piantone', 'Porta_Centrale', 'Porta_Posteriore')
NOMI_PORTE = {'Porta_Centrale': ('Porta_Cen_A', 'Porta_Cen_B'), 'Porta_Posteriore': ('Porta_Post_A', 'Porta_Post_B')}

def cassa(x):
    return 'Snodo' if x < XP else 'Telaio'

def osso_di(nome, ob):
    for nx in ('Ant', 'Cen', 'Post'):
        for nm in ('Dx', 'Sx'):
            if nome in (f'Ruota_{nx}_{nm}', f'Coprimozzo_{nx}_{nm}'): return f'Ruota_{nx}_{nm}'
    if nome == 'Porta_Anteriore': return 'Porta_Ant'
    if nome.startswith('Porta_Cen_') or nome.startswith('Porta_Post_'): return nome
    if nome == 'Ralla': return 'Telaio'
    xs = [v.co.x for v in ob.data.vertices] if ob.type == 'MESH' else [0.0]
    return cassa((min(xs) + max(xs))/2)

def dividi(pc, MAT, coll):
    # una parte = un oggetto; il nome dice in quale cassa sta (dal centro della parte)
    out = []
    for i, pd in enumerate(pc['parts']):
        x0, y0, x1, y1 = bbox(pd['outline'])
        cx = (pd['M'] @ Vector(((x0 + x1)/2, (y0 + y1)/2, 0.0))).x
        nome = NOMI_PORTE[pc['name']][i] if pc['name'] in NOMI_PORTE else f"{pc['name']}_{'Post' if cx < XP else 'Ant'}_{i + 1}"
        ob = make_object(PREF + nome, [(geo_of(pc, i, pd), pd['M'])], piece_mats(pc, CFG['final_stage'], MAT, CFG), coll, RIG_LOC)
        out.append((ob, nome))
    return out

def pesa(ob):
    # pesi graduali lungo x: 0 = segue il Telaio (davanti), 1 = segue lo Snodo (dietro)
    gt = ob.vertex_groups.new(name='Telaio'); gs = ob.vertex_groups.new(name='Snodo')
    for v in ob.data.vertices:
        w = min(1.0, max(0.0, (XJ1 - v.co.x)/(XJ1 - XJ2)))
        gs.add([v.index], w, 'REPLACE'); gt.add([v.index], 1.0 - w, 'REPLACE')

def run():
    coll = rig_reset(COLL)
    src = bpy.data.collections.get('Fase_10_Finito')
    if src is None:
        run_tutorial(CFG, pieces(), scritta_linea); src = bpy.data.collections['Fase_10_Finito']
    pezzi = copia_finito(src, PREF, coll, RIG_LOC, salta=DIVISI)
    MAT = make_materials(); PCS = {p['name']: p for p in pieces()}
    for n in DIVISI: pezzi += dividi(PCS[n], MAT, coll)
    arm = armatura_inizio('B18_Rig', coll, RIG_LOC)
    ossa_base(arm, XF - XR, ZA)
    osso(arm, 'Snodo', (XP, 0, ZA), (XP, 0, ZA + 0.8), 'Telaio', roll_up=(1, 0, 0))
    ossa_ruote(arm, ASSI_ANT, 1.15, ZA, 'Telaio')
    ossa_ruote(arm, ASSI_POST, 1.15, ZA, 'Snodo')
    osso_porta(arm, 'Porta_Ant', DOOR_F[1] - 0.02, YD, 0.62, 2.60)
    osso_porta(arm, 'Porta_Cen_A', DOOR_M[0] + 0.02, YD, 0.62, 2.60)
    osso_porta(arm, 'Porta_Cen_B', DOOR_M[1] - 0.02, YD, 0.62, 2.60)
    osso_porta(arm, 'Porta_Post_A', DOOR_P[0] + 0.02, YD, 0.62, 2.60, 'Snodo')
    osso_porta(arm, 'Porta_Post_B', DOOR_P[1] - 0.02, YD, 0.62, 2.60, 'Snodo')
    pb = armatura_fine(arm, ASSI_ANT + ASSI_POST, RW,
                       (('Porta_Ant', 1), ('Porta_Cen_A', -1), ('Porta_Cen_B', 1), ('Porta_Post_A', -1), ('Porta_Post_B', 1)))
    # snodo: proprietà + driver + limiti
    arm['snodo_gradi'] = 0.0
    arm.id_properties_ui('snodo_gradi').update(min=-30.0, max=30.0, description='Rotazione della cassa posteriore sulla ralla')
    fc = pb['Snodo'].driver_add('rotation_euler', 1); dr = fc.driver; dr.type = 'SCRIPTED'
    vv = dr.variables.new(); vv.name = 's'; vv.type = 'SINGLE_PROP'
    vv.targets[0].id_type = 'OBJECT'; vv.targets[0].id = arm; vv.targets[0].data_path = '["snodo_gradi"]'
    dr.expression = 'radians(s)'; pb['Snodo'].lock_rotation = (True, True, True); pb['Snodo'].lock_location = (True, True, True)
    # pezzi rigidi alle ossa; soffietto e pedana deformati tra le due casse
    rigidi = [(o, osso_di(n, o)) for o, n in pezzi if n not in DEFORMATI]
    imparenta(arm, rigidi)
    for o, n in pezzi:
        if n in DEFORMATI:
            mw = o.matrix_world.copy(); pesa(o)
            o.parent = arm; o.parent_type = 'OBJECT'; o.matrix_world = mw
            m = o.modifiers.new('Snodo', 'ARMATURE'); m.object = arm
    riposo(arm); arm['snodo_gradi'] = 0.0
    return arm

if __name__ == '__main__':
    run()
