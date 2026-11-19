# =====================================================================
# cb_scala_prova.py — Corsa Bis · confronto scala reale / scala di gioco
# Cosa fa: mette sulla tessera B01, nel viale, due bus urbani 12 m finiti:
#   - in metri reali, come si modella in Blender (12 × 2,55 × 3,2);
#   - in scala di gioco, con i fattori del GDD per i mezzi (lunghezza
#     ×1,25, larghezza e altezza ×1,5 → 15 × 3,8 × 4,8 unità).
#   Le tessere sono già in unità di gioco (1 unità = 1 m della tessera):
#   il secondo bus è quello che si vedrà nel gioco. La scala è su un empty
#   genitore ("Scala_Gioco"), così il modello resta in metri come da
#   pipeline e il fattore si cambia in un punto solo (come scala.json).
# Uso: apri il file nel Text Editor e premi Run Script (dopo cb_basi.py).
# =====================================================================
import bpy, os
from mathutils import Vector, Matrix

def _carica(nome):
    t = bpy.data.texts.get(nome)
    if t is not None: return t.as_string()
    raise FileNotFoundError(nome)

_nome_main = __name__; __name__ = 'cb_scala'
if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
exec(_carica('cb_tutorial.py')); exec(_carica('cb_bus12.py'))
exec(_carica('cb_tessera.py'))
__name__ = _nome_main

FATTORI_MEZZI = (1.25, 1.5, 1.5)        # GDD: ×1,5 in larghezza e altezza, ×1,25 in lunghezza (oltre i 6 m)
B01 = Vector((0.0, -700.0, 0.0))        # centro della tessera B01
Z_VIALE = 0.2 + 0.3                     # faccia superiore della carreggiata del viale (cb_basi: Z0 + SP)
CORSIE = (-7.875, -2.625)               # centri delle due corsie verso est (si guida a destra)

def bus_finito(coll, nome):
    MAT = make_materials(); fs = CFG['final_stage']; objs = []
    for pc in pieces():
        if not (pc['stage'] <= fs <= pc['until']): continue
        geos = [(geo_of(pc, i, pd), pd['M']) for i, pd in enumerate(pc['parts'])]
        objs.append(make_object(f"{nome}_{pc['name']}", geos, piece_mats(pc, fs, MAT, CFG), coll, (0, 0, 0)))
    return objs

def genitore(nome, coll, loc, scala):
    e = bpy.data.objects.new(nome, None); e.empty_display_type = 'ARROWS'; e.empty_display_size = 3
    e.location = loc; e.scale = scala; coll.objects.link(e); return e

def run():
    coll = bpy.data.collections.get('Scala_Prova')
    if coll:
        for o in list(coll.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0:
                (bpy.data.meshes if isinstance(d, bpy.types.Mesh) else bpy.data.curves).remove(d)
    else:
        coll = bpy.data.collections.new('Scala_Prova'); bpy.context.scene.collection.children.link(coll)
    out = {}
    for nome, corsia, scala in (('Bus12_Reale', CORSIE[0], (1, 1, 1)), ('Bus12_Gioco', CORSIE[1], FATTORI_MEZZI)):
        e = genitore(f'Scala_{nome}', coll, B01 + Vector((-40.0, corsia, Z_VIALE)), scala)
        for o in bus_finito(coll, nome): o.parent = e
        out[nome] = e
    M = materiali_tessera()
    cartello('bus 12 m · metri reali (12 × 2,55 × 3,2)', (B01.x - 40.0, B01.y - 22.0, 0), coll, M, size=1.6)
    cartello('bus 12 m · scala di gioco (15 × 3,8 × 4,8)', (B01.x - 40.0, B01.y + 22.0, 0), coll, M, size=1.6)
    return out

if __name__ == '__main__':
    run()
