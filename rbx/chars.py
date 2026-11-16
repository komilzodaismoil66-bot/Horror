"""Roblox-style R6 characters built procedurally in Blender (bpy).

Rig: root (empty, at the hips) -> torso, head, arms, legs; every limb's origin is its joint,
so posing = rotating parts. Units: 1 = 1 stud (torso 2x2x1, limbs 1x2x1, head ~1.25).
Front of a character = -Y.
"""
import math
import os
import random
import bpy
import bmesh
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex')
os.makedirs(TEX, exist_ok=True)


# ---------------------------------------------------------------- materials
_mats = {}


def mat(name, color, rough=0.55, metal=0.0, emit=None, emit_strength=0.0, image=None, alpha_img=False, coat=1.0):
    rough = min(rough, 0.42) if image is None else rough
    key = name
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    for nm in ('Coat Weight', 'Clearcoat'):
        if nm in p.inputs:
            p.inputs[nm].default_value = coat
            break
    if 'Coat Roughness' in p.inputs:
        p.inputs['Coat Roughness'].default_value = 0.08
    if emit is not None:
        p.inputs['Emission Color'].default_value = (*emit, 1)
        p.inputs['Emission Strength'].default_value = emit_strength
    if image is not None:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(image)
        tex.interpolation = 'Closest' if False else 'Linear'
        nt.links.new(tex.outputs['Color'], p.inputs['Base Color'])
        if alpha_img:
            nt.links.new(tex.outputs['Alpha'], p.inputs['Alpha'])
        if emit is not None:
            nt.links.new(tex.outputs['Color'], p.inputs['Emission Color'])
    _mats[key] = m
    return m


def hexrgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x ** 2.2 for x in c)          # sRGB -> linear


# ---------------------------------------------------------------- meshes
def box(name, size, offset=(0, 0, 0), material=None, bevel=0.07, taper_bottom=1.0, taper_top=1.0):
    """Box whose ORIGIN is at (0,0,0) and geometry is shifted by `offset` (so the origin can be a joint)."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        s = taper_bottom if v.co.z < 0 else taper_top
        v.co = Vector((v.co.x * size[0] * s + offset[0], v.co.y * size[1] * s + offset[1], v.co.z * size[2] + offset[2]))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    if material:
        ob.data.materials.append(material)
    if bevel > 0:
        md = ob.modifiers.new('bev', 'BEVEL')
        md.width = bevel
        md.segments = 4
        md.limit_method = 'NONE'
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def plane(name, w, h, loc, rot=(math.pi / 2, 0, 0), material=None):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    for v in bm.verts:
        v.co.x *= w
        v.co.y *= h
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        for l in f.loops:
            l[uv].uv = (l.vert.co.x / w + 0.5, l.vert.co.y / h + 0.5)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    if material:
        ob.data.materials.append(material)
    return ob


def cyl_head(name, r, h, zc, material, bevel=0.2):
    """Classic toy head: a cylinder with rounded rims (origin at the neck)."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=r, radius2=r, depth=h)
    for v in bm.verts:
        v.co.z += zc
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(material)
    md = ob.modifiers.new('bev', 'BEVEL')
    md.width = bevel
    md.segments = 5
    md.limit_method = 'ANGLE'
    md.angle_limit = math.radians(60)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def curved_face(name, r, w, h, zc, material, n=14):
    """Face decal wrapped around the front (-Y) of the cylinder head."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new()
    a = w / r / 2
    cols = []
    for i in range(n + 1):
        t = -a + 2 * a * i / n
        x, y = math.sin(t) * (r + 0.006), -math.cos(t) * (r + 0.006)
        cols.append((bm.verts.new((x, y, zc - h / 2)), bm.verts.new((x, y, zc + h / 2)), i / n))
    for (b0, t0, u0), (b1, t1, u1) in zip(cols, cols[1:]):
        f = bm.faces.new((b0, b1, t1, t0))
        for l, (u, v) in zip(f.loops, ((u0, 0), (u1, 0), (u1, 1), (u0, 1))):
            l[uv].uv = (u, v)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(material)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def spike(name, base, tip, r, material, sides=5):
    """Cone from base point to tip (hair spikes)."""
    base, tip = Vector(base), Vector(tip)
    d = tip - base
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r, radius2=0.0, depth=d.length)
    for v in bm.verts:
        v.co.z += d.length / 2
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.location = base
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    ob.data.materials.append(material)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def blob(name, loc, scale, material, rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1.0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    ob.scale = scale
    ob.rotation_euler = rot
    ob.data.materials.append(material)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


# ---------------------------------------------------------------- faces (PIL decals)
def face_png(kind):
    path = os.path.join(TEX, f'face_{kind}.png')
    S = 512
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = (20, 20, 22, 255)
    if kind == 'smirk':          # the suit guy: sharp brows, side-eye smirk
        d.polygon([(95, 150), (235, 118), (242, 152), (102, 186)], fill=k)
        d.polygon([(278, 138), (418, 130), (414, 164), (280, 170)], fill=k)
        for (x0, y0) in ((128, 196), (300, 190)):
            d.ellipse((x0, y0, x0 + 96, y0 + 74), fill=(250, 250, 250, 255), outline=k, width=9)
            d.ellipse((x0 + 34, y0 + 16, x0 + 80, y0 + 62), fill=k)
            d.ellipse((x0 + 44, y0 + 22, x0 + 58, y0 + 36), fill=(255, 255, 255, 255))
            d.line([(x0 - 2, y0 + 18), (x0 + 98, y0 + 14)], fill=k, width=14)
        d.line([(185, 372), (270, 384), (345, 358), (378, 330)], fill=k, width=15, joint='curve')
        d.line([(365, 325), (378, 312)], fill=k, width=9)
        d.line([(215, 300), (240, 300)], fill=(60, 60, 60, 160), width=6)
    elif kind == 'teeth':        # the emo guy: angry eyes, clenched teeth
        d.polygon([(110, 160), (225, 200), (220, 222), (105, 185)], fill=k)
        d.polygon([(290, 200), (405, 160), (410, 185), (295, 222)], fill=k)
        d.ellipse((140, 215, 215, 265), fill=(255, 255, 255, 255), outline=k, width=8)
        d.ellipse((300, 215, 375, 265), fill=(255, 255, 255, 255), outline=k, width=8)
        d.ellipse((165, 228, 192, 255), fill=k)
        d.ellipse((323, 228, 350, 255), fill=k)
        d.rounded_rectangle((150, 310, 365, 395), 18, fill=(250, 250, 250, 255), outline=k, width=10)
        for x in range(150, 366, 36):
            d.line([(x, 312), (x, 393)], fill=k, width=6)
        d.line([(152, 352), (363, 352)], fill=k, width=7)
    elif kind == 'calm':         # ally with blue streaks
        d.polygon([(130, 185), (225, 175), (225, 195), (130, 205)], fill=k)
        d.polygon([(290, 175), (385, 185), (385, 205), (290, 195)], fill=k)
        d.ellipse((160, 225, 205, 265), fill=k)
        d.ellipse((310, 225, 355, 265), fill=k)
        d.line([(215, 360), (300, 360)], fill=k, width=11)
    elif kind == 'boss':         # glowing red slits are separate emissive meshes; this is the cracked dark face
        d.line([(120, 170), (230, 205)], fill=(10, 0, 0, 255), width=14)
        d.line([(290, 205), (400, 170)], fill=(10, 0, 0, 255), width=14)
        d.line([(170, 360), (256, 385), (345, 360)], fill=(10, 0, 0, 255), width=10)
        for (a, b) in (((340, 120), (380, 230)), ((380, 230), (360, 300)), ((130, 300), (160, 420))):
            d.line([a, b], fill=(200, 20, 30, 255), width=5)
    im = im.filter(ImageFilter.SMOOTH)
    im.save(path)
    return path


# ---------------------------------------------------------------- the rig
class R6:
    def __init__(self, name, spec):
        self.name = name
        self.spec = spec
        self.parts = {}
        self.build()

    def p(self, key, ob, parent=None):
        ob.parent = parent or self.root
        self.parts[key] = ob
        return ob

    def build(self):
        s = self.spec
        root = bpy.data.objects.new(self.name + '_root', None)
        bpy.context.collection.objects.link(root)
        root.empty_display_size = 0.5
        root.rotation_mode = 'XYZ'
        self.root = root
        skin = mat(self.name + '_skin', hexrgb(s['skin']), 0.3)
        top = mat(self.name + '_top', hexrgb(s['top']), s.get('top_rough', 0.75))
        sleeve = mat(self.name + '_sleeve', hexrgb(s.get('sleeve', s['top'])), 0.75)
        pants = mat(self.name + '_pants', hexrgb(s['pants']), 0.85)
        shoe = mat(self.name + '_shoe', hexrgb(s.get('shoe', '#111111')), 0.4)
        # torso: hips at z=0, torso spans 0..2 above the hips (root sits at hip height 2)
        torso = self.p('torso', box(self.name + '_torso', (2, 1, 2), (0, 0, 1), top, bevel=0.16, taper_bottom=0.9))
        # legs (origin at the hip joint)
        lw = s.get('leg_flare', 1.0)
        for side, x in (('L', -0.5), ('R', 0.5)):
            leg = self.p('leg' + side, box(self.name + '_leg' + side, (1, 1, 2), (0, 0, -1), pants,
                                           taper_bottom=lw, bevel=0.12))
            leg.location = (x, 0, 0)
            sh = box(self.name + '_shoe' + side, (1.02 * lw, 1.12 * lw, 0.35), (0, -0.04, -1.83), shoe, bevel=0.08)
            sh.parent = leg
        # arms (origin at the shoulder joint)
        for side, x in (('L', -1.5), ('R', 1.5)):
            if s.get('long_sleeves', True):
                arm = self.p('arm' + side, box(self.name + '_arm' + side, (1, 1, 1.45), (0, 0, -0.63), sleeve, bevel=0.14), torso)
            else:
                arm = self.p('arm' + side, box(self.name + '_arm' + side, (1, 1, 2), (0, 0, -0.9), skin, bevel=0.16), torso)
            arm.location = (x, 0, 1.9)
            if s.get('long_sleeves', True):
                hand = box(self.name + '_hand' + side, (0.96, 0.96, 0.6), (0, 0, -1.6), skin, bevel=0.2)
                hand.parent = arm
                if s.get('cuffs'):
                    cuff = box(self.name + '_cuff' + side, (1.03, 1.03, 0.16), (0, 0, -1.3),
                               mat(self.name + '_cuffm', hexrgb(s['cuffs']), 0.6), bevel=0.02)
                    cuff.parent = arm
            else:
                slv = box(self.name + '_tsleeve' + side, (1.06, 1.06, 0.7), (0, 0, -0.25), top, bevel=0.06)
                slv.parent = arm
            if s.get('knuckles'):
                kn = box(self.name + '_kn' + side, (1.04, 1.04, 0.12), (0, 0, -1.55),
                         mat(self.name + '_knm', (0.02, 0, 0), 0.4, emit=s['knuckles'], emit_strength=8), bevel=0.02)
                kn.parent = arm
        # head (origin at the neck)
        head = self.p('head', cyl_head(self.name + '_head', 0.63, 1.2, 0.62, skin), torso)
        head.location = (0, 0, 2.0)
        fimg = face_png(s['face'])
        fm = mat(self.name + '_face', (1, 1, 1), 0.6, image=fimg, alpha_img=True)
        fp = curved_face(self.name + '_facepl', 0.63, 1.05, 1.05, 0.62, fm)
        fp.parent = head
        self.build_details(torso, head)
        root.location = (0, 0, 2)
        for ob in [root] + list(self.parts.values()):
            ob.rotation_mode = 'XYZ'

    def build_details(self, torso, head):
        s = self.spec
        kind = s['kind']
        r = random.Random(hash(self.name) % 1000)
        if kind == 'suit':
            white = mat(self.name + '_shirt', hexrgb('#f2f2f2'), 0.6)
            blackm = mat(self.name + '_tie', hexrgb('#0b0b0d'), 0.35)
            v = box(self.name + '_shirtV', (0.62, 0.05, 0.95), (0, -0.505, 1.5), white, bevel=0.0, taper_bottom=0.15)
            v.parent = torso
            tie = box(self.name + '_tieB', (0.16, 0.06, 0.95), (0, -0.53, 1.45), blackm, bevel=0.01, taper_bottom=1.6)
            tie.parent = torso
            knot = box(self.name + '_knot', (0.2, 0.07, 0.14), (0, -0.54, 1.9), blackm, bevel=0.01)
            knot.parent = torso
            sq = box(self.name + '_pocket', (0.28, 0.04, 0.12), (0.55, -0.51, 1.45), white, bevel=0.0)
            sq.parent = torso
            for sx in (-1, 1):
                lap = box(self.name + '_lapel%d' % sx, (0.12, 0.05, 0.9), (sx * 0.32, -0.52, 1.5),
                          mat(self.name + '_lapm', hexrgb('#1c1c20'), 0.4), bevel=0.0)
                lap.rotation_euler = (0, sx * 0.35, 0)
                lap.parent = torso
            hair = mat(self.name + '_hair', hexrgb('#7a4a22'), 0.45)
            hair_d = mat(self.name + '_hair_d', hexrgb('#4f2d12'), 0.45)
            hair_l = mat(self.name + '_hair_l', hexrgb('#a06a35'), 0.4)
            cap = box(self.name + '_haircap', (1.36, 1.32, 0.46), (0, 0.05, 1.13), hair, bevel=0.2)
            cap.parent = head
            back = blob(self.name + '_hairback', (0, 0.3, 1.2), (0.72, 0.5, 0.42), hair_d)
            back.parent = head
            for i in range(3):          # quiff: three big locks rising at the front and swept back
                x = -0.4 + i * 0.4
                lk = blob(self.name + '_lock%d' % i, (x, -0.3, 1.52 + (0.07 if i == 1 else 0)),
                          (0.27, 0.62, 0.26), (hair, hair_l, hair)[i], rot=(-0.5, 0, (i - 1) * 0.1))
                lk.parent = head
            for i in range(2):
                lk = blob(self.name + '_top%d' % i, (-0.22 + i * 0.44, 0.22, 1.42), (0.3, 0.55, 0.2), hair_d,
                          rot=(-1.3, 0, 0))
                lk.parent = head
            for sx in (-1, 1):
                side = box(self.name + '_side%d' % sx, (0.1, 0.6, 0.5), (sx * 0.64, 0.26, 0.95), hair, bevel=0.05)
                side.parent = head
        elif kind == 'emo':
            hair = mat(self.name + '_hair', hexrgb('#0b0b0e'), 0.3)
            cap = box(self.name + '_haircap', (1.36, 1.32, 0.55), (0, 0.05, 1.12), hair, bevel=0.2)
            cap.parent = head
            fr = box(self.name + '_fringe', (1.2, 0.2, 0.55), (0.1, -0.64, 0.95), hair, bevel=0.06)
            fr.rotation_euler = (0, 0, 0.0)
            fr.parent = head
            for i in range(40):          # huge spiky hair
                a = r.uniform(0, 2 * math.pi)
                up = r.uniform(0.25, 1.0)
                base = (math.cos(a) * 0.5, math.sin(a) * 0.5 + 0.12, 1.1)
                L = r.uniform(1.4, 2.6)
                tip = (base[0] + math.cos(a) * L * (1.1 - up), base[1] + math.sin(a) * L * (1.1 - up) + 0.2,
                       base[2] + L * up * 0.9)
                sp = spike(self.name + '_spike%d' % i, base, tip, r.uniform(0.2, 0.34), hair)
                sp.parent = head
            for i in range(6):           # spikes falling over the eyes
                base = (-0.45 + i * 0.18, -0.55, 1.0)
                sp = spike(self.name + '_bang%d' % i, base, (base[0] + r.uniform(-0.15, 0.15), -0.72, 0.55),
                           0.13, hair)
                sp.parent = head
        elif kind == 'mask':
            silver = mat(self.name + '_hair', hexrgb('#c9ced6'), 0.35, metal=0.3)
            cap = box(self.name + '_haircap', (1.32, 1.3, 0.5), (0, 0.06, 1.13), silver, bevel=0.2)
            cap.parent = head
            for i in range(12):
                a = math.pi * (0.1 + 0.8 * i / 11)
                base = (math.cos(a) * 0.55, 0.15 + math.sin(a) * 0.4, 1.15)
                tip = (base[0] * 1.6, base[1] + 0.5, base[2] + r.uniform(0.2, 0.5))
                sp = spike(self.name + '_sp%d' % i, base, tip, 0.18, silver)
                sp.parent = head
            mask = box(self.name + '_mask', (1.12, 0.12, 1.0), (0, -0.62, 0.58),
                       mat(self.name + '_maskm', hexrgb('#f4f4f2'), 0.25), bevel=0.05)
            mask.parent = head
            for sx in (-1, 1):
                slit = box(self.name + '_slit%d' % sx, (0.28, 0.05, 0.08), (sx * 0.25, -0.69, 0.68),
                           mat(self.name + '_slitm', (0.0, 0.0, 0.0), 0.5), bevel=0.0)
                slit.rotation_euler = (0, sx * -0.2, 0)
                slit.parent = head
            zip_ = box(self.name + '_zip', (0.05, 0.04, 1.9), (0.05, -0.51, 1.0),
                       mat(self.name + '_zipm', hexrgb('#9aa0a8'), 0.3, metal=0.8), bevel=0.0)
            zip_.parent = torso
            collar = box(self.name + '_collar', (1.5, 1.1, 0.3), (0, 0, 2.0), mat(self.name + '_top', (0, 0, 0)),
                         bevel=0.08)
            collar.parent = torso
        elif kind == 'streaks':
            hair = mat(self.name + '_hair', hexrgb('#0d0d12'), 0.35)
            blue = mat(self.name + '_blue', hexrgb('#1f6bff'), 0.35, emit=hexrgb('#1f6bff'), emit_strength=0.6)
            cap = box(self.name + '_haircap', (1.34, 1.3, 0.55), (0, 0.04, 1.12), hair, bevel=0.2)
            cap.parent = head
            for i in range(14):
                x = -0.6 + i * 0.093
                base = (x, -0.2 + r.uniform(-0.1, 0.3), 1.3)
                tip = (x * 1.2 + r.uniform(-0.1, 0.1), base[1] - 0.45, 0.85 + r.uniform(-0.1, 0.1))
                sp = spike(self.name + '_str%d' % i, base, tip, 0.15, blue if i % 3 == 1 else hair)
                sp.parent = head
            hood = box(self.name + '_hood', (1.8, 1.0, 0.45), (0, 0.28, 2.05), mat(self.name + '_top', (0, 0, 0)),
                       bevel=0.15)
            hood.parent = torso
        elif kind == 'boss':
            hair = mat(self.name + '_hair', hexrgb('#e9ecf2'), 0.3)
            red = mat(self.name + '_glow', (0.3, 0, 0), 0.4, emit=(1.0, 0.03, 0.02), emit_strength=25)
            cap = box(self.name + '_haircap', (1.36, 1.34, 0.5), (0, 0.06, 1.12), hair, bevel=0.2)
            cap.parent = head
            for i in range(16):          # long white hair streaming back
                a = r.uniform(-1.1, 1.1)
                base = (math.sin(a) * 0.5, 0.25, 1.15 + r.uniform(-0.1, 0.1))
                tip = (base[0] * 1.8, 1.5 + r.uniform(0, 0.9), base[2] - r.uniform(0.2, 1.4))
                sp = spike(self.name + '_hs%d' % i, base, tip, r.uniform(0.18, 0.28), hair)
                sp.parent = head
            for sx in (-1, 1):           # glowing eyes
                eye = box(self.name + '_eye%d' % sx, (0.3, 0.05, 0.09), (sx * 0.26, -0.63, 0.72), red, bevel=0.0)
                eye.rotation_euler = (0, sx * 0.25, 0)
                eye.parent = head
                horn = spike(self.name + '_horn%d' % sx, (sx * 0.45, 0.0, 1.2), (sx * 0.95, 0.2, 2.0), 0.14,
                             mat(self.name + '_hornm', hexrgb('#141418'), 0.3))
                horn.parent = head
                tail = box(self.name + '_coat%d' % sx, (0.95, 0.12, 2.2), (sx * 0.5, 0.52, -1.0),
                           mat(self.name + '_top', (0, 0, 0)), bevel=0.04, taper_bottom=1.25)
                tail.parent = torso
                pad = box(self.name + '_pad%d' % sx, (1.25, 1.25, 0.4), (0, 0, 0.12),
                          mat(self.name + '_padm', hexrgb('#16161c'), 0.3, metal=0.6), bevel=0.1)
                pad.parent = self.parts['arm' + ('L' if sx < 0 else 'R')]
                seam = box(self.name + '_seam%d' % sx, (0.05, 1.04, 1.9), (sx * 0.98, 0, 1.0), red, bevel=0.0)
                seam.parent = torso
            core = box(self.name + '_core', (0.5, 0.06, 0.5), (0, -0.52, 1.25), red, bevel=0.05)
            core.rotation_euler = (0, 0.785, 0)
            core.parent = torso
            belt = box(self.name + '_belt', (2.05, 1.06, 0.2), (0, 0, 0.12), red, bevel=0.0)
            belt.parent = torso

    # ---------------------------------------------------------------- posing
    def key(self, frame, loc=None, rot=None, **joints):
        """Keyframe the rig. joints: torso=(x,y,z) etc. in radians (XYZ euler)."""
        if loc is not None:
            self.root.location = loc
            self.root.keyframe_insert('location', frame=frame)
        if rot is not None:
            self.root.rotation_euler = rot
            self.root.keyframe_insert('rotation_euler', frame=frame)
        for j, v in joints.items():
            ob = self.parts[j]
            ob.rotation_euler = v
            ob.keyframe_insert('rotation_euler', frame=frame)


# ---------------------------------------------------------------- the cast
SPECS = {
    'suit': dict(kind='suit', skin='#e3e3e1', top='#121215', sleeve='#121215', pants='#0e0e10', shoe='#060607',
                 cuffs='#f2f2f2', face='smirk', top_rough=0.5),
    'emo': dict(kind='emo', skin='#e3e3e1', top='#0d0d10', pants='#8ea3b8', shoe='#121212', face='teeth',
                long_sleeves=False, leg_flare=1.28),
    'mask': dict(kind='mask', skin='#e3e3e1', top='#141418', sleeve='#141418', pants='#22232a', shoe='#0c0c0e',
                 face='calm'),
    'blue': dict(kind='streaks', skin='#e3e3e1', top='#16244a', sleeve='#16244a', pants='#7d838c', shoe='#e8e8e8',
                 face='calm', leg_flare=1.25),
    'boss': dict(kind='boss', skin='#3a3a40', top='#0a0a0d', sleeve='#0a0a0d', pants='#0a0a0d', shoe='#050505',
                 face='boss', knuckles=(1.0, 0.05, 0.02), top_rough=0.35),
}
