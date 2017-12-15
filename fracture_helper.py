bl_info = {
    "name": "Fracture Helpers",
    "author": "scorpion81 and Dennis Fassbaender",
    "version": (2, 1, 5),
    "blender": (2, 79, 0),
    "location": "Tool Shelf > Fracture > Fracture Helpers",
    "description": "Several fracture modifier setup helpers",
    "warning": "",
    "wiki_url": "",
    "category": "Object"}

import bpy
import math
import random
from bpy_extras import view3d_utils
from mathutils import Vector, Matrix

def setup_particles(count=150):
    ob = bpy.context.active_object
    bpy.ops.object.particle_system_add()
    #make particle system settings here....
    ob.particle_systems[0].name = "ParticleHelper"
    psys = ob.particle_systems[0].settings
    psys.count = count
    psys.frame_start = 1
    psys.frame_end = 1
    psys.lifetime = 1
    psys.factor_random = 0.0
    psys.normal_factor = 0.0
    psys.effector_weights.gravity = 0.0
    psys.draw_method = 'NONE'
    psys.use_render_emitter = False
    psys.render_type = 'NONE'
    psys.use_modifier_stack = True
    psys.emit_from = 'VOLUME'
    psys.distribution = 'RAND'
    psys.physics_type = 'NO'
    
def raycast(context, event, ray_max=1000.0, group=None):
    """Run this function on left mouse, execute the ray cast"""
    # get the context arguments
    scene = context.scene
    region = context.region
    rv3d = context.region_data
    coord = event.mouse_region_x, event.mouse_region_y
    hit_world = None
    normal_world = None

    # get the ray from the viewport and mouse
    view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)

    ray_target = ray_origin + (view_vector * ray_max)

    def visible_objects_and_duplis(group=None):
        """Loop over (object, matrix) pairs (mesh only)"""

        for obj in context.visible_objects:

            if group is not None:
                if obj.name in group.objects:
                   continue

            if obj.type == 'MESH':
                yield (obj, obj.matrix_world.copy())

            if obj.dupli_type != 'NONE':
                obj.dupli_list_create(scene)
                for dob in obj.dupli_list:
                    obj_dupli = dob.object
                    if obj_dupli.type == 'MESH':
                        yield (obj_dupli, dob.matrix.copy())

            obj.dupli_list_clear()

    def obj_ray_cast(obj, matrix):
        """Wrapper for ray casting that moves the ray into object space"""

        # get the ray relative to the object
        matrix_inv = matrix.inverted()
        ray_origin_obj = matrix_inv * ray_origin
        ray_target_obj = matrix_inv * ray_target

        # cast the ray
        result, hit, normal, face_index = obj.ray_cast(ray_origin_obj, ray_target_obj)

        if face_index != -1:
            return hit, normal, face_index
        else:
            return None, None, None

    # cast rays and find the closest object
    best_length_squared = ray_max * ray_max
    best_obj = None

    for obj, matrix in visible_objects_and_duplis(group=group):
        if obj.type == 'MESH':
            hit, normal, face_index = obj_ray_cast(obj, matrix)
            if hit is not None:
                hit_world = matrix * hit
                normal_world = matrix * normal
                scene.cursor_location = hit_world
                length_squared = (hit_world - ray_origin).length_squared
                if length_squared < best_length_squared:
                    best_length_squared = length_squared
                    best_obj = obj

    # now we have the object under the mouse cursor,
    # we could do lots of stuff but for the example just select.
    if best_obj is not None:
        best_obj.select = True
        context.scene.objects.active = best_obj

    return hit_world, normal_world

def check_fm():
    if bpy.context.active_object is None:
        return False

    for md in bpy.context.active_object.modifiers:
        if md.type == 'FRACTURE':
            return True
    return False

class MainOperationsPanel(bpy.types.Panel):
    bl_label = "Main operations" 
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Fracture"
    #bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        if not context.object:
            self.layout.label("Please select atleast one object first")
        else:
            layout = self.layout
            col = layout.column(align=True)
            md = find_modifier(context.object, "FRACTURE")
            if md:
                row = col.row(align=True)
                row.context_pointer_set("modifier", md)
                row.operator("object.modifier_remove", text = "Remove Fracture", icon='X')
                row.prop(md, "show_render", text="")
                row.prop(md, "show_viewport", text="")
                
                col.operator("fracture.execute", icon='MOD_EXPLODE')
                col.prop(md, "auto_execute", text="Toggle Automatic Execution", icon='FILE_REFRESH')
            else:
                col.operator("fracture.execute", icon='MOD_EXPLODE', text="Add Fracture")
                if not context.object.rigid_body:
                    col.operator("rigidbody.object_add", icon='MESH_ICOSPHERE',text="Add Rigidbody")
                else:
                    col.operator("rigidbody.object_remove", icon='X',text="Remove Rigidbody")
            if context.object.rigid_body:
                rb = context.object.rigid_body
                #col.prop(rb, "enabled")
                layout.prop(rb, "type")
                row = layout.row()
                row.prop(rb, "kinematic", text="Animated")
                row = layout.row()
                row.prop(rb, "stop_trigger", text="Untrigger")
                
                if rb.type == "ACTIVE":
                    row.prop(rb, "is_trigger")
                
                    row = layout.row()
                    row.prop(rb, "use_kinematic_deactivation", text="Triggered")
                    row.prop(rb, "is_ghost")
                    
                    layout.prop(rb, "mass")
                

class VIEW3D_SettingsPanel(bpy.types.Panel):
    bl_label = "3D View Settings" 
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Fracture"
    #bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        if not context.object:
            self.layout.label("Please select atleast one object first")
            
        else:
            layout = self.layout
            col = layout.column(align=True)
            col.prop(context.object, "show_wire", text="Toggle Wireframe", icon ='WIRE')
            col.prop(context.space_data, "show_relationship_lines", text="Toggle Relationship Lines", icon = 'PARTICLE_TIP')
            if len(context.object.particle_systems) > 0:
                col.prop(context.object.particle_systems[0].settings, "draw_method", text="", icon = 'MOD_PARTICLES')
            md = find_modifier(context.object, 'DYNAMIC_PAINT')
            if md and md.canvas_settings and "dp_canvas_FM" in md.canvas_settings.canvas_surfaces.keys():
                surf = md.canvas_settings.canvas_surfaces["dp_canvas_FM"]
                col.prop(surf, "show_preview", text="Toggle Dynamic Paint Preview", toggle=True, icon='RESTRICT_VIEW_OFF' if surf.show_preview else 'RESTRICT_VIEW_ON')
            
class ViewOperatorFracture(bpy.types.Operator):
    """Modal mouse based object fracture"""
    bl_idname = "fracture.mouse_based_fracture"
    bl_label = "Mouse based fracture"
    scaling = False
    hit2d = None
    size = 1.0
    act = None
    md = None
    gr = None
    msg = "Press LMB over fractured object to create helper, drag mouse to change size, release LMB to confirm, RMB or Esc ends modal operator"
    scale = Vector((1, 1, 1))

    def modal(self, context, event):
        #if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
        #    # allow navigation
        #    return {'PASS_THROUGH'}
        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                hit, normal = raycast(context, event, 1000.0, self.gr)
                if hit is not None and check_fm():
                    self.act = context.active_object
                    #self.act.select = False
                    if context.scene.mouse_mode == "Radial":
                        vec = normal.normalized()
                        #if (vec != Vector((0, 0, 1))):
                        #    vec = vec.cross(Vector((0, 0, 1))
                        
                        self.scale[0] = 1 #if vec[0] == 0 else vec[0] * 0
                        self.scale[1] = 1 #if vec[1] == 0 else vec[1] * 0
                        self.scale[2] = 1 #if vec[2] == 0 else vec[2] * 0
                        
                        print(self.scale)
                        
                        #bpy.ops.mesh.primitive_uv_sphere_add(size = 0.05, location=hit, rotation=rot, \
                        #                                     segments=self.act.mouse_segments, ring_count=self.act.mouse_rings)
                        #bpy.ops.object.editmode_toggle()
                        #bpy.ops.mesh.remove_doubles()
                        #bpy.ops.object.editmode_toggle()
                        
                        #sphere wont work so try with concentric circles
                        radius = 0.15
                        bpy.ops.mesh.primitive_circle_add(radius=radius, \
                                                              vertices=context.scene.mouse_segments, \
                                                              location=hit)
                        
                        bpy.ops.object.editmode_toggle()
             
                        radius += 0.1
                        for r in range(self.act.mouse_rings):
                            bpy.ops.mesh.primitive_circle_add(radius=radius, \
                                                              vertices=context.scene.mouse_segments, \
                                                              location=hit)
                            ob = context.active_object
                            ob.select = True
                            radius += 0.1
                        
                        bpy.ops.object.editmode_toggle()
                        
                        z = Vector((0, 0, 1))
                        ob = context.active_object
                        angle = vec.angle(z)
                        axis = z.cross(vec)
                        mat = Matrix.Rotation(angle, 4, axis)
                        mat.translation = self.act.matrix_world.inverted() * hit
                        
                        ob.matrix_world = self.act.matrix_world * mat
                                                     
                    else:
                        if context.scene.mouse_object == "Cube":
                            bpy.ops.mesh.primitive_cube_add(radius = 0.05, location=hit)
                        elif context.scene.mouse_object == "Sphere":
                            bpy.ops.mesh.primitive_uv_sphere_add(size = 0.05, location=hit)
                        else:
                            if context.scene.mouse_custom_object == "":
                                self.report({'WARNING'}, "Need to pick a custom object, please retry")
                                return {'CANCELLED'}
                                
                            ob = bpy.data.objects[context.scene.mouse_custom_object]
                            if ob != None:
                                context.scene.objects.active = ob
                                self.act.select = False
                                ob.select = True
                                bpy.ops.object.duplicate()
                                nob = context.active_object
                                nob.location = hit
                            else:
                                self.report({'WARNING'}, "Need to pick a custom object, please retry")
                                return {'CANCELLED'}
                    self.scaling = True
                    self.hit2d = event.mouse_region_x, event.mouse_region_y
                    context.active_object.draw_type = 'WIRE'
            elif event.value == 'RELEASE':
                   
                    self.hit2d = None
                    #print(self.act, context.active_object)
                    if not self.scaling:
                        self.report({'WARNING'}, "Ambigous target object, please retry")
                        context.scene.mouse_status = "Start mouse based fracture"
                        context.area.header_text_set()
                        return {'CANCELLED'}

                    self.scaling = False
                    if self.act != context.active_object and self.act is not None \
                    and context.active_object is not None:
                        if context.scene.mouse_mode == "Uniform":
                            setup_particles(context.scene.mouse_count)
                        self.gr.objects.link(context.active_object)
                        context.active_object.parent = self.act
                        context.active_object.location -= self.act.location
                        #put last helpers on a higher layer, in this case layer 16.
                        for x in range(0, 19):
                            if x == 15:
                                context.active_object.layers[x] = True
                            else:
                                context.active_object.layers[x] = False
                        
                        context.active_object.hide = True
                        context.scene.objects.active = self.act
                        if check_fm(): #active object changes here, so check again
                            bpy.ops.object.fracture_refresh(reset=False)
            return {'RUNNING_MODAL'}
        elif event.type == 'MOUSEMOVE':
            if not self.scaling:
                #main(context, event)
                pass
            else:
                hit2d = event.mouse_region_x, event.mouse_region_y
                size = Vector(hit2d).length - Vector(self.hit2d).length
                size *= 0.25
                if context.scene.mouse_mode == "Uniform":
                    context.active_object.dimensions = (size, size, size)
                else:
                    context.active_object.dimensions = (size * self.scale[0], 
                                                        size * self.scale[1],
                                                        size * self.scale[2])
                #self.hit2d = hit2d
            return {'RUNNING_MODAL'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            context.area.header_text_set()
            context.scene.mouse_status = "Start mouse based fracture"
            #delete group and group objects if desired
            if context.scene.delete_helpers:
                for o in self.gr.objects:
                    self.gr.objects.unlink(o)
                    context.scene.objects.unlink(o)
                    o.user_clear()
                    bpy.data.objects.remove(o)
                bpy.data.groups.remove(self.gr, do_unlink=True)
                
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        
        if context.active_object is None:
             self.report({'WARNING'}, "Need an Active object with Fracture Modifier!")
             return {'CANCELLED'}
            
        if context.space_data.type == 'VIEW_3D':
            self.md = None
            for md in context.active_object.modifiers:
                if md.type == 'FRACTURE':
                    self.md = md
                    break
            if self.md is not None:
                if bpy.data.groups.get("InteractiveHelpers", None) is None:
                    self.gr = bpy.data.groups.new("InteractiveHelpers")
                else:
                    self.gr = bpy.data.groups["InteractiveHelpers"]
                self.act = context.active_object
                self.md.extra_group = self.gr
                self.md.refresh = False
                if context.scene.mouse_mode == "Uniform":
                    self.md.point_source = md.point_source.union({'EXTRA_PARTICLES'})
                    self.md.use_particle_birth_coordinates = True
                else:
                    self.md.point_source = md.point_source.union({'EXTRA_VERTS'})
                
                context.area.header_text_set(text=self.msg)
                context.scene.mouse_status = "Mouse based fracture running"
                context.object.show_wire = True
                context.scene.layers[15] = True
                context.scene.layers[0] = True
                context.window_manager.modal_handler_add(self)
            else:
                self.report({'WARNING'}, "Active object must have a Fracture Modifier")
                return {'CANCELLED'}
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}

def main(context, start=1, random=0.0, snap=True):
   context.scene.layers[19] = True
   act = context.active_object
   act.select = False
   gr = None
   
   for ob in bpy.data.objects:
       try:
           ob["isCurve"] = 0
       except KeyError:
           pass

   for md in act.modifiers:
       if md.type == 'FRACTURE':
          gr = md.extra_group
          act.show_wire = True
          break
   for ob in context.selected_objects:
       if ob != act:
            ob["isCurve"] = (ob.type == 'CURVE')
            if (gr is not None) and ob.name in gr.objects:
                #already in existing group, skip  
                ob.select = False

   if (snap == True):            
       bpy.ops.view3d.snap_cursor_to_selected()
   else:
       bpy.ops.view3d.snap_cursor_to_active()
              
   bpy.ops.object.duplicate()
   bpy.ops.anim.keyframe_clear_v3d()   
   bpy.ops.rigidbody.objects_remove()
   
   for ob in context.selected_objects:
       if ob != act:
            context.scene.objects.active = ob
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
            ob.draw_type = 'BOUNDS'
            ob.hide_render = True
            ob.show_name = True
            ob.show_x_ray = True
            ob.name = ob.name.split(".")[0] + "_helper"
            ob.layers[19] = True
            for x in range(0, 19):
                ob.layers[x] = False

   bpy.ops.object.convert(target='MESH', keep_original=False)
   
   if gr is None:
       gr = bpy.data.groups.new("Helper")
       
   if (context.scene.rigidbody_world):
        context.scene.frame_set(context.scene.rigidbody_world.point_cache.frame_start)
   else:
        context.scene.frame_set(1.0)
          
   for ob in context.selected_objects:
       if ob != act:
            print(ob, act)
            context.scene.objects.active = ob
            gr.objects.link(ob)
            
            ob.matrix_world = act.matrix_world.inverted() * ob.matrix_world
            ob.parent = act
            
            if (snap == True and not ob["isCurve"]):
                bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
                bpy.ops.view3d.snap_selected_to_cursor(use_offset=True)
            
            if (ob["isCurve"]):
                #psys.emit_from = 'VERT'
                ob.modifiers.new(type='SKIN', name='SkinHelper')
            
            if (snap == False):
                #called from physical rough edges...
                #add solidify on inner face helper
                mod = ob.modifiers.new(type='SOLIDIFY', name='SolidifyHelper')
                mod.thickness = 0.25

            ob.modifiers.new(type='PARTICLE_SYSTEM', name='ParticleHelper')
            #make particle system settings here....
            psys = ob.particle_systems[0].settings
            psys.count = 500
            psys.frame_start = start
            psys.frame_end = 1
            psys.lifetime = 1
            psys.factor_random = 1.5
            psys.normal_factor = 0.0
            psys.effector_weights.gravity = 0.0
            psys.draw_method = 'NONE'
            psys.use_render_emitter = False
            psys.render_type = 'NONE'
            psys.use_modifier_stack = True
            psys.physics_type = 'NO'
                
            #if (ob["isCurve"]):
            #    psys.emit_from = 'VERT'
            #else:
            psys.emit_from = 'VOLUME'
            psys.distribution = 'RAND'
                
            ob.select = False
            
   context.scene.objects.active = act
   for md in act.modifiers:
       if md.type == 'FRACTURE':
           md.extra_group = gr
           md.refresh = False
           md.point_source = md.point_source.union({'EXTRA_PARTICLES'})
           md.use_particle_birth_coordinates = False
           break

   act.select = True
   bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
   act.select = False
   
   bpy.ops.object.fracture_refresh(reset=True)
   
   act = context.scene.objects.active
   use_curve = context.scene.use_animation_curve
   anim_ob = context.scene.animation_obj
   if (use_curve == True and anim_ob != ""):
       anim_ob = bpy.data.objects[anim_ob] 
       for ob in bpy.data.objects:
            try:
                if ((ob["isCurve"] == 1) and (ob.type == 'CURVE')):
                    print("FOUND CURVE", ob)
                    ob.select = True
                    context.scene.objects.active = ob
                    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
                    ob["isCurve"] = 0
                else:
                    ob.select = False
                    ob["isCurve"] = 0
            except KeyError:
                ob.select = False
                
       anim_ob.select = True
       bpy.ops.object.parent_set(type='PATH_CONST')
       context.scene.objects.active.select = False
       context.scene.objects.active = anim_ob
       bpy.ops.rigidbody.objects_add(type='ACTIVE')
       anim_ob.rigid_body.kinematic = True
       anim_ob.rigid_body.is_ghost = context.scene.animation_ghost
       anim_ob.rigid_body.is_trigger = True
       anim_ob.rigid_body.use_margin = True
       anim_ob.rigid_body.collision_margin = 0.0
       bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
       
       bpy.ops.object.location_clear()
       ctx = context.copy()
       ctx["constraint"] = anim_ob.constraints["AutoPath"]
       anim_ob.constraints["AutoPath"].use_curve_follow = True
       anim_ob.constraints["AutoPath"].forward_axis = 'FORWARD_X'
       bpy.ops.constraint.followpath_path_animate(ctx, constraint="AutoPath")
       
       context.scene.objects.active = act
       act.rigid_body.enabled = True
       act.rigid_body.kinematic = True
       act.rigid_body.use_kinematic_deactivation = True
   
   context.scene.animation_obj = ''
   context.scene.use_animation_curve = False
   context.scene.animation_ghost = False
   context.scene.update()
   
class FractureHelper(bpy.types.Operator):
    """Create helper object using an other object"""
    bl_idname = "fracture.create_helper"
    bl_label = "Generate smaller shards"
    start = bpy.props.IntProperty(name="start", default = 1)
    random = bpy.props.FloatProperty(name="random", default = 0.0)
    snap = bpy.props.BoolProperty(name="snap", default = True)

    def execute(self, context):
        act = context.active_object is not None
        mod = False
        isNoCurve = True
        isSingle = True
        
        for md in context.active_object.modifiers:
            if md.type == 'FRACTURE':
                mod = True
                break
            
        sel = len(context.selected_objects) > 1
        for ob in context.selected_objects:
            if ob.type == 'CURVE':
                if (isNoCurve == False):
                    isSingle = False
                    break
                isNoCurve = False
        
        if not(act and sel and mod):
            self.report({'WARNING'}, "Need an active object with fracture modifier and atleast another selected object") 
            return {'CANCELLED'}
            
        if (not(isSingle) or isNoCurve) and (context.scene.use_animation_curve == True) and (context.scene.animation_obj == ""):
            self.report({'WARNING'}, "For animation curve please select only one curve and specify an animation object") 
            return {'CANCELLED'}
    
        main(context, self.start, self.random, self.snap)
        return {'FINISHED'}
    #### Useful: The created HelperObject has to be parented to the Baseobject 
    ####           so its moved with it when translating / rotating    
    

class FracturePathPanel(bpy.types.Panel):
    bl_label = "Automations"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Fracture"
    bl_options = {'DEFAULT_CLOSED'}
  
    
    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        row = layout.row(align=True)
        
        col.label("Path animation:", icon='PINNED')
        col.prop_search(context.scene, "animation_obj", bpy.data, "objects", text="Object", icon='OBJECT_DATA')
        col.separator()
        col.prop(context.scene, "use_animation_curve", text="Use As Animation Path", icon = 'ANIM')
        col.prop(context.scene, "animation_ghost", text="Toggle RB Ghost", icon='GHOST_ENABLED')
        op = col.operator("fracture.create_helper", icon='MOD_PARTICLES')
        op.start = 0
        op.random = 15.0
        
        col.separator()
        col.separator()
        col.separator()
        
        col.label("Combination:", icon='PINNED')
        col.operator("fracture.combine_subobjects",icon='GROUP')


### from now much stuff is put into a common panel,  its better than having separate panels for everything

class FractureHelperPanel(bpy.types.Panel):
    bl_label = "Generate smaller shards"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Fracture"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        row = layout.row(align=True)
                    
        #Other objects as helpers:
        col.label(text="Smaller shards using other object:", icon='PINNED')
        #col.operator("object.fracture_helper", icon='MOD_PARTICLES')
        #col.prop(context.object, "particle_amount", text="Particle amount")
        #col.prop(context.object, "particle_random", text="Particle random")
        systems = len(context.object.particle_systems)
        col.operator("fracture.create_helper", icon='MOD_PARTICLES')
        if systems > 0:
            if systems > 1:
                col.label(text="Only the first particle system is used as helper particle system")
            psys = context.object.particle_systems[0]
            col.prop(psys.settings, "count", text="Particle amount")
            col.prop(psys.settings, "factor_random", text="Particle random")
            
        else:
            col.label(text="Click Generate Smaller shards to make this object a helper")
    
        col.separator()
        col.separator()
        col.separator()
        
        #Mouse based helpers:
        col.label(text="Smaller shards using mouse:", icon='PINNED')
        row = col.row(align=True)
        row.prop(context.scene, "mouse_mode", text="Fracture Mode", expand=True)
        if context.scene.mouse_mode == "Uniform":
            row = col.row(align=True)
            row.prop(context.scene, "mouse_object", text="Helper Object", expand=True)
            if (context.scene.mouse_object == "Custom"):
                col.prop_search(context.scene, "mouse_custom_object", bpy.data, "objects", text="")
            col.prop(context.scene, "mouse_count", text="Shard count")
        else:
            row = col.row(align=True)
            row.prop(context.scene, "mouse_segments", text="Segments")
            row.prop(context.scene, "mouse_rings", text="Rings")
            
        col.prop(context.scene, "delete_helpers", text="Delete helpers afterwards", icon='X')
        col.operator("fracture.mouse_based_fracture", text=context.scene.mouse_status, icon='RESTRICT_SELECT_OFF')
        col.separator()
        col.separator()
        col.separator()
        
        #Extract inner faces for rough edges (cluster)
        col.label(text="Rough edges:", icon='PINNED')
        col.operator("fracture.create_cluster_helpers", icon='FCURVE')
        col.operator("fracture.create_displaced_edges", icon='FCURVE')
            
            
            
class TimingPanel(bpy.types.Panel):
    bl_label = "Timing"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Fracture"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        row = layout.row(align=True)
        
        #Time control:
        col.label(text="Delayed fracture:", icon='PINNED')
        col.prop(context.scene, "is_dynamic", text="Object moves", icon='FORCE_HARMONIC')
        col.prop(context.scene, "fracture_frame", text="Start fracture from frame")
        col.operator("fracture.frame_set", icon='PREVIEW_RANGE')
        
        layout.prop(context.scene, "time_scale", text="Time Scale")
        
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("fracture.set_timescale")
        row.operator("fracture.clear_timescale")
        row = col.row(align=True)
        row.operator("fracture.clear_all_timescale")
        row.operator("fracture.apply_timescale")

#def update_wire(self, context):
#    context.object.show_wire = context.object.use_wire

#def update_relationships(self, context):
#    for area in context.screen.areas:
#        if area.type == 'VIEW_3D':
#            for space in area.spaces:
#                if space.type == 'VIEW_3D':
#                    space.show_relationship_lines = context.object.use_relationship_lines
#                    break

#def update_visible_particles(self, context):
#    if len(context.object.particle_systems) > 0:
#        if context.object.use_visible_particles:
#            context.object.particle_systems[0].settings.draw_method = 'DOT'
#        else:
#            context.object.particle_systems[0].settings.draw_method = 'NONE'
            
#def update_autoexecute(self, context):
#    context.object.modifiers["Fracture"].auto_execute = context.object.use_autoexecute

#def update_particle_amount(self, context):
#    if len(context.object.particle_systems) > 0:
#       context.object.particle_systems[0].settings.count = context.object.particle_amount

#def update_particle_random(self, context):
#    if len(context.object.particle_systems) > 0:
#       context.object.particle_systems[0].settings.factor_random = context.object.particle_random


class FractureFrameOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "fracture.frame_set"
    bl_label = "Set start frame"
    
    def execute(self, context):
        if context.object is not None:
            mod = False
            for md in context.object.modifiers:
                if md.type == 'FRACTURE':
                    mod = True
                    break
        
            if not(mod):
                self.report({'WARNING'}, "Need an active object with fracture modifier!") 
                return {'CANCELLED'}
                
            #if FractureMod, then save preset (FrameHelperPreset) and remove mod
            ctx = context.copy()
            ctx["fracture"] = md
            bpy.ops.fracture.preset_add(ctx, name="helperpreset")
            
            #determine old stack position (for re-insert there)
            pos = 0
            for modi in context.object.modifiers:
                if modi != md:
                    pos += 1
                else:
                    break
            
            context.object.modifiers.remove(md)
            frame_end = context.scene.fracture_frame
            
            context.object.select = True
            #bpy.ops.anim.keyframe_clear_v3d()
            
            try:
                ob = context.object
                delete_keyframes(context, ob, "location", 3)
                delete_keyframes(context, ob, "rotation_euler", 3)
                delete_keyframes(context, ob, "scale", 3)
                delete_keyframes(context, ob, "rigid_body.kinematic")
            except RuntimeError: # silent fail in case of no animation is present
                pass
            
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            
            context.object.rigid_body.kinematic = False
            if (context.scene.is_dynamic):
                bpy.ops.rigidbody.bake_to_keyframes('EXEC_DEFAULT', frame_start=1, frame_end=frame_end, step=1)
                          
            context.scene.frame_set(1)
           
            bpy.ops.rigidbody.objects_add(type='ACTIVE')
            #context.object.select = False
                 
            context.object.rigid_body.kinematic = True
            context.object.keyframe_insert(data_path="rigid_body.kinematic")
            
            
            context.scene.frame_set(frame_end)
            context.object.rigid_body.kinematic = False
            context.object.keyframe_insert(data_path="rigid_body.kinematic")
            
            context.scene.frame_set(1)
            
            #re-add fracture modifier
            bpy.ops.object.modifier_add(type='FRACTURE')
            #paths = bpy.utils.preset_paths("fracture")
            filepath = bpy.utils.preset_find("helperpreset", "fracture")
            for md in context.object.modifiers:
                if md.type == 'FRACTURE':
                    break
            ctx = context.copy()
            ctx["fracture"] = md
            bpy.ops.script.execute_preset(ctx, filepath=filepath, menu_idname="FRACTURE_MT_presets")
            bpy.context.object.modifiers["Fracture"].uv_layer = "InnerUV"
            #bpy.ops.object.fracture_refresh()
            
            #Move FM to position in modifier stack
            bpy.ops.fracture.move_fmtotop(pos=pos)
            bpy.ops.object.fracture_refresh(reset=True)
            
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Need an active object with fracture modifier!") 
            return {'CANCELLED'}
            
class ClusterHelperOperator(bpy.types.Operator):
    """Extracts the inner faces and uses this new mesh to generate smaller shards. These will be glued used clustergroups"""
    bl_idname = "fracture.create_cluster_helpers"
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
        bpy.ops.fracture.create_helper(start=0, random=15.0, snap=False)
        
        lastact.matrix_world = oldact.matrix_world.inverted() * lastact.matrix_world.copy()
        lastact.parent = oldact

        return {'FINISHED'}

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

### Rough edges using displacement modifier:
class DisplacementEdgesOperator(bpy.types.Operator):
    """Setups the modifier stack for simulated (not real) rough edges"""
    bl_idname = "fracture.create_displaced_edges"
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

class CombineSubObjectsOperator(bpy.types.Operator):
    """Combine multiple Fractured objects into one object"""
    bl_idname = "fracture.combine_subobjects"
    bl_label = "Combine Sub Objects"
    
    def execute(self, context):
        #prepare objects
        context.scene.layers[17] = True
        gr = bpy.data.groups.new("CombinationGroup")
        for ob in context.selected_objects:

             gr.objects.link(ob)
             context.scene.objects.active = ob
             for md in ob.modifiers:
                if (md.type == 'FRACTURE'):
                   bpy.ops.object.fracture_refresh(reset=True)
                   
                   #stop simulation and interaction
                   ob.rigid_body.kinematic = True
                   ob.rigid_body.is_ghost = True
                   break
                elif ob.rigid_body != None:
                   #stop simulation and interaction (regular rigidbodies)
                   ob.rigid_body.kinematic = True
                   ob.rigid_body.is_ghost = True
                   
             ob.layers[17] = True
             for x in range(0, 19):
                if x != 17:
                    ob.layers[x] = False
        
        #context.scene.update()
        context.scene.layers[17] = False
        
        if len(gr.objects) == 0:
            self.report({'WARNING'}, "Found no selected object with a fracture modifier") 
            return {'CANCELLED'}
                 
        #create carrier object at 0, 0, 0 -> transformations are taken into account
        bpy.ops.mesh.primitive_cube_add()
        active = context.active_object
        active.layers[0] = True
        active.layers[17] = False
        
        bpy.ops.object.modifier_add(type='FRACTURE')
        md = active.modifiers[0]
        md.point_source = set()
        md.dm_group = gr
        bpy.ops.object.fracture_refresh(reset=True)
        
        return {'FINISHED'}

#### ADD HERE NEW DEFINITIONS FOR INNER VERTEX (?????)
def find_modifier(ob, typ):
    for md in ob.modifiers:
        if md.type == typ:
            return md
    return None

def make_canvas(ob, start, end, fade):
    dp = find_modifier(ob, 'DYNAMIC_PAINT')
    if dp is None:
        dp = ob.modifiers.new(name="dp_canvas_FM", type='DYNAMIC_PAINT')
        dp.ui_type = 'CANVAS'
    if dp.canvas_settings is None:
        ctx = bpy.context.copy()
        ctx['object'] = ob
        bpy.ops.dpaint.type_toggle(ctx, type='CANVAS')
    
    canvas = dp.canvas_settings.canvas_surfaces[0]
    canvas.name = "dp_canvas_FM"
    canvas.use_antialiasing = True
    canvas.frame_start = 1 #start  else dp cache doesnt work properly
    canvas.frame_end = end
    canvas.surface_type = 'WEIGHT'
    canvas.use_dissolve = True
    canvas.dissolve_speed = fade
    canvas.use_dissolve_log = True
    
    vertgroup = None
    for vg in ob.vertex_groups:
        if vg.name == "dp_weight_FM":
            vertgroup = vg
                    
    if vertgroup is None:
        vertgroup = ob.vertex_groups.new(name="dp_weight_FM")
    
    canvas.output_name_a = vertgroup.name
    
    return vertgroup.name

class SmokeSetupOperator(bpy.types.Operator):
    """Setup smoke from dynamic paint"""
    bl_idname = "fracture.setup_smoke"
    bl_label = "Inner Smoke"
    
    def execute(self, context):
        allobs = bpy.data.objects
        flows = [] #context.selected_objects
        #flows.append(context.active_object)
        fr = context.scene.frame_current
        fmOb = None
        psys_name = "SMOKE_PSystem"

        
        #check whether smoke is already set up, if yes.. only set keyframes
        #check for selected objects...
        for ob in context.selected_objects:
            md = find_modifier(ob, 'SMOKE')
            if md is None or (md is not None and md.smoke_type not in {'FLOW', 'DOMAIN'}):
                flows.append(ob)
            #elif md.smoke_type == 'FLOW':
                #set_smoke_keyframes(self, context, ob, fr)
                
        
        #and for active object (not really sure whether this step here is necessary,
        #shouldnt active ob be in selected objs too ?        
        #if context.active_object is not None:        
        #    md = find_modifier(context.active_object, 'SMOKE')
        #    if md is None or (md is not None and md.smoke_type not in {'FLOW', 'DOMAIN'}):
        #        flows.append(context.active_object)
            #elif md.smoke_type == 'FLOW':
                #set_smoke_keyframes(self, context, context.active_object, fr)
        
        if len(flows) == 0:
            return {'FINISHED'}    
        
        #setup inner uv and FM, if not present - also remove Smoke_Collision
        for ob in flows:
            was_none = False
            partsys = None
                      
            bpy.ops.object.modifier_remove(modifier="Smoke_Collision")
            
            md = find_modifier(ob, 'FRACTURE')
            if md is None:
                was_none = True
                md = ob.modifiers.new(name="Fracture", type='FRACTURE')
                
            vg = make_canvas(ob, context.scene.emit_start, context.scene.emit_end, 75)
            
            # test whether ParticleSystem "ParticleDEBRIS" already exists.
            for psystem in ob.particle_systems:
                if psystem.name == psys_name:
                    partsys = psystem
                    break
                    # if yes,synchronize startframes (start/end)
                    # partsys.settings.frame_start = context.object.smokedebrisdust_emission_start
                    # partsys.settings.frame_end = context.object.smokedebrisdust_emission_start + 10
          #          partsys.settings.frame_start = context.scene.frame_current
        #            partsys.settings.frame_end = context.scene.frame_current + 10
            
            print(partsys, len(ob.particle_systems))        
            if partsys is None:
                # if no
                # operator mostly works on active object, so set current object as active
                # and restore the old active object afterwards
                context.scene.objects.active = ob
                bpy.ops.object.particle_system_add()
                bpy.context.object.modifiers[-1].name = "Smoke_ParticleSystem"

                #find last added particle system
                #particlesystems = [md for md in context.object.modifiers if md.type == "PARTICLE_SYSTEM"]
                psys = ob.particle_systems[-1]
                
                #make particle system settings here....
                #pdata = bpy.data.particles[-1]
                pdata = psys.settings
                psys.name = psys_name;
                pdata.name = "SMOKE_Settings"
                pdata.count = 25000
                
                #pdata.frame_start = context.object.smokedebrisdust_emission_start
                #pdata.frame_end = context.object.smokedebrisdust_emission_start + 10
                pdata.frame_start = context.scene.frame_current
                pdata.frame_end = context.scene.frame_current + 25
                pdata.lifetime = 5
                pdata.factor_random = 0
                pdata.normal_factor = 0
                pdata.tangent_phase = 0.1
                pdata.use_rotations = True
                pdata.rotation_factor_random = 0
                pdata.phase_factor_random = 0
                pdata.angular_velocity_mode = 'VELOCITY'
                pdata.angular_velocity_factor = 0
                pdata.use_dynamic_rotation = True
                pdata.particle_size = 0.2
                pdata.size_random = 0.5
                pdata.use_multiply_size_mass = True
                pdata.effector_weights.gravity = 1.0
                pdata.effector_weights.smokeflow = 0
                pdata.draw_method = 'RENDER'
                pdata.use_render_emitter = True
                pdata.use_modifier_stack = True
                psys.vertex_group_density = vg
                partsys = psys
       
            #only do necessary setup here
            context.scene.objects.active = ob
            #bpy.ops.object.fracture_refresh(reset=True)    
            
            #context.scene.objects.active = ob
            #bpy.ops.object.fracture_refresh(reset=True)
            fmOb = ob
        
        #setup quick smoke
        bpy.ops.object.quick_smoke()
        
        #setup a blend texture (works best with inner smoke)
        #tex = bpy.data.textures.new("SmokeTex", 'BLEND')
        
        #flow settings
        for ob in flows:
            md = find_modifier(ob, 'SMOKE')
            if md.smoke_type == 'FLOW':
                flow = md.flow_settings
                flow.smoke_flow_source = 'PARTICLES'
                flow.particle_system = partsys
                flow.particle_size = 0.3
                flow.surface_distance = 0.20
                flow.density = 0.63
                flow.subframes = 2
                flow.use_initial_velocity = False
                flow.velocity_factor = 1
                flow.velocity_normal = 1
                ob.draw_type = 'TEXTURED'
                
                #first two materials (should be regular and inner one)
                if context.scene.render.engine == 'BLENDER_RENDER':
                    if len(ob.material_slots) > 0:
                        outer = ob.material_slots[0].material
                        outer.use_transparent_shadows = True
                    if len(ob.material_slots) > 1:
                        inner = ob.material_slots[1].material
                        inner.use_transparent_shadows = True
                    
        #domain settings
        domainOb = context.active_object
        domainOb.layers[0] = True
        md = find_modifier(domainOb, 'SMOKE')
        if md.smoke_type == 'DOMAIN':
            domain = md.domain_settings
            domain.alpha = 0.01
            domain.beta = -0.25
            domain.vorticity = 2.5
            domain.use_dissolve_smoke = True
            domain.dissolve_speed = 60
            domain.use_dissolve_smoke_log = True
            domain.use_adaptive_domain = True
            domain.use_high_resolution = True
            domain.amplify = 1
            
            world = context.scene.rigidbody_world
            if world is None:
               bpy.ops.rigidbody.world_add()
               world = context.scene.rigidbody_world
                
            domain.point_cache.frame_start = world.point_cache.frame_start
            domain.point_cache.frame_end = world.point_cache.frame_end
        
        #domain render / material settings (BI)
        mat = domainOb.material_slots[0].material
        
        if context.scene.render.engine == 'BLENDER_RENDER':
            volume = mat.volume
            volume.density_scale = 3
            volume.use_light_cache = True
            volume.cache_resolution = 50
            volume.step_size = 0.03
        
        #make all Scene objects to Colliders (Smoke/Particle) (incl FM TO TOP OPERATOR)
        #bpy.ops.object.setup_collision() 
        
        #move FractureModifier to first Position (why ?)
        #bpy.ops.fracture.move_fmtotop()  
        
        #jump to Frame 1 
        bpy.context.scene.frame_current = 1
        
        #do refracture
        #if fmOb is not None:
        #    context.scene.objects.active = fmOb
        #    bpy.ops.object.fracture_refresh(reset=True)
        
        return {'FINISHED'}

class DustSetupOperator(bpy.types.Operator):
    """Setup dust from dynamic paint"""
    bl_idname = "fracture.setup_dust"
    bl_label = "Dust"
    
    def make_dust_objects_group(self, context, ob):
        actname = bpy.context.scene.objects.active.name
        dust_count = 1
        loc = ob.location.copy()
        x = 0.0
        gr = bpy.data.groups.new(actname + "_DustObjects")
        
        context.scene.layers[17] = True
        bpy.ops.object.empty_add(type='CIRCLE', view_align=False, location=loc.to_tuple())
        bpy.context.scene.objects.active.name = actname + "_DustObjects"
        bpy.context.object.show_name = True
        bpy.context.object.show_x_ray = True
        par = bpy.context.active_object
        
        for i in range(dust_count):
            #random size (0 bis 1) and 
            #translation by double size to X direction (to let it look good)
            size = random.random() * 0.5 + 0.5
            x += 1.5 * size
            context.scene.layers[17] = True
            bpy.ops.mesh.primitive_ico_sphere_add(size=size, location=(loc[0] + x, loc[1], loc[2]))
            
            #for ob in bpy.context.selected_objects:
            #    ob.name = actname + "_DebrisObject"
            context.active_object.name = actname + "_DustObject"
                
            #im objektmode in gruppe einfuegen  
            #bpy.ops.object.editmode_toggle()
            gr.objects.link(context.active_object)
            
            ob = context.active_object
            #adjust transformation and parent
            ob.matrix_world = par.matrix_world.inverted() * ob.matrix_world
            ob.parent = par
            #bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)
                        
            #switch layer
            context.scene.layers[0] = True
            #context.scene.layers[17] = False
            
        return gr
    
    def execute(self, context):
        selected = context.selected_objects
        allobs = bpy.data.objects
        #selected.append(context.active_object)
        act = context.active_object
        psys_name = "DUST_PSystem"
        fmOb = None
  
          
        if bpy.data.objects.get("Smoke Domain") is None:
          self.report({'WARNING'}, "Dust needs a smoke domain with the name 'Smoke Domain' !") 
          return {'CANCELLED'}
  
        #setup inner vertex group and FM, if not present
        for ob in selected:
            
            was_none = False
            vertgroup = None
            partsys = None
            gr = None
            
            md = find_modifier(ob, 'FRACTURE')
            if md is None:
                was_none = True
                md = ob.modifiers.new(name="Fracture", type='FRACTURE')

            fmOb = ob
            
            #create DP canvas here
            vg = make_canvas(ob, context.scene.emit_start, context.scene.emit_end, 75)
            
            # test whether ParticleSystem "ParticleDUST" already exists.
            for psystem in ob.particle_systems:
                if psystem.name == psys_name:
                    partsys = psystem
                    break
                    # if yes,synchronize startframes (start/end)
                    # partsys.settings.frame_start = context.object.smokedebrisdust_emission_start
                    # partsys.settings.frame_end = context.object.smokedebrisdust_emission_start + 10
                    #partsys.settings.frame_start = context.scene.frame_current
                    #partsys.settings.frame_end = context.scene.frame_current + 10
            
            print(partsys, len(ob.particle_systems))        
            if partsys is None:
                # if no
                # operator mostly works on active object, so set current object as active
                # and restore the old active object afterwards
                context.scene.objects.active = ob
                bpy.ops.object.particle_system_add()
                bpy.context.object.modifiers[-1].name = "Dust_ParticleSystem"
                
                gr = self.make_dust_objects_group(context, ob)

                #find last added particlesystem
                #particlesystems = [md for md in context.object.modifiers if md.type == "PARTICLE_SYSTEM"]
                psys = ob.particle_systems[-1]
                
                #make particle system settings here....
                #pdata = bpy.data.particles[-1]
                pdata = psys.settings
                psys.name = psys_name;
                pdata.name = "DUST_Settings"
                pdata.count = 2500
                
                #pdata.frame_start = context.object.smokedebrisdust_emission_start
                #pdata.frame_end = context.object.smokedebrisdust_emission_start + 10
                pdata.frame_start = context.scene.frame_current
                pdata.frame_end = context.scene.frame_current + 25
                pdata.lifetime = 75
                pdata.lifetime_random = 0.60
                pdata.factor_random = 0.85
                pdata.normal_factor = 0
                pdata.tangent_phase = 0.5
                pdata.subframes = 5
                pdata.use_rotations = False
                pdata.rotation_factor_random = 0.1
                pdata.phase_factor_random = 0.1
                pdata.angular_velocity_mode = 'VELOCITY'
                pdata.angular_velocity_factor = 1
                pdata.use_dynamic_rotation = True
                pdata.particle_size = 0.008
                pdata.size_random = 0.6
                pdata.brownian_factor = 3
                pdata.use_multiply_size_mass = False
                pdata.effector_weights.gravity = 1.0
                pdata.draw_method = 'RENDER'
                pdata.use_render_emitter = True
                pdata.render_type = 'GROUP'
                pdata.use_group_pick_random = True
                pdata.dupli_group = gr
                pdata.use_modifier_stack = True
                pdata.effector_weights.gravity = 0
                psys.vertex_group_density = vg
       
            #only do necessary setup here
           # md.autohide_dist = 0.0001
            context.scene.objects.active = ob
            #bpy.ops.object.fracture_refresh(reset=True)
            
            #now there definitely is an inner material,  set it on all Objects
            #in the debris group
            tmp_act = ob 
            if gr is not None:
                for obj in gr.objects:
                    context.scene.objects.active = obj
                    bpy.ops.object.material_slot_add()
                    obj.material_slots[0].material = md.inner_material
                context.scene.objects.active = tmp_act
                    
            
            #add Collision to current Object
            #ob.modifiers.new(name="Dust_Collision", type='COLLISION')
            #ob.collision.damping_factor = 0.7
            #ob.collision.friction_factor = 0.5
            #ob.collision.friction_random = 0.5
        
        #Domain with Force Field "Smoke Flow"
        bpy.context.scene.objects.active = bpy.data.objects["Smoke Domain"]
        bpy.ops.object.forcefield_toggle()
        bpy.context.object.field.type = 'SMOKE_FLOW'
        bpy.context.object.field.shape = 'SURFACE'
        bpy.context.object.field.source_object = bpy.data.objects["Smoke Domain"]
        bpy.context.object.field.strength = 0.75
        bpy.context.object.field.flow = 0.1
               
        #restore active object
        context.scene.objects.active = act
        
        #set RB Field Weights for "Smoke Flow" to 0 
        bpy.context.scene.rigidbody_world.effector_weights.smokeflow = 0

        #make all scene objects colliders (Smoke/Particle) (incl FM TO TOP OPERATOR)
        #bpy.ops.object.setup_collision()  
        
        #move FM to first position (why ?, new modifiers if any... will be put after it anyway)
        #bpy.ops.fracture.move_fmtotop()  
        
        context.scene.frame_current = 1
        
        #do refracture
        #if fmOb is not None:
        #    context.scene.objects.active = fmOb
        #    bpy.ops.object.fracture_refresh(reset=True)
        
        return {'FINISHED'} 

class DebrisSetupOperator(bpy.types.Operator):
    """Setup debris from dynamic paint"""
    bl_idname = "fracture.setup_debris"
    bl_label = "Debris"
    
    def make_debris_objects_group(self, context, ob):
        actname = bpy.context.scene.objects.active.name
        debris_count = 3
        loc = ob.location.copy()
        x = 0.0
        gr = bpy.data.groups.new(actname + "_DebrisObjects")
        
        context.scene.layers[17] = True
        bpy.ops.object.empty_add(type='CIRCLE', view_align=False, location=loc.to_tuple())
        bpy.context.scene.objects.active.name = actname + "_DebrisObjects"
        bpy.context.object.show_name = True
        bpy.context.object.show_x_ray = True
        par = bpy.context.active_object
        
        for i in range(debris_count):
            #random size (0 to 1) and 
            #translation by double size in X direction (only for the "Optics", let it look "good")
            size = random.random() * 0.5 + 0.5
            x += 3 * size
            context.scene.layers[17] = True
            bpy.ops.mesh.primitive_ico_sphere_add(size=size, location=(loc[0] + x, loc[1], loc[2]), subdivisions=1)
            
            #for ob in bpy.context.selected_objects:
            #    ob.name = actname + "_DebrisObject"
            context.active_object.name = actname + "_DebrisObject"
                
            #subdivide fractally in editmode (2x) -> looks (usually) better than 1x with 2 cuts
            bpy.ops.object.editmode_toggle()
            bpy.ops.mesh.subdivide(number_cuts=1, fractal=size*2.5, seed=random.randint(0,10))
            bpy.ops.mesh.subdivide(number_cuts=1, fractal=size*2.5, seed=random.randint(0,10))    
            #add in objectmode to group 
            bpy.ops.object.editmode_toggle()
            gr.objects.link(context.active_object)
            
            ob = context.active_object
            #adjust transformation and parent
            ob.matrix_world = par.matrix_world.inverted() * ob.matrix_world
            ob.parent = par
            #bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)
                        
            #switch Layer
            context.scene.layers[0] = True
            #context.scene.layers[17] = False
            
        return gr
    
    def execute(self, context):
        selected = context.selected_objects
        allobs = bpy.data.objects
        #selected.append(context.active_object)
        act = context.active_object
        psys_name = "DEBRIS_PSystem"
        fmOb = None
  
        #setup inner vertex group and FM, if not present
        for ob in selected:
            
            was_none = False
            vertgroup = None
            partsys = None
            gr = None
            
            md = find_modifier(ob, 'FRACTURE')
            if md is None:
                was_none = True
                md = ob.modifiers.new(name="Fracture", type='FRACTURE')

            fmOb = ob
            vg = make_canvas(ob, context.scene.emit_start, context.scene.emit_end, 75)     

            # test whether ParticleSystem "ParticleDEBRIS" already exists.
            for psystem in ob.particle_systems:
                if psystem.name == psys_name:
                    partsys = psystem
                    break
                    # if yes,synchronize startframes (start/end)
                    # partsys.settings.frame_start = context.object.smokedebrisdust_emission_start
                    # partsys.settings.frame_end = context.object.smokedebrisdust_emission_start + 10
                    #partsys.settings.frame_start = context.scene.frame_current
                    #partsys.settings.frame_end = context.scene.frame_current + 10
            
            print(partsys, len(ob.particle_systems))        
            if partsys is None:
                # if no
                # operator mostly works on active object, so set current object as active
                # and restore the old active object afterwards
                context.scene.objects.active = ob
                bpy.ops.object.particle_system_add()
                bpy.context.object.modifiers[-1].name = "Debris_ParticleSystem"
                
                gr = self.make_debris_objects_group(context, ob)

                #find last added particle system
                #particlesystems = [md for md in context.object.modifiers if md.type == "PARTICLE_SYSTEM"]
                psys = ob.particle_systems[-1]
                
                #make particle system settings here....
                #pdata = bpy.data.particles[-1]
                pdata = psys.settings
                psys.name = psys_name;
                pdata.name = "DEBRIS_Settings"
                pdata.count = 1000
                
                #pdata.frame_start = context.object.smokedebrisdust_emission_start
                #pdata.frame_end = context.object.smokedebrisdust_emission_start + 10
                pdata.frame_start = context.scene.frame_current
                pdata.frame_end = context.scene.frame_current + 25
                pdata.lifetime = context.scene.frame_end
                pdata.factor_random = 1
                pdata.normal_factor = 0
                pdata.tangent_phase = 0.1
                pdata.use_rotations = True
                pdata.rotation_factor_random = 0.5
                pdata.phase_factor_random = 0.5
                pdata.angular_velocity_mode = 'VELOCITY'
                pdata.angular_velocity_factor = 1
                pdata.use_dynamic_rotation = True
                pdata.particle_size = 0.135
                pdata.size_random = 0.81
                pdata.use_multiply_size_mass = True
                pdata.effector_weights.gravity = 1.0
                pdata.effector_weights.smokeflow = 0
                pdata.draw_method = 'RENDER'
                pdata.use_render_emitter = True
                pdata.render_type = 'GROUP'
                pdata.use_group_pick_random = True
                pdata.dupli_group = gr
                pdata.use_modifier_stack = True
                psys.vertex_group_density = vg
       
            #only do necessary setup here
            #md.autohide_dist = 0.0001
            context.scene.objects.active = ob
            #bpy.ops.object.fracture_refresh(reset=True)
            
            #now there definitely is an inner material,  set it on all Objects
            #in the debris group
            tmp_act = ob 
            if gr is not None:
                for obj in gr.objects:
                    context.scene.objects.active = obj
                    bpy.ops.object.material_slot_add()
                    obj.material_slots[0].material = md.inner_material
                context.scene.objects.active = tmp_act
                    
            
            #add Collision to current Object
            #ob.modifiers.new(name="Debris_Collision", type='COLLISION')
            #ob.collision.damping_factor = 0.7
            #ob.collision.friction_factor = 0.5
            #ob.collision.friction_random = 0.5
        
        #restore active object
        context.scene.objects.active = act
        
        #make all scene objects colliders (Smoke/Particle) (incl FM TO TOP OPERATOR)
        #bpy.ops.object.setup_collision()  
        
        #move FM to first position (why ?)
       # bpy.ops.fracture.move_fmtotop()  
        
        context.scene.frame_current = 1
        
        #do refracture
        #if fmOb is not None:
        #    context.scene.objects.active = fmOb
        #    bpy.ops.object.fracture_refresh(reset=True)
        
        return {'FINISHED'} 
        
#move FM to first position
class MoveFMToTopOperator(bpy.types.Operator):
    """Moves the Fracture Modifier on top position in stack"""
    bl_idname = "fracture.move_fmtotop"
    bl_label = "Move FM to top of stack"
    
    pos = bpy.props.IntProperty(name="pos")
    
    def execute(self, context):
        md = find_modifier(context.object, 'FRACTURE')
        #unless modifier isnt the first, move up...
        while md != context.object.modifiers[self.pos] and md is not None:
            bpy.ops.object.modifier_move_up(modifier="Fracture")
        return {'FINISHED'}

def delete_keyframes(context, ob, path, index=1):
    if ob.animation_data and ob.animation_data.action:
        fc = ob.animation_data.action.fcurves
        for i in range(index):
            f = fc.find(data_path=path, index=i)
            if f:
                fc.remove(f) 
    
#def set_smoke_keyframes(self, context, ob, fr):
#    #starting from current frame
#    #Smoke Flow Source -> Keyframe on Surface: 0.14
#    #go back 3 Frames in timeline, Keyframe on Surface: 0.00
#    #go forward 13 Frames in timeline, Keyframe on Surface: 0.00
#    #ob = context.object
#    md = ob.modifiers["Smoke"]
#    #print(md)
#    if md.type == 'SMOKE' and md.smoke_type == 'FLOW':
#        # Warning, this deletes ALL keyframes on this object, no easy way to only delete all 
#        # keyframes on a specific property (without memorizing the frame numbers)
#        ob.select = True
#        #bpy.ops.anim.keyframe_clear_v3d()
#        try:
#            #why on earth do we need to jump to all keyframes in this case ?! transformation
#            #keyframes can be deleted in 1 go 
#            delete_keyframes(context, ob, "modifiers[\"Smoke\"].flow_settings.surface_distance")
#        except RuntimeError:
#            pass
#        
#        #fr = context.scene.frame_current
#        md.flow_settings.surface_distance = 0.1
#        ob.keyframe_insert(data_path="modifiers[\"Smoke\"].flow_settings.surface_distance")
#        
#        context.scene.frame_current -= 3
#        md.flow_settings.surface_distance = 0.0
#        ob.keyframe_insert(data_path="modifiers[\"Smoke\"].flow_settings.surface_distance")
#        
#        context.scene.frame_current += 28
#        ob.keyframe_insert(data_path="modifiers[\"Smoke\"].flow_settings.surface_distance")
#        
#        context.scene.frame_current = fr
#        
#                
## set current frame via click as emission_start
#class GetFrameOperator(bpy.types.Operator):
#    """Looks for the actual frame"""
#    bl_idname = "fracture.get_frame"
#    bl_label = "Start all emissions now"   
#    
#    
#    def execute(self, context):
#        ob = context.object
#        psys_name = "DEBRIS_PSystem"
#        try:
#            psys = ob.particle_systems[psys_name]
#            pdata = psys.settings
#            pdata.frame_start = context.scene.frame_current
#            pdata.frame_end = context.scene.frame_current + 10
#        
#        except KeyError:
#            self.report({'WARNING'}, "No debris particle system found, skipping")
#        
#        try:
#            fr = context.scene.frame_current    
#            set_smoke_keyframes(self, context, ob, fr)
#        except KeyError:
#            self.report({'WARNING'}, "No smoke modifier (flow) found, skipping")
#        
#        #Move FM to top position in modifier stack
#        bpy.ops.fracture.move_fmtotop()   
#        
#        context.scene.frame_current = 1
#        
#        return {'FINISHED'} 

# Add per click a collision modifier to all objects if not existing    
# valid for Collision- and SmokeModifier (?)

### Domain object has to be excluded
### And: As Idea: should objects whose name ends with "_nsc" NOT become smoke colliders ?
###      (nsc=no smoke collisions) until this smoke explosion bug is fixed by the devs somewhen ?

class CollisionSetupOperator(bpy.types.Operator):
    """Setup collision for selected objects"""
    bl_idname = "fracture.setup_collision"
    bl_label = "Collision on selected objects"
    
    def execute(self, context):
        selected = context.selected_objects
        #allobs = bpy.data.objects
        #selected.append(context.active_object)
        #act = context.active_object
               
        for ob in selected:
        
           if ob.type != 'MESH':
               continue
           
           md = find_modifier(ob, 'COLLISION')
           md2 = find_modifier(ob, 'SMOKE')
           if md2 is not None and md2.smoke_type == 'DOMAIN':
               continue
               
           if md is None:
                #was_none = True
                ob.modifiers.new(name="Debris_Collision", type='COLLISION')
                ob.collision.damping_factor = 0.8
                ob.collision.friction_factor = 0.4
                ob.collision.friction_random = 0.3
           
           #taken out due to instability of smoke simulation 22.03.2016
           if md2 is None:
                md2 = ob.modifiers.new(name="Smoke_Collision", type='SMOKE')
           
           # only when no domain exists and its name doesnt end on _nsc, make smoke type to collision
           # but what about existing flows, are they being excluded via _nsc ?
           if md2.smoke_type not in {'DOMAIN', 'FLOW'} and not ob.name.endswith("_nsc"):     
                md2.smoke_type = 'COLLISION'
        
        #move FractureModifier to first Position (why ?)
       # bpy.ops.fracture.move_fmtotop()            
        
        return {'FINISHED'} 
        
        

class SmokeDebrisDustSetupPanel(bpy.types.Panel):
    bl_label = "Smoke / Dust / Debris"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Fracture"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(context.scene, "emit_start", text="All Emissions Start")
        row.prop(context.scene, "emit_end", text="All Emissions End")
        if context.object and context.object.particle_systems.active:
            row = col.row(align=True)
            row.prop(context.object.particle_systems.active.settings, "lifetime", text="Lifetime (Only Active PSystem)")
        
        row = col.row(align=True)
        row.operator("fracture.setup_smoke", icon='MOD_SMOKE')
        row.operator("fracture.setup_dust", icon='STICKY_UVS_VERT')
        row.operator("fracture.setup_debris", icon='STICKY_UVS_DISABLE')
        
        col.operator("fracture.create_brush", icon='MOD_DYNAMICPAINT')
        row = col.row(align=True)
        row.prop(context.scene, "brush_fade", text="Brush Fadeout")
        row.operator("fracture.set_fade_brush", icon='PREVIEW_RANGE')
        
        #col.operator("fracture.get_frame", icon='TIME')
        col.operator("fracture.setup_collision", icon='MOD_PHYSICS')
                   

class ExecuteFractureOperator(bpy.types.Operator):
    """Adds FM when needed and (re)fractures..."""
    bl_idname = "fracture.execute"
    bl_label = "Execute Fracture"
    
    def execute(self, context):
        
        for ob in context.selected_objects:
            if ob.type != 'MESH':
                continue
                   
            md = find_modifier(ob, 'FRACTURE')
            if md is None:
                md = ob.modifiers.new(type='FRACTURE', name="Fracture")
           
            #Apply Scale has to be executed beforehand... 
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            context.scene.objects.active = ob
            
            #jump back to start frame
            if (context.scene.rigidbody_world):
                context.scene.frame_set(context.scene.rigidbody_world.point_cache.frame_start)
            else:
                context.scene.frame_set(1.0)
            
            bpy.ops.object.fracture_refresh(reset=True)
            #activate PhysicsTab ... but how?
            #bpy.data.screens = 'PHYSICS'
        
        
        return {'FINISHED'}

class SetTimeScaleOperator(bpy.types.Operator):
    """Sets time scale keyframes..."""
    bl_idname = "fracture.set_timescale"
    bl_label = "Set Time Scale"
    
    def execute(self, context):
        
        bpy.context.scene.keyframe_insert(data_path="time_scale")
            
        for o in bpy.context.scene.objects:
            md = find_modifier(o, 'FLUID_SIMULATION')
            if md is not None and md.settings.type == 'DOMAIN':
                md.settings.simulation_rate = bpy.context.scene.time_scale / 100
                o.keyframe_insert(data_path="modifiers[\""+md.name+"\"].settings.simulation_rate")
                
            md = find_modifier(o, 'SMOKE')
            if md is not None and md.smoke_type == 'DOMAIN':
                md.domain_settings.time_scale = bpy.context.scene.time_scale / 100
                o.keyframe_insert(data_path="modifiers[\""+md.name+"\"].domain_settings.time_scale")
            
            #GAH take ALL particlesystems per object into account     
            for md in o.modifiers:
                if md.type == 'PARTICLE_SYSTEM' and md.particle_system.settings.physics_type == 'NEWTON':
                    md.particle_system.settings.timestep = bpy.context.scene.time_scale / 100 * 0.04
                    md.particle_system.settings.keyframe_insert(data_path="timestep")
                
            #FLIP Fluid compat    
            if hasattr(o, "flip_fluid_object"):
                if hasattr(o.flip_fluid_object, "domain"):
                    o.flip_fluid_object.domain.time_scale = bpy.context.scene.time_scale / 100
                    o.keyframe_insert(data_path="flip_fluid_object.domain.time_scale") 
    
        #special case rigidbody, this is located at context.scene.rigidbody_world
        if bpy.context.scene.rigidbody_world is not None:
           bpy.context.scene.rigidbody_world.time_scale = bpy.context.scene.time_scale / 100    
           bpy.context.scene.keyframe_insert(data_path="rigidbody_world.time_scale")
        
        return {'FINISHED'}
           
class ClearTimeScaleOperator(bpy.types.Operator):
    """Clears time scale keyframes..."""
    bl_idname = "fracture.clear_timescale"
    bl_label = "Clear Time Scale"
    
    def execute(self, context):
        
        try:
            bpy.context.scene.keyframe_delete(data_path="time_scale")
        except RuntimeError:
            pass
            
        for o in bpy.context.scene.objects:
            md = find_modifier(o, 'FLUID_SIMULATION')
            if md is not None and md.settings.type == 'DOMAIN':
                try:
                    o.keyframe_delete(data_path="modifiers[\""+md.name+"\"].settings.simulation_rate")
                except RuntimeError: # silent fail in case of no animation is present
                    pass
                
            md = find_modifier(o, 'SMOKE')
            if md is not None and md.smoke_type == 'DOMAIN':
                try:
                    o.keyframe_delete(data_path="modifiers[\""+md.name+"\"].domain_settings.time_scale")
                except RuntimeError: # silent fail in case of no animation is present
                    pass
            
            #GAH take ALL particlesystems per object into account     
            for md in o.modifiers:
                if md.type == 'PARTICLE_SYSTEM' and md.particle_system.settings.physics_type == 'NEWTON':
                    try:
                        md.particle_system.settings.keyframe_delete(data_path="timestep")
                    except RuntimeError: # silent fail in case of no animation is present
                        pass 
                
            #FLIP Fluid compat    
            if hasattr(o, "flip_fluid_object"):
                if hasattr(o.flip_fluid_object, "domain"):
                    o.keyframe_delete(data_path="flip_fluid_object.domain.time_scale")
    
        #special case rigidbody, this is located at context.scene.rigidbody_world
        if bpy.context.scene.rigidbody_world is not None:
            try:
                bpy.context.scene.keyframe_delete(data_path="rigidbody_world.time_scale")
            except RuntimeError: # silent fail in case of no animation is present
                pass
            
        return {'FINISHED'}
    
class ClearAllTimeScaleOperator(bpy.types.Operator):
    """Clears time scale keyframes..."""
    bl_idname = "fracture.clear_all_timescale"
    bl_label = "Clear All Time Scale"
    
    def execute(self, context):
        
        delete_keyframes(bpy.context, bpy.context.scene, "time_scale")
        bpy.context.scene.time_scale = 100
            
        for o in bpy.context.scene.objects:
            md = find_modifier(o, 'FLUID_SIMULATION')
            if md is not None and md.settings.type == 'DOMAIN':
                md.settings.simulation_rate = 1.0
                try:
                    delete_keyframes(bpy.context, o, "modifiers[\""+md.name+"\"].settings.simulation_rate")
                except RuntimeError: # silent fail in case of no animation is present
                    pass
                
            md = find_modifier(o, 'SMOKE')
            if md is not None and md.smoke_type == 'DOMAIN':
                md.domain_settings.time_scale = 1.0
                try:
                    delete_keyframes(bpy.context, o, "modifiers[\""+md.name+"\"].domain_settings.time_scale")
                except RuntimeError: # silent fail in case of no animation is present
                    pass
            
            #GAH take ALL particlesystems per object into account     
            for md in o.modifiers: 
                if md.type == 'PARTICLE_SYSTEM' and md.particle_system.settings.physics_type == 'NEWTON':
                    md.particle_system.settings.timestep = 0.04
                    try:
                        delete_keyframes(bpy.context, md.particle_system.settings, "timestep")
                    except RuntimeError: # silent fail in case of no animation is present
                        pass
            
            #FLIP Fluid compat    
            if hasattr(o, "flip_fluid_object"):
                if hasattr(o.flip_fluid_object, "domain"):
                    o.flip_fluid_object.domain.time_scale = 1.0
                    delete_keyframes(bpy.context, o, "flip_fluid_object.domain.time_scale") 
    
        #special case rigidbody, this is located at context.scene.rigidbody_world
        if bpy.context.scene.rigidbody_world is not None:
            bpy.context.scene.rigidbody_world.time_scale = 1.0
            try:
                delete_keyframes(bpy.context, bpy.context.scene, "rigidbody_world.time_scale")
            except RuntimeError: # silent fail in case of no animation is present
                pass
            
        return {'FINISHED'}
    
class ApplyTimeScaleOperator(bpy.types.Operator):
    """Applies time scale keyframes to all matching scene objects"""
    bl_idname = "fracture.apply_timescale"
    bl_label = "Apply Time Scale"
    
    def execute(self, context):
        anim = bpy.context.scene.animation_data
        if anim is None:
            return {'CANCELLED'}
        
        action = anim.action
        if action is None:
            return {'CANCELLED'}
            
        for fc in action.fcurves:
            if fc.data_path == 'time_scale':
                for keyf in fc.keyframe_points:
                    bpy.context.scene.frame_set(keyf.co[0])
                     
                    for o in bpy.context.scene.objects:
                        md = find_modifier(o, 'FLUID_SIMULATION')
                        if md is not None and md.settings.type == 'DOMAIN':
                            md.settings.simulation_rate = keyf.co[1] / 100 
                            o.keyframe_insert(data_path="modifiers[\""+md.name+"\"].settings.simulation_rate")
                            
                        md = find_modifier(o, 'SMOKE')
                        if md is not None and md.smoke_type == 'DOMAIN':
                            md.domain_settings.time_scale = keyf.co[1] / 100
                            o.keyframe_insert(data_path="modifiers[\""+md.name+"\"].domain_settings.time_scale")
                             
                        #GAH take ALL particlesystems per object into account     
                        for md in o.modifiers:
                            if md.type == 'PARTICLE_SYSTEM' and md.particle_system.settings.physics_type == 'NEWTON':
                                md.particle_system.settings.timestep = keyf.co[1] / 100 * 0.04
                                md.particle_system.settings.keyframe_insert(data_path="timestep")
                            
                        #FLIP Fluid compat    
                        if hasattr(o, "flip_fluid_object"):
                            if hasattr(o.flip_fluid_object, "domain"):
                                o.flip_fluid_object.domain.time_scale = keyf.co[1] / 100
                                o.keyframe_insert(data_path="flip_fluid_object.domain.time_scale") 
                
                    #special case rigidbody, this is located at context.scene.rigidbody_world
                    if bpy.context.scene.rigidbody_world is not None:
                       bpy.context.scene.rigidbody_world.time_scale = keyf.co[1] / 100    
                       bpy.context.scene.keyframe_insert(data_path="rigidbody_world.time_scale")
        
        bpy.context.scene.frame_set(1)
        
        return {'FINISHED'}
            
def update_timescale(self, context):
    if bpy.context.object is None:
        return
    
    for o in bpy.context.scene.objects:
        md = find_modifier(o, 'FLUID_SIMULATION')
        if md is not None and md.settings.type == 'DOMAIN':
            md.settings.simulation_rate = bpy.context.object.time_scale / 100 
        md = find_modifier(o, 'SMOKE')
        if md is not None and md.smoke_type == 'DOMAIN':
            md.domain_settings.time_scale = bpy.context.object.time_scale / 100 
        #GAH take ALL particlesystems per object into account     
        for md in o.modifiers:
            if md.type == 'PARTICLE_SYSTEM' and md.particle_system.settings.physics_type == 'NEWTON':
                md.particle_system.settings.timestep = bpy.context.object.time_scale / 100 * 0.04
            
        # FLIP FLUID compat
        if hasattr(o, "flip_fluid_object"):
            if hasattr(o.flip_fluid_object, "domain"):
                o.flip_fluid_object.domain.time_scale = bpy.context.object.time_scale / 100 
    
    #special case rigidbody, this is located at context.scene.rigidbody_world
    if bpy.context.scene.rigidbody_world is not None:
        bpy.context.scene.rigidbody_world.time_scale = bpy.context.object.time_scale / 100
        
def update_start_end(self, context):
    for o in bpy.context.scene.objects:
        md = find_modifier(o, 'DYNAMIC_PAINT')
        if md and md.canvas_settings:
            surf = md.canvas_settings.canvas_surfaces["dp_canvas_FM"]
            surf.frame_start = 1 #bpy.context.scene.emit_start else the DP cache doesnt work properly
            surf.frame_end = bpy.context.scene.emit_end
        
        for md in o.modifiers:
            if md.type == 'PARTICLE_SYSTEM':
                if md.particle_system.name in {'SMOKE_PSystem', 'DUST_PSystem', 'DEBRIS_PSystem'}:
                    md.particle_system.settings.frame_start = bpy.context.scene.emit_start
                    md.particle_system.settings.frame_end = bpy.context.scene.emit_end
            
        
class MakeBrushOperator(bpy.types.Operator):
    """creates a dynamic paint brush on selected objects"""
    bl_idname = "fracture.create_brush"
    bl_label = "Create Brush"
    
    def execute(self, context):
        for o in context.selected_objects:
            md = find_modifier(o, 'DYNAMIC_PAINT')
            if md is None:
                md = o.modifiers.new(name="dp_brush_FM", type='DYNAMIC_PAINT')
                
            if md is not None and md.brush_settings is None:
                md.ui_type = 'BRUSH'
                ctx = context.copy()
                ctx['object'] = o
                bpy.ops.dpaint.type_toggle(ctx, type='BRUSH')
            
           
            brush = md.brush_settings
            brush.paint_source = 'VOLUME_DISTANCE'
            brush.paint_distance = 0.2
        return {'FINISHED'}   

class SetFadeBrushOperator(bpy.types.Operator):
    """animates the alpha of a brush to fade it out"""
    bl_idname = "fracture.set_fade_brush"
    bl_label = "Set Brush Fadeout"
    
    def execute(self, context):
        for o in context.selected_objects:
            md = find_modifier(o, 'DYNAMIC_PAINT')
            if md and md.brush_settings:
                brush = md.brush_settings
                delete_keyframes(bpy.context, o, "modifiers[\""+md.name+"\"].brush_settings.paint_alpha")
                cur = context.scene.frame_current
                
                brush.paint_alpha = 1.0
                o.keyframe_insert(data_path="modifiers[\""+md.name+"\"].brush_settings.paint_alpha")
                
                context.scene.frame_current = cur + context.scene.brush_fade
                brush.paint_alpha = 0.0
                o.keyframe_insert(data_path="modifiers[\""+md.name+"\"].brush_settings.paint_alpha")
                
                context.scene.frame_current = cur
        return {'FINISHED'}
    
class ClusterVertexGroup(bpy.types.PropertyGroup):
    cluster = bpy.props.IntProperty(name="cluster", description="Cluster Index")
    vertex_group = bpy.props.StringProperty(name="vertex_group", description="Vertex Group Name")
    

class AddCustomClusterOperator(bpy.types.Operator):
    """adds a custom cluster slot"""
    bl_idname = "fracture.custom_cluster_add"
    bl_label = "Add Custom Cluster Slot"
    
    def execute(self, context):
        count = len(context.scene.custom_clusters)
        c = context.scene.custom_clusters.add()
        c.cluster = count
        c.vertex_group = ""
        
        return {'FINISHED'}
        
class RemoveCustomClusterOperator(bpy.types.Operator):
    """removes a custom cluster slot"""
    bl_idname = "fracture.custom_cluster_remove"
    bl_label = "Remove Custom Cluster Slot"
    
    index = bpy.props.IntProperty(name="index")
    
    def execute(self, context):
        context.scene.custom_clusters.remove(self.index)
            
        return {'FINISHED'}

class ApplyCustomClustersOperator(bpy.types.Operator):
    """applies the custom clusters"""
    bl_idname = "fracture.custom_clusters_apply"
    bl_label = "Apply Clusters"
    
    def execute(self, context):
        md = context.object.modifiers["Fracture"] #check type !
        for mi in md.mesh_islands:
            maxweight = 0
            maxindex = 0
            weight = 0
            for v in mi.vertices:
                vg = md.vertex_groups[v.index]
                for w in vg.weights:
                    weight += w.weight
                    if weight > maxweight:
                        maxweight = weight
                        maxindex = w.group
            #find group name
            gn = context.object.vertex_groups[maxindex].name
            
            for c in context.scene.custom_clusters:
                if c.vertex_group == gn:
                    print("Assign", mi.name, c.cluster)
                    mi.cluster_index = c.cluster
                    break        
        
        return {'FINISHED'}
    
class CustomClusterPanel(bpy.types.Panel):
    bl_label = "Cluster Editor"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Fracture"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        for i,c in enumerate(context.scene.custom_clusters):
            row = layout.row(align=True)
            row.prop_search(c, "vertex_group", context.object, "vertex_groups", text="")
            row.prop(c, "cluster", text="")
            row.operator("fracture.custom_cluster_remove", text="", icon = 'ZOOMOUT').index = i;
        
        layout.operator("fracture.custom_cluster_add", text="", icon = 'ZOOMIN')
        
        if len(context.scene.custom_clusters) > 0:
            layout.operator("fracture.custom_clusters_apply")
            
def register():
    
    bpy.utils.register_class(MainOperationsPanel)
    bpy.utils.register_class(VIEW3D_SettingsPanel)
    bpy.utils.register_class(FractureHelper)
    bpy.utils.register_class(FractureHelperPanel)
    bpy.utils.register_class(TimingPanel)
    bpy.utils.register_class(FracturePathPanel)
    bpy.utils.register_class(FractureFrameOperator)
    bpy.utils.register_class(ClusterHelperOperator)
    bpy.utils.register_class(DisplacementEdgesOperator)
    bpy.utils.register_class(CombineSubObjectsOperator)
    bpy.utils.register_class(ViewOperatorFracture)
    bpy.utils.register_class(SmokeSetupOperator)
    bpy.utils.register_class(DustSetupOperator)
    bpy.utils.register_class(DebrisSetupOperator)    
    bpy.utils.register_class(SmokeDebrisDustSetupPanel)
    #bpy.utils.register_class(GetFrameOperator)
    bpy.utils.register_class(CollisionSetupOperator)
    bpy.utils.register_class(MoveFMToTopOperator)
    bpy.utils.register_class(ExecuteFractureOperator)
    bpy.utils.register_class(SetTimeScaleOperator)
    bpy.utils.register_class(ClearTimeScaleOperator)
    bpy.utils.register_class(ClearAllTimeScaleOperator)
    bpy.utils.register_class(ApplyTimeScaleOperator)
    bpy.utils.register_class(MakeBrushOperator)
    bpy.utils.register_class(SetFadeBrushOperator)
    bpy.utils.register_class(ClusterVertexGroup)
    bpy.utils.register_class(AddCustomClusterOperator)
    bpy.utils.register_class(RemoveCustomClusterOperator)
    bpy.utils.register_class(ApplyCustomClustersOperator)
    bpy.utils.register_class(CustomClusterPanel)
    
    bpy.types.Scene.use_animation_curve = bpy.props.BoolProperty(name="use_animation_curve", default=False)
    bpy.types.Scene.animation_obj = bpy.props.StringProperty(name="animation_obj", default = "")
    bpy.types.Scene.animation_ghost = bpy.props.BoolProperty(name="animation_ghost", default = False)
    bpy.types.Scene.fracture_frame = bpy.props.IntProperty(name="fracture_frame", default=1)
    bpy.types.Scene.is_dynamic = bpy.props.BoolProperty(name="is_dynamic", default=True)
    bpy.types.Scene.mouse_mode = bpy.props.EnumProperty(name="mouse_mode", items=[("Uniform", "Uniform", "Uniform", 'MESH_CUBE', 0), \
                                                                                   ("Radial", "Radial", "Radial", 'MESH_UVSPHERE', 1)])
                                                                                   
    bpy.types.Scene.mouse_object = bpy.props.EnumProperty(name="mouse_object", items=[("Cube", "Cube", "Cube", 'MESH_CUBE', 0), \
                                                                                         ("Sphere", "Sphere", "Sphere", 'MESH_UVSPHERE', 1), \
                                                                                         ("Custom", "Custom", "Custom", 'MESH_MONKEY', 2) ], default="Sphere")
    bpy.types.Scene.mouse_custom_object = bpy.props.StringProperty(name="mouse_custom_object", default="")
    bpy.types.Scene.mouse_count = bpy.props.IntProperty(name="mouse_count", default=50)
    bpy.types.Scene.mouse_segments = bpy.props.IntProperty(name="mouse_segments", default=8, min=1, max=100)
    bpy.types.Scene.mouse_rings = bpy.props.IntProperty(name="mouse_segments", default=8, min=1, max=100)
    bpy.types.Scene.mouse_status = bpy.props.StringProperty(name="mouse_status", default="Start mouse based fracture")
    bpy.types.Scene.delete_helpers = bpy.props.BoolProperty(name="delete_helpers", default=False)
    bpy.types.Scene.time_scale = bpy.props.IntProperty(name="time_scale", default=100, step=1, min=0, max=200, subtype="PERCENTAGE", update=update_timescale)
    bpy.types.Scene.emit_start = bpy.props.IntProperty(name="emit_start", default=1, min=1, update=update_start_end)
    bpy.types.Scene.emit_end = bpy.props.IntProperty(name="emit_end", default=250, min=1, update=update_start_end)
    bpy.types.Scene.brush_fade = bpy.props.IntProperty(name="brush_fade", default=25, min=1)
    bpy.types.Scene.custom_clusters = bpy.props.CollectionProperty(name="custom_clusters", type=ClusterVertexGroup)
    
def unregister():
    bpy.utils.unregister_class(MainOperationsPanel)
    bpy.utils.unregister_class(VIEW3D_SettingsPanel)
    bpy.utils.unregister_class(CombineSubObjectsOperator)
    bpy.utils.unregister_class(FractureFrameOperator)
    bpy.utils.unregister_class(TimingPanel)
    bpy.utils.unregister_class(FracturePathPanel)
    bpy.utils.unregister_class(FractureHelperPanel)
    bpy.utils.unregister_class(FractureHelper)
    bpy.utils.unregister_class(ClusterHelperOperator)
    bpy.utils.unregister_class(DisplacementEdgesOperator)
    bpy.utils.unregister_class(ViewOperatorFracture)
    bpy.utils.unregister_class(SmokeSetupOperator)
    bpy.utils.unregister_class(DustSetupOperator)
    bpy.utils.unregister_class(DebrisSetupOperator)
    bpy.utils.unregister_class(SmokeDebrisDustSetupPanel)
    #bpy.utils.unregister_class(GetFrameOperator)
    bpy.utils.unregister_class(CollisionSetupOperator)
    bpy.utils.unregister_class(MoveFMToTopOperator)
    bpy.utils.unregister_class(ExecuteFractureOperator)
    bpy.utils.unregister_class(SetTimeScaleOperator)
    bpy.utils.unregister_class(ClearTimeScaleOperator)
    bpy.utils.unregister_class(ClearAllTimeScaleOperator)
    bpy.utils.unregister_class(ApplyTimeScaleOperator)
    bpy.utils.unregister_class(MakeBrushOperator)
    bpy.utils.unregister_class(SetFadeBrushOperator)
    
    bpy.utils.unregister_class(CustomClusterPanel)
    bpy.utils.unregister_class(AddCustomClusterOperator)
    bpy.utils.unregister_class(RemoveCustomClusterOperator)
    bpy.utils.unregister_class(ApplyCustomClustersOperator)
   
    
       
    del bpy.types.Scene.use_animation_curve
    del bpy.types.Scene.animation_obj
    del bpy.types.Scene.animation_ghost
    del bpy.types.Scene.fracture_frame
    del bpy.types.Scene.is_dynamic
    del bpy.types.Scene.mouse_object
    del bpy.types.Scene.mouse_count
    del bpy.types.Scene.mouse_status
    del bpy.types.Scene.mouse_rings
    del bpy.types.Scene.mouse_segments
    del bpy.types.Scene.delete_helpers
    del bpy.types.Scene.time_scale
    del bpy.types.Scene.emit_start
    del bpy.types.Scene.emit_end
    del bpy.types.Scene.brush_fade
    del bpy.types.Scene.custom_clusters
    
    bpy.utils.unregister_class(ClusterVertexGroup)


if __name__ == "__main__":
    register()
