# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

bl_info = {
    "name": "Fracture Modifier - Hotkey: 'Alt F'",
    "description": "Pie menu for Fracture Modifier controls",
    "author": "JT Nelson(JTa) and Martin Felke(Scorpion81)",
    "version": (0, 1, 2),
    "blender": (2, 78, 0),
    "location": "3D View",
    "warning": "WIP - use with caution, requires Fracture Helper addon",
    "wiki_url": "",
    "category": "Pie Menu"
    }

#
# Code partially based on the Fracture Helpers addon v2.0.42 by Scorpion81 and Dennis Fassbaender(dafassi)
#
# General TODO list
# clean up code to make more robust in a real workflow
# add 2nd level menus from real workflows for additional functionality in 3D View fullscreen usage
# make consistent the use of fracture helper functions vs. internal functions as needed
#
# NOTE: this addon overrides the existing 'Alt F' hotkey functionality
#

import bpy
from bpy.types import (
        Menu,
        Operator,
        )
import math
import random
from bpy_extras import view3d_utils
from mathutils import Vector, Matrix

# Pie Fracture
class PieFracture(Menu):
    bl_idname = "pie.fracture"
    bl_label = "Pie Fracture"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # 4 - LEFT --dun
        pie.operator("object.create_cluster_helpers", text="Rough Edges Phys", icon='FCURVE')
        # 6 - RIGHT  --WIP needs lots of code
        pie.operator("object.fracture_pie_dust_add", text="Dust(WIP)", icon='STICKY_UVS_VERT')
        # 2 - BOTTOM  --dun
        pie.operator("object.fracture_pie_remove_mod", text="Remove Fracture", icon='X')
        # 8 - TOP **TODO** make toggle of add fm or refracture in context - object.fracture_pie_refresh
        pie.operator("object.fracture", text="(Re)fracture", icon='MOD_EXPLODE')
        # 7 - TOP - LEFT  --use default rb add passive for now **TODO** change to more robust rb handling
        pie.operator("object.fracture_pie_rigidbody_objects_add", text="Rigidbody Passive", icon='MESH_ICOSPHERE')
        # 9 - TOP - RIGHT  --WIP needs lots of code
        pie.operator("object.setup_smoke", text="Inner Smoke(WIP)", icon='MOD_SMOKE')
        # 1 - BOTTOM - LEFT  --dun
        pie.operator("object.create_displaced_edges", text="Rough Edges Sim'd", icon='FCURVE')
        # 3 - BOTTOM - RIGHT  --WIP needs lots of code
        pie.operator("object.setup_debris", text="Debris(WIP)", icon="STICKY_UVS_DISABLE")


# Fracture  object.fracture  hmmm, already works, must pick up the helper addon
# no code since already works...check it out later

# Fracture Pie Refresh, used by other classes
# **TODO** test to see if op works without this code like object.fracture
class FracturePieRefresh(Operator):
    bl_idname = "object.fracture_pie_refresh"
    bl_label = "Fracture Pie Refresh"
    bl_description = "Refracture Object After Changes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        #op = pie.operator("object.fracture_refresh")
        #op.reset = True
        #op.modifier="Fracture"
        bpy.ops.object.fracture_refresh(modifier="Fracture", reset=True)

        return {'FINISHED'}

# Remove FM modifier
class FracturePieRemoveMod(Operator):
    bl_idname = "object.fracture_pie_remove_mod"
    bl_label = "Fracture Pie Remove Modifier"
    bl_description = "Remove Fracture Modifier"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for mod in context.active_object.modifiers:
            bpy.ops.object.modifier_remove(modifier="Fracture")
        return {'FINISHED'}

# Rough Edges Simulated
class ClusterHelperOperator(bpy.types.Operator):
    """Extracts the inner faces and uses this new mesh to generate smaller shards. These will be glued used clustergroups"""
    bl_idname = "object.create_cluster_helpers"
    bl_label = "Physical rough edges"

    def make_cluster_cores(self, context, oldact, lastact):
	    # now convert to objects and create empties at the locs
        tempOb = lastact #context.active_object
        print(tempOb)
        context.scene.objects.active = oldact
        for o in bpy.data.objects:
            o.select = False

        oldact.select = True
        bpy.ops.object.rigidbody_convert_to_objects()

        gr = bpy.data.groups["OB"+oldact.name+"_conv"]
        gh = bpy.data.groups.new("ClusterHelpers")
        context.scene.layers[18] = True
        par = bpy.data.objects.new("ClusterHelperParent", None)
        par.matrix_world = oldact.matrix_world.copy()
        context.scene.objects.link(par)
        par.layers[18] = True
        par.layers[0] = False
        for go in gr.objects:
            if go == tempOb:
                continue
            ob = bpy.data.objects.new("ClusterHelper", None)
            #ob.location = go.location.copy() - par.location
            ob.matrix_world = par.matrix_world.inverted() * go.matrix_world.copy()
            ob.parent = par
            context.scene.objects.link(ob)
            ob.layers[18] = True
            ob.layers[0] = False

            gh.objects.link(ob)
            gr.objects.unlink(go)
            context.scene.objects.unlink(go)
            bpy.data.objects.remove(go)

        bpy.data.groups.remove(gr, do_unlink=True)

        #parent Clusterparent to baseobject
        par.matrix_world = oldact.matrix_world.inverted() * par.matrix_world.copy()
        par.parent = oldact

        #parent innerfaces to baseobject (doesnt work here for some reason, so do it later)
        #tempOb.matrix_world = oldact.matrix_world.inverted() * tempOb.matrix_world.copy()
        #tempOb.parent = oldact

        # select Extracted InnerObject / Baseobject
        print(tempOb)
        tempOb.select = True
        oldact.select = True

        return gh


    def extract_inner_faces(self, context, md):
        # first separate the inner faces as new object
        # execute fracture to be sure we have shard
        bpy.ops.object.fracture_refresh();

        for o in bpy.data.objects:
            o.select = False

        active = context.active_object
        active.select = True
        oldact = active

        #need to dupe object for applying it
        bpy.ops.object.duplicate()

        #context.active_object.select = True
        #bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        # execute fracture again to be sure we have shards
        bpy.ops.object.fracture_refresh(reset=True)

        # apply to get real mesh and edit it
        bpy.ops.object.modifier_apply(apply_as='DATA', modifier=md.name)
        context.active_object.data.update(True, True)

        #remove all other modifiers except FM
        for mod in context.active_object.modifiers:
            bpy.ops.object.modifier_remove(modifier=mod.name)

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')

        context.tool_settings.mesh_select_mode = (False, False, True)
        #i = 0
        for p in context.active_object.data.polygons:
            if p.material_index == 0:
               #print(i, p.material_index, "SELECTED")
               p.select = True
            else:
               #print(i, p.material_index, "DESELECTED")
               p.select = False
            #i += 1

        bpy.ops.object.mode_set(mode='EDIT')
        # delete all with outer material
        bpy.ops.mesh.delete(type='FACE')
        bpy.ops.object.mode_set(mode='OBJECT')

        context.active_object.name = context.active_object.name[:-4] + "_Inner"
        bpy.ops.rigidbody.objects_remove()

        lastact = context.active_object
        context.active_object.layers[18] = True
        context.active_object.layers[0] = False

        print("LAST:", lastact)

        # select Extracted InnerObject / Baseobject of InnerObject -> line 755 (possibly wrong line number by now...)
        # FM: ClusterGroup: insert ClusterHelpers  -> line 841 - 848
        # FM: activate constraints if necessary and set
        #      Angle 0.4 // ClusterAngle 1.0
        # execute fracture_helper()

        return oldact, lastact

    def execute(self, context):
        act = context.active_object is not None
        mod = False

        for md in context.active_object.modifiers:
            if md.type == 'FRACTURE':
                mod = True
                break

        if not(act and mod):
            self.report({'WARNING'}, "Need an active object with fracture modifier")
            return {'CANCELLED'}

        oldact, lastact = self.extract_inner_faces(context, md)
        gh = self.make_cluster_cores(context, oldact, lastact)

        # FM: ClusterGroup: insert ClusterHelpers
        md.cluster_group = gh
        # FM: activate constraints if necessary and set
        #     Angle 0.4 // ClusterAngle 1.0
        md.breaking_angle = math.radians(2.0)
        md.cluster_breaking_angle = math.radians(0.1)
        md.use_constraints = True
        context.scene.objects.active = oldact
        # execute fracture_helper()
        bpy.ops.object.fracture_helper(start=0, random=15.0, snap=False)

        lastact.matrix_world = oldact.matrix_world.inverted() * lastact.matrix_world.copy()
        lastact.parent = oldact

        return {'FINISHED'}
# End class ClusterHelperOperator

# Next 3 defs called by DisplacementEdgesOperator
def ensure_modifier(ob, type, name):
    md = find_modifier(ob, type)
    if md is None:
        md = ob.modifiers.new(type=type, name=name)
    return md

def ensure_uv(context, ob, name):

    #doesnt work, sadly...
    #uv = ob.data.uv_layers.new(name="InnerUV")
    uv = None
    context.scene.objects.active = ob
    #InnerUV should be the 2nd one,
    # maybe we want to have an outer UV too, so add anyway

    for u in ob.data.uv_layers:
        if u.name == name:
            uv = u
            break

    if uv is None:
        bpy.ops.mesh.uv_texture_add()
        uv = ob.data.uv_layers.active
        uv.name = name

    return uv

def ensure_texture(ob):
    name = ob.name +  "_Displacement"
    try:
        tex = bpy.data.textures[name]
    except KeyError:
        tex = bpy.data.textures.new(type='CLOUDS', name=name)

    return tex

#### ADD HERE NEW DEFINITIONS FOR INNER VERTEX (?????)
def find_modifier(ob, typ): # used by Rough Edges Sim'd
    for md in ob.modifiers:
        if md.type == typ:
            return md
    return None

def find_inner_uv(ob): # used by smoke setup operator
    for uv in ob.data.uv_textures:
        if uv.name == "InnerUV":
            return uv
    return None

### Rough edges using displacement modifier:
class DisplacementEdgesOperator(bpy.types.Operator):
    """Setups the modifier stack for simulated (not real) rough edges"""
    bl_idname = "object.create_displaced_edges"
    bl_label = "Simulated rough edges"

    def execute(self, context):

        for ob in context.selected_objects:
            if ob.type != 'MESH':
                continue

            fmd = ensure_modifier(ob, 'FRACTURE', "Fracture")
            smd = ensure_modifier(ob, 'SUBSURF', "Subsurf")
            dmd = ensure_modifier(ob, 'DISPLACE', "Displace")
            emd = ensure_modifier(ob, 'EDGE_SPLIT', "EdgeSplit")

            bpy.ops.object.shade_smooth()
            uv = ensure_uv(context, ob, "InnerUV")
            tex = ensure_texture(ob)

            fmd.use_smooth = True
            fmd.uv_layer = uv.name
            fmd.autohide_dist = 0.0001

            smd.subdivision_type = 'SIMPLE'
            smd.levels = 2

            dmd.texture_coords = 'UV'
            dmd.uv_layer = uv.name
            dmd.strength = 0.5
            dmd.texture = tex

            emd.split_angle = math.radians(45)

            bpy.ops.object.fracture_refresh(modifier="Fracture", reset=True)

        return {'FINISHED'}
# End class DisplacementEdgesOperator

# Rigidbody management, toggles on/off active for now without chaning label
class FracturePieRBAdd(Operator):
    bl_idname = "object.fracture_pie_rigidbody_objects_add"
    bl_label = "Fracture Pie Rigid Body Add"
    bl_description = "Rigid Body Passive"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not context.object.rigid_body:
            bpy.ops.rigidbody.objects_add(type='PASSIVE')
        else:
            bpy.ops.rigidbody.objects_remove()
        return {'FINISHED'}

# Pie Dust Add
class FracturePieDustAdd(Operator):
    bl_idname = "object.fracture_pie_dust_add"
    bl_label = "Fracture Pie Dust Add"
    bl_description = "Dust"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not context.object:
            self.layout.label("Please select at least one object first")
        else:
            bpy.ops.object.setup_smoke()
            bpy.ops.object.setup_dust()
        return {'FINISHED'}
# End class DustSetupOperator

classes = (
    PieFracture,
    FracturePieRefresh,
    FracturePieRemoveMod,
    ClusterHelperOperator,
    DisplacementEdgesOperator,
    FracturePieRBAdd,
    FracturePieDustAdd
    )

addon_keymaps = []


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    wm = bpy.context.window_manager
    if wm.keyconfigs.addon:
        # Fracture
        km = wm.keyconfigs.addon.keymaps.new(name='Object Non-modal')
        kmi = km.keymap_items.new('wm.call_menu_pie', 'F', 'PRESS', alt=True)
        kmi.properties.name = "pie.fracture"
        addon_keymaps.append((km, kmi))


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        for km, kmi in addon_keymaps:
            km.keymap_items.remove(kmi)
    addon_keymaps.clear()


if __name__ == "__main__":
    register()
