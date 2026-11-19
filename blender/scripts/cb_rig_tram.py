# =====================================================================
# cb_rig_tram.py — Corsa Bis · Rig del tram
# Cosa fa: copia il tram finito (fase 10 del tutorial) accanto al tutorial
#   e lo collega a un'armatura pronta da animare.
#   Comandi (proprietà dell'oggetto "TR_Rig", animabili con I sul campo):
#     percorso_m    metri percorsi: le 12 ruote girano di conseguenza
#     curva_gradi   piega il tram in curva (±20°): la cassa davanti ruota
#                   di +curva, quella dietro di -curva rispetto alla
#                   centrale, i soffietti si aprono a ventaglio e i
#                   carrelli delle casse esterne seguono il binario
#                   (metà dell'angolo, al contrario della cassa)
#   Ossa da animare (Pose Mode):
#     Root                      sposta/ruota tutto il tram
#     Porta_<cassa><n>_<lato>_a/_b   le 20 ante (rotazione Y, 0-85°)
#     Lira_1, Lira_2            alza le lire verso la linea aerea (rotazione Y, 0-40°)
# Come: parti comuni da cb_rig.py. Casse e carrelli sono pezzi rigidi;
#   soffietti e pedane sono deformati con pesi graduali tra le casse.
#   Porte, lire e corrimano sono ricostruiti in pezzi separati.
# Export glTF: porta "TR_Rig" a location (0, 0, 0) prima di esportare.
# Uso: apri il file nel Text Editor e premi Run Script.
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

_nome_main = __name__; __name__ = 'cb_extra'        # carica il tram senza lanciarne il tutorial
if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'run_tutorial' not in globals(): exec(_carica('cb_tutorial.py'))
exec(_carica('cb_tram.py'))
exec(_carica('cb_rig.py'))
__name__ = _nome_main

COLL = 'Tram_Rig'; PREF = 'TR_'
RIG_LOC = Vector((CFG['STAGE_X'][10], -7.5, 0.0))
PERNI = {'A': sum(GIUNTI[0])/2, 'C': sum(GIUNTI[1])/2}     # centro dei due soffietti
SNODO = {'A': 'Snodo_A', 'B': 'Telaio', 'C': 'Snodo_C'}
DIVISI = ('Lire', 'Corrimano') + tuple(f'Porte_{k}_{nm}' for k in CASSE for nm in ('Dx', 'Sx'))
DEFORMATI = ('Soffietto_1', 'Soffietto_2', 'Pedana_Snodo_1', 'Pedana_Snodo_2')

def cassa_di_x(x):
    return 'A' if x > PERNI['A'] else ('C' if x < PERNI['C'] else 'B')

def osso_di(nome, ob):
    if nome.startswith(('Ruota_', 'Coprimozzo_')): return 'Ruota_' + nome.split('_', 1)[1]
    if nome.startswith('Asse_'): return 'Carrello_' + nome[5]
    if nome.startswith('Carrello_'): return nome
    if nome.startswith(('Porta_', 'Lira_')): return nome
    if nome.startswith('Portale_B'): return 'Telaio'          # i portali della cassa centrale
    if nome.endswith('_Ant') or 'Ant_' in nome or nome.startswith('Scritta_Linea_Ant'): return SNODO['A']
    if nome.endswith('_Post') or 'Post_' in nome: return SNODO['C']
    for k in CASSE:
        if f'_{k}_' in nome + '_' or nome.endswith(f'_{k}'): return SNODO[k]
    xs = [(ob.matrix_world @ v.co).x - RIG_LOC.x for v in ob.data.vertices] if ob.type == 'MESH' else [0.0]
    return SNODO[cassa_di_x((min(xs) + max(xs))/2)]

def dividi(PCS, MAT, coll):
    out = []
    pc = PCS['Lire']; out += ricostruisci(pc, ('Lira_1', 'Lira_2'), MAT, CFG, coll, RIG_LOC, PREF)
    pc = PCS['Corrimano']
    for i, pd in enumerate(pc['parts']):
        x = pd['M'].translation.x
        ob = make_object(f'{PREF}Corrimano_{cassa_di_x(x)}_{i+1}', [(geo_of(pc, i, pd), pd['M'])], piece_mats(pc, CFG['final_stage'], MAT, CFG), coll, RIG_LOC)
        out.append((ob, f'Corrimano_{cassa_di_x(x)}_{i+1}'))
    for k in CASSE:
        for nm in ('Dx', 'Sx'):
            pc = PCS[f'Porte_{k}_{nm}']
            nomi = [f'Porta_{k}{j+1}_{nm}_{ab}' for j in range(len(DOORS[k])) for ab in ('a', 'b')]
            out += ricostruisci(pc, nomi, MAT, CFG, coll, RIG_LOC, PREF)
    return out

def pesa(ob, nome):
    # 0 = segue la cassa centrale (Telaio), 1 = segue la cassa esterna
    a, b = GIUNTI[0] if nome.endswith('_1') else GIUNTI[1]; est = 'Snodo_A' if nome.endswith('_1') else 'Snodo_C'
    gt = ob.vertex_groups.new(name='Telaio'); ge = ob.vertex_groups.new(name=est)
    for v in ob.data.vertices:
        x = v.co.x
        w = (x - a)/(b - a) if est == 'Snodo_A' else (b - x)/(b - a)
        w = min(1.0, max(0.0, w)); ge.add([v.index], w, 'REPLACE'); gt.add([v.index], 1.0 - w, 'REPLACE')

def driver(arm, bone, expr):
    fc = arm.pose.bones[bone].driver_add('rotation_euler', 1); dr = fc.driver; dr.type = 'SCRIPTED'
    vv = dr.variables.new(); vv.name = 'c'; vv.type = 'SINGLE_PROP'
    vv.targets[0].id_type = 'OBJECT'; vv.targets[0].id = arm; vv.targets[0].data_path = '["curva_gradi"]'
    dr.expression = expr

def run():
    coll = rig_reset(COLL)
    src = bpy.data.collections.get('Fase_10_Finito')
    if src is None:
        run_tutorial(CFG, pieces(), scritta_linea); src = bpy.data.collections['Fase_10_Finito']
    pezzi = copia_finito(src, PREF, coll, RIG_LOC, salta=DIVISI)
    MAT = make_materials(); PCS = {p['name']: p for p in pieces()}
    pezzi += dividi(PCS, MAT, coll)
    arm = armatura_inizio('TR_Rig', coll, RIG_LOC)
    ossa_base(arm, 2*XE, ZB)
    for k, xp in PERNI.items():
        osso(arm, f'Snodo_{k}', (xp, 0, ZB), (xp, 0, ZB + 0.8), 'Telaio', roll_up=(1, 0, 0))
    assi = []
    for k, bc in CARRELLI.items():
        osso(arm, f'Carrello_{k}', (bc, 0, ZA), (bc, 0, ZA + 0.6), SNODO[k], roll_up=(1, 0, 0))
        nomi = [(bc - PASSO_C, f'{k}1', False), (bc + PASSO_C, f'{k}2', False)]
        ossa_ruote(arm, nomi, 0.74, ZA, f'Carrello_{k}'); assi += nomi
    porte = []
    for k in CASSE:
        for s, nm in ((-1, 'Dx'), (1, 'Sx')):
            for j, (d0, d1) in enumerate(DOORS[k]):
                osso_porta(arm, f'Porta_{k}{j+1}_{nm}_a', d0 + 0.02, s*(W + 0.02), ZB - 0.08, ZW1 + 0.05, SNODO[k])
                osso_porta(arm, f'Porta_{k}{j+1}_{nm}_b', d1 - 0.02, s*(W + 0.02), ZB - 0.08, ZW1 + 0.05, SNODO[k])
                porte += [(f'Porta_{k}{j+1}_{nm}_a', s), (f'Porta_{k}{j+1}_{nm}_b', -s)]
    for i, xb in enumerate((2.4, -0.2)):
        osso(arm, f'Lira_{i+1}', (xb, -0.3, ZL + T), (xb, 0.3, ZL + T), 'Telaio', roll_up=(0, 0, 1))
    pb = armatura_fine(arm, assi, RW, porte, comandi_extra=('Lira_1', 'Lira_2'))
    for i in (1, 2):
        c = pb[f'Lira_{i}'].constraints.new('LIMIT_ROTATION'); c.owner_space = 'LOCAL'; c.use_limit_y = True
        c.min_y, c.max_y = 0.0, math.radians(40); pb[f'Lira_{i}'].lock_rotation = (True, False, True); pb[f'Lira_{i}'].lock_location = (True, True, True)
    arm['curva_gradi'] = 0.0
    arm.id_properties_ui('curva_gradi').update(min=-20.0, max=20.0, description='Piega il tram in curva (+ = sinistra)')
    driver(arm, 'Snodo_A', 'radians(c)'); driver(arm, 'Snodo_C', '-radians(c)')
    driver(arm, 'Carrello_A', '-radians(c)/2'); driver(arm, 'Carrello_C', 'radians(c)/2')
    for n in ('Snodo_A', 'Snodo_C', 'Carrello_A', 'Carrello_B', 'Carrello_C'):
        pb[n].lock_rotation = (True, True, True); pb[n].lock_location = (True, True, True)
    imparenta(arm, [(o, osso_di(n, o)) for o, n in pezzi if n not in DEFORMATI])
    for o, n in pezzi:
        if n in DEFORMATI:
            mw = o.matrix_world.copy(); pesa(o, n)
            o.parent = arm; o.parent_type = 'OBJECT'; o.matrix_world = mw
            m = o.modifiers.new('Snodo', 'ARMATURE'); m.object = arm
    riposo(arm)
    arm['curva_gradi'] = 0.0
    return arm

if __name__ == '__main__':
    run()
