# =====================================================================
# cb_bus18.py — Corsa Bis · Bus snodato 18 m di cartone
# Cosa fa: definisce i pezzi del bus snodato del GDD (18 × 2,55 × 3,2 m
#   reali; in gioco 22,5 × 3,8 × 4,8; solo viali) e lancia il tutorial
#   in 10 fasi: 1 taglio · 2 telaio e ralla · 3 scocche · 4 tetti ·
#   5 soffietto · 6 ruote e assi · 7 interni · 8 dettagli · 9 pittura ·
#   10 finito.
# Come: stesso stile e stesso motore del bus 12 m. Due casse (anteriore
#   10,6 m con muso, posteriore 6,5 m con motore) unite da un soffietto a
#   fisarmonica di cartone piegato su un piatto girevole (ralla). Tre assi.
#   Porte solo sul lato destro: anteriore, centrale, cassa posteriore.
# Uso: apri questo file nel Text Editor e premi Run Script; carica da
#   solo cb_lib.py e cb_tutorial.py dalla stessa cartella.
# =====================================================================
import bpy, math, os
from mathutils import Vector, Matrix

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
XR, XF = -8.92, 8.92                        # retro e muso (+ paraurti = 18 m)
XJ1, XJ2 = -1.70, -2.40                     # fine cassa anteriore / inizio cassa posteriore: in mezzo il soffietto
ZB, ZM, ZT, ZF = 0.50, 1.30, 2.92, 0.66     # fondo scocca, base parabrezza, tetto, piano pavimento
ZA, RW, RA = 0.50, 0.50, 0.60               # asse ruote, raggio ruota, raggio passaruota
WF, W2, WR = 6.30, 0.40, -6.60              # assi: anteriore, centrale (cassa ant.), posteriore (cassa post.)
SLANT = 0.16                                # inclinazione del parabrezza
ZW0, ZW1 = 1.42, 2.62                       # fascia dei finestrini
DOOR_F, DOOR_M, DOOR_P = (7.15, 8.25), (2.40, 3.90), (-4.60, -3.10)   # porte (lato destro)
LINEA = '4 · STAZIONE'                      # testo dell'indicatore di linea

CFG = dict(
    root='Bus18_Cartone_Tutorial', Y0=-15.0, SHEET=(0.0, -8.0), sheet_w=26.0, label_dy=3.4,
    STAGE_X={s: 40.0 + (s - 2)*22.0 for s in range(2, 11)}, paint_stage=9, final_stage=10,
    wheel=dict(RW=RW, DT=0.09, ZA=ZA, YW0=0.85, stage=6),
    NOMI={2: 'Telaio', 3: 'Scocche', 4: 'Tetti', 5: 'Soffietto', 6: 'Ruote', 7: 'Interni', 8: 'Dettagli', 9: 'Pittura', 10: 'Finito'},
    TITOLI={1: '1 · Taglio dei pezzi', 2: '2 · Telaio: pavimenti, longheroni, passaruota, ralla',
            3: '3 · Scocche: fiancate, muso, parabrezza, retro, portali', 4: '4 · Tetti e climatizzatore',
            5: '5 · Soffietto a fisarmonica', 6: '6 · Ruote e assi (tre assi)',
            7: '7 · Interni: sedili, posto guida, corrimano', 8: '8 · Dettagli: porte, fari, griglie, paraurti, indicatore',
            9: '9 · Pittura', 10: '10 · Bus snodato finito'})

# ---------- contorni ----------
def side_outline(x0, x1, axles, front):
    # fiancata di una cassa: passaruota sugli assi, muso inclinato solo davanti
    pts = [(x0, ZB)]
    for cx in sorted(axles):
        pts += arc(cx, ZA, RA, math.pi, 0.0, 16)
    if front: pts += [(x1, ZB), (x1, ZM), (x1 - SLANT, ZT), (x0, ZT)]
    else: pts += [(x1, ZB), (x1, ZT), (x0, ZT)]
    return pts

def fill(x0, x1, n, g=0.14):
    w = (x1 - x0 - (n - 1)*g)/n
    return [rect(x0 + i*(w + g), ZW0, x0 + i*(w + g) + w, ZW1) for i in range(n)]

def door_hole(d): return rect(d[0], 0.60, d[1], ZW1)

def holes_front(right):
    if right: return fill(-1.5, 2.2, 3) + fill(4.1, 6.95, 2) + [door_hole(DOOR_F), door_hole(DOOR_M)]
    return fill(-1.5, 6.95, 7) + [rect(7.15, ZW0, 8.6, ZW1)]

def holes_rear(right):
    if right: return fill(-8.7, -4.8, 3) + [door_hole(DOOR_P)]
    return fill(-8.7, -2.6, 5)

def door_leaf(x0, x1):
    return part(rect(x0, 0.62, x1, 2.60), frame((0, -(WI + 0.025), 0), (1, 0, 0), (0, 0, 1)),
                [rect(x0 + 0.08, 1.45, x1 - 0.08, 2.50), rect(x0 + 0.08, 0.74, x1 - 0.08, 1.33)], t=0.04)

def double_door(d):
    m = (d[0] + d[1])/2
    return [door_leaf(d[0] + 0.02, m - 0.01), door_leaf(m + 0.01, d[1] - 0.02)]

def zigzag(x0, x1, base, amp, thick, n, sign):
    # striscia di cartone piegata a fisarmonica (vista in sezione)
    xs = [x0 + (x1 - x0)*i/n for i in range(n + 1)]
    outer = [(x, base + sign*(amp if i % 2 else 0.0)) for i, x in enumerate(xs)]
    return outer + [(x, y - sign*thick) for x, y in reversed(outer)]

def windshield_frame():
    A = Vector((XF, 0, ZM)); B = Vector((XF - SLANT, 0, ZT)); sv = B - A; L = sv.length; sv.normalize()
    nv = Vector((sv.z, 0, -sv.x))
    return A, sv, nv, L

# ---------- pezzi ----------
def pieces():
    out = []; LATI = ((-1, 'Dx'), (1, 'Sx')); cfg = CFG
    AX = ((WF, 'Ant'), (W2, 'Cen'), (WR, 'Post'))
    # fase 2: telaio e ralla
    Mfloor = frame((0, 0, ZF), (1, 0, 0), (0, -1, 0))
    out.append(P('Pavimento_Ant', 2, [part(rect(XJ1, -WI, XF - T, WI), Mfloor)]))
    out.append(P('Pavimento_Post', 2, [part(rect(XR + T, -WI, XJ2, WI), Mfloor)]))
    out.append(P('Pedana_Snodo', 2, [part(rect(XJ2, -1.10, XJ1, 1.10), Mfloor, t=0.06)]))
    out.append(P('Ralla', 2, [part(circle((XJ1 + XJ2)/2, 0, 0.85, 32), frame((0, 0, ZF - T), (1, 0, 0), (0, -1, 0)))]))
    for s, nm in LATI:
        Ml = frame((0, s*0.73, 0), (1, 0, 0), (0, 0, 1), (0, s, 0))
        out.append(P(f'Longherone_Ant_{nm}', 2, [part(rect(XJ1 + 0.2, 0.34, XF - 0.42, ZF - T), Ml, [circle(W2, ZA, 0.075, 16), circle(WF, ZA, 0.075, 16)])]))
        out.append(P(f'Longherone_Post_{nm}', 2, [part(rect(XR + 0.42, 0.34, XJ2 - 0.2, ZF - T), Ml, [circle(WR, ZA, 0.075, 16)])]))
    for cx, nx in AX:
        out.append(P(f'Passaruota_{nx}_Sx', 2, box_parts(cx - 0.62, cx + 0.62, 0.74, WI, ZF, 1.14, t=0.06)))
        out.append(P(f'Passaruota_{nx}_Dx', 2, box_parts(cx - 0.62, cx + 0.62, -WI, -0.74, ZF, 1.14, t=0.06)))
    # fase 3: scocche
    for s, nm in LATI:
        Ms = frame((0, s*WI, 0), (1, 0, 0), (0, 0, 1), (0, s, 0))
        out.append(P(f'Fiancata_Ant_{nm}', 3, [part(side_outline(XJ1, XF, (W2, WF), True), Ms, holes_front(s < 0))], paint='arancio'))
        out.append(P(f'Fiancata_Post_{nm}', 3, [part(side_outline(XR, XJ2, (WR,), False), Ms, holes_rear(s < 0))], paint='arancio'))
    out.append(P('Muso', 3, [part(rect(-WI, ZB, WI, ZM), frame((XF - T, 0, 0), (0, 1, 0), (0, 0, 1)))], paint='arancio', early=True))
    A, sv, nv, Lw = windshield_frame()
    out.append(P('Parabrezza', 3, [part(rect(-WI, 0, WI, Lw), frame(A - nv*T, (0, 1, 0), sv, nv),
                                        [rect(-1.08, 0.10, -0.03, 1.20), rect(0.03, 0.10, 1.08, 1.20)])], paint='arancio', early=True))
    out.append(P('Retro', 3, [part(rect(-WI, ZB, WI, ZT), frame((XR + T, 0, 0), (0, -1, 0), (0, 0, 1)), [rect(-0.95, 1.90, 0.95, ZW1)])],
                 paint='arancio', early=True))
    portal = [rect(-1.0, 0.70, 1.0, 2.62)]
    out.append(P('Portale_Ant', 3, [part(rect(-WI, ZB, WI, ZT), frame((XJ1 + T, 0, 0), (0, -1, 0), (0, 0, 1)), portal)], paint='arancio'))
    out.append(P('Portale_Post', 3, [part(rect(-WI, ZB, WI, ZT), frame((XJ2 - T, 0, 0), (0, 1, 0), (0, 0, 1)), portal)], paint='arancio'))
    tapes = []
    for s in (-1, 1):
        for z in (1.0, 2.3):
            tapes.append(tape_L((XR, s*W, z), (0, 0, 1), (1, 0, 0), (0, s, 0), (0, -s, 0), (-1, 0, 0), seed=int(z*10) + s))
            tapes.append(tape_L((XJ1, s*W, z), (0, 0, 1), (1, 0, 0), (0, s, 0), (0, -s, 0), (-1, 0, 0), seed=int(z*10) + 5*s))
            tapes.append(tape_L((XJ2, s*W, z), (0, 0, 1), (-1, 0, 0), (0, s, 0), (0, -s, 0), (1, 0, 0), seed=int(z*10) + 7*s))
        tapes.append(tape_L((XF, s*W, 0.9), (0, 0, 1), (-1, 0, 0), (0, s, 0), (0, -s, 0), (1, 0, 0), seed=41 + s))
    out.append(P('Nastro_Scocche', 3, [dict(geo=g, M=Matrix()) for g in tapes], kind='tape', sheet=False, until=6))
    # fase 4: tetti e climatizzatore
    out.append(P('Tetto_Ant', 4, [part(rect(XJ1 - 0.04, -W, XF - SLANT + 0.06, W), frame((0, 0, ZT), (1, 0, 0), (0, 1, 0)))], paint='crema', early=True))
    out.append(P('Tetto_Post', 4, [part(rect(XR - 0.06, -W, XJ2 + 0.04, W), frame((0, 0, ZT), (1, 0, 0), (0, 1, 0)))], paint='crema', early=True))
    out.append(P('Climatizzatore', 4, box_parts(2.0, 4.2, -0.75, 0.75, ZT + T, 3.20, t=0.06), paint='crema', early=True))
    tapes = []
    for s in (-1, 1):
        for x in (-7.6, -4.0, 0.0, 3.0, 6.0, 8.0):
            tapes.append(tape_L((x, s*W, ZT + T), (1, 0, 0), (0, -s, 0), (0, 0, 1), (0, 0, -1), (0, s, 0), seed=int(x*10) + 3*s))
    out.append(P('Nastro_Tetti', 4, [dict(geo=g, M=Matrix()) for g in tapes], kind='tape', sheet=False, until=6))
    # fase 5: soffietto a fisarmonica (pareti e tetto piegati)
    hz = ZT + T - 0.06 - (ZB + 0.12)
    sof = [part(zigzag(XJ2, XJ1, -1.19, 0.08, 0.05, 8, -1), frame((0, 0, ZB + 0.12), (1, 0, 0), (0, 1, 0)), t=hz, rough=0.003, warp=0.0, nick=0.0, step=1.0),
           part(zigzag(XJ2, XJ1, 1.19, 0.08, 0.05, 8, 1), frame((0, 0, ZB + 0.12), (1, 0, 0), (0, 1, 0)), t=hz, rough=0.003, warp=0.0, nick=0.0, step=1.0),
           part(zigzag(XJ2, XJ1, ZT, 0.08, 0.05, 8, 1), frame((0, -1.19, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0)), t=2.38, rough=0.003, warp=0.0, nick=0.0, step=1.0)]
    sf = P('Soffietto', 5, sof, paint='grigio', early=True); sf['edge_face'] = True
    out.append(sf)
    # fase 6: ruote e assi
    for cx, nx in AX:
        out.append(P(f'Asse_{nx}', 6, [dowel((cx, -1.27, ZA), (0, 1, 0), 2.54, 0.055)], kind='wood'))
        for s, nm in LATI:
            out.append(P(f'Ruota_{nx}_{nm}', 6, wheel_parts(cx, s, cfg)))
            out.append(P(f'Coprimozzo_{nx}_{nm}', 6, [hubcap_part(cx, s, cfg)], paint='crema'))
    # fase 7: interni
    for i, xc in enumerate((-8.4, -5.3, -4.25, -3.2, -1.0, 1.55, 2.6, 3.65, 4.7)):
        out.append(P(f'Sedili_Sx_{i+1}', 7, seat_parts(xc, 0.30, 1.15, ZF), paint='blu', sheet=False))
    for i, xc in enumerate((-8.4, -5.3, -1.0, 1.5, 4.4)):
        out.append(P(f'Sedili_Dx_{i+1}', 7, seat_parts(xc, -1.15, -0.30, ZF), paint='blu', sheet=False))
    out.append(P('Posto_Guida', 7, seat_parts(7.9, 0.25, 0.95, ZF), paint='blu', sheet=False))
    sc = Vector((8.2, 0.6, 1.5)); sd = Vector((-0.6, 0, 0.8))
    out.append(P('Cruscotto_Volante', 7, [part(rect(8.3, -WI + 0.02, XF - T - 0.02, WI - 0.02), frame((0, 0, 1.16), (1, 0, 0), (0, 1, 0)), t=0.06, rough=0.006),
                                         part(circle(0, 0, 0.22, 24), frame_dir(sc, sd), [circle(0, 0, 0.17, 24)], t=0.04, rough=0.003, nick=0.0)],
                 paint='grigio', sheet=False))
    poles = [dowel((x, -0.95, ZF), (0, 0, 1), ZT - ZF, 0.025)
             for x in (DOOR_F[0] - 0.15, DOOR_M[0] - 0.15, DOOR_M[1] + 0.15, DOOR_P[0] - 0.15, DOOR_P[1] + 0.15)]
    poles += [dowel((-1.5, s*0.80, 2.50), (1, 0, 0), 9.4, 0.022) for s in (-1, 1)]
    poles += [dowel((-8.6, s*0.80, 2.50), (1, 0, 0), 6.0, 0.022) for s in (-1, 1)]
    poles.append(dowel((8.55, 0.6, 1.22), Vector((-0.35, 0, 0.28)), 0.42, 0.025))
    out.append(P('Corrimano_Piantone', 7, poles, kind='wood'))
    # fase 8: dettagli esterni
    out.append(P('Porta_Anteriore', 8, [door_leaf(DOOR_F[0] + 0.02, DOOR_F[1] - 0.02)], paint='grigio'))
    out.append(P('Porta_Centrale', 8, double_door(DOOR_M), paint='grigio'))
    out.append(P('Porta_Posteriore', 8, double_door(DOOR_P), paint='grigio'))
    belts = {-1: [(XJ1 + 0.05, DOOR_M[0] - 0.08), (DOOR_M[1] + 0.08, DOOR_F[0] - 0.08), (DOOR_F[1] + 0.08, XF - 0.07),
                  (XR + 0.07, DOOR_P[0] - 0.08), (DOOR_P[1] + 0.08, XJ2 - 0.05)],
             1: [(XJ1 + 0.05, XF - 0.07), (XR + 0.07, XJ2 - 0.05)]}
    for s, nm in LATI:
        out.append(P(f'Fascia_{nm}', 8, [part(rect(a, 1.27, b, 1.35), frame((0, s*W, 0), (1, 0, 0), (0, 0, 1), (0, s, 0)), t=0.03, rough=0.005)
                                         for a, b in belts[s]], paint='crema'))
        out.append(P(f'Specchietto_{nm}', 8, [part(rect(-0.1, 0, 0.1, 0.34), frame((XF + 0.23, s*1.38, 2.20), (0, 1, 0), (0, 0, 1)), t=0.04, rough=0.004)],
                     paint='grigio'))
        out.append(P(f'Asta_Specchietto_{nm}', 8, [dowel((XF - 0.22, s*1.20, 2.82), (0.45, s*0.18, -0.25), 0.545, 0.022)], kind='wood'))
    Mmuso = frame((XF, 0, 0), (0, 1, 0), (0, 0, 1))
    out.append(P('Griglia_Ant', 8, [part(rect(-0.45, 0.72, 0.45, 1.12), Mmuso, slots(-0.38, 0.38, 0.78, 0.045, 0.085, 4), t=0.04, rough=0.005)], paint='grigio'))
    out.append(P('Fari', 8, [button(s*0.95, 0.92, 0.11, Mmuso) for s in (-1, 1)] + [button(s*0.68, 0.92, 0.09, Mmuso) for s in (-1, 1)], kind='plastic_giallo'))
    out.append(P('Frecce_Ant', 8, [button(s*1.10, 1.16, 0.06, Mmuso) for s in (-1, 1)], kind='plastic_arancio'))
    Mret = frame((XR, 0, 0), (0, -1, 0), (0, 0, 1))
    out.append(P('Griglia_Motore', 8, [part(rect(-0.7, 0.75, 0.7, 1.30), Mret, slots(-0.62, 0.62, 0.80, 0.05, 0.10, 5), t=0.04, rough=0.005)], paint='grigio'))
    out.append(P('Fanali_Post', 8, [button(s*0.98, 1.00, 0.11, Mret) for s in (-1, 1)], kind='plastic_rosso'))
    out.append(P('Frecce_Post', 8, [button(s*0.98, 1.26, 0.07, Mret) for s in (-1, 1)], kind='plastic_arancio'))
    out.append(P('Paraurti_Ant', 8, [part(rect(-W, 0.36, W, 0.62), frame((XF, 0, 0), (0, 1, 0), (0, 0, 1))),
                                      part(rect(XF - T, -W, 9.0, W), frame((0, 0, 0.62), (1, 0, 0), (0, 1, 0)))], paint='grigio'))
    out.append(P('Paraurti_Post', 8, [part(rect(-W, 0.36, W, 0.62), frame((XR, 0, 0), (0, -1, 0), (0, 0, 1))),
                                       part(rect(-9.0, -W, XR + T, W), frame((0, 0, 0.62), (1, 0, 0), (0, 1, 0)))], paint='grigio'))
    out.append(P('Indicatore_Linea', 8, [part(rect(-0.95, Lw - 0.36, 0.95, Lw - 0.07), frame(A, (0, 1, 0), sv, nv), t=0.03, rough=0.004)], paint='grigio'))
    return out

def scritta_linea(s, coll, MAT, loc):
    # numero e destinazione della linea sull'indicatore (pennarello, poi giallo "luminoso")
    if s < 8: return
    A, sv, nv, Lw = windshield_frame()
    M = Matrix.Translation(loc) @ frame(A, (0, 1, 0), sv, nv) @ Matrix.Translation((0, Lw - 0.285, 0.035))
    cu = bpy.data.curves.new('Scritta_Linea', 'FONT'); cu.body = LINEA
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.size = 0.2; cu.extrude = 0.004
    cu.materials.append(MAT['plastic_giallo'] if s >= CFG['final_stage'] else MAT['inchiostro'])
    ob = bpy.data.objects.new(f'F{s}_Scritta_Linea', cu); ob.matrix_world = M; coll.objects.link(ob)

if __name__ == '__main__':
    run_tutorial(CFG, pieces(), scritta_linea)
