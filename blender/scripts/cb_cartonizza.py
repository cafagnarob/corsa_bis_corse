# =====================================================================
# cb_cartonizza.py — Corsa Bis · trasforma i tuoi modelli in cartone
# Cosa fa: prende gli oggetti selezionati, fatti come pezzi di cartone
#   (piani piatti, di solito con il modificatore Solidify), e li rifà con
#   cb_lib.py: bordi tagliati un po' storti, angoli consumati, onda del
#   cartone ondulato sul taglio, kraft o vernice usurati.
# Come modellare per usarlo:
#   - un pezzo = un oggetto con facce tutte sullo stesso piano (come un
#     foglio); più pezzi piatti nello stesso oggetto vanno bene, se sono
#     separati (non collegati da spigoli);
#   - i buchi (finestrini, feritoie) sono buchi veri nella mesh: facce
#     cancellate, non un Boolean;
#   - spessore e lato da Solidify (Thickness e Offset); senza Solidify si
#     usa lo spessore standard verso l'interno (Offset -1);
#   - colore: se il primo materiale è uno dei CB_ (es. CB_Vernice_Arancio)
#     viene usato per la faccia; altrimenti kraft al naturale.
# Cosa fa con l'originale: lo nasconde (non lo cancella) e crea accanto
#   "<nome>_cartone" nella collection "Cartonizzati". Rilanciando, i
#   "_cartone" vecchi vengono rifatti.
# Cosa NON fa: forme curve o volumi pieni (un cubo, una sfera): vanno
#   spezzati in facce piatte; le ruote si fanno con le funzioni di cb_lib.
# Uso: seleziona gli oggetti, apri questo file nel Text Editor, Run Script.
# =====================================================================
import bpy, math, os, zlib
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

TOLL_PIANO = 0.002      # m: scarto massimo dal piano perché un pezzo sia "piatto"

# ---------- lettura della mesh ----------
def _isole(me):
    # gruppi di facce collegate da spigoli: ogni gruppo è un foglio
    adj = {}
    for e in me.edges: adj.setdefault(e.vertices[0], []).append(e.vertices[1]); adj.setdefault(e.vertices[1], []).append(e.vertices[0])
    vf = {}
    for p in me.polygons:
        for v in p.vertices: vf.setdefault(v, []).append(p.index)
    visti = set(); out = []
    for p in me.polygons:
        if p.index in visti: continue
        stack = [p.index]; gruppo = []
        while stack:
            f = stack.pop()
            if f in visti: continue
            visti.add(f); gruppo.append(f)
            for v in me.polygons[f].vertices: stack += [g for g in vf[v] if g not in visti]
        out.append(gruppo)
    return out

def _anelli(me, facce):
    # spigoli di bordo (usati da una sola faccia del gruppo) chiusi in anelli
    cont = {}
    for f in facce:
        for ek in me.polygons[f].edge_keys: cont[ek] = cont.get(ek, 0) + 1
    bordo = [ek for ek, n in cont.items() if n == 1]
    vic = {}
    for a, b in bordo: vic.setdefault(a, []).append(b); vic.setdefault(b, []).append(a)
    usati = set(); anelli = []
    for a, b in bordo:
        if (a, b) in usati: continue
        anello = [a]; prec, cur = a, b; usati.add((min(a, b), max(a, b)))
        while cur != a and len(anello) < 100000:
            anello.append(cur)
            nxt = [n for n in vic[cur] if n != prec and (min(cur, n), max(cur, n)) not in usati]
            if not nxt: break
            usati.add((min(cur, nxt[0]), max(cur, nxt[0]))); prec, cur = cur, nxt[0]
        if len(anello) >= 3: anelli.append(anello)
    return anelli

def _area2d(l):
    return sum(l[i][0]*l[(i+1) % len(l)][1] - l[(i+1) % len(l)][0]*l[i][1] for i in range(len(l)))/2

def _dentro(p, poly):
    x, y = p; c = False; n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]; x1, y1 = poly[(i+1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0)*(x1 - x0)/(y1 - y0): c = not c
    return c

def _pulisci(loop, tol=1e-4):
    # toglie i punti allineati: la libreria ricampiona da sola i lati lunghi
    out = []
    n = len(loop)
    for i in range(n):
        a = Vector(loop[i-1]); b = Vector(loop[i]); c = Vector(loop[(i+1) % n])
        if abs((b - a).x*(c - b).y - (b - a).y*(c - b).x) > tol*max((b - a).length, 1e-6): out.append(loop[i])
    return out if len(out) >= 3 else loop

def _solidify(ob):
    for m in ob.modifiers:
        if m.type == 'SOLIDIFY' and m.show_viewport: return abs(m.thickness), m.offset*(1 if m.thickness >= 0 else -1)
    return T, -1.0

# ---------- conversione ----------
def cartonizza_oggetto(ob, MAT, coll):
    me = ob.data; mw = ob.matrix_world
    sc = mw.to_scale(); M0 = Matrix.LocRotScale(mw.to_translation(), mw.to_quaternion(), None)
    S = Matrix.Diagonal((*sc, 1.0))                          # la scala dell'oggetto entra nella geometria
    spess, offset = _solidify(ob)
    top = MAT['kraft']
    if ob.material_slots and ob.material_slots[0].material and ob.material_slots[0].material.name.startswith('CB_'):
        top = ob.material_slots[0].material
    geos = []; saltati = 0
    for k, facce in enumerate(_isole(me)):
        pts = [S @ me.vertices[v].co for f in facce for v in me.polygons[f].vertices]
        n = Vector()
        for f in facce: n += (S.to_3x3() @ me.polygons[f].normal)*me.polygons[f].area
        if n.length < 1e-9: saltati += 1; continue
        n.normalize(); o = sum(pts, Vector())/len(pts)
        if max(abs((p - o).dot(n)) for p in pts) > TOLL_PIANO: saltati += 1; continue
        u = (n.orthogonal()).normalized()
        # asse u lungo il lato più lungo del pezzo (onda e venature dritte)
        anelli = _anelli(me, facce)
        if not anelli: saltati += 1; continue
        lungo = max(anelli, key=len)
        best = max(((S @ me.vertices[lungo[i]].co) - (S @ me.vertices[lungo[i-1]].co) for i in range(len(lungo))), key=lambda d: d.length)
        best = best - n*best.dot(n)
        if best.length > 1e-6: u = best.normalized()
        v = n.cross(u)
        loops2d = [[((S @ me.vertices[i].co - o).dot(u), (S @ me.vertices[i].co - o).dot(v)) for i in a] for a in anelli]
        loops2d = [_pulisci(l) for l in loops2d]
        # esterni e buchi: un anello dentro un numero dispari di altri è un buco
        livello = [sum(_dentro(l[0], m) for j, m in enumerate(loops2d) if j != i) for i, l in enumerate(loops2d)]
        for i, l in enumerate(loops2d):
            if livello[i] % 2: continue
            fori = [h for j, h in enumerate(loops2d) if livello[j] == livello[i] + 1 and _dentro(h[0], l)]
            z0 = (offset - 1)/2*spess                        # Solidify: offset -1 = verso l'interno, +1 = verso la normale
            g = build_panel(l, fori, t=spess, seed=zlib.crc32(f'{ob.name}/{k}/{i}'.encode()) % 10000)
            geos.append((g, frame(o + n*z0, u, v, n)))
    if not geos: return None, saltati
    nome = ob.name + '_cartone'
    vecchio = bpy.data.objects.get(nome)
    if vecchio:
        d = vecchio.data; bpy.data.objects.remove(vecchio, do_unlink=True); bpy.data.meshes.remove(d)
    nuovo = make_object(nome, geos, [top, MAT['bordo'], MAT['interno']], coll)
    nuovo.matrix_world = M0
    ob.hide_set(True); ob.hide_render = True
    return nuovo, saltati

def run(oggetti=None):
    MAT = make_materials()
    coll = bpy.data.collections.get('Cartonizzati')
    if coll is None:
        coll = bpy.data.collections.new('Cartonizzati'); bpy.context.scene.collection.children.link(coll)
    oggetti = oggetti if oggetti is not None else [o for o in bpy.context.selected_objects if o.type == 'MESH']
    fatti = []; avvisi = []
    for ob in oggetti:
        if ob.name.endswith('_cartone'): continue
        nuovo, saltati = cartonizza_oggetto(ob, MAT, coll)
        if nuovo: fatti.append(nuovo)
        if saltati: avvisi.append(f'{ob.name}: {saltati} parti non piatte saltate')
    print(f'Cartonizzati {len(fatti)} oggetti'); [print('  ' + a) for a in avvisi]
    return fatti, avvisi

if __name__ == '__main__':
    run()
