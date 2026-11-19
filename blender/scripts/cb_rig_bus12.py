# =====================================================================
# cb_rig_bus12.py — Corsa Bis · Rig del bus urbano 12 m
# Cosa fa: copia il bus finito (fase 9 del tutorial) accanto al tutorial e
#   lo collega a un'armatura pronta da animare.
#   Comandi (proprietà dell'oggetto "B12_Rig", animabili con I sul campo):
#     percorso_m    metri percorsi: le 4 ruote girano di conseguenza
#     sterzo_gradi  sterzata delle ruote anteriori (+ = sinistra)
#   Ossa da animare (Pose Mode, rotazione Y, da 0 a ±85°):
#     Root                    sposta/ruota tutto il bus
#     Porta_Ant               porta anteriore (cerniera sul lato del muso)
#     Porta_Cen_A, _Cen_B     le due ante della porta centrale
# Come: parti comuni da cb_rig.py; qui solo posizioni di assi e porte.
#   La porta centrale (un pezzo con due ante) viene ricostruita in due oggetti.
# Export glTF: porta "B12_Rig" a location (0, 0, 0) prima di esportare.
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

_nome_main = __name__; __name__ = 'cb_rig'          # carica il bus senza lanciarne il tutorial
if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'run_tutorial' not in globals(): exec(_carica('cb_tutorial.py'))
exec(_carica('cb_bus12.py'))
exec(_carica('cb_rig.py'))
__name__ = _nome_main

COLL = 'Bus12_Rig'; PREF = 'B12_'
RIG_LOC = Vector((CFG['STAGE_X'][9], -7.5, 0.0))
ASSI = ((WR, 'Post', False), (WF, 'Ant', True))
YD = -(WI + 0.025)                                  # piano delle ante (lato destro)
MID = (DOOR_M[0] + DOOR_M[1])/2

def osso_di(nome):
    for nx in ('Ant', 'Post'):
        for nm in ('Dx', 'Sx'):
            if nome in (f'Ruota_{nx}_{nm}', f'Coprimozzo_{nx}_{nm}'): return f'Ruota_{nx}_{nm}'
    return {'Porta_Anteriore': 'Porta_Ant', 'Porta_Cen_A': 'Porta_Cen_A', 'Porta_Cen_B': 'Porta_Cen_B'}.get(nome, 'Telaio')

def run():
    coll = rig_reset(COLL)
    src = bpy.data.collections.get('Fase_9_Finito')
    if src is None:
        run_tutorial(CFG, pieces(), scritta_linea); src = bpy.data.collections['Fase_9_Finito']
    pezzi = copia_finito(src, PREF, coll, RIG_LOC, salta=('Porta_Centrale',))
    MAT = make_materials(); PCS = {p['name']: p for p in pieces()}
    pezzi += ricostruisci(PCS['Porta_Centrale'], ('Porta_Cen_A', 'Porta_Cen_B'), MAT, CFG, coll, RIG_LOC, PREF)
    arm = armatura_inizio('B12_Rig', coll, RIG_LOC)
    ossa_base(arm, XF - XR, ZA)
    ossa_ruote(arm, ASSI, 1.15, ZA)
    # cerniere: anteriore sul bordo verso il muso; ante centrali sui bordi esterni
    osso_porta(arm, 'Porta_Ant', DOOR_F[1] - 0.02, YD, 0.62, 2.60)
    osso_porta(arm, 'Porta_Cen_A', DOOR_M[0] + 0.02, YD, 0.62, 2.60)
    osso_porta(arm, 'Porta_Cen_B', DOOR_M[1] - 0.02, YD, 0.62, 2.60)
    # lato destro: cerniera davanti -> si apre con angoli +, cerniera dietro -> angoli -
    armatura_fine(arm, ASSI, RW, (('Porta_Ant', 1), ('Porta_Cen_A', -1), ('Porta_Cen_B', 1)))
    imparenta(arm, [(o, osso_di(n)) for o, n in pezzi])
    riposo(arm)
    return arm

if __name__ == '__main__':
    run()
