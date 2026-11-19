# =====================================================================
# cb_rig_utilitaria.py — Corsa Bis · Rig dell'utilitaria
# Cosa fa: copia l'utilitaria finita (fase 8 del tutorial) accanto al
#   tutorial e la collega a un'armatura pronta da animare.
#   Comandi (proprietà dell'oggetto "UT_Rig", animabili con I sul campo):
#     percorso_m    metri percorsi: le 4 ruote girano di conseguenza
#     sterzo_gradi  sterzata delle ruote anteriori (+ = sinistra)
#   Ossa da animare (Pose Mode, rotazione Y, da 0 a ±85°):
#     Root                          sposta/ruota tutta l'auto
#     Porta_Ant_Dx/_Sx, Porta_Post_Dx/_Sx   le 4 portiere (cerniera davanti)
# Come: parti comuni da cb_rig.py; qui solo posizioni di assi e porte.
# Export glTF: porta "UT_Rig" a location (0, 0, 0) prima di esportare.
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

_nome_main = __name__; __name__ = 'cb_extra'        # carica l'utilitaria senza lanciarne il tutorial
if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'run_tutorial' not in globals(): exec(_carica('cb_tutorial.py'))
exec(_carica('cb_utilitaria.py'))
exec(_carica('cb_rig.py'))
__name__ = _nome_main

COLL = 'Utilitaria_Rig'; PREF = 'UT_'
RIG_LOC = Vector((CFG['STAGE_X'][8], -7.5, 0.0))
ASSI = ((WR, 'Post', False), (WF, 'Ant', True))
CERNIERE = {'Ant': 0.80, 'Post': -0.03}          # bordo anteriore di ogni porta

def osso_di(nome):
    for nx in ('Ant', 'Post'):
        for nm in ('Dx', 'Sx'):
            if nome in (f'Ruota_{nx}_{nm}', f'Coprimozzo_{nx}_{nm}'): return f'Ruota_{nx}_{nm}'
            if nome == f'Porta_{nx}_{nm}': return nome
    return 'Telaio'

def run():
    coll = rig_reset(COLL)
    src = bpy.data.collections.get('Fase_8_Finito')
    if src is None:
        run_tutorial(CFG, pieces()); src = bpy.data.collections['Fase_8_Finito']
    pezzi = copia_finito(src, PREF, coll, RIG_LOC)
    arm = armatura_inizio('UT_Rig', coll, RIG_LOC)
    ossa_base(arm, XF - XR, ZA)
    ossa_ruote(arm, ASSI, 0.62, ZA)
    porte = []
    for nx, x in CERNIERE.items():
        for s, nm in ((-1, 'Dx'), (1, 'Sx')):
            osso_porta(arm, f'Porta_{nx}_{nm}', x, s*W, 0.40, 1.38)
            porte.append((f'Porta_{nx}_{nm}', 1 if s < 0 else -1))   # destra: angoli +, sinistra: angoli -
    armatura_fine(arm, ASSI, RW, porte)
    imparenta(arm, [(o, osso_di(n)) for o, n in pezzi])
    riposo(arm)
    return arm

if __name__ == '__main__':
    run()
