# =====================================================================
# cb_bus12.py — Corsa Bis · Bus urbano 12 m di cartone
# Cosa fa: definisce i pezzi del bus urbano del GDD (12 × 2,55 × 3,2 m
#   reali; in gioco 15 × 3,8 × 4,8) e lancia il tutorial in 9 fasi:
#   1 taglio · 2 telaio · 3 scocca · 4 tetto e climatizzatore ·
#   5 ruote e assi · 6 interni · 7 dettagli · 8 pittura · 9 finito.
# Come: stesso stile del minibus (cb_lib.py) e stesso motore delle fasi
#   (cb_tutorial.py); qui ci sono solo misure, pezzi e livrea.
#   Muso piatto con parabrezza grande e indicatore di linea; porte solo
#   sul lato destro (anteriore e centrale a due ante), come in Italia.
# Uso: apri questo file nel Text Editor e premi Run Script; carica da
#   solo cb_lib.py e cb_tutorial.py dalla stessa cartella. Cancella e rifà tutto.
# =====================================================================
import bpy, math
from mathutils import Vector, Matrix
import os

def _carica(nome):
    # cerca il file prima nel Text Editor, poi nella cartella degli script aperti da disco
    t = bpy.data.texts.get(nome)
    if t is not None: return t.as_string()
    for tx in bpy.data.texts:
        if tx.filepath:
            p = os.path.join(os.path.dirname(bpy.path.abspath(tx.filepath)), nome)
            if os.path.exists(p):
                with open(p, encoding='utf-8') as f: return f.read()
    raise FileNotFoundError(nome + ': aprilo nel Text Editor o mettilo nella stessa cartella di questo script')

if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'run_tutorial' not in globals(): exec(_carica('cb_tutorial.py'))

# ---------- misure (metri reali) ----------
W = 1.275; WI = W - T                       # mezza larghezza esterna / interna
XR, XF = -5.92, 5.92                        # retro e muso delle fiancate (+ paraurti = 12 m)
ZB, ZM, ZT, ZF = 0.50, 1.30, 2.92, 0.66     # fondo scocca, base parabrezza, tetto, piano pavimento
ZA, RW, RA = 0.50, 0.50, 0.60               # asse ruote, raggio ruota, raggio passaruota
WR, WF = -2.60, 3.30                        # assi: passo 5,9 m
SLANT = 0.16                                # inclinazione del parabrezza
ZW0, ZW1 = 1.42, 2.62                       # fascia dei finestrini
LINEA = '1 · CENTRO'                        # testo dell'indicatore di linea

CFG = dict(
    root='Bus12_Cartone_Tutorial', Y0=-15.0, SHEET=(0.0, -8.0), sheet_w=24.0, label_dy=3.4,
    STAGE_X={s: 36.0 + (s - 2)*15.0 for s in range(2, 10)}, paint_stage=8, final_stage=9,
    wheel=dict(RW=RW, DT=0.09, ZA=ZA, YW0=0.85, stage=5),
    NOMI={2: 'Telaio', 3: 'Scocca', 4: 'Tetto', 5: 'Ruote', 6: 'Interni', 7: 'Dettagli', 8: 'Pittura', 9: 'Finito'},
    TITOLI={1: '1 · Taglio dei pezzi', 2: '2 · Telaio: pavimento, longheroni, passaruota',
            3: '3 · Scocca: fiancate, muso, parabrezza e retro', 4: '4 · Tetto e climatizzatore',
            5: '5 · Ruote e assi', 6: '6 · Interni: sedili, posto guida, corrimano',
            7: '7 · Dettagli: porte, fari, griglie, paraurti, indicatore', 8: '8 · Pittura', 9: '9 · Bus urbano finito'})

# ---------- contorni ----------
def side_outline():
    a = math.asin(max(0.0, ZB - ZA)/RA)
    pts = [(XR, ZB)]
    pts += arc(WR, ZA, RA, math.pi - a, a, 16)
    pts += arc(WF, ZA, RA, math.pi - a, a, 16)
    pts += [(XF, ZB), (XF, ZM), (XF - SLANT, ZT), (XR, ZT)]
    return pts

def fill(x0, x1, n, g=0.14):
    w = (x1 - x0 - (n - 1)*g)/n
    return [rect(x0 + i*(w + g), ZW0, x0 + i*(w + g) + w, ZW1) for i in range(n)]

DOOR_F = (4.15, 5.25)      # porta anteriore (lato destro)
DOOR_M = (-0.60, 0.90)     # porta centrale a due ante (lato destro)

def side_holes(right):
    if right:
        return fill(-5.7, -0.8, 4) + fill(1.1, 3.95, 2) + [rect(DOOR_F[0], 0.60, DOOR_F[1], ZW1), rect(DOOR_M[0], 0.60, DOOR_M[1], ZW1)]
    return fill(-5.7, 3.95, 7) + [rect(4.15, ZW0, 5.6, ZW1)]

def door_leaf(x0, x1):
    return part(rect(x0, 0.62, x1, 2.60), frame((0, -(WI + 0.025), 0), (1, 0, 0), (0, 0, 1)),
                [rect(x0 + 0.08, 1.45, x1 - 0.08, 2.50), rect(x0 + 0.08, 0.74, x1 - 0.08, 1.33)], t=0.04)

def windshield_frame():
    A = Vector((XF, 0, ZM)); B = Vector((XF - SLANT, 0, ZT)); sv = B - A; L = sv.length; sv.normalize()
    nv = Vector((sv.z, 0, -sv.x))
    return A, sv, nv, L

# ---------- pezzi ----------
def pieces():
    out = []; LATI = ((-1, 'Dx'), (1, 'Sx')); cfg = CFG
    # fase 2: telaio
    out.append(P('Pavimento', 2, [part(rect(XR + T, -WI, XF - T, WI), frame((0, 0, ZF), (1, 0, 0), (0, -1, 0)))]))
    for s, nm in LATI:
        out.append(P(f'Longherone_{nm}', 2, [part(rect(-5.5, 0.34, 5.5, ZF - T), frame((0, s*0.73, 0), (1, 0, 0), (0, 0, 1), (0, s, 0)),
                                                 [circle(WR, ZA, 0.075, 16), circle(WF, ZA, 0.075, 16)])]))
    # passaruota interni: scatole sopra le ruote, nascondono le ruote dentro l'abitacolo
    for cx, nx in ((WR, 'Post'), (WF, 'Ant')):
        out.append(P(f'Passaruota_{nx}_Sx', 2, box_parts(cx - 0.62, cx + 0.62, 0.74, WI, ZF, 1.14, t=0.06)))
        out.append(P(f'Passaruota_{nx}_Dx', 2, box_parts(cx - 0.62, cx + 0.62, -WI, -0.74, ZF, 1.14, t=0.06)))
    # fase 3: scocca
    for s, nm in LATI:
        out.append(P(f'Fiancata_{nm}', 3, [part(side_outline(), frame((0, s*WI, 0), (1, 0, 0), (0, 0, 1), (0, s, 0)), side_holes(s < 0))],
                     paint='arancio'))
    out.append(P('Muso', 3, [part(rect(-WI, ZB, WI, ZM), frame((XF - T, 0, 0), (0, 1, 0), (0, 0, 1)))], paint='arancio', early=True))
    A, sv, nv, Lw = windshield_frame()
    out.append(P('Parabrezza', 3, [part(rect(-WI, 0, WI, Lw), frame(A - nv*T, (0, 1, 0), sv, nv),
                                        [rect(-1.08, 0.10, -0.03, 1.20), rect(0.03, 0.10, 1.08, 1.20)])], paint='arancio', early=True))
    out.append(P('Retro', 3, [part(rect(-WI, ZB, WI, ZT), frame((XR + T, 0, 0), (0, -1, 0), (0, 0, 1)), [rect(-0.95, 1.90, 0.95, ZW1)])],
                 paint='arancio', early=True))
    tapes = []
    for s in (-1, 1):
        for z in (1.0, 2.3):
            tapes.append(tape_L((XR, s*W, z), (0, 0, 1), (1, 0, 0), (0, s, 0), (0, -s, 0), (-1, 0, 0), seed=int(z*10) + s))
        tapes.append(tape_L((XF, s*W, 0.9), (0, 0, 1), (-1, 0, 0), (0, s, 0), (0, -s, 0), (1, 0, 0), seed=41 + s))
    out.append(P('Nastro_Scocca', 3, [dict(geo=g, M=Matrix()) for g in tapes], kind='tape', sheet=False, until=5))
    # fase 4: tetto e climatizzatore
    out.append(P('Tetto', 4, [part(rect(XR - 0.06, -W, XF - SLANT + 0.06, W), frame((0, 0, ZT), (1, 0, 0), (0, 1, 0)))], paint='crema', early=True))
    out.append(P('Climatizzatore', 4, box_parts(-1.6, 0.6, -0.75, 0.75, ZT + T, 3.20, t=0.06), paint='crema', early=True))
    tapes = []
    for s in (-1, 1):
        for x in (-4.6, -2.0, 1.6, 4.4):
            tapes.append(tape_L((x, s*W, ZT + T), (1, 0, 0), (0, -s, 0), (0, 0, 1), (0, 0, -1), (0, s, 0), seed=int(x*10) + 3*s))
    out.append(P('Nastro_Tetto', 4, [dict(geo=g, M=Matrix()) for g in tapes], kind='tape', sheet=False, until=5))
    # fase 5: ruote e assi
    for cx, nx in ((WR, 'Post'), (WF, 'Ant')):
        out.append(P(f'Asse_{nx}', 5, [dowel((cx, -1.27, ZA), (0, 1, 0), 2.54, 0.055)], kind='wood'))
        for s, nm in LATI:
            out.append(P(f'Ruota_{nx}_{nm}', 5, wheel_parts(cx, s, cfg)))
            out.append(P(f'Coprimozzo_{nx}_{nm}', 5, [hubcap_part(cx, s, cfg)], paint='crema'))
    # fase 6: interni
    LEFT = (-5.3, -4.25, -1.55, -0.5, 0.55, 1.6)
    RIGHT = (-5.3, -4.25, -1.55, 1.4)
    for i, xc in enumerate(LEFT):
        out.append(P(f'Sedili_Sx_{i+1}', 6, seat_parts(xc, 0.30, 1.15, ZF), paint='blu', sheet=False))
    for i, xc in enumerate(RIGHT):
        out.append(P(f'Sedili_Dx_{i+1}', 6, seat_parts(xc, -1.15, -0.30, ZF), paint='blu', sheet=False))
    out.append(P('Posto_Guida', 6, seat_parts(4.9, 0.25, 0.95, ZF), paint='blu', sheet=False))
    sc = Vector((5.2, 0.6, 1.5)); sd = Vector((-0.6, 0, 0.8))
    out.append(P('Cruscotto_Volante', 6, [part(rect(5.3, -WI + 0.02, XF - T - 0.02, WI - 0.02), frame((0, 0, 1.16), (1, 0, 0), (0, 1, 0)), t=0.06, rough=0.006),
                                         part(circle(0, 0, 0.22, 24), frame_dir(sc, sd), [circle(0, 0, 0.17, 24)], t=0.04, rough=0.003, nick=0.0)],
                 paint='grigio', sheet=False))
    poles = [dowel((x, -0.95, ZF), (0, 0, 1), ZT - ZF, 0.025) for x in (DOOR_M[0] - 0.15, DOOR_M[1] + 0.15, DOOR_F[0] - 0.15)]
    poles += [dowel((-5.6, s*0.80, 2.50), (1, 0, 0), 9.6, 0.022) for s in (-1, 1)]
    poles.append(dowel((5.55, 0.6, 1.22), Vector((-0.35, 0, 0.28)), 0.42, 0.025))
    out.append(P('Corrimano_Piantone', 6, poles, kind='wood'))
    # fase 7: dettagli esterni
    out.append(P('Porta_Anteriore', 7, [door_leaf(DOOR_F[0] + 0.02, DOOR_F[1] - 0.02)], paint='grigio'))
    mid = (DOOR_M[0] + DOOR_M[1])/2
    out.append(P('Porta_Centrale', 7, [door_leaf(DOOR_M[0] + 0.02, mid - 0.01), door_leaf(mid + 0.01, DOOR_M[1] - 0.02)], paint='grigio'))
    belts = {-1: [(-5.85, DOOR_M[0] - 0.08), (DOOR_M[1] + 0.08, DOOR_F[0] - 0.08), (DOOR_F[1] + 0.08, 5.85)], 1: [(-5.85, 5.85)]}
    for s, nm in LATI:
        out.append(P(f'Fascia_{nm}', 7, [part(rect(a, 1.27, b, 1.35), frame((0, s*W, 0), (1, 0, 0), (0, 0, 1), (0, s, 0)), t=0.03, rough=0.005)
                                         for a, b in belts[s]], paint='crema'))
        out.append(P(f'Specchietto_{nm}', 7, [part(rect(-0.1, 0, 0.1, 0.34), frame((6.15, s*1.38, 2.20), (0, 1, 0), (0, 0, 1)), t=0.04, rough=0.004)],
                     paint='grigio'))
        out.append(P(f'Asta_Specchietto_{nm}', 7, [dowel((5.70, s*1.20, 2.82), (0.45, s*0.18, -0.25), 0.545, 0.022)], kind='wood'))
    Mmuso = frame((XF, 0, 0), (0, 1, 0), (0, 0, 1))
    out.append(P('Griglia_Ant', 7, [part(rect(-0.45, 0.72, 0.45, 1.12), Mmuso, slots(-0.38, 0.38, 0.78, 0.045, 0.085, 4), t=0.04, rough=0.005)], paint='grigio'))
    out.append(P('Fari', 7, [button(s*0.95, 0.92, 0.11, Mmuso) for s in (-1, 1)] + [button(s*0.68, 0.92, 0.09, Mmuso) for s in (-1, 1)], kind='plastic_giallo'))
    out.append(P('Frecce_Ant', 7, [button(s*1.10, 1.16, 0.06, Mmuso) for s in (-1, 1)], kind='plastic_arancio'))
    Mret = frame((XR, 0, 0), (0, -1, 0), (0, 0, 1))
    out.append(P('Griglia_Motore', 7, [part(rect(-0.7, 0.75, 0.7, 1.30), Mret, slots(-0.62, 0.62, 0.80, 0.05, 0.10, 5), t=0.04, rough=0.005)], paint='grigio'))
    out.append(P('Fanali_Post', 7, [button(s*0.98, 1.00, 0.11, Mret) for s in (-1, 1)], kind='plastic_rosso'))
    out.append(P('Frecce_Post', 7, [button(s*0.98, 1.26, 0.07, Mret) for s in (-1, 1)], kind='plastic_arancio'))
    out.append(P('Paraurti_Ant', 7, [part(rect(-W, 0.36, W, 0.62), frame((XF, 0, 0), (0, 1, 0), (0, 0, 1))),
                                      part(rect(XF - T, -W, 6.0, W), frame((0, 0, 0.62), (1, 0, 0), (0, 1, 0)))], paint='grigio'))
    out.append(P('Paraurti_Post', 7, [part(rect(-W, 0.36, W, 0.62), frame((XR, 0, 0), (0, -1, 0), (0, 0, 1))),
                                       part(rect(-6.0, -W, XR + T, W), frame((0, 0, 0.62), (1, 0, 0), (0, 1, 0)))], paint='grigio'))
    out.append(P('Indicatore_Linea', 7, [part(rect(-0.95, Lw - 0.36, 0.95, Lw - 0.07), frame(A, (0, 1, 0), sv, nv), t=0.03, rough=0.004)], paint='grigio'))
    return out

def scritta_linea(s, coll, MAT, loc):
    # numero e destinazione della linea sull'indicatore (pennarello, poi giallo "luminoso")
    if s < 7: return
    A, sv, nv, Lw = windshield_frame()
    M = Matrix.Translation(loc) @ frame(A, (0, 1, 0), sv, nv) @ Matrix.Translation((0, Lw - 0.215 - 0.07, 0.035))
    cu = bpy.data.curves.new('Scritta_Linea', 'FONT'); cu.body = LINEA
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.size = 0.2; cu.extrude = 0.004
    cu.materials.append(MAT['plastic_giallo'] if s >= CFG['final_stage'] else MAT['inchiostro'])
    ob = bpy.data.objects.new(f'F{s}_Scritta_Linea', cu); ob.matrix_world = M; coll.objects.link(ob)

if __name__ == '__main__':
    run_tutorial(CFG, pieces(), scritta_linea)
