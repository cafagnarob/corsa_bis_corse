# =====================================================================
# cb_rig_minibus.py — Corsa Bis · Rig del minibus
# Cosa fa: copia il minibus finito (fase 8 del tutorial) accanto al
#   tutorial e lo collega a un'armatura pronta da animare.
#   Comandi (proprietà dell'oggetto "MB_Rig", animabili con I sul campo):
#     percorso_m    metri percorsi: le 4 ruote girano di conseguenza
#     sterzo_gradi  sterzata delle ruote anteriori (+ = sinistra)
#   Ossa da animare (Pose Mode, rotazione Y, da 0 a ±85°):
#     Root              sposta/ruota tutto il minibus
#     Porta_Dx, _Sx     le due portiere (cerniera verso il muso)
# Come: parti comuni da cb_rig.py; qui solo posizioni di assi e porte.
# Export glTF: porta "MB_Rig" a location (0, 0, 0) prima di esportare.
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

_nome_main = __name__; __name__ = 'cb_extra'        # carica il minibus senza lanciarne il tutorial
if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'run_tutorial' not in globals(): exec(_carica('cb_tutorial.py'))
exec(_carica('cb_minibus.py'))
exec(_carica('cb_rig.py'))
__name__ = _nome_main

COLL = 'Minibus_Rig'; PREF = 'MB_'
RIG_LOC = Vector((CFG['STAGE_X'][8], -7.5, 0.0))
ASSI = ((WR, 'Post', False), (WF, 'Ant', True))

def osso_di(nome):
    for nx in ('Ant', 'Post'):
        for nm in ('Dx', 'Sx'):
            if nome in (f'Ruota_{nx}_{nm}', f'Coprimozzo_{nx}_{nm}'): return f'Ruota_{nx}_{nm}'
    return nome if nome in ('Porta_Dx', 'Porta_Sx') else 'Telaio'

def run():
    coll = rig_reset(COLL)
    src = bpy.data.collections.get('Fase_8_Finito')
    if src is None:
        run_tutorial(CFG, pieces()); src = bpy.data.collections['Fase_8_Finito']
    pezzi = copia_finito(src, PREF, coll, RIG_LOC)
    arm = armatura_inizio('MB_Rig', coll, RIG_LOC)
    ossa_base(arm, XF - XR, ZA)
    ossa_ruote(arm, ASSI, 1.0, ZA)
    for s, nm in ((-1, 'Dx'), (1, 'Sx')):
        osso_porta(arm, f'Porta_{nm}', 2.22, s*W, 0.62, 2.66)
    # cerniera davanti: a destra si apre con angoli +, a sinistra con angoli -
    armatura_fine(arm, ASSI, RW, (('Porta_Dx', 1), ('Porta_Sx', -1)))
    imparenta(arm, [(o, osso_di(n)) for o, n in pezzi])
    riposo(arm)
    return arm

if __name__ == '__main__':
    run()
