# =====================================================================
# cb_tutorial.py — Corsa Bis · motore del "tutorial di montaggio"
# Cosa fa: dato un elenco di pezzi di cartone (definiti nel file del
#   mezzo) e una configurazione, costruisce nella scena:
#   fase 1 = tutti i pezzi stesi sul tappetino da taglio + legno e bottoni;
#   fasi successive = il mezzo montato fino a quel passaggio, affiancato,
#   con un cartellino di cartone col titolo; una ruota smontata accanto
#   alla fase delle ruote.
# Come: ogni pezzo dichiara la fase in cui entra (e fino a quale resta,
#   es. il nastro di carta), il tipo (cartone, legno, nastro, bottone) e
#   il colore della vernice. Ogni fase ricostruisce i pezzi con lo stesso
#   seed, quindi sono identici tra una fase e l'altra.
# Uguale per tutti i mezzi: cambia solo il file del mezzo (es. cb_bus12.py).
# Richiede: cb_lib.py (nel Text Editor o nella stessa cartella).
# =====================================================================
import bpy, math, zlib
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

# ---------- descrizione dei pezzi ----------
def P(name, stage, parts, kind='carton', paint=None, early=False, sheet=True, until=99):
    return dict(name=name, stage=stage, parts=parts, kind=kind, paint=paint, early=early, sheet=sheet, until=until)

def part(outline, M, holes=(), t=T, **kw):
    return dict(outline=outline, holes=list(holes), M=M, t=t, kw=kw)

def button(cx, cy, r, M):
    # bottone da cucito: disco con 4 forellini (fari e fanali)
    holes = [circle(cx + dx, cy + dy, r*0.16, 10) for dx, dy in ((-r*0.3, -r*0.3), (r*0.3, -r*0.3), (r*0.3, r*0.3), (-r*0.3, r*0.3))]
    return part(circle(cx, cy, r, 24), M, holes, t=0.05, rough=0.002, warp=0.0, nick=0.0)

def dowel(p0, d, length, r):
    # bacchetta di legno da p0 lungo la direzione d
    return part(circle(0, 0, r, 12), frame_dir(p0, d), t=length, rough=0.001, warp=0.0, nick=0.0)

def slots(x0, x1, v0, h, step, n):
    return [rect(x0, v0 + k*step, x1, v0 + k*step + h) for k in range(n)]

def box_parts(x0, x1, y0, y1, z0, z1, t=T):
    # scatola aperta sotto: coperchio + 4 pareti (es. climatizzatore sul tetto)
    return [part(rect(x0, y0, x1, y1), frame((0, 0, z1 - t), (1, 0, 0), (0, 1, 0)), t=t),
            part(rect(y0, z0, y1, z1 - t), frame((x1 - t, 0, 0), (0, 1, 0), (0, 0, 1)), t=t),
            part(rect(-y1, z0, -y0, z1 - t), frame((x0 + t, 0, 0), (0, -1, 0), (0, 0, 1)), t=t),
            part(rect(x0 + t, z0, x1 - t, z1 - t), frame((0, y1 - t, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0)), t=t),
            part(rect(x0 + t, z0, x1 - t, z1 - t), frame((0, y0 + t, 0), (1, 0, 0), (0, 0, 1)), t=t)]

def seat_parts(xc, y0, y1, zf, zs=1.05, zb=1.70):
    # sedile appena accennato: seduta, schienale, fianchetto anteriore
    return [part(rect(xc - 0.24, y0, xc + 0.20, y1), frame((0, 0, zs), (1, 0, 0), (0, 1, 0)), rough=0.006),
            part(rect(y0, zs, y1, zb), frame((xc - 0.32, 0, 0), (0, 1, 0), (0, 0, 1)), rough=0.006),
            part(rect(y0 + 0.02, zf, y1 - 0.02, zs), frame((xc + 0.10, 0, 0), (0, 1, 0), (0, 0, 1)), rough=0.006)]

def wheel_parts(cx, s, cfg):
    w = cfg['wheel']
    return [part(tread(w['RW'], w['RW'] - 0.035), frame((cx, s*(w['YW0'] + k*w['DT']), w['ZA']), (1, 0, 0), (0, 0, 1), (0, s, 0)),
                 [circle(0, 0, 0.065, 16)], t=w['DT'], rough=0.006, nick=0.01) for k in range(4)]

def hubcap_part(cx, s, cfg):
    w = cfg['wheel']
    # RH = raggio del coprimozzo (0,27 m se il mezzo non lo dice)
    return part(circle(0, 0, w.get('RH', 0.27), 28), frame((cx, s*(w['YW0'] + 4*w['DT']), w['ZA']), (1, 0, 0), (0, 0, 1), (0, s, 0)),
                [circle(0, 0, 0.065, 14)], t=0.05, rough=0.004)

# ---------- costruzione ----------
def seed_of(name, i):
    return zlib.crc32(f'{name}/{i}'.encode()) % 10000

def geo_of(pc, i, pd):
    if 'geo' in pd: return pd['geo']
    return build_panel(pd['outline'], pd['holes'], t=pd['t'], seed=seed_of(pc['name'], i), **pd['kw'])

def piece_mats(pc, s, MAT, cfg):
    k = pc['kind']
    if k == 'carton':
        top = MAT['kraft']
        if pc['paint'] and (s >= cfg['final_stage'] or (s == cfg['paint_stage'] and pc['early'])):
            top = MAT['vernice_' + pc['paint']]
        # edge_face: pezzi piegati (es. soffietto) dove i fianchi estrusi sono superficie, non taglio
        return [top, top if pc.get('edge_face') else MAT['bordo'], MAT['interno']]
    if k == 'wood': return [MAT['legno']]*3
    if k == 'tape': return [MAT['nastro']]*3
    if k == 'string': return [MAT['spago']]*3
    if k.startswith('plastic_') and s >= cfg['final_stage']:
        # bottoni dei fari: accesi solo sul mezzo finito
        k = 'luce_' + k[len('plastic_'):]
    return [MAT.get(k, MAT.get('plastic_' + k[5:]))]*3

def reset_root(name):
    root = bpy.data.collections.get(name)
    if root:
        for c in list(root.children_recursive) + [root]:
            for o in list(c.objects):
                data = o.data; bpy.data.objects.remove(o, do_unlink=True)
                if data and data.users == 0:
                    (bpy.data.meshes if isinstance(data, bpy.types.Mesh) else bpy.data.curves).remove(data)
        for c in list(root.children_recursive): bpy.data.collections.remove(c)
        bpy.data.collections.remove(root)
    root = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(root)
    return root

def sub(root, name):
    c = bpy.data.collections.new(name); root.children.link(c); return c

def cartellino(text, loc, coll, MAT):
    # cartellino di cartone kraft con il titolo della fase scritto a pennarello
    lab = make_label(text, (loc[0], loc[1], 0.045), coll, MAT['inchiostro'])
    bpy.context.view_layer.update()
    w = lab.dimensions.x + 0.8; h = 1.0
    g = build_panel(rect(-w/2, -h/2, w/2, h/2), t=0.04, rough=0.02, warp=0.0, seed=len(text))
    make_object('Cartellino_' + text[:12], [(g, Matrix())], [MAT['kraft'], MAT['bordo'], MAT['interno']], coll, (loc[0], loc[1] + 0.2, 0.0))
    return lab

def build_stage(s, coll, MAT, PCS, cfg):
    loc = (cfg['STAGE_X'][s], cfg['Y0'], 0.0)
    for pc in PCS:
        if not (pc['stage'] <= s <= pc['until']): continue
        geos = [(geo_of(pc, i, pd), pd['M']) for i, pd in enumerate(pc['parts'])]
        make_object(f"F{s}_{pc['name']}", geos, piece_mats(pc, s, MAT, cfg), coll, loc)

def build_sheet(coll, MAT, PCS, cfg):
    # fase 1: pezzi di cartone stesi sul tappetino, poi bacchette e bottoni
    SX, SY = cfg['SHEET']; maxw = cfg['sheet_w']; org = (SX, SY, 0)
    items = []
    for pc in PCS:
        if not pc['sheet'] or pc['kind'] != 'carton': continue
        for i, pd in enumerate(pc['parts']):
            x0, y0, x1, y1 = bbox(pd['outline'])
            items.append((y1 - y0, x1 - x0, pc, i, pd, x0, y0))
    items.sort(key=lambda t: (-round(t[0], 1), -t[1]))
    gap = 0.3; cx = 0.0; cy = 0.0; rowh = 0.0
    for h, w, pc, i, pd, x0, y0 in items:
        if cx > 0 and cx + w > maxw:
            cx = 0.0; cy -= rowh + gap; rowh = 0.0
        M = Matrix.Translation((cx - x0, cy - h - y0, 0.0))
        make_object(f"F1_{pc['name']}_{i}", [(geo_of(pc, i, pd), M)], piece_mats(pc, 1, MAT, cfg), coll, org)
        cx += w + gap; rowh = max(rowh, h)
    cy -= rowh + 0.6; cx = 0.0; ytop = cy
    for pc in PCS:
        if pc['kind'] == 'wood' and pc['sheet']:
            for i, pd in enumerate(pc['parts']):
                r = bbox(pd['outline'])[3]
                make_object(f"F1_{pc['name']}_{i}", [(geo_of(pc, i, pd), frame_dir((0, cy, r), (1, 0, 0)))], piece_mats(pc, 1, MAT, cfg), coll, org)
                cy -= 0.3
    bx = maxw*0.55; by = ytop
    for pc in PCS:
        if pc['kind'].startswith('plastic') and pc['sheet']:
            for i, pd in enumerate(pc['parts']):
                x0, y0, x1, y1 = bbox(pd['outline'])
                make_object(f"F1_{pc['name']}_{i}", [(geo_of(pc, i, pd), Matrix.Translation((bx - x0, by - y1, 0.0)))], piece_mats(pc, 1, MAT, cfg), coll, org)
                bx += (x1 - x0) + 0.25
    bottom = cy - 0.3
    mat_geo = build_panel(rect(-0.5, bottom - 0.4, maxw + 0.5, 0.5), t=0.02, rough=0.0, warp=0.0, nick=0.0, step=5.0)
    make_object('F1_Tappetino_Taglio', [(mat_geo, Matrix.Translation((0, 0, -0.021)))], [MAT['tappetino']]*3, coll, org)
    cartellino(cfg['TITOLI'][1], (SX + maxw/2, SY + bottom - 1.4, 0.0), coll, MAT)

def build_exploded_wheel(coll, MAT, cfg):
    # accanto alla fase delle ruote: 4 dischi + coprimozzo infilati sull'asse
    w = cfg['wheel']; s = w['stage']
    loc = (cfg['STAGE_X'][s], cfg['Y0'] + cfg['label_dy'] + 1.2, 0.0); parts = []
    for k in range(4):
        parts.append(part(tread(w['RW'], w['RW'] - 0.035), frame((0, -k*0.5, w['ZA']), (1, 0, 0), (0, 0, 1)), [circle(0, 0, 0.065, 16)], t=w['DT'], rough=0.006, nick=0.01))
    parts.append(part(circle(0, 0, w.get('RH', 0.27), 28), frame((0, -4*0.5, w['ZA']), (1, 0, 0), (0, 0, 1)), [circle(0, 0, 0.065, 14)], t=0.05, rough=0.004))
    pc = P('Ruota_Esplosa', s, parts)
    make_object(f'F{s}_Ruota_Esplosa', [(geo_of(pc, i, pd), pd['M']) for i, pd in enumerate(parts)], piece_mats(pc, s, MAT, cfg), coll, loc)
    ax = dowel((0, 0.6, w['ZA']), (0, -1, 0), 2.9, w.get('RA_ASSE', 0.055)); pa = P('Asse_Esploso', s, [ax], kind='wood')
    make_object(f'F{s}_Asse_Esploso', [(geo_of(pa, 0, ax), ax['M'])], piece_mats(pa, s, MAT, cfg), coll, loc)

def run_tutorial(cfg, PCS, extras=None):
    MAT = make_materials()
    root = reset_root(cfg['root'])
    build_sheet(sub(root, 'Fase_1_Taglio'), MAT, PCS, cfg)
    for s in sorted(cfg['STAGE_X']):
        c = sub(root, f"Fase_{s}_{cfg['NOMI'][s]}")
        build_stage(s, c, MAT, PCS, cfg)
        cartellino(cfg['TITOLI'][s], (cfg['STAGE_X'][s], cfg['Y0'] - cfg['label_dy'], 0.0), c, MAT)
        if s == cfg['wheel']['stage']: build_exploded_wheel(c, MAT, cfg)
        if extras: extras(s, c, MAT, (cfg['STAGE_X'][s], cfg['Y0'], 0.0))
    return root
