# =====================================================================
# cb_minibus.py — Corsa Bis · Minibus di cartone
# Cosa fa: definisce i pezzi del Minibus del GDD (7,5 × 2,2 × 2,9 m
#   reali; in gioco 9,4 × 3,3 × 4,4) e lancia il tutorial in 8 fasi:
#   1 taglio · 2 telaio · 3 scocca · 4 tetto e cofano · 5 ruote e assi ·
#   6 dettagli · 7 pittura · 8 finito.
# Come: stile da cb_lib.py, fasi da cb_tutorial.py; qui solo misure,
#   pezzi e livrea. Pulmino col cofano, come le reference di cartone.
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
W = 1.10; WI = W - T                       # mezza larghezza esterna / interna
XR, XF = -3.66, 3.62                       # retro e muso delle fiancate
ZB, ZH, ZT, ZF = 0.55, 1.55, 2.82, 0.68    # fondo scocca, cofano, tetto, piano pavimento
ZA, RW, RA = 0.50, 0.50, 0.60              # asse ruote, raggio ruota, raggio passaruota
WR, WF = -2.40, 2.85                       # assi (posteriore, anteriore)

CFG = dict(
    root='Minibus_Cartone_Tutorial', Y0=-15.0, SHEET=(0.0, -8.0), sheet_w=15.0, label_dy=3.0,
    STAGE_X={s: 22.0 + (s - 2)*10.0 for s in range(2, 9)}, paint_stage=7, final_stage=8,
    wheel=dict(RW=RW, DT=0.09, ZA=ZA, YW0=0.70, stage=5),
    NOMI={2: 'Telaio', 3: 'Scocca', 4: 'Tetto_Cofano', 5: 'Ruote', 6: 'Dettagli', 7: 'Pittura', 8: 'Finito'},
    TITOLI={1: '1 · Taglio dei pezzi', 2: '2 · Telaio: pavimento e longheroni',
            3: '3 · Scocca: fiancate, frontale e retro', 4: '4 · Tetto e cofano',
            5: '5 · Ruote e assi', 6: '6 · Dettagli: porte, griglia, fari, sedili',
            7: '7 · Pittura', 8: '8 · Minibus finito'})

# ---------- contorni ----------
def side_outline():
    a = math.asin((ZB - ZA)/RA)
    pts = [(XR, ZB)]
    pts += arc(WR, ZA, RA, math.pi - a, a, 16)
    pts += arc(WF, ZA, RA, math.pi - a, a, 16)
    pts += [(XF, ZB), (XF, ZH), (2.62, ZH), (2.42, ZT), (XR, ZT)]
    return pts

def side_windows():
    h = []; x0 = -3.42; wd = 1.06; g = 0.16
    for i in range(4):
        xa = x0 + i*(wd + g); h.append(rect(xa, 1.58, xa + wd, 2.55))
    h.append(rect(1.52, 1.58, 2.12, 2.55))
    return h

# ---------- pezzi ----------
def pieces():
    out = []; LATI = ((-1, 'Dx'), (1, 'Sx')); cfg = CFG
    # fase 2: telaio
    out.append(P('Pavimento', 2, [part(rect(XR + T, -WI, 3.54, WI), frame((0, 0, ZF), (1, 0, 0), (0, -1, 0)))]))
    for s, nm in LATI:
        out.append(P(f'Longherone_{nm}', 2, [part(rect(-3.3, 0.34, 3.3, 0.60), frame((0, s*0.58, 0), (1, 0, 0), (0, 0, 1), (0, s, 0)),
                                                 [circle(WR, ZA, 0.075, 16), circle(WF, ZA, 0.075, 16)])]))
    # fase 3: scocca
    for s, nm in LATI:
        out.append(P(f'Fiancata_{nm}', 3, [part(side_outline(), frame((0, s*WI, 0), (1, 0, 0), (0, 0, 1), (0, s, 0)), side_windows())], paint='arancio'))
    A = Vector((2.62, 0, ZH)); B = Vector((2.42, 0, ZT)); sv = B - A; Lfp = sv.length; sv.normalize()
    nv = Vector((sv.z, 0, -sv.x))
    out.append(P('Frontale_Parabrezza', 3, [part(rect(-WI, 0, WI, Lfp), frame(A - nv*T, (0, 1, 0), sv, nv),
                                               [rect(-0.92, 0.22, -0.06, 1.12), rect(0.06, 0.22, 0.92, 1.12)])], paint='arancio', early=True))
    out.append(P('Retro', 3, [part(rect(-WI, ZB, WI, ZT), frame((XR + T, 0, 0), (0, -1, 0), (0, 0, 1)), [rect(-0.8, 1.85, 0.8, 2.55)])],
                 paint='arancio', early=True))
    tapes = []
    for s in (-1, 1):
        for z in (1.0, 2.25):
            tapes.append(tape_L((XR, s*W, z), (0, 0, 1), (1, 0, 0), (0, s, 0), (0, -s, 0), (-1, 0, 0), seed=int(z*10) + s))
    out.append(P('Nastro_Scocca', 3, [dict(geo=g, M=Matrix()) for g in tapes], kind='tape', sheet=False, until=5))
    # fase 4: tetto e cofano
    out.append(P('Tetto', 4, [part(rect(-3.72, -W, 2.55, W), frame((0, 0, ZT), (1, 0, 0), (0, 1, 0)))], paint='crema', early=True))
    out.append(P('Cofano', 4, [part(rect(2.54, -WI, 3.62, WI), frame((0, 0, ZH - T), (1, 0, 0), (0, 1, 0)))], paint='arancio', early=True))
    out.append(P('Muso', 4, [part(rect(-WI, ZB, WI, ZH - T), frame((3.54, 0, 0), (0, 1, 0), (0, 0, 1)))], paint='arancio', early=True))
    tapes = []
    for s in (-1, 1):
        for x in (-2.6, -0.7, 1.3):
            tapes.append(tape_L((x, s*W, ZT + T), (1, 0, 0), (0, -s, 0), (0, 0, 1), (0, 0, -1), (0, s, 0), seed=int(x*10) + 3*s))
        tapes.append(tape_L((3.1, s*W, ZH), (1, 0, 0), (0, -s, 0), (0, 0, 1), (0, 0, -1), (0, s, 0), seed=31 + s))
        tapes.append(tape_L((XF, s*W, 1.05), (0, 0, 1), (-1, 0, 0), (0, s, 0), (0, -s, 0), (1, 0, 0), seed=41 + s))
    out.append(P('Nastro_Tetto_Cofano', 4, [dict(geo=g, M=Matrix()) for g in tapes], kind='tape', sheet=False, until=5))
    # fase 5: ruote e assi
    for cx, nx in ((WR, 'Post'), (WF, 'Ant')):
        out.append(P(f'Asse_{nx}', 5, [dowel((cx, -1.12, ZA), (0, 1, 0), 2.24, 0.055)], kind='wood'))
        for s, nm in LATI:
            out.append(P(f'Ruota_{nx}_{nm}', 5, wheel_parts(cx, s, cfg)))
            out.append(P(f'Coprimozzo_{nx}_{nm}', 5, [hubcap_part(cx, s, cfg)], paint='crema'))
    # fase 6: dettagli
    for s, nm in LATI:
        out.append(P(f'Porta_{nm}', 6, [part(rect(1.42, 0.62, 2.22, 2.66), frame((0, s*W, 0), (1, 0, 0), (0, 0, 1), (0, s, 0)),
                                             [rect(1.50, 1.56, 2.14, 2.57)], t=0.04),
                                        part(rect(1.54, 1.30, 1.74, 1.37), frame((0, s*(W + 0.04), 0), (1, 0, 0), (0, 0, 1), (0, s, 0)),
                                             t=0.03, rough=0.003)], paint='arancio'))
        out.append(P(f'Fascia_{nm}', 6, [part(rect(-3.6, 1.40, 1.36, 1.49), frame((0, s*W, 0), (1, 0, 0), (0, 0, 1), (0, s, 0)), t=0.03, rough=0.005)],
                     paint='crema'))
        out.append(P(f'Specchietto_{nm}', 6, [part(rect(-0.1, 0, 0.1, 0.3), frame((2.74, s*1.30, 1.88), (0, 1, 0), (0, 0, 1)), t=0.04, rough=0.004)],
                     paint='grigio'))
        out.append(P(f'Asta_Specchietto_{nm}', 6, [dowel((2.48, s*1.08, 2.04), (0.24, s*0.24, 0), 0.34, 0.022)], kind='wood'))
    Mmuso = frame((3.62, 0, 0), (0, 1, 0), (0, 0, 1))
    out.append(P('Griglia', 6, [part(rect(-0.5, 0.78, 0.5, 1.32), Mmuso, slots(-0.42, 0.42, 0.85, 0.05, 0.095, 5), t=0.04, rough=0.005)], paint='grigio'))
    out.append(P('Fari', 6, [button(s*0.78, 1.15, 0.13, Mmuso) for s in (-1, 1)], kind='plastic_giallo'))
    out.append(P('Frecce_Ant', 6, [button(s*0.78, 0.90, 0.07, Mmuso) for s in (-1, 1)], kind='plastic_arancio'))
    Mret = frame((XR, 0, 0), (0, -1, 0), (0, 0, 1))
    out.append(P('Fanali_Post', 6, [button(s*0.82, 0.98, 0.11, Mret) for s in (-1, 1)], kind='plastic_rosso'))
    out.append(P('Frecce_Post', 6, [button(s*0.82, 1.24, 0.07, Mret) for s in (-1, 1)], kind='plastic_arancio'))
    out.append(P('Paraurti_Ant', 6, [part(rect(-W, 0.42, W, 0.72), frame((3.67, 0, 0), (0, 1, 0), (0, 0, 1))),
                                      part(rect(3.58, -W, 3.75, W), frame((0, 0, 0.72), (1, 0, 0), (0, 1, 0)))], paint='grigio'))
    out.append(P('Paraurti_Post', 6, [part(rect(-W, 0.42, W, 0.72), frame((-3.67, 0, 0), (0, -1, 0), (0, 0, 1))),
                                       part(rect(-3.75, -W, -3.62, W), frame((0, 0, 0.72), (1, 0, 0), (0, 1, 0)))], paint='grigio'))
    for i, xc in enumerate((-2.89, -1.67, -0.45, 0.77)):
        pr = []
        for yc in (-0.5, 0.5):
            pr += seat_parts(xc, yc - 0.38, yc + 0.38, ZF, zs=1.02, zb=1.66)
        out.append(P(f'Sedili_Fila_{i+1}', 6, pr, paint='blu', sheet=False))
    return out

if __name__ == '__main__':
    run_tutorial(CFG, pieces())
