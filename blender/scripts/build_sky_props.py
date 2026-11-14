"""Sunline map and sky props, plus the first-person visor/scanner rig.

moon_globe.glb  Unit-radius Moon, LOLA-derived colour + normal maps (from Echo-Path's make_moon_textures.py, LDEM_4).
                Built vertex by vertex so latitude/longitude are exact: Blender (cos φ cos λ, cos φ sin λ, sin φ),
                i.e. glTF/Godot  position(φ, λ) = (cos φ cos λ, sin φ, -cos φ sin λ). +X faces the near side (λ = 0).
                Texture u = (λ + 180)/360 (make_moon_textures.py puts column 0 at 180° W), v = (φ + 90)/180.
earth.glb       Unit-radius Earth, NASA Blue Marble NG (Jan 2004) with clouds screen-blended. u = (λ + 180)/360.
sun_disc.glb    Unit-radius emissive disc facing Godot +Z; Godot scales it to the Sun's angular size from the data.
site_pin.glb    Map pin, 1 unit tall, tip at the origin; Godot tints it per site.
fp_rig.glb      First-person rig in camera space (Godot: +X right, +Y up, -Z forward; Blender: +X right, +Z up,
                +Y forward): right forearm, glove and the cyan scanner, kept low and near the centre so they stay
                on screen in portrait too. The helmet visor frame is a Godot screen overlay instead of a mesh, so it
                fits every aspect ratio. Bone `fp_arm` animates:
                fp_idle (48 f loop), fp_scan_raise (16 f), fp_scan_hold (48 f loop).
Outputs: blender/sky_props.blend and the GLBs above.
"""
import math
import sys
from pathlib import Path
import bpy
import bmesh

sys.path.insert(0, str(Path(r'C:\dev\godot\new-game-project\blender\scripts')))
import importlib
import sunline_common as C
importlib.reload(C)

TEX = C.BLEND_DIR/'data'/'textures'
X = (1, 0, 0)


def textured(name, color_img, normal_img=None, roughness=.95):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = roughness
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = bpy.data.images.load(str(TEX/color_img))
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    if normal_img:
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = bpy.data.images.load(str(TEX/normal_img))
        n.image.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nt.links.new(n.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


def latlon_sphere(name, material_, lon_u, n_lon=96, n_lat=48, lam0=0.0):
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    grid = []
    for i in range(n_lat+1):
        phi = -90+180*i/n_lat
        row = []
        for j in range(n_lon+1):
            lam = lam0+360*j/n_lon          # the texture seam falls between lam0 and lam0 + 360
            p, l = math.radians(phi), math.radians(lam)
            row.append((bm.verts.new((math.cos(p)*math.cos(l), math.cos(p)*math.sin(l), math.sin(p))), phi, lam))
        grid.append(row)
    for i in range(n_lat):
        for j in range(n_lon):
            quad = (grid[i][j], grid[i][j+1], grid[i+1][j+1], grid[i+1][j])
            vs = [q[0] for q in quad]
            if len(set(vs)) < 3:
                continue
            try:
                f = bm.faces.new(vs)
            except ValueError:
                continue
            for loop, (v, phi, lam) in zip(f.loops, quad):
                loop[uv].uv = (lon_u(lam), (phi+90)/180)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)   # merge poles (UVs stay per-loop)
    ob = C.mesh_object(name, bm, material_)
    return ob


def build_fp_rig():
    arm = C.build_rig('FPRig', {
        'root': ((0, 0, 0), (0, .05, 0), None, False),
        'fp_arm': ((.20, 0, -.30), (.09, .30, -.11), 'root', True),
    })
    orange, white, dark = C.mat('suit_orange', roughness=.75), C.mat('suit_white', roughness=.6), C.mat('suit_dark', roughness=.5)
    # match astronaut v3 (the team's turnaround sheet): navy wrist cuff, royal-blue glove
    navy = C.material('suit_navy', (0.09, 0.17, 0.36, 1), roughness=.6)
    royal = C.material('suit_royal', (0.13, 0.30, 0.68, 1), roughness=.55)
    gold = C.material('visor_rim_gold', (0.55, 0.40, 0.18, 1), metallic=.8, roughness=.35)
    # visor rim: a flattened torus just in front of the eye, mostly outside the view; shows at the screen edges
    bm = bmesh.new()
    seg, tube = 48, 8
    ring = []
    for i in range(seg):
        a = 2*math.pi*i/seg
        cx, cz = .17*math.cos(a)*1.35, .17*math.sin(a)
        ring.append([bm.verts.new((cx+.025*math.cos(2*math.pi*k/tube)*math.cos(a), .10+.025*math.sin(2*math.pi*k/tube),
                                   cz+.025*math.cos(2*math.pi*k/tube)*math.sin(a))) for k in range(tube)])
    for i in range(seg):
        for k in range(tube):
            bm.faces.new((ring[i][k], ring[(i+1) % seg][k], ring[(i+1) % seg][(k+1) % tube], ring[i][(k+1) % tube]))
    rim = C.mesh_object('VisorRim', bm, gold)
    C.assign_group(rim, 'root')
    parts = [(C.strut('fp_forearm', (.20, 0, -.30), (.095, .28, -.12), .05, segments=14, material_=orange), 'fp_arm'),
             (C.strut('fp_cuff', (.10, .265, -.125), (.093, .29, -.115), .06, segments=14, material_=navy), 'fp_arm'),
             (C.sphere('fp_glove', .052, (.09, .31, -.105), material_=royal, scale=(.95, 1.2, .9)), 'fp_arm')]
    # scanner: reuse the exported astronaut scanner (points -Y in its own frame); turn it to point +Y (forward)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(C.MODELS/'scanner.glb'))
    sc = next(o for o in set(bpy.data.objects)-before if o.type == 'MESH')
    for o in set(bpy.data.objects)-before:
        if o is not sc:
            bpy.data.objects.remove(o, do_unlink=True)
    sc.parent = None
    sc.rotation_mode = 'XYZ'                      # the glTF importer uses quaternions; switch so the turn applies
    sc.rotation_euler = (0, 0, math.radians(180))
    sc.location = (.10, .34, -.10)
    parts.append((sc, 'fp_arm'))
    bpy.data.objects.remove(rim, do_unlink=True)          # visor frame is a Godot overlay (see docstring)
    body = C.skin(parts, 'FPView', arm)
    # animations: arm low and to the side at rest; raised to the centre to scan
    C.new_action(arm, 'fp_idle', (1, 49))
    for f, s in ((1, 0), (13, 1), (25, 0), (37, -1), (49, 0)):
        C.key_pose(arm, f, {'fp_arm': (X, -14+1.2*s)}, {'fp_arm': (0, 0, -.06+.004*s)})
    C.new_action(arm, 'fp_scan_raise', (1, 17), loop=False)
    for f in range(1, 18, 2):
        u = (f-1)/16
        e = u*u*(3-2*u)
        C.key_pose(arm, f, {'fp_arm': (X, -14+14*e)}, {'fp_arm': (-.05*e, 0, -.06+.07*e)})
    C.new_action(arm, 'fp_scan_hold', (1, 49))
    for f, s in ((1, 0), (13, 1), (25, 0), (37, -1), (49, 0)):
        C.key_pose(arm, f, {'fp_arm': (X, .6*s)}, {'fp_arm': (-.05, 0, .01+.002*s)})
    C.rest(arm)
    return arm, body


def main():
    C.new_scene()
    out = {}
    moon = latlon_sphere('MoonGlobe', textured('moon_surface', 'moon_color_1024.jpg', 'moon_normal_1024.jpg'),
                         lon_u=lambda lam: (lam+180)/360, lam0=-180.0)
    C.export_glb('moon_globe', [moon], animations=False)
    out['moon_globe'] = C.triangles([moon])

    earth_mat = textured('earth_surface', 'earth_color_1024.jpg', roughness=.85)
    earth_mat.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = 0.15   # no grey sheen over the oceans
    earth = latlon_sphere('Earth', earth_mat,
                          lon_u=lambda lam: (lam+180)/360, n_lon=64, n_lat=32, lam0=-180.0)
    # atmospheric limb: camera-facing quad (Godot: billboard, unshaded, additive; fade on the night side by Sun
    # direction). References: Apollo 8 AS08-14-2383 and Artemis II art002e021278 — thin pale-blue rim, lit side only.
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    w = 1.04
    vs = [bm.verts.new((x, -0.0, z)) for x, z in ((-w, -w), (w, -w), (w, w), (-w, w))]
    f = bm.faces.new(vs)
    for loop, (u, v) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uvl].uv = (u, v)
    limb_mat = C.texture_material('earth_limb', (0.62, 0.80, 1.0, 1), albedo='../textures/earth_limb.png', roughness=1.0)
    limb_mat.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (0.62, 0.80, 1.0, 1)
    limb_mat.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 0.8
    tex = next(n for n in limb_mat.node_tree.nodes if n.type == 'TEX_IMAGE')
    limb_mat.node_tree.links.new(tex.outputs['Alpha'], limb_mat.node_tree.nodes['Principled BSDF'].inputs['Alpha'])
    try:
        limb_mat.surface_render_method = 'BLENDED'
    except Exception:
        pass
    limb = C.mesh_object('AtmosphereLimb', bm, limb_mat, smooth=False)
    C.export_glb('earth', [earth, limb], animations=False)
    out['earth'] = C.triangles([earth])

    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, cap_tris=True, segments=48, radius=1.0)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__('mathutils').Matrix.Rotation(math.radians(90), 3, 'X'))
    sun = C.mesh_object('SunDisc', bm, C.material('sun_emission', (1, .97, .9, 1), emission=(1, .97, .9, 1), strength=8.0), smooth=False)
    C.export_glb('sun_disc', [sun], animations=False)
    out['sun_disc'] = C.triangles([sun])

    pin_parts = [C.cylinder('pin_stem', .03, .7, (0, 0, .35), segments=8, material_=C.mat('suit_white')),
                 C.sphere('pin_head', .16, (0, 0, .82), segments=16, rings=10, material_=C.mat('kapton', metallic=.3, roughness=.4)),
                 C.cylinder('pin_tip', .03, .08, (0, 0, .04), segments=8, radius_top=.0, material_=C.mat('suit_dark'))]
    pin_parts[2].rotation_euler = (math.radians(180), 0, 0)
    C.apply_transforms(pin_parts)
    pin = C.join(pin_parts, 'SitePin')
    C.export_glb('site_pin', [pin], animations=False)
    out['site_pin'] = C.triangles([pin])

    arm, fp = build_fp_rig()
    C.export_glb('fp_rig', [arm, fp], animations=True)
    out['fp_rig'] = C.triangles([fp])
    C.save_blend('sky_props')
    return out


result = main()
