# =====================================================================
# cb_tram.py — Corsa Bis · Tram di cartone
# Cosa fa: definisce i pezzi del tram del GDD (32 × 2,4 × 3,5 m reali; in
#   gioco 40 × 3,6 × 5,25; solo viali con binari) e lancia il tutorial in
#   10 fasi: 1 taglio · 2 telaio e carrelli · 3 casse · 4 tetti e
#   lanternini · 5 soffietti · 6 ruote e assi · 7 interni · 8 dettagli ·
#   9 pittura · 10 finito.
# Come: stesso stile e motore degli altri mezzi. Il GDD chiede un tram
#   "come un trenino": tre casse (A davanti, B centrale, C dietro) unite da
#   due soffietti, tre carrelli a due assi. Dalla reference: tetto con il
#   lanternino a finestrelle, due lire di presa inclinate sulla cassa
#   centrale, fascia bassa azzurra e parte alta crema, porte doppie.
#   Tram bidirezionale: cabina e fari a entrambe le testate, porte sui
#   due lati.
# Uso: apri questo file nel Text Editor e premi Run Script; carica da
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
W = 1.20; WI = W - T                         # mezza larghezza esterna / interna
XE = 15.92                                   # testate (+ paraurti = 32 m)
CASSE = {'A': (5.5, XE), 'B': (-4.75, 4.75), 'C': (-XE, -5.5)}
GIUNTI = ((4.75, 5.5), (-5.5, -4.75))        # soffietti tra le casse
DOORS = {'A': [(7.0, 8.3), (13.2, 14.5)], 'B': [(-0.65, 0.65)], 'C': [(-8.3, -7.0), (-14.5, -13.2)]}
ZB, ZF, ZW0, ZW1, ZT, ZL = 0.75, 0.85, 1.45, 2.35, 2.75, 2.95   # fondo, pavimento, finestrini, tetto, lanternino
ZA, RW = 0.33, 0.33                          # asse e raggio delle ruote (piccole, sui carrelli)
CARRELLI = {'A': 11.0, 'B': 0.0, 'C': -11.0}; PASSO_C = 0.9   # centro carrello, mezzo passo degli assi
LINEA = '2 · OSPEDALE'

CFG = dict(
    root='Tram_Cartone_Tutorial', Y0=-15.0, SHEET=(0.0, -8.0), sheet_w=34.0, label_dy=3.0,
    STAGE_X={s: 52.0 + (s - 2)*38.0 for s in range(2, 11)}, paint_stage=9, final_stage=10,
    wheel=dict(RW=RW, DT=0.06, ZA=ZA, YW0=0.62, stage=6, RH=0.16, RA_ASSE=0.04),
    NOMI={2: 'Telaio', 3: 'Casse', 4: 'Tetti', 5: 'Soffietti', 6: 'Ruote', 7: 'Interni', 8: 'Dettagli', 9: 'Pittura', 10: 'Finito'},
    TITOLI={1: '1 · Taglio dei pezzi', 2: '2 · Telaio: pavimenti e carrelli', 3: '3 · Casse: fiancate, testate, portali',
            4: '4 · Tetti e lanternini', 5: '5 · Soffietti', 6: '6 · Ruote e assi (sei assi su tre carrelli)',
            7: '7 · Interni: sedili, posti guida, corrimano', 8: '8 · Dettagli: porte, fasce, fari, lire, indicatori',
            9: '9 · Pittura', 10: '10 · Tram finito'})

# ---------- aiuti ----------
def side(s, y): return frame((0, s*y, 0), (1, 0, 0), (0, 0, 1), (0, s, 0))

def segmenti(k):
    # tratti di fiancata tra le porte (da riempire di finestrini)
    x0, x1 = CASSE[k]; tagli = sorted(DOORS[k]); out = []; a = x0 + 0.25
    for d0, d1 in tagli:
        out.append((a, d0 - 0.15)); a = d1 + 0.15
    out.append((a, x1 - 0.25))
    return [(a, b) for a, b in out if b - a > 0.5]

def finestrini(k):
    h = []
    for a, b in segmenti(k):
        n = max(1, round((b - a)/1.45)); g = 0.14; w = (b - a - (n - 1)*g)/n
        h += [rect(a + i*(w + g), ZW0, a + i*(w + g) + w, ZW1) for i in range(n)]
    return h

def door_leaf(x0, x1, s):
    return part(rect(x0, ZB - 0.08, x1, ZW1 + 0.05), side(s, W + 0.02),
                [rect(x0 + 0.07, ZW0 - 0.05, x1 - 0.07, ZW1 - 0.04), rect(x0 + 0.07, ZB + 0.08, x1 - 0.07, ZW0 - 0.2)], t=0.04)

def zigzag(x0, x1, base, amp, thick, n, sign):
    xs = [x0 + (x1 - x0)*i/n for i in range(n + 1)]
    outer = [(x, base + sign*(amp if i % 2 else 0.0)) for i, x in enumerate(xs)]
    return outer + [(x, y - sign*thick) for x, y in reversed(outer)]

def testata(sx):
    # sx = +1 davanti (x = +XE), -1 dietro: frame con la faccia esterna verso fuori
    return frame((sx*(XE - T), 0, 0), (0, sx, 0), (0, 0, 1))

def lira(xb, d):
    # lira di presa di cartone (come nella reference): asta + anello, inclinata di 20°
    a = math.radians(20); u = Vector((d*math.cos(a), 0, math.sin(a))); v = Vector((0, 1, 0)).cross(u)
    out = [(0, -0.05), (0.52, -0.05)] + arc(0.72, 0, 0.22, -2.4, 2.4, 16) + [(0.52, 0.05), (0, 0.05)]
    return part(out, frame((xb, -0.03, ZL + T), u, v, (0, 1, 0)), [circle(0.72, 0, 0.15, 16)], t=0.06, rough=0.004, nick=0.01)

# ---------- pezzi ----------
def pieces():
    out = []; LATI = ((-1, 'Dx'), (1, 'Sx')); cfg = CFG
    # fase 2: telaio e carrelli
    for k, (x0, x1) in CASSE.items():
        out.append(P(f'Pavimento_{k}', 2, [part(rect(x0 + T, -WI, x1 - T, WI), frame((0, 0, ZF), (1, 0, 0), (0, -1, 0)))]))
        bc = CARRELLI[k]
        tel = [part(rect(bc - 1.4, 0.12, bc + 1.4, ZB - 0.06), side(s, 0.52), [circle(bc - PASSO_C, ZA, 0.05, 14), circle(bc + PASSO_C, ZA, 0.05, 14)])
               for s in (-1, 1)]
        tel.append(part(rect(bc - 1.2, -0.62, bc + 1.2, 0.62), frame((0, 0, ZB - 0.06), (1, 0, 0), (0, 1, 0)), t=0.06))
        out.append(P(f'Carrello_{k}', 2, tel, paint='grigio'))
    for i, (a, b) in enumerate(GIUNTI):
        out.append(P(f'Pedana_Snodo_{i+1}', 2, [part(rect(a, -1.0, b, 1.0), frame((0, 0, ZF), (1, 0, 0), (0, -1, 0)), t=0.06)]))
    # fase 3: casse
    for k, (x0, x1) in CASSE.items():
        for s, nm in LATI:
            holes = finestrini(k) + [rect(d0, ZB + 0.06, d1, ZW1 + 0.05) for d0, d1 in DOORS[k]]
            out.append(P(f'Fiancata_{k}_{nm}', 3, [part(rect(x0, ZB, x1, ZT), side(s, WI), holes)], paint='crema'))
    for sx, nm in ((1, 'Ant'), (-1, 'Post')):
        out.append(P(f'Testata_{nm}', 3, [part(rect(-WI, ZB, WI, ZT), testata(sx), [rect(-0.85, ZW0 - 0.1, 0.85, ZW1)])], paint='azzurro', early=True))
    portale = [rect(-0.95, ZF + 0.05, 0.95, ZW1 + 0.15)]
    for x, sx, nm in ((5.5, -1, 'A'), (4.75, 1, 'B_Ant'), (-4.75, -1, 'B_Post'), (-5.5, 1, 'C')):
        out.append(P(f'Portale_{nm}', 3, [part(rect(-WI, ZB, WI, ZT), frame((x - sx*T, 0, 0), (0, sx, 0), (0, 0, 1)), portale)], paint='crema'))
    tapes = []
    for s in (-1, 1):
        for x, dx in ((XE, -1), (-XE, 1), (5.5, 1), (4.75, -1), (-4.75, 1), (-5.5, -1)):
            tapes.append(tape_L((x, s*W, 1.8), (0, 0, 1), (dx, 0, 0), (0, s, 0), (0, -s, 0), (-dx, 0, 0), seed=int(x*10) + s))
    out.append(P('Nastro_Casse', 3, [dict(geo=g, M=Matrix()) for g in tapes], kind='tape', sheet=False, until=6))
    # fase 4: tetti e lanternini
    for k, (x0, x1) in CASSE.items():
        out.append(P(f'Tetto_{k}', 4, [part(rect(x0 - 0.03, -W, x1 + 0.03, W), frame((0, 0, ZT), (1, 0, 0), (0, 1, 0)))], paint='grigio', early=True))
        lx0, lx1 = x0 + 0.7, x1 - 0.7
        fin = []; n = int((lx1 - lx0)/0.9)
        for i in range(n):
            a = lx0 + 0.2 + i*(lx1 - lx0 - 0.4)/n; fin.append(rect(a, ZT + T + 0.04, a + 0.5, ZL - 0.03))
        lant = [part(rect(lx0, ZT + T, lx1, ZL), side(s, 0.55), fin, t=0.05) for s in (-1, 1)]
        lant.append(part(rect(lx0 - 0.06, -0.62, lx1 + 0.06, 0.62), frame((0, 0, ZL), (1, 0, 0), (0, 1, 0)), t=0.05))
        lant += [part(rect(-0.55, ZT + T, 0.55, ZL), frame((x + 0.05*sx, 0, 0), (0, sx, 0), (0, 0, 1)), t=0.05) for x, sx in ((lx1, 1), (lx0, -1))]
        out.append(P(f'Lanternino_{k}', 4, lant, paint='crema', early=True))
    tapes = []
    for s in (-1, 1):
        for x in (-13.0, -9.0, -2.5, 2.5, 9.0, 13.0):
            tapes.append(tape_L((x, s*W, ZT + T), (1, 0, 0), (0, -s, 0), (0, 0, 1), (0, 0, -1), (0, s, 0), seed=int(x*10) + 3*s))
    out.append(P('Nastro_Tetti', 4, [dict(geo=g, M=Matrix()) for g in tapes], kind='tape', sheet=False, until=6))
    # fase 5: soffietti
    hz = ZT - 0.06 - (ZB + 0.08)
    for i, (a, b) in enumerate(GIUNTI):
        sof = [part(zigzag(a, b, -1.12, 0.07, 0.05, 6, -1), frame((0, 0, ZB + 0.08), (1, 0, 0), (0, 1, 0)), t=hz, rough=0.003, warp=0.0, nick=0.0, step=1.0),
               part(zigzag(a, b, 1.12, 0.07, 0.05, 6, 1), frame((0, 0, ZB + 0.08), (1, 0, 0), (0, 1, 0)), t=hz, rough=0.003, warp=0.0, nick=0.0, step=1.0),
               part(zigzag(a, b, ZT - 0.02, 0.07, 0.05, 6, 1), frame((0, -1.12, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0)), t=2.24, rough=0.003, warp=0.0, nick=0.0, step=1.0)]
        sf = P(f'Soffietto_{i+1}', 5, sof, paint='grigio', early=True); sf['edge_face'] = True; out.append(sf)
    # fase 6: ruote e assi
    for k, bc in CARRELLI.items():
        for j, cx in enumerate((bc - PASSO_C, bc + PASSO_C)):
            nx = f'{k}{j+1}'
            out.append(P(f'Asse_{nx}', 6, [dowel((cx, -1.0, ZA), (0, 1, 0), 2.0, 0.04)], kind='wood'))
            for s, nm in LATI:
                out.append(P(f'Ruota_{nx}_{nm}', 6, wheel_parts(cx, s, cfg)))
                out.append(P(f'Coprimozzo_{nx}_{nm}', 6, [hubcap_part(cx, s, cfg)], paint='grigio'))
    # fase 7: interni
    n = 0
    for k in CASSE:
        for a, b in segmenti(k):
            xc = a + 0.5
            while xc < b - 0.3:
                n += 1
                out.append(P(f'Sedili_{k}_{n}', 7, seat_parts(xc, 0.30, 1.05, ZF, zs=1.25, zb=1.85) + seat_parts(xc, -1.05, -0.30, ZF, zs=1.25, zb=1.85),
                             paint='blu', sheet=False))
                xc += 1.1
    for sx, nm in ((1, 'Ant'), (-1, 'Post')):
        xg = sx*(XE - 0.9)
        sc = Vector((sx*(XE - 0.45), 0.0, 1.55)); sd = Vector((-sx*0.6, 0, 0.8))
        out.append(P(f'Posto_Guida_{nm}', 7, [part(rect(-0.45, ZF, 0.45, 1.25), frame((xg, 0, 0), (0, 1, 0), (0, 0, 1)), rough=0.006),
                                             part(rect(-0.4, ZB + 0.6, 0.4, 1.45), frame((sx*(XE - 0.35), 0, 0), (0, 1, 0), (0, 0, 1)), t=0.05, rough=0.006),
                                             part(circle(0, 0, 0.18, 20), frame_dir(sc, sd), [circle(0, 0, 0.14, 20)], t=0.03, rough=0.002, nick=0.0)],
                     paint='grigio', sheet=False))
    poles = [dowel((x, s*0.85, ZF), (0, 0, 1), ZT - ZF, 0.025) for k in DOORS for d in DOORS[k] for x in d for s in (-1, 1)]
    out.append(P('Corrimano', 7, poles, kind='wood'))
    # fase 8: dettagli
    for k in CASSE:
        for s, nm in LATI:
            ante = []
            for d0, d1 in DOORS[k]:
                m = (d0 + d1)/2; ante += [door_leaf(d0 + 0.02, m - 0.01, s), door_leaf(m + 0.01, d1 - 0.02, s)]
            out.append(P(f'Porte_{k}_{nm}', 8, ante, paint='azzurro'))
            x0, x1 = CASSE[k]; tagli = sorted(DOORS[k]); a = x0 + 0.02; fasce = []
            for d0, d1 in tagli + [(x1 - 0.02, x1)]:
                if d0 - a > 0.1: fasce.append(part(rect(a, ZB, d0 - 0.06, ZW0 - 0.12), side(s, W), t=0.03, rough=0.005))
                a = d1 + 0.06
            fasce.append(part(rect(x0 + 0.02, ZW1 + 0.12, x1 - 0.02, ZW1 + 0.2), side(s, W), t=0.03, rough=0.004))
            out.append(P(f'Fasce_{k}_{nm}', 8, fasce, paint='azzurro'))
    for sx, nm in ((1, 'Ant'), (-1, 'Post')):
        Mt = frame((sx*XE, 0, 0), (0, sx, 0), (0, 0, 1))
        out.append(P(f'Fari_{nm}', 8, [button(s*0.80, 1.05, 0.12, Mt) for s in (-1, 1)], kind='plastic_giallo'))
        out.append(P(f'Fanali_{nm}', 8, [button(s*0.95, 1.30, 0.07, Mt) for s in (-1, 1)], kind='plastic_rosso'))
        out.append(P(f'Indicatore_{nm}', 8, [part(rect(-0.75, ZW1 + 0.08, 0.75, ZT - 0.05), Mt, t=0.03, rough=0.004)], paint='grigio'))
        out.append(P(f'Paraurti_{nm}', 8, [part(rect(-W, 0.45, W, ZB + 0.05), frame((sx*(XE + 0.06), 0, 0), (0, sx, 0), (0, 0, 1))),
                                            part(rect(min(sx*(XE - T), sx*16.0), -W, max(sx*(XE - T), sx*16.0), W), frame((0, 0, ZB + 0.05), (1, 0, 0), (0, 1, 0)))],
                     paint='grigio'))
    out.append(P('Lire', 8, [lira(2.4, -1), lira(-0.2, -1)], paint='grigio'))
    out.append(P('Basi_Lire', 8, box_parts(-0.5, 0.5, -0.2, 0.2, ZL, ZL + 0.12, t=0.04) + box_parts(1.9, 2.9, -0.2, 0.2, ZL, ZL + 0.12, t=0.04), paint='grigio'))
    return out

def scritta_linea(s, coll, MAT, loc):
    # numero e destinazione sugli indicatori delle due testate (pennarello, poi giallo acceso)
    if s < 8: return
    mat = MAT['luce_giallo'] if s >= CFG['final_stage'] else MAT['inchiostro']
    for sx in (1, -1):
        M = Matrix.Translation(loc) @ frame((sx*(XE + 0.035), 0, (ZW1 + ZT)/2 + 0.01), (0, sx, 0), (0, 0, 1))
        cu = bpy.data.curves.new('Scritta_Linea', 'FONT'); cu.body = LINEA
        cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.size = 0.17; cu.extrude = 0.004; cu.materials.append(mat)
        ob = bpy.data.objects.new(f'F{s}_Scritta_Linea_{"Ant" if sx > 0 else "Post"}', cu); ob.matrix_world = M; coll.objects.link(ob)

if __name__ == '__main__':
    run_tutorial(CFG, pieces(), scritta_linea)
