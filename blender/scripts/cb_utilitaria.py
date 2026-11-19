# =====================================================================
# cb_utilitaria.py — Corsa Bis · Utilitaria di cartone (auto del traffico)
# Cosa fa: definisce i pezzi dell'utilitaria del GDD (3,6 × 1,6 × 1,5 m
#   reali; in gioco 5,4 × 2,4 × 2,25) e lancia il tutorial in 8 fasi:
#   1 taglio · 2 telaio · 3 scocca · 4 tetto e cofano · 5 ruote e assi ·
#   6 dettagli · 7 pittura · 8 finito.
# Come: stesso stile e motore degli altri mezzi. Dalla reference: berlina
#   a 4 porte squadrata, cartone kraft al naturale, porte disegnate come
#   pannelli sovrapposti, fari a bottone gialli, ruote spesse con il
#   coprimozzo rosso, sedili azzurri. Il colore della carrozzeria si
#   cambia con CARROZZERIA (None = kraft naturale, es. 'verde' per lo
#   stato del traffico del GDD).
# Uso: apri il file nel Text Editor e premi Run Script; carica da
#   solo cb_lib.py e cb_tutorial.py dalla stessa cartella.
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

if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'run_tutorial' not in globals(): exec(_carica('cb_tutorial.py'))

# ---------- misure (metri reali) ----------
W = 0.80; WI = W - T                        # mezza larghezza esterna / interna
XR, XF = -1.66, 1.66                        # retro e muso della scocca (+ paraurti = 3,6 m)
ZB, ZH, ZT, ZF = 0.32, 0.84, 1.42, 0.46     # fondo scocca, cofano, tetto, piano pavimento
ZL = 0.98                                   # linea di cintura (base dei finestrini)
XA0, XA1 = 0.85, 0.36                       # montante anteriore: base (sul cofano) e cima (sul tetto)
XP0, XP1 = XR, -1.54                        # lunotto: base e cima
ZA, RW, RA = 0.30, 0.30, 0.36               # asse ruote, raggio ruota, raggio passaruota
WR, WF = -1.15, 1.20                        # assi
CARROZZERIA = None                          # None = kraft; oppure 'arancio', 'crema', 'blu', 'rosso', 'azzurro'...

CFG = dict(
    root='Utilitaria_Cartone_Tutorial', Y0=-15.0, SHEET=(0.0, -8.0), sheet_w=8.0, label_dy=2.0,
    STAGE_X={s: 13.0 + (s - 2)*6.0 for s in range(2, 9)}, paint_stage=7, final_stage=8,
    wheel=dict(RW=RW, DT=0.06, ZA=ZA, YW0=0.54, stage=5, RH=0.14, RA_ASSE=0.04),
    NOMI={2: 'Telaio', 3: 'Scocca', 4: 'Tetto_Cofano', 5: 'Ruote', 6: 'Dettagli', 7: 'Pittura', 8: 'Finito'},
    TITOLI={1: '1 · Taglio dei pezzi', 2: '2 · Telaio', 3: '3 · Scocca', 4: '4 · Tetto e cofano',
            5: '5 · Ruote e assi', 6: '6 · Dettagli', 7: '7 · Pittura', 8: '8 · Utilitaria finita'})

# ---------- contorni ----------
def side_outline():
    a = math.asin((ZB - ZA)/RA)
    pts = [(XR, ZB)] + arc(WR, ZA, RA, math.pi - a, a, 14) + arc(WF, ZA, RA, math.pi - a, a, 14)
    return pts + [(XF, ZB), (XF, ZH), (XA0, ZH), (XA1, ZT), (XP1, ZT), (XP0, ZL)]

def pillar_x(z):
    # x del montante anteriore all'altezza z
    return XA0 + (XA1 - XA0)*(z - ZH)/(ZT - ZH)

FIN_ANT = [(0.06, ZL), (pillar_x(ZL) - 0.09, ZL), (pillar_x(1.32) - 0.09, 1.32), (0.06, 1.32)]
FIN_POST = rect(-0.68, ZL, -0.10, 1.32)
FIN_TERZO = [(-1.44, ZL), (-0.86, ZL), (-0.86, 1.32), (-1.36, 1.32)]

def slant(A, B, outward):
    # pannello inclinato da A a B (piano x-z): direzione lungo il pannello e normale verso l'esterno
    A = Vector(A); B = Vector(B); sv = B - A; L = sv.length; sv.normalize()
    nv = Vector((sv.z, 0, -sv.x))
    if nv.x*outward < 0: nv = -nv
    return A, sv, nv, L

def pieces():
    out = []; LATI = ((-1, 'Dx'), (1, 'Sx')); cfg = CFG; pc_ = CARROZZERIA
    side = lambda s, y: frame((0, s*y, 0), (1, 0, 0), (0, 0, 1), (0, s, 0))
    # fase 2: telaio
    out.append(P('Pavimento', 2, [part(rect(XR + T, -WI, XF - T, WI), frame((0, 0, ZF), (1, 0, 0), (0, -1, 0)))]))
    for s, nm in LATI:
        out.append(P(f'Longherone_{nm}', 2, [part(rect(-1.55, 0.16, 1.55, ZF - T), side(s, 0.42), [circle(WR, ZA, 0.05, 14), circle(WF, ZA, 0.05, 14)])]))
    for cx, nx in ((WR, 'Post'), (WF, 'Ant')):
        out.append(P(f'Passaruota_{nx}_Sx', 2, box_parts(cx - 0.38, cx + 0.38, 0.46, WI, ZF, 0.74, t=0.05)))
        out.append(P(f'Passaruota_{nx}_Dx', 2, box_parts(cx - 0.38, cx + 0.38, -WI, -0.46, ZF, 0.74, t=0.05)))
    # fase 3: scocca
    for s, nm in LATI:
        out.append(P(f'Fiancata_{nm}', 3, [part(side_outline(), side(s, WI), [FIN_ANT, FIN_POST, FIN_TERZO])], paint=pc_))
    out.append(P('Muso', 3, [part(rect(-WI, ZB, WI, ZH - T), frame((XF - T, 0, 0), (0, 1, 0), (0, 0, 1)))], paint=pc_, early=True))
    out.append(P('Retro', 3, [part(rect(-WI, ZB, WI, ZL), frame((XR + T, 0, 0), (0, -1, 0), (0, 0, 1)))], paint=pc_, early=True))
    A, sv, nv, L = slant((XA0, 0, ZH), (XA1, 0, ZT), 1)
    out.append(P('Parabrezza', 3, [part(rect(-WI, 0, WI, L), frame(A - nv*T, (0, 1, 0), sv, nv), [rect(-0.62, 0.08, 0.62, L - 0.08)])], paint=pc_, early=True))
    A, sv, nv, L = slant((XP0, 0, ZL), (XP1, 0, ZT), -1)
    out.append(P('Lunotto', 3, [part(rect(-WI, 0, WI, L), frame(A - nv*T, (0, -1, 0), sv, nv), [rect(-0.55, 0.07, 0.55, L - 0.08)])], paint=pc_, early=True))
    tapes = []
    for s in (-1, 1):
        tapes.append(tape_L((XR, s*W, 0.62), (0, 0, 1), (1, 0, 0), (0, s, 0), (0, -s, 0), (-1, 0, 0), w=0.10, la=0.09, lb=0.09, seed=3 + s))
        tapes.append(tape_L((XF, s*W, 0.58), (0, 0, 1), (-1, 0, 0), (0, s, 0), (0, -s, 0), (1, 0, 0), w=0.10, la=0.09, lb=0.09, seed=7 + s))
    out.append(P('Nastro_Scocca', 3, [dict(geo=g, M=Matrix()) for g in tapes], kind='tape', sheet=False, until=5))
    # fase 4: tetto e cofano
    out.append(P('Tetto', 4, [part(rect(XP1 - 0.04, -W, XA1 + 0.04, W), frame((0, 0, ZT), (1, 0, 0), (0, 1, 0)))], paint=pc_, early=True))
    out.append(P('Cofano', 4, [part(rect(XA0 - 0.04, -WI, XF, WI), frame((0, 0, ZH - T), (1, 0, 0), (0, 1, 0))),
                               part(rect(XA0 + 0.10, -0.04, XF - 0.06, 0.04), frame((0, 0, ZH), (1, 0, 0), (0, 1, 0)), t=0.02, rough=0.003)],
                 paint=pc_, early=True))
    tapes = []
    for s in (-1, 1):
        for x in (-1.0, 0.0):
            tapes.append(tape_L((x, s*W, ZT + T), (1, 0, 0), (0, -s, 0), (0, 0, 1), (0, 0, -1), (0, s, 0), w=0.10, la=0.09, lb=0.09, seed=int(x*10) + 11*s))
        tapes.append(tape_L((1.35, s*W, ZH), (1, 0, 0), (0, -s, 0), (0, 0, 1), (0, 0, -1), (0, s, 0), w=0.10, la=0.09, lb=0.09, seed=21 + s))
    out.append(P('Nastro_Tetto_Cofano', 4, [dict(geo=g, M=Matrix()) for g in tapes], kind='tape', sheet=False, until=5))
    # fase 5: ruote e assi
    for cx, nx in ((WR, 'Post'), (WF, 'Ant')):
        out.append(P(f'Asse_{nx}', 5, [dowel((cx, -0.84, ZA), (0, 1, 0), 1.68, 0.04)], kind='wood'))
        for s, nm in LATI:
            out.append(P(f'Ruota_{nx}_{nm}', 5, wheel_parts(cx, s, cfg)))
            out.append(P(f'Coprimozzo_{nx}_{nm}', 5, [hubcap_part(cx, s, cfg)], paint='rosso', early=True))
    # fase 6: dettagli
    for s, nm in LATI:
        porta_ant = [(-0.01, 0.40), (0.80, 0.40), (0.80, ZH + 0.02), (pillar_x(1.38), 1.38), (-0.01, 1.38)]
        out.append(P(f'Porta_Ant_{nm}', 6, [part(porta_ant, side(s, W), [FIN_ANT], t=0.03),
                                            part(rect(0.52, 0.86, 0.68, 0.91), side(s, W + 0.03), t=0.025, rough=0.002, nick=0.005)], paint=pc_))
        out.append(P(f'Porta_Post_{nm}', 6, [part(rect(-0.76, 0.40, -0.03, 1.38), side(s, W), [FIN_POST], t=0.03),
                                             part(rect(-0.25, 0.86, -0.09, 0.91), side(s, W + 0.03), t=0.025, rough=0.002, nick=0.005)], paint=pc_))
        out.append(P(f'Specchietto_{nm}', 6, [part(rect(-0.07, 0, 0.07, 0.11), frame((XA0 - 0.05, s*0.94, ZL + 0.02), (0, 1, 0), (0, 0, 1)), t=0.05, rough=0.003, nick=0.01)], paint=pc_))
        out.append(P(f'Asta_Specchietto_{nm}', 6, [dowel((XA0 - 0.03, s*0.78, ZL + 0.06), (0, s, 0), 0.12, 0.012)], kind='wood'))
    Mmuso = frame((XF, 0, 0), (0, 1, 0), (0, 0, 1))
    out.append(P('Griglia', 6, [part(rect(-0.30, 0.50, 0.30, 0.76), Mmuso, slots(-0.25, 0.25, 0.55, 0.025, 0.05, 4), t=0.03, rough=0.003, nick=0.01)], paint=pc_))
    out.append(P('Fari', 6, [button(s*0.55, 0.63, 0.11, Mmuso) for s in (-1, 1)], kind='plastic_giallo'))
    Mret = frame((XR, 0, 0), (0, -1, 0), (0, 0, 1))
    out.append(P('Fanali_Post', 6, [button(s*0.58, 0.78, 0.08, Mret) for s in (-1, 1)], kind='plastic_rosso'))
    out.append(P('Paraurti_Ant', 6, [part(rect(-W, 0.26, W, 0.42), frame((XF + 0.06, 0, 0), (0, 1, 0), (0, 0, 1))),
                                      part(rect(XF - T, -W, XF + 0.14, W), frame((0, 0, 0.42), (1, 0, 0), (0, 1, 0)))], paint=pc_))
    out.append(P('Paraurti_Post', 6, [part(rect(-W, 0.26, W, 0.42), frame((XR - 0.06, 0, 0), (0, -1, 0), (0, 0, 1))),
                                       part(rect(XR - 0.14, -W, XR + T, W), frame((0, 0, 0.42), (1, 0, 0), (0, 1, 0)))], paint=pc_))
    out.append(P('Sedili_Ant', 6, seat_parts(0.10, 0.06, 0.62, ZF, zs=0.72, zb=1.18) + seat_parts(0.10, -0.62, -0.06, ZF, zs=0.72, zb=1.18), paint='azzurro', sheet=False))
    out.append(P('Divano_Post', 6, seat_parts(-0.92, -0.62, 0.62, ZF, zs=0.72, zb=1.18), paint='azzurro', sheet=False))
    sc = Vector((0.48, 0.34, 0.98)); sd = Vector((-0.6, 0, 0.8))
    out.append(P('Cruscotto_Volante', 6, [part(rect(0.60, -WI + 0.02, XA0 - 0.04, WI - 0.02), frame((0, 0, 0.86), (1, 0, 0), (0, 1, 0)), t=0.04, rough=0.004),
                                          part(circle(0, 0, 0.13, 20), frame_dir(sc, sd), [circle(0, 0, 0.10, 20)], t=0.03, rough=0.002, nick=0.0)],
                 paint='grigio', sheet=False))
    return out

if __name__ == '__main__':
    run_tutorial(CFG, pieces())
