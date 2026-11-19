# =====================================================================
# cb_atlante_edifici.py — Corsa Bis · atlante di facciata per i gusci degli edifici
# Cosa fa (file EDIFICI aperto, kit costruito da cb_edifici.py in Kit_Borgo):
#   i gusci del gioco (circa 100 triangoli a edificio, usati in tutte le viste
#   tranne la vista a piedi) hanno le facciate disegnate da questo atlante.
#   Ogni riquadro è un modulo del kit visto di fronte, montato con i pezzi
#   veri (persiane, balconi, cornici, tende, insegne) e cotto in Cycles
#   (Diffuso solo colore, selected to active su un piano davanti al modulo);
#   dietro le aperture c'è un fondale di cartone in ombra.
#   - facciate_colore.jpg  2048 x 2048, 128 pixel per metro; l'intonaco esce
#                          quasi bianco (la texture intonaco_colore.jpg)
#   - facciate_maschera.jpg  2048 x 2048: bianco = intonaco da TINGERE nel
#                          codice col colore della casa; nero = tutto il resto
#                          (kraft, stucco, vetri, tende, insegne) che resta com'è
#   - facciate.json        per ogni riquadro: rettangolo UV, misure in metri
#   Righe: terra (moduli 2 x 4 m), piani (2 x 3 m), fasce (2 x 0,5 m); poi le stesse per i palazzoni.
#   Nei riquadri u cresce verso destra guardando la facciata: u0 = bordo
#   sinistro (y = -2 nel modulo), u1 = bordo destro (y = 0, l'origine).
# Uso: Run Script, oppure costruisci(); bake('colore'); bake('maschera');
#   esporta(). Richiede cb_edifici.py e cb_lib.py nel Text Editor.
# =====================================================================
import bpy, os, json, math
from mathutils import Vector

_e = {'__name__': 'cb_edifici'}
exec(bpy.data.texts['cb_edifici.py'].as_string(), _e)
istanza, FINESTRA_PIANO, mat_tende = _e['istanza'], _e['FINESTRA_PIANO'], _e['mat_tende']

PX = 128                           # pixel per metro
W_IMG, H_IMG = 2048, 2048
CELLA_W = 2*PX                     # un modulo = 256 pixel
RIGHE = {'terra': (0, 4.0), 'piano': (512, 3.0), 'fasce': (896, 0.5), 'fasce2': (960, 0.5),        # borgo e corte
         'piano_pal': (1024, 3.0), 'terra_pal': (1408, 4.0), 'fasce_pal': (1920, 1.0)}             # palazzoni
# (pixel dal basso, altezza in m)

def persiane(aperte, a_gradi=125):
    # due ante incernierate ai lati della finestra (come in palazzo()): aperte contro il muro o chiuse
    u0, u1, z0, z1 = FINESTRA_PIANO; a = math.radians(a_gradi) if aperte else 0.0
    return [('Persiana', (0, -u0, z0), a, None), ('Persiana', (0, -u1, z0), math.pi - a, None)]

CELLE = [   # nome, riga, colonna, muro (pezzo del kit), aggiunte [(pezzo, posizione, rotazione, colore)]
    ('Terra_Parete', 'terra', 0, 'Terra_Parete', []),
    ('Terra_Porta', 'terra', 1, 'Terra_Porta', []),
    ('Terra_Porta_Pensilina', 'terra', 2, 'Terra_Porta', [('Pensilina', (0, 0, 0), 0, None)]),
    ('Terra_Vetrina', 'terra', 3, 'Terra_Vetrina', []),
    ('Terra_Vetrina_Tenda', 'terra', 4, 'Terra_Vetrina', [('Tenda', (0, 0, 0), 0, 'tenda')]),
    ('Terra_Vetrina_Insegna', 'terra', 5, 'Terra_Vetrina', [('Insegna_Bar', (0, 0, 0), 0, None)]),
    ('Terra_Serranda', 'terra', 6, 'Terra_Serranda', []),
    ('Terra_Portone', 'terra', 7, 'Terra_Portone', []),
    ('Piano_Parete', 'piano', 0, 'Modulo_Parete', []),
    ('Piano_Finestra_Aperta', 'piano', 1, 'Modulo_Finestra', persiane(True)),
    ('Piano_Finestra_Chiusa', 'piano', 2, 'Modulo_Finestra', persiane(False)),
    ('Piano_Portafinestra', 'piano', 3, 'Modulo_Portafinestra', []),
    ('Piano_Portafinestra_Balcone', 'piano', 4, 'Modulo_Portafinestra', [('Balcone', (0, 0, 0), 0, None)]),
    ('Corte_Finestra_Aperta', 'piano', 5, 'Modulo_Finestra', [('Cornice_Finestra', (0, 0, 0), 0, 'stucco')] + persiane(True)),
    ('Corte_Finestra_Chiusa', 'piano', 6, 'Modulo_Finestra', [('Cornice_Finestra', (0, 0, 0), 0, 'stucco')] + persiane(False)),
    ('Corte_Portafinestra_Balcone', 'piano', 7, 'Modulo_Portafinestra', [('Cornice_Portafinestra', (0, 0, 0), 0, 'stucco'), ('Balcone', (0, 0, 0), 0, None)]),
    ('Fascia_Marcapiano', 'fasce', 0, None, [('Marcapiano', (0, 0, 0), 0, 'stucco')]),
    ('Fascia_Cornicione', 'fasce', 1, None, [('Cornicione', (0, 0, 0), 0, 'stucco')]),
    ('Fascia_Cornicione_Corte', 'fasce', 2, None, [('Cornicione_Corte', (0, 0, 0), 0, 'stucco')]),
]
# palazzoni: tapparelle a tre altezze (f = quanto è abbassata), balcone a nastro col parapetto cemento chiaro
ALT_TAPP = {'Tapparella_Finestra': 1.5, 'Tapparella_Porta': 2.38, 'Tapparella_Piccola': 1.5}
def tapp(pezzo, f):
    su = min((1 - f)*ALT_TAPP[pezzo], 1.45)
    return [] if su >= ALT_TAPP[pezzo] - 0.02 else [(pezzo, (0, 0, 2.4 + su), 0, None)]
BALC = [('Pal_Balcone', (0, 0, 0), 0, 'cemento')]
CELLE += [
    ('Pal_Finestra_Su', 'piano_pal', 0, 'Pal_Finestra', tapp('Tapparella_Finestra', 0.0)),
    ('Pal_Finestra_Meta', 'piano_pal', 1, 'Pal_Finestra', tapp('Tapparella_Finestra', 0.5)),
    ('Pal_Finestra_Giu', 'piano_pal', 2, 'Pal_Finestra', tapp('Tapparella_Finestra', 1.0)),
    ('Pal_Finestra_Balcone', 'piano_pal', 3, 'Pal_Finestra', tapp('Tapparella_Finestra', 0.25) + BALC),
    ('Pal_Portafinestra_Balcone', 'piano_pal', 4, 'Pal_Portafinestra', tapp('Tapparella_Porta', 0.5) + tapp('Tapparella_Piccola', 0.25) + BALC),
    ('Pal_Portafinestra_Balcone_Chiusa', 'piano_pal', 5, 'Pal_Portafinestra', tapp('Tapparella_Porta', 1.0) + tapp('Tapparella_Piccola', 1.0) + BALC),
    ('Pal_Vano_Scala', 'piano_pal', 6, 'Pal_Vano_Scala', [('Marcapiano', (0, 0, -0.08), 0, 'cemento')]),
    ('Pal_Testata', 'piano_pal', 7, 'Modulo_Parete', [('Marcapiano', (0, 0, -0.08), 0, 'cemento')]),
    ('Pal_Terra_Androne', 'terra_pal', 0, 'Pal_Terra_Androne', []),
    ('Fascia_Parapetto_Pal', 'fasce_pal', 0, None, [('Pal_Parapetto', (0, 0, 0), 0, 'intonaco')]),
]
# villette: nella riga terra_pal (4 m), riquadri alti 3 m (porta, garage) o 1,3 m (recinzione, cancello)
CELLE += [
    ('Villa_Porta_Portico', 'terra_pal', 1, 'Villa_Porta', [('Villa_Portico', (0, 0, 0), 0, None)]),
    ('Villa_Porta', 'terra_pal', 2, 'Villa_Porta', []),
    ('Villa_Garage', 'terra_pal', 3, 'Villa_Garage', []),
    ('Villa_Recinzione', 'terra_pal', 4, None, [('Recinzione', (0, 0, 0), 0, 'intonaco')]),
    ('Villa_Cancello', 'terra_pal', 5, None, [('Recinzione_Cancello', (0, 0, 0), 0, 'intonaco')]),
]
ALTEZZA_PEZZO = {'Fascia_Marcapiano': 0.16, 'Fascia_Cornicione': 0.30, 'Fascia_Cornicione_Corte': 0.40, 'Fascia_Parapetto_Pal': 0.72,
                 'Villa_Porta_Portico': 3.0, 'Villa_Porta': 3.0, 'Villa_Garage': 3.0, 'Villa_Recinzione': 1.3, 'Villa_Cancello': 1.3}

def cartella():
    t = bpy.data.texts.get('cb_atlante_edifici.py')
    radice = os.path.dirname(os.path.dirname(os.path.dirname(bpy.path.abspath(t.filepath))))
    return os.path.join(radice, 'packages', 'web', 'public', 'textures', 'edifici')

def mat_immagine(nome, file, tinta=(1, 1, 1), ripeti=0.25):
    # intonaco dell'atlante: la texture ripetibile (UV del kit in metri, periodo 4 m), eventualmente tinta
    m = bpy.data.materials.get(nome) or bpy.data.materials.new(nome); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    uv = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (ripeti, ripeti, 1)
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(file, check_existing=True)
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
    mx.inputs[7].default_value = (*tinta, 1)
    nt.links.new(uv.outputs['UV'], mp.inputs['Vector']); nt.links.new(mp.outputs[0], t.inputs['Vector'])
    nt.links.new(t.outputs['Color'], mx.inputs[6]); nt.links.new(mx.outputs[2], b.inputs['Base Color'])
    nt.links.new(b.outputs[0], o.inputs['Surface'])
    return m

def mat_lamiera(file):
    # come l'intonaco, con il chiaro-scuro delle costole nel colore (il bake Diffuso non ha luce):
    # le UV dell'ondulato hanno v lungo le onde, periodo ONDA (0,2 m) come nella geometria
    m = mat_immagine('ATL_Lamiera', file); nt = m.node_tree
    uv = next(n for n in nt.nodes if n.type == 'TEX_COORD'); mx = next(n for n in nt.nodes if n.type == 'MIX')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(uv.outputs['UV'], sep.inputs[0])
    a = nt.nodes.new('ShaderNodeMath'); a.operation = 'MULTIPLY'; a.inputs[1].default_value = 2*math.pi/_e['ONDA']
    nt.links.new(sep.outputs['Y'], a.inputs[0])
    sn = nt.nodes.new('ShaderNodeMath'); sn.operation = 'SINE'; nt.links.new(a.outputs[0], sn.inputs[0])
    r = nt.nodes.new('ShaderNodeMapRange'); r.inputs['From Min'].default_value = -1; r.inputs['To Min'].default_value = 0.72
    nt.links.new(sn.outputs[0], r.inputs['Value'])
    cc = nt.nodes.new('ShaderNodeCombineColor')
    for k in ('Red', 'Green', 'Blue'): nt.links.new(r.outputs['Result'], cc.inputs[k])
    nt.links.new(cc.outputs[0], mx.inputs[7])
    return m

def mat_piatto(nome, col):
    m = bpy.data.materials.get(nome) or bpy.data.materials.new(nome); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*col, 1); return m

# ---------- seconda pagina: zona industriale (e, più avanti, i grattacieli dalla riga 896) ----------
#   file facciate_industria_colore.jpg / _maschera.jpg / facciate_industria.json, stesse regole.
#   Un riquadro può essere largo più moduli (6° elemento della tupla): il portone è largo 2 moduli (4 m).
RIGHE_IND = {'ind_terra': (0, 4.0), 'ind_alto': (512, 3.0), 'gr_piano': (896, 3.0), 'gr_terra': (1280, 4.0), 'gr_fasce': (1792, 1.5)}
CELLE_IND = [
    ('Cap_Parete', 'ind_terra', 0, 'Cap_Parete', []),
    ('Cap_Porta', 'ind_terra', 1, 'Cap_Porta', []),
    ('Cap_Portone', 'ind_terra', 2, 'Cap_Portone', [], 2),
    ('Cap_Parete_Alta', 'ind_alto', 0, 'Cap_Parete_Alta', []),
    ('Cap_Finestrata', 'ind_alto', 1, 'Cap_Finestrata', []),
    ('Gr_Nastro', 'gr_piano', 0, 'Gr_Nastro', []),
    ('Gr_Vetrata', 'gr_piano', 1, 'Gr_Vetrata', []),
    ('Gr_Terra_Vetrata', 'gr_terra', 0, 'Gr_Terra_Vetrata', []),
    ('Gr_Coronamento', 'gr_fasce', 0, None, [('Gr_Coronamento', (0, 0, 0), 0, 'intonaco')]),
]
ALTEZZA_PEZZO_IND = {'Gr_Coronamento': 1.12}
PAGINE = {'facciate': (lambda: CELLE, lambda: RIGHE), 'facciate_industria': (lambda: CELLE_IND, lambda: RIGHE_IND)}

def _cella(c):
    nome, riga, col, muro, extra = c[:5]; return nome, riga, col, muro, extra, (c[5] if len(c) > 5 else 1)

def rett_uv(riga, col, h=None, nm=1, righe=None):
    righe = righe or RIGHE; y0, hm = righe[riga]; h = hm if h is None else h
    return (col*CELLA_W/W_IMG, y0/H_IMG, (col + nm)*CELLA_W/W_IMG, (y0 + h*PX)/H_IMG)

def costruisci(modo='colore', pagina='facciate'):
    # modo 'colore': materiali veri; 'maschera': bianco sull'intonaco da tingere, nero altrove
    celle, righe = PAGINE[pagina][0](), PAGINE[pagina][1]()
    c = bpy.data.collections.get('Atlante_Sorgenti')
    if c:
        for o in list(c.objects):
            if o.name.startswith('ATL_Piastrella'): continue
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0 and isinstance(d, bpy.types.Mesh): bpy.data.meshes.remove(d)
    else:
        c = bpy.data.collections.new('Atlante_Sorgenti'); bpy.context.scene.collection.children.link(c)
    kit = {o.name: o for o in bpy.data.collections['Kit_Borgo'].objects}
    d = cartella()
    M = {'intonaco': mat_immagine('ATL_Intonaco', os.path.join(d, 'intonaco_colore.jpg')),
         'stucco': mat_immagine('ATL_Stucco', os.path.join(d, 'intonaco_colore.jpg'), (0.92, 0.88, 0.78)),
         'cemento': mat_immagine('ATL_Cemento', os.path.join(d, 'intonaco_colore.jpg'), (0.78, 0.76, 0.71)),
         'tenda': mat_tende()[0], 'interno': bpy.data.materials['CB_B_Interno']}
    M['lamiera'] = mat_lamiera(os.path.join(d, 'intonaco_colore.jpg'))
    bianco, nero = mat_piatto('ATL_Bianco', (1, 1, 1)), mat_piatto('ATL_Nero', (0, 0, 0))
    V, F, UV = [], [], []
    def maschera(o, tingi):
        for k, s in enumerate(o.material_slots):
            s.link = 'OBJECT'; s.material = bianco if (tingi and k == 0) else nero
    for i, cella in enumerate(celle):
        nome, riga, col, muro, extra, nm = _cella(cella)
        base = Vector((300.0, -8.0*i, 0.0)); h = righe[riga][1]; wm = MODULO_ATL*nm
        if muro:
            o = istanza(f'ATL_{nome}_Muro', kit[muro].data, c, None, base, 0.0, M['lamiera' if muro.startswith('Cap_') else 'intonaco'])
            if modo == 'maschera': maschera(o, True)
            # fondale in ombra dietro le aperture
            g = _e['build_panel'](_e['rect'](0, 0, wm, h), t=0.02, rough=0, warp=0, nick=0, step=50.0)
            f = _e['make_object'](f'ATL_{nome}_Fondale', [(g, _e['frame']((-0.6, 0, 0), (0, -1, 0), (0, 0, 1), (1, 0, 0)))], [M['interno']]*3, c)
            f.location = base
            if modo == 'maschera': maschera(f, False)
        for j, (pz, loc, r, colore) in enumerate(extra):
            o = istanza(f'ATL_{nome}_{pz}_{j}', kit[pz].data, c, None, base + Vector(loc), r, M.get(colore))
            if modo == 'maschera': maschera(o, colore == 'intonaco')       # 'intonaco' = pezzo nel colore della casa
        # piano di destinazione davanti al modulo (normale +X), UV nel riquadro dell'atlante
        u0, v0, u1, v1 = rett_uv(riga, col, nm=nm, righe=righe); x = base.x + 1.5; n = len(V)
        V += [(x, base.y, 0.0), (x, base.y, h), (x, base.y - wm, h), (x, base.y - wm, 0.0)]
        F.append((n, n + 1, n + 2, n + 3)); UV += [(u1, v0), (u1, v1), (u0, v1), (u0, v0)]
    me = bpy.data.meshes.new('ATL_Bersaglio'); me.from_pydata(V, [], F)
    uvl = me.uv_layers.new(name='UVMap')
    for li, uvv in enumerate(UV): uvl.data[li].uv = uvv
    ob = bpy.data.objects.new('ATL_Bersaglio', me); c.objects.link(ob)
    return ob
MODULO_ATL = 2.0

def nome_img(pagina, modo):
    return ('Atlante_Facciate_' if pagina == 'facciate' else f'Atlante_{pagina}_') + modo

def bake(modo='colore', pagina='facciate'):
    costruisci(modo, pagina)
    ob = bpy.data.objects['ATL_Bersaglio']; sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 8
    nome = nome_img(pagina, modo)
    im = bpy.data.images.get(nome) or bpy.data.images.new(nome, W_IMG, H_IMG)
    m = bpy.data.materials.get('ATL_Bersaglio') or bpy.data.materials.new('ATL_Bersaglio'); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); nt.nodes.new('ShaderNodeOutputMaterial')
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = im; nt.nodes.active = t
    ob.data.materials.clear(); ob.data.materials.append(m)
    b = sc.render.bake; b.use_selected_to_active = True; b.cage_extrusion = 0.05; b.max_ray_distance = 2.4
    b.margin = 2; b.use_clear = True
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in bpy.data.collections['Atlante_Sorgenti'].objects:
        if o != ob and not o.name.startswith('ATL_Piastrella'): o.select_set(True)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
    b.use_selected_to_active = False
    return im

def esporta(pagina='facciate'):
    celle_, righe = PAGINE[pagina][0](), PAGINE[pagina][1]()
    d = cartella(); os.makedirs(d, exist_ok=True); out = {}
    im = bpy.data.images[nome_img(pagina, 'colore')]
    im.filepath_raw = os.path.join(d, f'{pagina}_colore.jpg'); im.file_format = 'JPEG'; im.save(quality=90)
    mk = bpy.data.images[nome_img(pagina, 'maschera')]          # stessa misura del colore (piatta, pesa poco)
    mk.filepath_raw = os.path.join(d, f'{pagina}_maschera.jpg'); mk.file_format = 'JPEG'; mk.save(quality=92)
    celle = {}
    for cella in celle_:
        nome, riga, col, muro, extra, nm = _cella(cella)
        h = ALTEZZA_PEZZO.get(nome, globals().get('ALTEZZA_PEZZO_IND', {}).get(nome, righe[riga][1]))
        celle[nome] = {'uv': [round(x, 5) for x in rett_uv(riga, col, h, nm, righe)], 'larghezza_m': MODULO_ATL*nm, 'altezza_m': h,
                       'riga': riga.rstrip('2')}
    js = {'immagine': f'{pagina}_colore.jpg', 'maschera': f'{pagina}_maschera.jpg', 'pixel_per_metro': PX,
          'nota': 'u cresce verso destra guardando la facciata; maschera bianca = intonaco da tingere', 'celle': celle}
    with open(os.path.join(d, f'{pagina}.json'), 'w', encoding='utf-8') as f: json.dump(js, f, ensure_ascii=False, indent=1)
    for f_ in (f'{pagina}_colore.jpg', f'{pagina}_maschera.jpg', f'{pagina}.json'): out[f_] = round(os.path.getsize(os.path.join(d, f_))/1e6, 2)
    return out

# ---------- tetto dei gusci: ondulato kraft visto dall'alto, ripetibile ----------
#   tetto_ondulato_colore.jpg / _normale.png, 1024 x 1024, periodo 4 m come le altre texture del kit
#   (repeat = 1/4 con UV in metri). Le onde (20 per periodo, passo 0,2 m come l'ondulato del kit) variano
#   lungo u: nel codice u va lungo la gronda, v lungo la pendenza (le costole scendono dal colmo).
#   Il chiaro-scuro delle onde è anche nel colore, così si legge dall'alto con la luce piatta.
TETTI = {   # file: (onde per periodo di 4 m, immagine di base, tinta, altezza dell'onda nel rilievo)
    'tetto_ondulato': (20, 'kraft_colore.jpg', (1, 1, 1), 0.03),
    'tetto_coppi': (16, 'intonaco_colore.jpg', (0.72, 0.25, 0.15), 0.06),
}
def tetto(file_base='tetto_ondulato'):
    onde, base_img, tinta, rilievo = TETTI[file_base]
    d = cartella(); nome = 'ATL_Piastrella_Tetto'
    ob = bpy.data.objects.get(nome)
    if ob is None:
        me = bpy.data.meshes.new(nome)
        me.from_pydata([(0, 0, 0), (4, 0, 0), (4, 4, 0), (0, 4, 0)], [], [(0, 1, 2, 3)])
        uvl = me.uv_layers.new(name='UVMap')
        for li, uvv in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))): uvl.data[li].uv = uvv
        ob = bpy.data.objects.new(nome, me); bpy.data.collections['Atlante_Sorgenti'].objects.link(ob)
    ob.location = (300.0, 20.0, 0.0)
    m = bpy.data.materials.get('ATL_Tetto') or bpy.data.materials.new('ATL_Tetto'); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); L = nt.links.new
    o = nt.nodes.new('ShaderNodeOutputMaterial'); b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    uv = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(uv.outputs['UV'], sep.inputs[0])
    kr = nt.nodes.new('ShaderNodeTexImage'); kr.image = bpy.data.images.load(os.path.join(d, base_img), check_existing=True)
    L(uv.outputs['UV'], kr.inputs['Vector'])
    ang = nt.nodes.new('ShaderNodeMath'); ang.operation = 'MULTIPLY'; ang.inputs[1].default_value = 2*math.pi*onde; L(sep.outputs['X'], ang.inputs[0])
    sn = nt.nodes.new('ShaderNodeMath'); sn.operation = 'SINE'; L(ang.outputs[0], sn.inputs[0])
    lu = nt.nodes.new('ShaderNodeMapRange'); lu.inputs['From Min'].default_value = -1; lu.inputs['To Min'].default_value = 0.74
    L(sn.outputs[0], lu.inputs['Value'])
    cc = nt.nodes.new('ShaderNodeCombineColor')
    for k in ('Red', 'Green', 'Blue'): L(lu.outputs['Result'], cc.inputs[k])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
    tn = nt.nodes.new('ShaderNodeMix'); tn.data_type = 'RGBA'; tn.blend_type = 'MULTIPLY'; tn.inputs[0].default_value = 1.0
    L(kr.outputs['Color'], tn.inputs[6]); tn.inputs[7].default_value = (*tinta, 1)
    L(tn.outputs[2], mx.inputs[6]); L(cc.outputs[0], mx.inputs[7]); L(mx.outputs[2], b.inputs['Base Color'])
    bu = nt.nodes.new('ShaderNodeBump'); bu.inputs['Strength'].default_value = 0.8; bu.inputs['Distance'].default_value = rilievo
    L(sn.outputs[0], bu.inputs['Height']); L(bu.outputs['Normal'], b.inputs['Normal']); L(b.outputs[0], o.inputs['Surface'])
    ob.data.materials.clear(); ob.data.materials.append(m)
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 4
    sc.render.bake.use_selected_to_active = False; out = {}
    for tipo, file, spazio in (('DIFFUSE', file_base + '_colore.jpg', 'sRGB'), ('NORMAL', file_base + '_normale.png', 'Non-Color')):
        im = bpy.data.images.get('ATL_' + file) or bpy.data.images.new('ATL_' + file, 1024, 1024)
        im.colorspace_settings.name = spazio
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = im
        for n in nt.nodes: n.select = False
        t.select = True; nt.nodes.active = t
        for x in bpy.context.view_layer.objects: x.select_set(False)
        bpy.context.view_layer.objects.active = ob; ob.select_set(True)
        if tipo == 'DIFFUSE': bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, margin=0, use_clear=True)
        else: bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', margin=0, use_clear=True)
        nt.nodes.remove(t)
        im.filepath_raw = os.path.join(d, file); im.file_format = 'JPEG' if file.endswith('.jpg') else 'PNG'
        if file.endswith('.jpg'): im.save(quality=90)
        else: im.save()
        out[file] = round(os.path.getsize(im.filepath_raw)/1e6, 2)
    return out

def run():
    bake('colore'); bake('maschera'); r = esporta(); r.update(tetto('tetto_ondulato')); r.update(tetto('tetto_coppi')); return r

if __name__ == '__main__':
    print(run())
