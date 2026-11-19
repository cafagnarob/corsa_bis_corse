# =====================================================================
# cb_lod_tram.py — Corsa Bis · LOD del tram
# Cosa fa: mette in fila, sotto il tutorial, le sei versioni del tram:
#   LOD0  modello completo (fase 10)                    a bordo, a piedi
#   LOD1  senza interni e nastro, ruote a 2 dischi      zoom, modellino
#   LOD2  senza pezzi nascosti, ruote a 1 disco         volo d'uccello
#   LOD3  volumi principali, una sola mesh              tabellone vicino
#   LOD4  tre casse estruse con la fascia azzurra, tetti, lanternini,
#         soffietti e carrelli a blocchi, finestrini e luci dipinti
#                                                       tabellone lontano
#   LOD5  tre gettoni snodabili (tetti grigi, lanternini crema, testate
#         azzurre) su dischi-perno, con l'armatura L5_Rig  2D dall'alto
# Come: LOD1-3 e fila di confronto da cb_lod.py; qui LOD4 e LOD5.
#   Tutti i LOD si piegano in curva: ognuno ha la sua armatura L<n>_Rig con
#   lo stesso comando del rig completo (curva_gradi, ±20°). LOD1-2 hanno
#   anche percorso_m per le ruote; LOD3-4 sono una mesh per cassa, per
#   carrello e per soffietto; il LOD0 si anima con Tram_Rig (cb_rig_tram.py).
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
exec(_carica('cb_lod.py'))
exec(_carica('cb_rig.py'))           # armatura del LOD5 snodabile
__name__ = _nome_main

# ---------- snodo dei LOD: stesso comando del rig completo (curva_gradi) ----------
PERNI = {'A': sum(GIUNTI[0])/2, 'C': sum(GIUNTI[1])/2}
OSSO_CASSA = {'A': 'Snodo_A', 'B': 'Telaio', 'C': 'Snodo_C'}

def cassa_di_x(x):
    return 'A' if x > PERNI['A'] else ('C' if x < PERNI['C'] else 'B')

def chiave(nome, xc):
    # in quale parte del tram sta un pezzo: cassa, soffietto (S1/S2), carrello o ruota
    for i in (1, 2):
        if nome.startswith((f'Soffietto_{i}', f'Pedana_Snodo_{i}', f'Soffietto{i}')): return f'S{i}'
    if nome.startswith(('Ruota_', 'Coprimozzo_')): return 'R:' + nome.split('_', 1)[1]
    if nome.startswith('Carrello_'): return 'K' + nome[9]
    if nome.startswith('Asse_'): return 'K' + nome[5]
    if 'Scritta_Linea_Ant' in nome: return 'A'
    if 'Scritta_Linea_Post' in nome: return 'C'
    return cassa_di_x(xc)

def osso_chiave(k):
    if k in OSSO_CASSA: return OSSO_CASSA[k]
    if k.startswith('K'): return 'Carrello_' + k[1]
    if k.startswith('R:'): return 'Ruota_' + k[2:]
    return None                                           # soffietti: deformati

def pesa(ob, i):
    a, b = GIUNTI[i - 1]; est = 'Snodo_A' if i == 1 else 'Snodo_C'
    gt = ob.vertex_groups.new(name='Telaio'); ge = ob.vertex_groups.new(name=est)
    for v in ob.data.vertices:
        w = (v.co.x - a)/(b - a) if i == 1 else (b - v.co.x)/(b - a)
        w = min(1.0, max(0.0, w)); ge.add([v.index], w, 'REPLACE'); gt.add([v.index], 1.0 - w, 'REPLACE')

def snoda(nome_rig, coll, loc, oggetti):
    # oggetti: lista di (oggetto, chiave). Crea l'armatura del LOD e lega i pezzi.
    ruote = sorted({k[2:] for _, k in oggetti if k.startswith('R:')})
    arm = armatura_inizio(nome_rig, coll, loc)
    osso(arm, 'Root', (0, 0, 0), (3.0, 0, 0), roll_up=(0, 0, 1))
    osso(arm, 'Telaio', (0, 0, ZB), (0, 0, ZB + 0.8), 'Root', roll_up=(1, 0, 0))
    for k, xp in PERNI.items():
        osso(arm, f'Snodo_{k}', (xp, 0, ZB), (xp, 0, ZB + 0.8), 'Telaio', roll_up=(1, 0, 0))
    assi = []
    for k, bc in CARRELLI.items():
        osso(arm, f'Carrello_{k}', (bc, 0, ZA), (bc, 0, ZA + 0.6), OSSO_CASSA[k], roll_up=(1, 0, 0))
        mie = sorted({r.split('_')[0] for r in ruote if r.startswith(k)})
        if mie:
            nomi = [(bc - PASSO_C if nx.endswith('1') else bc + PASSO_C, nx, False) for nx in mie]
            ossa_ruote(arm, nomi, 0.74, ZA, f'Carrello_{k}'); assi += nomi
    pb = armatura_fine(arm, assi, RW, [])
    arm['curva_gradi'] = 0.0
    arm.id_properties_ui('curva_gradi').update(min=-20.0, max=20.0, description='Piega il tram in curva (+ = sinistra)')
    for bone, expr in (('Snodo_A', 'radians(c)'), ('Snodo_C', '-radians(c)'), ('Carrello_A', '-radians(c)/2'), ('Carrello_C', 'radians(c)/2')):
        fc = pb[bone].driver_add('rotation_euler', 1); dr = fc.driver; dr.type = 'SCRIPTED'
        vv = dr.variables.new(); vv.name = 'c'; vv.type = 'SINGLE_PROP'
        vv.targets[0].id_type = 'OBJECT'; vv.targets[0].id = arm; vv.targets[0].data_path = '["curva_gradi"]'
        dr.expression = expr
    for n in ('Snodo_A', 'Snodo_C', 'Carrello_A', 'Carrello_B', 'Carrello_C'):
        pb[n].lock_rotation = (True, True, True); pb[n].lock_location = (True, True, True)
    imparenta(arm, [(o, osso_chiave(k)) for o, k in oggetti if osso_chiave(k)])
    for o, k in oggetti:
        if k in ('S1', 'S2'):
            mw = o.matrix_world.copy(); pesa(o, int(k[1]))
            o.parent = arm; o.parent_type = 'OBJECT'; o.matrix_world = mw
            m = o.modifiers.new('Snodo', 'ARMATURE'); m.object = arm
    riposo(arm)
    return arm

def xc_oggetto(o, loc):
    if o.type != 'MESH' or not o.data.vertices: return o.matrix_world.translation.x - loc.x
    xs = [(o.matrix_world @ v.co).x - loc.x for v in o.data.vertices]; return (min(xs) + max(xs))/2

def xc_pezzo(pc):
    xs = []
    for pd in pc['parts']:
        if 'outline' not in pd: continue
        for p in pd['outline']: xs.append((pd['M'] @ Vector((p[0], p[1], 0))).x)
    return (min(xs) + max(xs))/2 if xs else 0.0

def lod_separati(L, coll, loc):
    # LOD1-2: pezzi già separati con il nome del pezzo
    pref = f'L{L}_'; ogg = []
    for o in coll.objects:
        if o.type not in ('MESH', 'FONT') or o.name.startswith(('Cartellino', 'Etichetta')): continue
        nome = o.name[len(pref):] if o.name.startswith(pref) else o.name
        ogg.append((o, chiave(nome, xc_oggetto(o, loc))))
    return snoda(f'L{L}_Rig', coll, loc, ogg)

def lod3_a_gruppi(coll, loc, MAT, PCS):
    # LOD3: una mesh per cassa, per carrello e per soffietto (invece di una sola)
    vecchio = bpy.data.objects.get('L3_Mezzo')
    if vecchio:
        d = vecchio.data; bpy.data.objects.remove(vecchio, do_unlink=True); bpy.data.meshes.remove(d)
    gruppi = {}
    for pc in pezzi_lod(PCS, CFG, 3):
        k = chiave(pc['name'], xc_pezzo(pc))
        if k.startswith('R:'): k = 'K' + k[2]                # LOD3: le ruote stanno col carrello
        gruppi.setdefault(k, []).append(pc)
    ogg = []
    for k, pcs in gruppi.items():
        for o in costruisci(pcs, MAT, CFG, coll, loc, f'L3_{k}', unisci=True): ogg.append((o, k))
    return snoda('L3_Rig', coll, loc, ogg)

def lod4(MAT, coll, loc):
    A, C, G, I = MAT['vernice_azzurro'], MAT['vernice_crema'], MAT['vernice_grigio'], MAT['inchiostro']
    gr = {k: [([C, C, C], []), ([A, A, A], []), ([G, G, G], []), ([I, I, I], []), ([MAT['luce_giallo']]*3, []), ([MAT['luce_rosso']]*3, [])] for k in CASSE}
    e = 0.006
    for k, (x0, x1) in CASSE.items():
        gr[k][0][1].append(estruso(rect(x0, ZB, x1, ZT), -W, W))
        gr[k][0][1].append(lastra(x0 + 0.7, x1 - 0.7, -0.55, 0.55, ZT + 0.05, ZL - ZT))
        gr[k][1][1].append(estruso(rect(x0 + 0.01, ZB, x1 - 0.01, ZW0 - 0.12), -W - 0.01, W + 0.01))
        gr[k][2][1].append(lastra(x0 - 0.03, x1 + 0.03, -W, W, ZT, 0.05))
        for s in (-1, 1):
            y = s*(W + 0.01 + e)
            for h in finestrini(k):
                (a, z0), (b, z1) = h[0], h[2]; gr[k][3][1].append((quad((a, y, z0), (b, y, z0), (b, y, z1), (a, y, z1)), Matrix()))
            for d0, d1 in DOORS[k]: gr[k][3][1].append((quad((d0, y, ZB + 0.06), (d1, y, ZB + 0.06), (d1, y, ZW1), (d0, y, ZW1)), Matrix()))
    for sx, k in ((1, 'A'), (-1, 'C')):
        x = sx*(XE + e)
        gr[k][3][1].append((quad((x, -0.85*sx, ZW0 - 0.1), (x, 0.85*sx, ZW0 - 0.1), (x, 0.85*sx, ZW1), (x, -0.85*sx, ZW1)), Matrix()))
        x = sx*(XE + 2*e)
        for s in (-1, 1):
            gr[k][4][1].append((quad((x, s*0.70, 0.95), (x, s*0.90, 0.95), (x, s*0.90, 1.15), (x, s*0.70, 1.15)), Matrix()))
            gr[k][5][1].append((quad((x, s*0.88, 1.24), (x, s*1.02, 1.24), (x, s*1.02, 1.36), (x, s*0.88, 1.36)), Matrix()))
    ogg = []
    for k in CASSE:
        ogg.append((unisci(f'L4_Cassa_{k}', [g for g in gr[k] if g[1]], coll, loc), k))
        bc = CARRELLI[k]
        ogg.append((unisci(f'L4_Carrello_{k}', [([G, G, G], [estruso(rect(bc - 1.4, 0.12, bc + 1.4, ZB), -0.9, 0.9)])], coll, loc), 'K' + k))
    for i, (a, b) in enumerate(GIUNTI):
        # soffietto a blocco con 6 tagli lungo x, così si piega bene
        prof = [(a + (b - a)*j/6, ZB + 0.08) for j in range(7)] + [(a + (b - a)*j/6, ZT - 0.02) for j in reversed(range(7))]
        ogg.append((unisci(f'L4_Soffietto_{i+1}', [([G, G, G], [estruso(prof, -1.12, 1.12)])], coll, loc), f'S{i+1}'))
    snoda('L4_Rig', coll, loc, ogg)
    return [o for o, _ in ogg]

def lod5(MAT, coll, loc):
    # LOD5 snodabile: tre gettoni (uno per cassa) + due dischi di cartone sui
    # perni dei soffietti, legati a una piccola armatura "L5_Rig" con lo
    # stesso comando del rig completo (curva_gradi). Il gettone davanti ha la
    # punta a freccia; i gettoni finiscono prima del perno, così ruotando non
    # si sovrappongono e il disco copre lo spazio tra le casse.
    G, C, A, K = MAT['vernice_grigio'], MAT['vernice_crema'], MAT['vernice_azzurro'], MAT['kraft']
    zt = 0.15; e = 0.004; w = 1.25; loc = Vector(loc)
    def gettone_cassa(nome, x0, x1, punta_davanti, retro_tondo):
        r = 0.35
        out = [(x0, -w)] if not retro_tondo else arc(x0 + r, -w + r, r, math.pi, 1.5*math.pi, 3)
        out += [(x1 - 0.45, -w), (x1, 0.0), (x1 - 0.45, w)] if punta_davanti else [(x1, -w), (x1, w)]
        out += [(x0, w)] if not retro_tondo else arc(x0 + r, w - r, r, 0.5*math.pi, math.pi, 3)
        strati = [(G, [rettangolo_a(x0 + 0.05, x1 - (0.5 if punta_davanti else 0.05), -1.10, 1.10)]),
                  (C, [rettangolo_a(x0 + 0.7, x1 - 0.7, -0.5, 0.5)])]
        if punta_davanti: strati.append((A, [rettangolo_a(x1 - 0.95, x1 - 0.55, -1.05, 1.05)]))
        if retro_tondo: strati.append((A, [rettangolo_a(x0 + 0.05, x0 + 0.45, -1.05, 1.05)]))
        g = [([K, MAT['bordo'], MAT['interno']], [(build_panel(out, t=zt, rough=0, warp=0, nick=0, step=50.0), Matrix())])]
        for i, (m, geos) in enumerate(strati):
            g.append(([m]*3, [(f(zt + e*(i + 1)), Matrix()) for f in geos]))
        return unisci(nome, g, coll, loc)
    objs = [gettone_cassa('L5_Cassa_A', CASSE['A'][0], 16.0, True, False),
            gettone_cassa('L5_Cassa_B', CASSE['B'][0], CASSE['B'][1], False, False),
            gettone_cassa('L5_Cassa_C', -16.0, CASSE['C'][1], False, True)]
    for i, (a, b) in enumerate(GIUNTI):
        xp = (a + b)/2
        disco = build_panel(circle(xp, 0, 1.30, 20), t=zt - 0.02, rough=0, warp=0, nick=0, step=50.0)
        objs.append(unisci(f'L5_Snodo_{i+1}', [([G, MAT['bordo'], MAT['interno']], [(disco, Matrix())])], coll, loc))
    # armatura: stesso comando del rig completo
    arm = armatura_inizio('L5_Rig', coll, loc)
    osso(arm, 'Root', (0, 0, 0), (3.0, 0, 0), roll_up=(0, 0, 1))
    osso(arm, 'Telaio', (0, 0, 0), (0, 0, 0.5), 'Root', roll_up=(1, 0, 0))
    for k, (a, b) in (('A', GIUNTI[0]), ('C', GIUNTI[1])):
        xp = (a + b)/2; osso(arm, f'Snodo_{k}', (xp, 0, 0), (xp, 0, 0.5), 'Telaio', roll_up=(1, 0, 0))
    bpy.ops.object.mode_set(mode='POSE')
    for b in arm.pose.bones: b.rotation_mode = 'XYZ'; b.lock_location = (True, True, True)
    arm['curva_gradi'] = 0.0
    arm.id_properties_ui('curva_gradi').update(min=-20.0, max=20.0, description='Piega il gettone in curva (+ = sinistra)')
    for bone, expr in (('Snodo_A', 'radians(c)'), ('Snodo_C', '-radians(c)')):
        fc = arm.pose.bones[bone].driver_add('rotation_euler', 1); dr = fc.driver; dr.type = 'SCRIPTED'
        vv = dr.variables.new(); vv.name = 'c'; vv.type = 'SINGLE_PROP'
        vv.targets[0].id_type = 'OBJECT'; vv.targets[0].id = arm; vv.targets[0].data_path = '["curva_gradi"]'
        dr.expression = expr; arm.pose.bones[bone].lock_rotation = (True, True, True)
    bpy.ops.object.mode_set(mode='OBJECT')
    imparenta(arm, [(objs[0], 'Snodo_A'), (objs[1], 'Telaio'), (objs[2], 'Snodo_C'), (objs[3], 'Telaio'), (objs[4], 'Telaio')])
    return objs

def scritta(L, coll, MAT, loc):
    scritta_linea(CFG['final_stage'], coll, MAT, tuple(loc))

def run():
    if bpy.data.collections.get('Fase_10_Finito') is None:
        run_tutorial(CFG, pieces(), scritta_linea)
    out = fila_lod('Tram_LOD', CFG, pieces(), lod4, lod5, -40.0, 52.0, 38.0, scritta)
    # LOD1-3 snodabili (LOD4 e LOD5 si snodano già nella loro funzione)
    MAT = make_materials(); PCS = pieces()
    for L in (1, 2):
        lod_separati(L, bpy.data.collections[f'Tram_LOD_{L}'], Vector((52.0 + L*38.0, -40.0, 0.0)))
    lod3_a_gruppi(bpy.data.collections['Tram_LOD_3'], Vector((52.0 + 3*38.0, -40.0, 0.0)), MAT, PCS)
    return out

if __name__ == '__main__':
    print(run())
