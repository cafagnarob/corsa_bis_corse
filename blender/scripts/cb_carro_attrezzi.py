# =====================================================================
# cb_carro_attrezzi.py — Corsa Bis · Carro attrezzi di cartone
# Cosa fa: definisce i pezzi del carro attrezzi del GDD (8,5 × 2,5 × 3,2 m
#   reali; in gioco 10,6 × 3,75 × 4,8; Fase 2: guasti e officina) e lancia
#   il tutorial in 9 fasi: 1 taglio · 2 telaio · 3 cabina e cofano ·
#   4 cassone · 5 gru · 6 ruote e assi · 7 dettagli · 8 pittura · 9 finito.
# Come: stesso stile e motore degli altri mezzi. Cabina col cofano davanti,
#   cassone a sponde basse dietro, gru con torre a due piastre, braccio
#   inclinato verso il retro, argano di legno, cavo di spago e gancio di
#   cartone spesso. Livrea dell'azienda (arancio, crema, grigio scuro).
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
W = 1.25; WI = W - T                       # mezza larghezza esterna / interna
XB, XC, XH, XF = -3.40, 1.55, 3.30, 4.12   # retro cassone (corto: la gru sporge dietro), retro cabina, base parabrezza, muso
ZB, ZP, ZS, ZH, ZT = 0.55, 0.70, 1.25, 1.60, 2.90   # fondo scocca, pianale, sponde, cofano, tetto cabina
ZA, RW, RA = 0.50, 0.50, 0.60              # asse ruote, raggio ruota, raggio passaruota
WR, WF = -2.30, 3.30                       # assi
P0 = Vector((0.80, 2.30)); P1 = Vector((-4.20, 3.00)); HB = 0.30   # gru: perno, punta (oltre il retro: il gancio pende fuori dal cassone), altezza braccio

CFG = dict(
    root='CarroAttrezzi_Cartone_Tutorial', Y0=-15.0, SHEET=(0.0, -8.0), sheet_w=16.0, label_dy=3.2,
    STAGE_X={s: 26.0 + (s - 2)*12.0 for s in range(2, 10)}, paint_stage=8, final_stage=9,
    wheel=dict(RW=RW, DT=0.09, ZA=ZA, YW0=0.75, stage=6),
    NOMI={2: 'Telaio', 3: 'Cabina', 4: 'Cassone', 5: 'Gru', 6: 'Ruote', 7: 'Dettagli', 8: 'Pittura', 9: 'Finito'},
    TITOLI={1: '1 · Taglio dei pezzi', 2: '2 · Telaio: pianale, longheroni, passaruota',
            3: '3 · Cabina e cofano', 4: '4 · Cassone: sponde e cassette attrezzi',
            5: '5 · Gru: torre, braccio, argano, spago e gancio', 6: '6 · Ruote e assi',
            7: '7 · Dettagli: porte, fari, lampeggianti, paraurti', 8: '8 · Pittura', 9: '9 · Carro attrezzi finito'})

# ---------- contorni ----------
def cab_side():
    pts = [(XC, ZB)] + arc(WF, ZA, RA, math.pi, 0.0, 16)
    return pts + [(XF, ZB), (XF, ZH), (XH, ZH), (XH - 0.15, ZT), (XC, ZT)]

def body_side():
    return [(XB, ZB)] + arc(WR, ZA, RA, math.pi, 0.0, 16) + [(1.45, ZB), (1.45, ZS), (XB, ZS)]

def beam(p0, p1, h):
    # rettangolo inclinato lungo p0 -> p1 (piano x-z)
    d = (p1 - p0).normalized(); n = Vector((-d.y, d.x))*h/2
    return [tuple(p0 - n), tuple(p1 - n), tuple(p1 + n), tuple(p0 + n)]

def hook_outline():
    # gancio a J ritagliato nel cartone spesso
    pts = [(-0.05, 0.45), (-0.05, 0.0)] + arc(0.15, 0.0, 0.20, math.pi, 2*math.pi, 12)[1:]
    pts += [(0.35, 0.08), (0.25, 0.08)] + arc(0.15, 0.0, 0.10, 2*math.pi, math.pi, 8) + [(0.05, 0.45)]
    return pts

def windshield_frame():
    A = Vector((XH, 0, ZH)); B = Vector((XH - 0.15, 0, ZT)); sv = B - A; L = sv.length; sv.normalize()
    return A, sv, Vector((sv.z, 0, -sv.x)), L

# ---------- pezzi ----------
def pieces():
    out = []; LATI = ((-1, 'Dx'), (1, 'Sx')); cfg = CFG
    def side_frame(s, y=None): return frame((0, s*(WI if y is None else y), 0), (1, 0, 0), (0, 0, 1), (0, s, 0))
    # fase 2: telaio
    out.append(P('Pianale', 2, [part(rect(XB + T, -WI, XF - T, WI), frame((0, 0, ZP - T), (1, 0, 0), (0, 1, 0)))], paint='grigio'))   # faccia esterna in alto: si vede nel cassone
    for s, nm in LATI:
        out.append(P(f'Longherone_{nm}', 2, [part(rect(-3.25, 0.34, 3.7, ZP - T), side_frame(s, 0.60), [circle(WR, ZA, 0.075, 16), circle(WF, ZA, 0.075, 16)])]))
    for cx, nx in ((WR, 'Post'), (WF, 'Ant')):
        out.append(P(f'Passaruota_{nx}_Sx', 2, box_parts(cx - 0.62, cx + 0.62, 0.72, WI, ZP, 1.14, t=0.06), paint='grigio'))
        out.append(P(f'Passaruota_{nx}_Dx', 2, box_parts(cx - 0.62, cx + 0.62, -WI, -0.72, ZP, 1.14, t=0.06), paint='grigio'))
    # fase 3: cabina e cofano
    for s, nm in LATI:
        out.append(P(f'Fiancata_Cabina_{nm}', 3, [part(cab_side(), side_frame(s), [rect(1.75, 1.85, 2.56, 2.65)])], paint='arancio'))
    out.append(P('Retro_Cabina', 3, [part(rect(-WI, ZB, WI, ZT), frame((XC + T, 0, 0), (0, -1, 0), (0, 0, 1)), [rect(-0.5, 2.0, 0.5, 2.6)])], paint='arancio', early=True))
    A, sv, nv, Lw = windshield_frame()
    out.append(P('Parabrezza', 3, [part(rect(-WI, 0, WI, Lw), frame(A - nv*T, (0, 1, 0), sv, nv), [rect(-1.08, 0.12, -0.03, 1.15), rect(0.03, 0.12, 1.08, 1.15)])],
                 paint='arancio', early=True))
    out.append(P('Cofano', 3, [part(rect(XH - 0.08, -WI, XF, WI), frame((0, 0, ZH - T), (1, 0, 0), (0, 1, 0)))], paint='arancio', early=True))
    out.append(P('Muso', 3, [part(rect(-WI, ZB, WI, ZH - T), frame((XF - T, 0, 0), (0, 1, 0), (0, 0, 1)))], paint='arancio', early=True))
    out.append(P('Tetto_Cabina', 3, [part(rect(XC - 0.05, -W, XH - 0.09, W), frame((0, 0, ZT), (1, 0, 0), (0, 1, 0)))], paint='crema', early=True))
    tapes = []
    for s in (-1, 1):
        for z in (1.2, 2.4):
            tapes.append(tape_L((XC, s*W, z), (0, 0, 1), (1, 0, 0), (0, s, 0), (0, -s, 0), (-1, 0, 0), seed=int(z*10) + s))
        tapes.append(tape_L((XF, s*W, 1.0), (0, 0, 1), (-1, 0, 0), (0, s, 0), (0, -s, 0), (1, 0, 0), seed=41 + s))
        tapes.append(tape_L((2.4, s*W, ZT + T), (1, 0, 0), (0, -s, 0), (0, 0, 1), (0, 0, -1), (0, s, 0), seed=51 + s))
    out.append(P('Nastro_Cabina', 3, [dict(geo=g, M=Matrix()) for g in tapes], kind='tape', sheet=False, until=6))
    # fase 4: cassone
    for s, nm in LATI:
        out.append(P(f'Sponda_{nm}', 4, [part(body_side(), side_frame(s))], paint='grigio'))
        out.append(P(f'Cassetta_Attrezzi_{nm}', 4, box_parts(-1.5, 0.5, 0.88, 1.20, 0.28, 0.62, t=0.06) if s > 0 else
                     box_parts(-1.5, 0.5, -1.20, -0.88, 0.28, 0.62, t=0.06), paint='grigio'))
    out.append(P('Sponda_Posteriore', 4, [part(rect(-WI, ZB, WI, ZS), frame((XB + T, 0, 0), (0, -1, 0), (0, 0, 1)))], paint='grigio', early=True))
    tapes = [tape_L((XB, s*W, 0.9), (0, 0, 1), (1, 0, 0), (0, s, 0), (0, -s, 0), (-1, 0, 0), seed=61 + s) for s in (-1, 1)]
    out.append(P('Nastro_Cassone', 4, [dict(geo=g, M=Matrix()) for g in tapes], kind='tape', sheet=False, until=6))
    # fase 5: gru
    tower = [(-0.30, ZP), (1.35, ZP), (1.35, 1.20), (1.00, 2.55), (0.55, 2.55)]
    out.append(P('Torre_Gru', 5, [part(tower, side_frame(s, 0.30), [circle(P0.x, P0.y, 0.05, 12)]) for s in (-1, 1)], paint='arancio', early=True))
    d = (P1 - P0).normalized(); up = Vector((d.y, -d.x)) if d.x < 0 else Vector((-d.y, d.x)); p0e = P0 - d*0.25; Lb = (P1 - p0e).length
    plates = [part(beam(p0e, P1, HB), side_frame(s, 0.10), [circle(P0.x, P0.y, 0.05, 12)]) for s in (-1, 1)]
    top_o = Vector((p0e.x + up.x*HB/2, 0, p0e.y + up.y*HB/2))
    plates.append(part(rect(0, -0.18, Lb, 0.18), frame(top_o, (d.x, 0, d.y), (0, -1, 0)), t=0.06))
    out.append(P('Braccio_Gru', 5, plates, paint='arancio', early=True))
    pist_a = Vector((0.20, 0, 1.00)); pb = P0 + d*1.5 - up*(HB/2); pist_b = Vector((pb.x, 0, pb.y))
    out.append(P('Perno_Argano_Pistone', 5, [dowel((P0.x, -0.45, P0.y), (0, 1, 0), 0.90, 0.045),
                                             dowel((P1.x, -0.22, P1.y), (0, 1, 0), 0.44, 0.04),
                                             dowel((1.15, -0.30, 1.45), (0, 1, 0), 0.60, 0.13),
                                             dowel(pist_a, pist_b - pist_a, (pist_b - pist_a).length, 0.06)], kind='wood'))
    ca = Vector((1.15, 0, 1.58)); cb = Vector((P1.x, 0, P1.y - 0.15)); hz = 1.20
    out.append(P('Cavo_Spago', 5, [dowel(ca, cb - ca, (cb - ca).length, 0.014), dowel(cb, (0, 0, -1), cb.z - (hz + 0.45), 0.014)], kind='string', sheet=False))
    out.append(P('Gancio', 5, [part(hook_outline(), frame((P1.x, -0.03, hz), (1, 0, 0), (0, 0, 1), (0, 1, 0)), [circle(0, 0.38, 0.025, 10)], t=0.06, rough=0.004, nick=0.01)],
                 paint='grigio'))
    # fase 6: ruote e assi
    for cx, nx in ((WR, 'Post'), (WF, 'Ant')):
        out.append(P(f'Asse_{nx}', 6, [dowel((cx, -1.18, ZA), (0, 1, 0), 2.36, 0.055)], kind='wood'))
        for s, nm in LATI:
            out.append(P(f'Ruota_{nx}_{nm}', 6, wheel_parts(cx, s, cfg)))
            out.append(P(f'Coprimozzo_{nx}_{nm}', 6, [hubcap_part(cx, s, cfg)], paint='crema'))
    # fase 7: dettagli
    for s, nm in LATI:
        out.append(P(f'Porta_{nm}', 7, [part(rect(1.65, 0.62, 2.66, 2.78), side_frame(s, W), [rect(1.72, 1.82, 2.59, 2.68)], t=0.04),
                                        part(rect(1.75, 1.45, 1.95, 1.52), side_frame(s, W + 0.04), t=0.03, rough=0.003)], paint='arancio'))
        out.append(P(f'Specchietto_{nm}', 7, [part(rect(-0.1, 0, 0.1, 0.32), frame((3.37, s*1.45, 2.15), (0, 1, 0), (0, 0, 1)), t=0.04, rough=0.004)], paint='grigio'))
        out.append(P(f'Asta_Specchietto_{nm}', 7, [dowel((3.10, s*1.22, 2.50), (0.25, s*0.22, -0.10), 0.34, 0.022)], kind='wood'))
    Mmuso = frame((XF, 0, 0), (0, 1, 0), (0, 0, 1))
    out.append(P('Griglia', 7, [part(rect(-0.6, 0.72, 0.6, 1.42), Mmuso, slots(-0.52, 0.52, 0.78, 0.055, 0.105, 6), t=0.04, rough=0.005)], paint='grigio'))
    out.append(P('Fari', 7, [button(s*0.88, 1.05, 0.14, Mmuso) for s in (-1, 1)], kind='plastic_giallo'))
    out.append(P('Frecce_Ant', 7, [button(s*0.88, 1.34, 0.07, Mmuso) for s in (-1, 1)], kind='plastic_arancio'))
    Mret = frame((XB, 0, 0), (0, -1, 0), (0, 0, 1))
    out.append(P('Fanali_Post', 7, [button(s*0.90, 0.95, 0.11, Mret) for s in (-1, 1)], kind='plastic_rosso'))
    out.append(P('Lampeggianti', 7, [part(circle(2.4, s*0.6, 0.14, 20), frame((0, 0, ZT + T), (1, 0, 0), (0, 1, 0)), t=0.14, rough=0.002, warp=0.0, nick=0.0)
                                     for s in (-1, 1)], kind='plastic_arancio'))
    out.append(P('Paraurti_Ant', 7, [part(rect(-W, 0.36, W, 0.66), frame((XF + 0.05, 0, 0), (0, 1, 0), (0, 0, 1))),
                                      part(rect(XF - T, -W, 4.25, W), frame((0, 0, 0.66), (1, 0, 0), (0, 1, 0)))], paint='grigio'))
    out.append(P('Barra_Posteriore', 7, [part(rect(-1.1, 0.32, 1.1, ZB), frame((XB - 0.05, 0, 0), (0, -1, 0), (0, 0, 1)))], paint='grigio'))
    sc = Vector((2.85, 0.5, 1.75)); sd = Vector((-0.6, 0, 0.8))
    out.append(P('Posto_Guida', 7, seat_parts(2.0, -0.95, 0.95, ZP, zs=1.15, zb=1.85), paint='blu', sheet=False))
    out.append(P('Cruscotto_Volante', 7, [part(rect(2.95, -WI + 0.02, XH - 0.1, WI - 0.02), frame((0, 0, 1.50), (1, 0, 0), (0, 1, 0)), t=0.06, rough=0.006),
                                         part(circle(0, 0, 0.20, 24), frame_dir(sc, sd), [circle(0, 0, 0.155, 24)], t=0.04, rough=0.003, nick=0.0)],
                 paint='grigio', sheet=False))
    out.append(P('Piantone', 7, [dowel((3.15, 0.5, 1.50), Vector((-0.30, 0, 0.25)), 0.39, 0.025)], kind='wood'))
    return out

if __name__ == '__main__':
    run_tutorial(CFG, pieces())
