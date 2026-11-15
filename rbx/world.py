"""Night ruined-city arena + VFX helpers (bpy)."""
import math
import random
import bpy
import bmesh
from mathutils import Vector
from chars import mat, hexrgb, box, blob

FPS = 24


def F(s):
    return int(round(s * FPS)) + 1


# ---------------------------------------------------------------- fog (distance-based, cheap in Cycles)
def fog_group():
    if 'FogMix' in bpy.data.node_groups:
        return bpy.data.node_groups['FogMix']
    g = bpy.data.node_groups.new('FogMix', 'ShaderNodeTree')
    g.interface.new_socket('Shader', in_out='INPUT', socket_type='NodeSocketShader')
    g.interface.new_socket('Shader', in_out='OUTPUT', socket_type='NodeSocketShader')
    n = g.nodes
    gi = n.new('NodeGroupInput')
    go = n.new('NodeGroupOutput')
    cam = n.new('ShaderNodeCameraData')
    m1 = n.new('ShaderNodeMath')
    m1.operation = 'MULTIPLY'
    m1.inputs[1].default_value = -0.028
    m1.name = 'density'
    m2 = n.new('ShaderNodeMath')
    m2.operation = 'EXPONENT'
    m3 = n.new('ShaderNodeMath')
    m3.operation = 'SUBTRACT'
    m3.inputs[0].default_value = 1.0
    rgb = n.new('ShaderNodeRGB')
    rgb.name = 'FogColor'
    rgb.outputs[0].default_value = (0.020, 0.028, 0.045, 1)
    em = n.new('ShaderNodeEmission')
    mix = n.new('ShaderNodeMixShader')
    L = g.links
    L.new(cam.outputs['View Distance'], m1.inputs[0])
    L.new(m1.outputs[0], m2.inputs[0])
    L.new(m2.outputs[0], m3.inputs[1])
    L.new(m3.outputs[0], mix.inputs[0])
    L.new(gi.outputs[0], mix.inputs[1])
    L.new(rgb.outputs[0], em.inputs[0])
    L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], go.inputs[0])
    return g


def apply_fog(skip_prefix=('fx_',)):
    g = fog_group()
    for m in bpy.data.materials:
        if any(m.name.startswith(p) for p in skip_prefix) or not m.use_nodes:
            continue
        nt = m.node_tree
        out = nt.nodes.get('Material Output')
        if out is None or not out.inputs['Surface'].is_linked:
            continue
        link = out.inputs['Surface'].links[0]
        src = link.from_socket
        if src.node.type == 'GROUP':
            continue
        gn = nt.nodes.new('ShaderNodeGroup')
        gn.node_tree = g
        nt.links.remove(link)
        nt.links.new(src, gn.inputs[0])
        nt.links.new(gn.outputs[0], out.inputs['Surface'])


def key_fog(t, color, density=None):
    g = fog_group()
    rgb = g.nodes['FogColor'].outputs[0]
    rgb.default_value = (*color, 1)
    rgb.keyframe_insert('default_value', frame=F(t))
    if density is not None:
        d = g.nodes['density'].inputs[1]
        d.default_value = -density
        d.keyframe_insert('default_value', frame=F(t))


# ---------------------------------------------------------------- environment
def ground():
    m = bpy.data.materials.new('asphalt')
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    p.inputs['Roughness'].default_value = 0.55
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 1.5
    noise.inputs['Detail'].default_value = 8
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.018, 0.019, 0.022, 1)
    ramp.color_ramp.elements[1].color = (0.06, 0.062, 0.07, 1)
    nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    rough = nt.nodes.new('ShaderNodeMapRange')
    nt.links.new(noise.outputs['Fac'], rough.inputs['Value'])
    rough.inputs['To Min'].default_value = 0.25          # wet patches reflect the lamps
    rough.inputs['To Max'].default_value = 0.85
    nt.links.new(rough.outputs['Result'], p.inputs['Roughness'])
    bpy.ops.mesh.primitive_plane_add(size=400)
    g = bpy.context.object
    g.name = 'ground'
    g.data.materials.append(m)
    # painted arena circle
    line = mat('paint', (0.25, 0.22, 0.12), 0.6)
    bpy.ops.mesh.primitive_torus_add(major_radius=11, minor_radius=0.08, location=(0, 0, 0.0))
    t = bpy.context.object
    t.scale = (1, 1, 0.05)
    t.data.materials.append(line)


def buildings(seed=3):
    r = random.Random(seed)
    conc = mat('concrete', hexrgb('#2a2d33'), 0.9)
    conc2 = mat('concrete2', hexrgb('#1d2026'), 0.9)
    win_on = mat('win_on', (0.3, 0.2, 0.08), 0.5, emit=(1.0, 0.62, 0.3), emit_strength=3)
    win_off = mat('win_off', (0.01, 0.01, 0.012), 0.3)
    for i in range(34):
        a = 2 * math.pi * i / 34 + r.uniform(-0.05, 0.05)
        d = r.uniform(34, 60)
        w, dp, h = r.uniform(8, 16), r.uniform(8, 14), r.uniform(12, 46)
        x, y = math.cos(a) * d, math.sin(a) * d
        b = box('bld%d' % i, (w, dp, h), (0, 0, h / 2), conc if i % 2 else conc2, bevel=0.0)
        b.location = (x, y, 0)
        b.rotation_euler = (0, 0, a + r.uniform(-0.2, 0.2))
        # broken top
        for k in range(r.randint(1, 3)):
            c = box('bldc%d_%d' % (i, k), (r.uniform(2, w * 0.6), r.uniform(2, dp * 0.6), r.uniform(1, 5)),
                    (r.uniform(-w / 3, w / 3), r.uniform(-dp / 3, dp / 3), h + r.uniform(0, 2)), conc2, bevel=0.0)
            c.parent = b
            c.rotation_euler = (r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3), 0)
        # windows facing the arena
        rows = int(h / 4)
        for rr in range(rows):
            for cc in range(int(w / 3)):
                if r.random() < 0.5:
                    continue
                wm = win_on if r.random() < 0.08 else win_off
                wb = box('win%d_%d_%d' % (i, rr, cc), (1.2, 0.2, 1.8), (-w / 2 + 1.8 + cc * 3, -dp / 2 - 0.05,
                                                                        2.5 + rr * 4), wm, bevel=0.0)
                wb.parent = b
                # parent frame keeps it on the building's front (which faces -Y locally); turn the building so
                # its local -Y faces the centre
        b.rotation_euler = (0, 0, math.atan2(y, x) + math.pi / 2 + r.uniform(-0.2, 0.2))


def debris_field(seed=5, n=90):
    r = random.Random(seed)
    conc = mat('rubble', hexrgb('#34373d'), 0.95)
    for i in range(n):
        a = r.uniform(0, 2 * math.pi)
        d = r.uniform(13, 32)
        s = r.uniform(0.4, 2.2)
        b = box('rub%d' % i, (s, s * r.uniform(0.5, 1.2), s * r.uniform(0.3, 0.9)), (0, 0, 0), conc, bevel=0.04)
        b.location = (math.cos(a) * d, math.sin(a) * d, s * 0.25)
        b.rotation_euler = (r.uniform(-0.4, 0.4), r.uniform(-0.4, 0.4), r.uniform(0, 3))


LAMPS = []


def lamps():
    pole = mat('pole', hexrgb('#15171c'), 0.5, metal=0.6)
    bulb = mat('fx_bulb', (1, 0.7, 0.4), 0.3, emit=(1.0, 0.6, 0.28), emit_strength=40)
    for i, (x, y) in enumerate(((-15, 12), (15, 12), (-15, -12), (16, -11), (0, 22))):
        p = box('lamp%d' % i, (0.4, 0.4, 9), (0, 0, 4.5), pole, bevel=0.05)
        p.location = (x, y, 0)
        h = box('lamph%d' % i, (1.6, 0.6, 0.4), (0.6, 0, 9.0), pole, bevel=0.05)
        h.parent = p
        bb = box('fx_lampb%d' % i, (1.2, 0.4, 0.12), (0.7, 0, 8.76), bulb, bevel=0.0)
        bb.parent = p
        bpy.ops.object.light_add(type='SPOT', location=(x + 0.7, y, 8.6))
        L = bpy.context.object
        L.name = 'lampL%d' % i
        L.data.energy = 2600
        L.data.color = (1.0, 0.62, 0.32)
        L.data.spot_size = math.radians(95)
        L.data.spot_blend = 0.6
        L.data.shadow_soft_size = 0.4
        LAMPS.append(L)


PILLARS = {}


def pillar(name, pos, size=(2.2, 2.2, 9), grid=(2, 2, 6)):
    """A concrete pillar made of chunks so it can shatter."""
    conc = mat('pillar', hexrgb('#4a4d55'), 0.85)
    chunks = []
    sx, sy, sz = size[0] / grid[0], size[1] / grid[1], size[2] / grid[2]
    for i in range(grid[0]):
        for j in range(grid[1]):
            for k in range(grid[2]):
                c = box('%s_%d%d%d' % (name, i, j, k), (sx * 0.98, sy * 0.98, sz * 0.98), (0, 0, 0), conc, bevel=0.03)
                c.location = (pos[0] - size[0] / 2 + sx * (i + 0.5), pos[1] - size[1] / 2 + sy * (j + 0.5),
                              sz * (k + 0.5))
                chunks.append(c)
    PILLARS[name] = (chunks, pos)
    return chunks


def shatter(name, t, impact_dir, power=14.0, seed=1):
    chunks, pos = PILLARS[name]
    r = random.Random(seed)
    f0 = F(t)
    for c in chunks:
        p0 = Vector(c.location)
        c.keyframe_insert('location', frame=f0)
        c.keyframe_insert('rotation_euler', frame=f0)
        v = Vector((impact_dir[0] * power * r.uniform(0.5, 1.2) + r.uniform(-3, 3),
                    impact_dir[1] * power * r.uniform(0.5, 1.2) + r.uniform(-3, 3), r.uniform(2, 9)))
        rot = Vector((r.uniform(-8, 8), r.uniform(-8, 8), r.uniform(-8, 8)))
        landed = False
        for k in range(1, 60):
            tt = k * 2 / FPS
            p = p0 + v * tt + Vector((0, 0, -0.5 * 25 * tt * tt))
            if p.z < 0.5:
                p.z = 0.5
                landed = True
            c.location = p
            c.rotation_euler = rot * min(tt, 1.0 if landed else tt)
            c.keyframe_insert('location', frame=f0 + 2 * k)
            c.keyframe_insert('rotation_euler', frame=f0 + 2 * k)
            if landed:
                break


# ---------------------------------------------------------------- VFX
_fx_n = [0]


def _fxname(base):
    _fx_n[0] += 1
    return 'fx_%s_%d' % (base, _fx_n[0])


def fx_mat(color, strength, name=None):
    """Emission + transparency mix whose 'fade' (Value node) can be keyframed. Returns (material, fade socket)."""
    m = bpy.data.materials.new(name or _fxname('m'))
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*color, 1)
    em.inputs['Strength'].default_value = strength
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    val = nt.nodes.new('ShaderNodeValue')
    val.name = 'fade'
    val.outputs[0].default_value = 1.0
    nt.links.new(val.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    return m, val.outputs[0]


def smoke_mat(color, name=None):
    m = bpy.data.materials.new(name or _fxname('smoke'))
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = 1.0
    val = nt.nodes.new('ShaderNodeValue')
    val.name = 'fade'
    val.outputs[0].default_value = 0.0
    nt.links.new(val.outputs[0], p.inputs['Alpha'])
    return m, val.outputs[0]


def key_fade(sock, pairs):
    for t, v in pairs:
        sock.default_value = v
        sock.keyframe_insert('default_value', frame=F(t) if isinstance(t, float) else t)


def key_scale(ob, pairs):
    for f, s in pairs:
        ob.scale = (s, s, s) if not isinstance(s, tuple) else s
        ob.keyframe_insert('scale', frame=f)


def impact(t, pos, size=1.0, color=(1.0, 0.85, 0.6), light=True):
    """Hit flash: bright core + expanding ring + point light pulse."""
    f = F(t)
    m, fade = fx_mat(color, 30)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=pos)
    s = bpy.context.object
    s.name = _fxname('flash')
    s.data.materials.append(m)
    key_scale(s, [(f - 1, 0.01), (f, 0.9 * size), (f + 2, 1.4 * size), (f + 5, 0.01)])
    key_fade(fade, [(f - 1, 0), (f, 1), (f + 4, 0)])
    rm, rfade = fx_mat(color, 12)
    bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.06, location=pos)
    ring = bpy.context.object
    ring.name = _fxname('ring')
    ring.rotation_euler = (random.uniform(0, 3), random.uniform(0, 3), 0)
    ring.data.materials.append(rm)
    key_scale(ring, [(f - 1, 0.01), (f, 0.5 * size), (f + 8, 4.5 * size)])
    key_fade(rfade, [(f - 1, 0), (f, 1), (f + 8, 0)])
    if light:
        bpy.ops.object.light_add(type='POINT', location=pos)
        L = bpy.context.object
        L.name = _fxname('hitlight')
        L.data.color = color
        L.data.shadow_soft_size = 0.5
        for ff, e in ((f - 1, 0), (f, 4000 * size), (f + 5, 0)):
            L.data.energy = e
            L.data.keyframe_insert('energy', frame=ff)


def shockwave(t, pos, r_end=20, dur=0.7, color=(0.8, 0.9, 1.0), strength=10, flat=True):
    f = F(t)
    m, fade = fx_mat(color, strength)
    bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.12, location=pos)
    ring = bpy.context.object
    ring.name = _fxname('wave')
    ring.data.materials.append(m)
    if not flat:
        ring.rotation_euler = (math.pi / 2, 0, random.uniform(0, 3))
    key_scale(ring, [(f - 1, (0.01, 0.01, 0.01)), (f, (1, 1, 1)), (f + int(dur * FPS), (r_end, r_end, r_end * 0.4))])
    key_fade(fade, [(f - 1, 0), (f, 1), (f + int(dur * FPS), 0)])


def dust(t, pos, n=8, spread=3.0, size=2.0, dur=1.6, color=(0.18, 0.17, 0.16), seed=0):
    r = random.Random(seed)
    f = F(t)
    for i in range(n):
        m, fade = smoke_mat(color)
        p = (pos[0] + r.uniform(-1, 1) * spread * 0.3, pos[1] + r.uniform(-1, 1) * spread * 0.3, pos[2] + 0.3)
        b = blob(_fxname('dust'), p, (0.01, 0.01, 0.01), m)
        b.keyframe_insert('location', frame=f - 1)
        end = (p[0] + r.uniform(-1, 1) * spread, p[1] + r.uniform(-1, 1) * spread, p[2] + r.uniform(0.3, 1.8))
        sz = size * r.uniform(0.6, 1.3)
        key_scale(b, [(f - 1, 0.01), (f, sz * 0.4), (f + int(dur * FPS), sz)])
        b.location = end
        b.keyframe_insert('location', frame=f + int(dur * FPS))
        key_fade(fade, [(f - 1, 0), (f + 1, 0.55), (f + int(dur * FPS), 0)])


def debris(t, pos, n=14, speed=10, seed=0, size=0.35):
    r = random.Random(seed)
    m = mat('rubble', hexrgb('#34373d'), 0.95)
    f0 = F(t)
    for i in range(n):
        s = size * r.uniform(0.5, 1.6)
        c = box(_fxname('deb'), (s, s, s), (0, 0, 0), m, bevel=0.02)
        p0 = Vector((pos[0], pos[1], max(0.3, pos[2])))
        c.location = (p0.x, p0.y, -5)
        c.keyframe_insert('location', frame=f0 - 1)
        v = Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(0.6, 1.6))) * speed
        rot = Vector((r.uniform(-9, 9), r.uniform(-9, 9), r.uniform(-9, 9)))
        for k in range(0, 40):
            tt = k * 2 / FPS
            p = p0 + v * tt + Vector((0, 0, -0.5 * 30 * tt * tt))
            done = p.z < s / 2 and k > 0
            if done:
                p.z = s / 2
            c.location = p
            c.rotation_euler = rot * tt
            c.keyframe_insert('location', frame=f0 + 2 * k)
            c.keyframe_insert('rotation_euler', frame=f0 + 2 * k)
            if done:
                break


def cracks(t, center, n=9, length=14, color=(1.0, 0.06, 0.02), seed=0, dur=1.2, width=0.22):
    r = random.Random(seed)
    m, fade = fx_mat(color, 12)
    f0 = F(t)
    for i in range(n):
        a = 2 * math.pi * i / n + r.uniform(-0.2, 0.2)
        x, y = center[0], center[1]
        segs = 6
        for k in range(segs):
            a += r.uniform(-0.5, 0.5)
            L = length / segs * r.uniform(0.7, 1.3)
            nx, ny = x + math.cos(a) * L, y + math.sin(a) * L
            c = box(_fxname('crack'), (L, width * (1 - k / segs) + 0.05, 0.05), (L / 2, 0, 0.02), m, bevel=0.0)
            c.location = (x, y, 0)
            c.rotation_euler = (0, 0, a)
            fs = f0 + int(k * dur * FPS / segs)
            key_scale(c, [(fs - 1, (0.001, 1, 1)), (fs + 3, (1, 1, 1))])
            x, y = nx, ny
    key_fade(fade, [(f0 - 1, 1)])
    return fade


def smoke_cloud(t0, t1, center, n=26, radius=7, color=(0.06, 0.06, 0.07), seed=0, rise=2.0):
    r = random.Random(seed)
    for i in range(n):
        m, fade = smoke_mat(color)
        p = Vector((center[0] + r.uniform(-radius, radius), center[1] + r.uniform(-radius, radius) * 0.6,
                    r.uniform(0.5, 6)))
        b = blob(_fxname('smk'), p, (1, 1, 1), m)
        sz = r.uniform(2.5, 4.5)
        key_scale(b, [(F(t0), sz * 0.7), (F(t1), sz * 1.3)])
        b.keyframe_insert('location', frame=F(t0))
        b.location = p + Vector((r.uniform(-2, 2), r.uniform(-1, 1), rise))
        b.keyframe_insert('location', frame=F(t1))
        key_fade(fade, [(F(t0) - 1, 0), (F(t0) + 12, 0.85), (F(t1) - 30, 0.7), (F(t1), 0)])


def energy_sphere(t0, t1, pos, r_end=60, color=(1.0, 0.1, 0.05)):
    m, fade = fx_mat(color, 6)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1, location=pos)
    s = bpy.context.object
    s.name = _fxname('esphere')
    s.data.materials.append(m)
    for p in s.data.polygons:
        p.use_smooth = True
    key_scale(s, [(F(t0) - 1, 0.01), (F(t0), 1.5), (F(t1), r_end)])
    key_fade(fade, [(F(t0) - 1, 0), (F(t0), 0.55), (F(t1) - 6, 0.35), (F(t1), 0)])
    bpy.ops.object.light_add(type='POINT', location=pos)
    L = bpy.context.object
    L.data.color = color
    for ff, e in ((F(t0) - 1, 0), (F(t0) + 4, 60000), (F(t1), 0)):
        L.data.energy = e
        L.data.keyframe_insert('energy', frame=ff)


def aura(t0, t1, follow, n=30, color=(1.0, 0.08, 0.04), seed=0):
    """Floating red embers orbiting a character (parented to its root)."""
    r = random.Random(seed)
    m, fade = fx_mat(color, 20)
    for i in range(n):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.07)
        e = bpy.context.object
        e.name = _fxname('ember')
        e.data.materials.append(m)
        e.parent = follow
        a0 = r.uniform(0, 2 * math.pi)
        rad = r.uniform(1.5, 3.0)
        for k in range(int((t1 - t0) * 4) + 1):
            tt = t0 + k / 4
            a = a0 + tt * r.uniform(0.6, 1.4)
            e.location = (math.cos(a) * rad, math.sin(a) * rad, ((tt * 0.8 + i * 0.37) % 6.0) - 2.0)
            e.keyframe_insert('location', frame=F(tt))
    key_fade(fade, [(F(t0) - 1, 0), (F(t0) + 10, 1), (F(t1), 1)])
