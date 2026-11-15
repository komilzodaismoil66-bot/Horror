import sys, os, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
import chars
sc = bpy.context.scene
cast = {}
for i, (k, spec) in enumerate(chars.SPECS.items()):
    c = chars.R6(k, spec)
    c.root.location = ((i - 2) * 3.6, 0, 2)
    cast[k] = c
cast['emo'].parts['armR'].rotation_euler = (0.4, 0, 0.3)
bpy.ops.mesh.primitive_plane_add(size=80)
g = bpy.context.object; g.data.materials.append(chars.mat('ground', (0.05, 0.05, 0.06), 0.8))
bpy.ops.object.light_add(type='AREA', location=(4, -10, 12)); L = bpy.context.object; L.data.energy = 4000; L.data.size = 6
L.rotation_euler = (0.7, 0, 0.3)
bpy.ops.object.light_add(type='AREA', location=(-6, 8, 6)); R = bpy.context.object; R.data.energy = 2500; R.data.color = (0.4, 0.6, 1.0)
R.rotation_euler = (-1.0, 0, 3.6)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.02, 0.025, 0.04, 1)
bpy.ops.object.camera_add(location=(0, -26, 5.5), rotation=(math.radians(84), 0, 0)); sc.camera = bpy.context.object
sc.camera.data.lens = 40
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 16; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080; sc.render.resolution_percentage = 50
sc.render.filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lineup.png')
t = time.time(); bpy.ops.render.render(write_still=True); print('done', round(time.time() - t, 1))
