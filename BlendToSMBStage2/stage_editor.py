import bpy
import bgl
import bmesh
import enum
import os
import copy
import subprocess
import sys
import mathutils
import random
import math
import pdb

from . import statics, stage_object_drawing, generate_config, dimension_dict
from .descriptors import descriptors, descriptor_item_group, descriptor_model_stage, descriptor_track_path
from bpy.props import BoolProperty, PointerProperty, EnumProperty, FloatProperty, IntProperty
from enum import Enum
from sys import platform
from mathutils import Vector, Matrix

if platform == "linux" or platform == "linux2":
    from lxml import etree
else:
    import xml.etree.ElementTree as etree

# Operator for adding external background objects
class OBJECT_OT_add_external_objects(bpy.types.Operator):
    bl_idname = "object.add_external_objects"
    bl_label = "Add External Objects"
    bl_description = "Add external objects, such as those found in background files"
    bl_options={'UNDO'} 

    def execute(self, context):
        #Create the text block
        textblock  = bpy.data.texts.get("blendtosmbstage:addexternalobjects")
        if textblock is None:
            textblock  = bpy.data.texts.new("blendtosmbstage:addexternalobjects")

        textblock.from_string("""# Write your external objects from line 9 onwards, one per line
# Then hit "Run script" at the bottom to add them
# Don't forget to parent them to item groups or mark them as background objects!

import bpy


external_objects = \"\"\"

\"\"\"

bpy.ops.object.confirm_add_external_objects("INVOKE_DEFAULT", objects=external_objects)
""")

        #Open the user prefs window
        bpy.ops.screen.userpref_show("INVOKE_DEFAULT")

        #Change area type to a text editor
        area = bpy.context.window_manager.windows[-1].screen.areas[0]
        area.type = "TEXT_EDITOR"
        area.spaces[0].text = textblock
        area.spaces[0].show_line_highlight = True
        area.spaces[0].show_line_numbers = True
        area.spaces[0].show_syntax_highlight = True
        bpy.ops.text.jump(line=1) #Scroll to the top

        return {'FINISHED'}

# Operator that actually adds the listed external objects
class OBJECT_OT_confirm_add_external_objects(bpy.types.Operator):
    bl_idname = "object.confirm_add_external_objects"
    bl_label = "Confirm Add External Objects"
    bl_options={'UNDO'} 
    
    objects: bpy.props.StringProperty()

    def execute(self, context):
        obj_list = self.objects.split("\n")
        for obj in obj_list:
            if obj == "":
                continue

            bpy.ops.object.create_new_empty_and_select("INVOKE_DEFAULT", name="[EXT:{}]".format(str(obj)))
        return  {'FINISHED'}

# Operator for 'converting' the active object to a specific type
# TODO: Make this remove tags so object names don't become cluttered
class OBJECT_OT_convert_selected(bpy.types.Operator):
    bl_idname = "object.convert_selected"
    bl_label = "Convert Selected Item"
    bl_description = "Converts selected item to a specified type"
    bl_options={'UNDO'} 

    prefix: bpy.props.StringProperty(default="[]")

    def execute(self, context):
        selected = bpy.context.active_object

        # Set rotation mode
        #selected.rotation_mode = 'XZY'

        # Clear active properties
        if self.prefix not in ["[MODEL]", "[NODISP]", "[MIR]", "[NOCOLI]"]:
            for key in selected.keys():
                del selected[key]

        # Append new prefix
        selected.name = self.prefix + " " + selected.name

        # Construct the newly converted object
        for desc in descriptors.descriptors:
            if selected.name.startswith(desc.get_object_name()): 
                desc.construct(selected)

        return {'FINISHED'}

# Operator for creating a new empty with a specified name and setting up its properties
class OBJECT_OT_create_new_empty_and_select(bpy.types.Operator):
    bl_idname = "object.create_new_empty_and_select"
    bl_label = "Create New Empty And Select"
    bl_description = "Creates a new empty object of a specified name"
    bl_options={'UNDO'} 
    name: bpy.props.StringProperty(default="Empty")

    def execute(self, context):
        newEmpty = bpy.data.objects.new(self.name, None)
        newEmpty.location = bpy.context.scene.cursor.location
        bpy.context.collection.objects.link(newEmpty)
        newEmpty.empty_display_size = 0.5 if newEmpty.name.startswith("[FALLOUT_VOL]") else 1.0
        newEmpty.empty_display_type = "CUBE" if newEmpty.name.startswith("[FALLOUT_VOL]") else "ARROWS"
        #newEmpty.rotation_mode = 'XZY'
        bpy.context.view_layer.objects.active = newEmpty

        if bpy.context.mode == 'OBJECT':
            bpy.ops.object.select_all(action='DESELECT')
        else:
            bpy.context.object.select_set(False)

        # Set up custom Monkey Ball-related properties
        for desc in descriptors.descriptors:
            if desc.get_object_name() in newEmpty.name:
                desc.construct(newEmpty)

        newEmpty.select_set(True)
        updateUIProps(newEmpty)
        return {'FINISHED'}

# UI panel for group creation 
class VIEW3D_PT_1_item_group_panel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_1_item_group_panel"
    bl_label = "Item Groups"
    bl_category = "Blend2SMB"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout

        layout.label(text="Item Groups")
        new_item_group = layout.operator("object.create_new_empty_and_select", text="New Item Group")
        new_item_group.name = "[IG] New Item Group"

# UI panel for stage object creation
class VIEW3D_PT_2_stage_object_panel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_2_stage_object_panel"
    bl_label = "Add Stage Objects"
    bl_category = "Blend2SMB"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        game_mode = context.scene.stage_game_mode

        layout = self.layout
        layout.label(text="Add Placeables")
        new_start = layout.operator("object.create_new_empty_and_select", text="Starting Position")
        new_start.name = "[START]"

        goal_row = layout.row(align=True)
        new_goal_b = goal_row.operator("object.create_new_empty_and_select", text="Goal (B)")
        new_goal_b.name = "[GOAL_B] Blue Goal"
        new_goal_g = goal_row.operator("object.create_new_empty_and_select", text="Goal (G)")
        new_goal_g.name = "[GOAL_G] Green Goal"
        new_goal_r = goal_row.operator("object.create_new_empty_and_select", text="Goal (R)")
        new_goal_r.name = "[GOAL_R] Red Goal"

        banana_row = layout.row(align=True)
        new_banana_s = banana_row.operator("object.create_new_empty_and_select", text="Banana")
        new_banana_s.name = "[BANANA_S] Banana"
        new_banana_b = banana_row.operator("object.create_new_empty_and_select", text="Bunch")
        new_banana_b.name = "[BANANA_B] Banana Bunch"

        new_bumper = layout.operator("object.create_new_empty_and_select", text="Bumper")
        new_bumper.name = "[BUMPER] Bumper"
        new_jamabar = layout.operator("object.create_new_empty_and_select", text="Jamabar")
        new_jamabar.name = "[JAMABAR] Jamabar"
        
        col_object_row = layout.row(align=True)
        new_cone_col = col_object_row.operator("object.create_new_empty_and_select", text="Cone")
        new_cone_col.name = "[CONE_COL] Cone Collision Object"
        new_sphere_col = col_object_row.operator("object.create_new_empty_and_select", text="Sphere")
        new_sphere_col.name = "[SPHERE_COL] Sphere Collision Object"
        new_cylinder_col = col_object_row.operator("object.create_new_empty_and_select", text="Cylinder")
        new_cylinder_col.name = "[CYLINDER_COL] Cylinder Collision Object"

        new_wormhole = layout.operator("object.create_new_empty_and_select", text="Wormhole")
        new_wormhole.name = "[WH] Wormhole"

        new_fallout_volume = layout.operator("object.create_new_empty_and_select", text="Fallout Volume")
        new_fallout_volume.name = "[FALLOUT_VOL] Fallout Volume"


        layout.label(text="Add Switches")
        switch_row = layout.row(align=True)
        new_rewind = switch_row.operator("object.create_new_empty_and_select", text="<<")
        new_rewind.name = "[SW_RW] New Rewind Switch"
        new_reverse = switch_row.operator("object.create_new_empty_and_select", text="<")
        new_reverse.name = "[SW_PLAY_BACKWARDS] New Backwards Switch"
        new_pause = switch_row.operator("object.create_new_empty_and_select", text="||")
        new_pause.name = "[SW_PAUSE] New Pause Switch"
        new_play = switch_row.operator("object.create_new_empty_and_select", text=">")
        new_play.name = "[SW_PLAY] New Play Switch"
        new_fast_forward = switch_row.operator("object.create_new_empty_and_select", text=">>")
        new_fast_forward.name = "[SW_FF] New Fast Forward Switch"

        if (game_mode == 'MONKEY_RACE_2'):
            layout.label(text="Add Monkey Race Mechanics")

            new_booster = layout.operator("object.create_new_empty_and_select", text="Booster")
            new_booster.name = "[BOOSTER] Booster"

            new_path = layout.operator("object.generate_track_path", text="Track Path from Selected")

        elif (game_mode == 'MONKEY_GOLF_2'):
            layout.label(text="Add Monkey Golf Mechanics")

            new_golf_hole = layout.operator("object.create_new_empty_and_select", text="Golf Hole")
            new_golf_hole.name = "[GOLF_HOLE] Golf Hole"

        layout.label(text="Add External")
        external_objects = layout.operator("object.add_external_objects", text="External Objects")
        bg_import = layout.operator("object.import_background", text="External Background")
        bg_path = layout.prop(context.scene, "background_import_path")
        bg_preview = layout.prop(context.scene, "background_import_preview")
        bg_cube = layout.prop(context.scene, "background_import_use_cubes")
        gma_import = layout.prop(context.scene, "import_gma_path")
        tpl_import = layout.prop(context.scene, "import_tpl_path")

# UI panel for active object modification
class VIEW3D_PT_3_active_object_panel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_3_active_object_panel"
    bl_label = "Active Object Settings"
    bl_category = "Blend2SMB"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        properties = layout.column()
        obj = context.active_object

        if obj is not None: 
            properties.label(text=obj.name)

            # Various conversion options

            if '[PATH]' not in obj.name:
                convert_ig = properties.operator("object.convert_selected", text="Convert to Item Group")
                convert_ig.prefix = "[IG]"
                if obj.data is not None:
                    convert_bg = properties.operator("object.convert_selected", text="Convert to Background Object")
                    convert_bg.prefix = "[BG]"
                    convert_fg = properties.operator("object.convert_selected", text="Convert to Foreground Object")
                    convert_fg.prefix = "[FG]"

                if '[BG]' not in obj.name and '[FG]' not in obj.name and obj.data is not None:
                    make_nodisp = properties.operator("object.convert_selected", text="Make invisible (NODISP)")
                    make_nodisp.prefix = "[NODISP]"
                    make_nocoli = properties.operator("object.convert_selected", text="Make non-collidable (NOCOLI)")
                    make_nocoli.prefix = "[NOCOLI]"
                    make_mirror = properties.operator("object.convert_selected", text="Make runtime reflective")
                    make_mirror.prefix = "[MIR]"
                    convert_level_model = properties.operator("object.convert_selected", text="Add Custom Model Properties")
                    convert_level_model.prefix = "[MODEL]"

                if '[START]' in obj.name:
                    make_cpu_starts = properties.operator("object.generate_cpu_starts", text="Make CPU Starts from Selected")

            if '[PATH]' in obj.name:
                make_cpu_paths = properties.operator("object.generate_cpu_paths", text="Make CPU Paths from Selected")

            properties.separator()
            
        # Fancy UI properties
        if context.active_object is not None:
            obj = context.active_object

            is_descriptor = False
            propertyGroup = []

            for desc in descriptors.descriptors:
                if desc.get_object_name() in obj.name:
                    is_descriptor = True
                    propertyGroup.append(desc.return_properties(obj))
                    if "[MODEL]" not in obj.name: break

            for group in [group for group in propertyGroup if group is not None]:
                for ui_prop in group.__annotations__.keys():
                    properties.prop(group, ui_prop)
                
# UI panel for various export options
class VIEW3D_PT_4_export_panel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_4_export_panel"
    bl_label = "Export"
    bl_category = "Blend2SMB"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Export Settings")
        layout.prop(context.scene, "export_timestep")
        layout.prop(context.scene, "export_value_round")
        layout.prop(context.scene, "export_time_round")
        layout.label(text="Export Paths")
        layout.prop(context.scene, "export_config_path")
        layout.prop(context.scene, "export_model_path")
        layout.prop(context.scene, "export_gma_path")
        layout.prop(context.scene, "export_tpl_path")
        layout.prop(context.scene, "export_raw_stagedef_path")
        layout.prop(context.scene, "export_stagedef_path")
        layout.prop(context.scene, "export_background_path")
        layout.prop(context.scene, "auto_path_names")
        layout.label(text="Export Operators")
        layout.operator("object.generate_config", text="Generate Config")
        layout.operator("object.export_obj", text="Export OBJ")
        layout.operator("object.export_gmatpl", text="Export GMA/TPL")
        export_lz_raw = layout.operator("object.export_stagedef", text="Export LZ.RAW")
        export_lz_raw.compressed = False;
        export_lz = layout.operator("object.export_stagedef", text="Export LZ")
        export_lz.compressed = True;
        export_bg = layout.operator("object.export_background", text="Export Background")

# UI panel for global scene/stage settings
class VIEW3D_PT_5_settings(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_5_settings"
    bl_label = "Settings"
    bl_category = "Blend2SMB"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Stage Properties")
        layout.prop(context.scene, "stage_game_mode")
        layout.prop(context.scene, "falloutProp")
        layout.prop(context.scene, "fog_type")
        layout.prop(context.scene, "fog_start_distance")
        layout.prop(context.scene, "fog_end_distance")
        layout.prop(context.scene, "fog_color")
        layout.label(text="Editor Operators")
        layout.operator("view3d.draw_stage_objects")
        layout.operator("object.generate_texture_scroll_preview")
        layout.operator("object.set_backface_culling")
        layout.label(text="Editor Properties")
        layout.prop(context.scene, "draw_stage_objects")
        layout.prop(context.scene, "draw_falloutProp")
        layout.prop(context.scene, "draw_collision_grid")
        layout.prop(context.scene, "optimize_keyframes")

# Operator for toggling the drawing of stage objects
class VIEW3D_OT_draw_stage_objects(bpy.types.Operator):
    bl_idname = "view3d.draw_stage_objects"
    bl_label = "Draw Stage Objects"
    bl_description = "Whether or not visual representations of stage objects should be drawn"

    def modal(self, context, event):
        context.area.tag_redraw()
        return {'PASS_THROUGH'}

    def execute(self, context):
        global draw_handlers
        if context.scene.draw_stage_objects and context.area.type == "VIEW_3D":
            # Arguments passed to the callback
            args = (self, context)
            # Adds the region drawing callback
            self._handle_3d = bpy.types.SpaceView3D.draw_handler_add(draw_callback_3d, args, "WINDOW", "POST_VIEW")

            statics.active_draw_handlers.append(self._handle_3d)
            context.window_manager.modal_handler_add(self)

            return {'RUNNING_MODAL'}
        else:
            self.report({"WARNING"}, "View3D not found, or stage visibility toggled off.")
            return {'CANCELLED'}

# Callback function for drawing stage objects
def draw_callback_3d(self, context):
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glEnable(bgl.GL_DEPTH_TEST)
    if context.scene.draw_stage_objects:
        # Draw objects
        for obj in context.scene.objects:
            if obj.visible_get():
                for desc in descriptors.descriptors:
                    if desc.get_object_name() in obj.name:
                        desc.render(obj)
        # Draw fallout plane
        if bpy.context.scene.draw_falloutProp:
            FALLOUT_COLOR = (0.96, 0.26, 0.21, 0.3)
            stage_object_drawing.draw_grid(-512, -512, 32, 32, 32, 32, bpy.context.scene.falloutProp, FALLOUT_COLOR)

# Function for automatically setting up path names
def autoPathNames(self, context):
    if context.scene.auto_path_names:
        default_filename = "//" + os.path.splitext(os.path.basename(bpy.context.blend_data.filepath))[0]
        context.scene.export_config_path = default_filename + ".xml"
        context.scene.export_model_path = default_filename + ".obj"
        context.scene.export_gma_path = default_filename + ".gma"
        context.scene.export_tpl_path = default_filename + ".tpl"
        context.scene.export_raw_stagedef_path = default_filename + ".lz.raw"
        context.scene.export_stagedef_path = default_filename + ".lz"
        context.scene.export_background_path = default_filename + ".bg.xml"

# Function for syncing properties and UI properties of objects on load
def autoUpdateUIProps():
    bpy.context.view_layer.objects.active = None 

    for obj in bpy.context.scene.objects:
        updateUIProps(obj)

def updateUIProps(obj):
        propertyGroup = []
        # Append only one property group, unless the object has the '[MODEL]' tag
        for desc in descriptors.descriptors:
            if desc.get_object_name() in obj.name: 
                propertyGroup.append(desc.return_properties(obj))
                if "[MODEL]" not in obj.name: break
        
        for group in [group for group in propertyGroup if group is not None]:
            for ui_prop in group.__annotations__.keys():
                if (ui_prop in obj.keys()):
                    if getattr(group, ui_prop) is not None:
                        val = type(getattr(group, ui_prop))(obj[ui_prop])
                        if getattr(group, ui_prop) != val:
                            setattr(group, ui_prop, val)
                else:
                    print("Property " + ui_prop + " not found in " + obj.name)

# Operator for auto-generating keyframes for a UV warp modifier to preview texture scroll
class OBJECT_OT_generate_texture_scroll_preview(bpy.types.Operator):
    bl_idname = "object.generate_texture_scroll_preview"
    bl_label = "Genreate Texture Scroll Preview"
    bl_description = "Generates keyframes for previewing texture scroll"
    bl_options = {'UNDO'}

    def execute(self, context):
        for obj in context.scene.objects:
            if obj.get("texScrollUSpeed", 0.0) or obj.get("texScrollVSpeed", 0.0):
                if 'texScrollModifier' not in obj.modifiers.keys():
                    modifier = obj.modifiers.new('texScrollModifier', 'UV_WARP')
                else:
                    modifier = obj.modifiers['texScrollModifier']
                    
                offset = modifier.offset
                frame_start = context.scene.frame_start
                frame_end = context.scene.frame_end
                u_end = (obj["texScrollUSpeed"] / 60) * frame_end
                v_end = (obj["texScrollVSpeed"] / 60) * frame_end

                offset[0] = 0.0
                offset[1] = 0.0
                offset.data.keyframe_insert('offset', frame=frame_start)

                offset[0] = u_end
                offset[1] = v_end
                offset.data.keyframe_insert('offset', frame=frame_end)
                
                for fcurve in obj.animation_data.action.fcurves:
                    if 'texScrollModifier' in fcurve.data_path:
                        for keyframe in fcurve.keyframe_points:
                            keyframe.interpolation = 'LINEAR'

            else:
                if 'texScrollModifier' in obj.modifiers.keys():
                    obj.modifiers.remove(obj.modifiers['texScrollModifier'])

        return {'FINISHED'}

# Operator for generating a track path from selected faces
class OBJECT_OT_generate_track_path(bpy.types.Operator):
    bl_idname = "object.generate_track_path"
    bl_label = "Generate Track Path from Selected"
    bl_description = "Generates a track path from the selected faces"
    bl_options={'UNDO'} 

    def execute(self, context):
        obj = bpy.context.active_object
        mesh = bmesh.from_edit_mesh(obj.data)

        # TODO: Calculate this mathemagically instead of relying on selection order
        selected_faces = list(dict.fromkeys(mesh.select_history)) 

        # Track paths must begin and end at the same point, so we append the first face to the end
        selected_faces.append(selected_faces[0])

        # Track path keyframes are generated from the median point of each keyframe
        median_points = [face.calc_center_median() for face in selected_faces]

        if (len(median_points) > 101):
            raise Exception("Track paths cannot have more than 100 points selected")

        # Track paths must have 101 keyframes, so we need to subdivide it
        vert_count = len(median_points)

        # Determine the number of times to subdivide the path
        subdivision_count = 0
        while True:
            subdivision_count = subdivision_count + 1
            final_vert_count = vert_count + (subdivision_count*(vert_count-1))
            if final_vert_count >= 101:
                break
        
        # Subdivide the path
        subdivided_path = []
        for i in range(0, len(median_points)-1):
            subdivided_path.append(median_points[i])

            if subdivision_count != 1:
                for segment in range(1, subdivision_count):
                    lerp_factor = segment/subdivision_count
                    new_point = median_points[i].lerp(median_points[i+1], lerp_factor)
                    subdivided_path.append(new_point)

        subdivided_path.append(median_points[-1])

        # Fill in the remainder of the points by randomly distributing them (definitely not the best way)
        while len(subdivided_path) < 101:
            target_index = random.randint(0, len(subdivided_path)-2)
            target_index_vert = subdivided_path[target_index]
            target_index_next = subdivided_path[target_index+1]
            new_point = target_index_vert.lerp(target_index_next, 0.5) 
            subdivided_path.insert(target_index+1, new_point)

        # Create the curve object from the generated path
        path_curve_data = bpy.data.curves.new('path', type='CURVE')
        path_curve_data.dimensions = '3D'

        path_spline = path_curve_data.splines.new('POLY')
        path_spline.points.add(len(subdivided_path)-1)
        
        for i, point in enumerate(subdivided_path):
            path_spline.points[i].co = (point[0], point[1], point[2], 1)

        path_curve = bpy.data.objects.new('[PATH] Race Track Path', path_curve_data)
        descriptor_track_path.DescriptorTrackPath.construct(path_curve)
        updateUIProps(path_curve)
        path_curve.data.transform(path_curve.matrix_world)
        path_curve.matrix_world = Matrix()
        context.collection.objects.link(path_curve)
        path_curve.location = obj.location

        return {'FINISHED'}

# Operator for generating CPU paths based on a player track path
class OBJECT_OT_generate_cpu_paths(bpy.types.Operator):
    bl_idname = "object.generate_cpu_paths"
    bl_label = "Generate CPU Paths"
    bl_description = "Generates 7 CPU paths for the selected track path"
    bl_options={'UNDO'} 

    def execute(self, context):
        path = bpy.context.active_object
        copies = 0
        while copies < 7:
            path_dupe = path.copy()
            path_dupe.data = path.data.copy()
            path_dupe["playerID"] = copies+2

            # CPU paths are 0.5 above player paths
            path_dupe.location[2] = path_dupe.location[2] + 0.5

            context.collection.objects.link(path_dupe)
            copies = copies+1

        return {'FINISHED'}

# Opeartor for generatin an arrangement of 7 CPU player starts
class OBJECT_OT_generate_cpu_starts(bpy.types.Operator):
    bl_idname = "object.generate_cpu_starts"
    bl_label = "Generate CPU Starts"
    bl_description = "Generates 7 CPU starting positions for the selected starting position"
    bl_options={'UNDO'} 

    def execute(self, context):
        start = bpy.context.active_object
        copies = 0
        while copies < 7:
            start_dupe = start.copy()
            start_dupe["playerID"] = copies+2

            new_pos = (copies+1)*math.cos(start.rotation_euler.z)*Vector((-1, 1, 0)) + (copies+1)*math.sin(start.rotation_euler.z)*Vector((-1, -1, 0))
            start_dupe.location = start_dupe.location + new_pos 

            context.collection.objects.link(start_dupe)
            copies = copies+1

        return {'FINISHED'}

# Operator for setting backface culling on all materials of all objects
class OBJECT_OT_set_backface_culling(bpy.types.Operator):
    bl_idname = "object.set_backface_culling"
    bl_label = "Set Backface Culling"
    bl_description = "Sets the backface culling attribute on all materials"
    bl_options={'UNDO'} 

    def execute(self, context):
        for mat in bpy.data.materials:
            if hasattr(mat, 'use_backface_culling'):
                mat.use_backface_culling = True

        return {'FINISHED'}

# Operator for exporting the stage model as a .OBJ file
class OBJECT_OT_export_obj(bpy.types.Operator):
    bl_idname = "object.export_obj"
    bl_label = "Export OBJ"
    bl_description = "Clean up model and export OBJ to the selected path"
    bl_options={'UNDO'} 

    def execute(self, context):
        origin_frame = context.scene.frame_start

        # Cleans up models to fix common crashes
        print("Cleaning up meshes...")
        if context.active_object is None:
            context.view_layer.objects.active = context.scene.objects[0]

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        for obj in [obj for obj in bpy.context.editable_objects if obj.type == 'MESH']:
            print(str(obj))
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.dissolve_degenerate()
            bpy.ops.mesh.delete_loose()
            bpy.ops.object.mode_set(mode='OBJECT')

        # Sets frame to start
        context.scene.frame_set(origin_frame)

        # BG and FG models need to be at the origin, so this saves their original world matrix and moves them
        # Also clears and restores frame 0 animation data. Very jank - I hate everything about this
        # If someone can find a smarter way to move things to the origin for export, and then move them back,
        # while also preserving animation data, please let me know. I'm dumb
        # (This is necessary since exporting as an OBJ will snap objects to their first keyframe position)

        bg_fg_models = [obj for obj in bpy.context.scene.objects if obj.name.startswith("[BG]") or obj.name.startswith("[FG]")]

        orig_matrix_dict = {}
        orig_pos_rot_scale = [{}, {}, {}]

        for obj in bg_fg_models:
            if obj.animation_data is not None and obj.animation_data.action is not None:
                orig_matrix_dict[obj.name] = copy.copy(obj.matrix_world)
                print("\tMoving object " + obj.name + " to origin for export")
                fcurves  = obj.animation_data.action.fcurves
                orig_pos = [None, None, None]
                orig_rot = [None, None, None]
                orig_scale = [None, None, None]

                # Position keyframes
                for index in [0, 1, 2]:
                    # Find location fcurve for current channel (X, Y, Z position)
                    fcurve = fcurves.find("location", index=index)
                    if fcurve is not None:
                        default_keyframe_point = -1
                        # Look for a keyframe that exists on the currently selected frame
                        for keyframe_index in range(len(fcurve.keyframe_points)):
                            if fcurve.keyframe_points[keyframe_index].co[0] == float(origin_frame):
                                default_keyframe_point = keyframe_index
                                break

                        # If a keyframe already exists on the currently selected frame, set its value to 0
                        if default_keyframe_point != -1:
                            orig_pos[index] = obj.location[index]
                            fcurve.keyframe_points[default_keyframe_point].co[1] = 0

                        # Otherwise, create a new keyframe and set its value to zero
                        else:
                            obj.location[index] = 0
                            obj.keyframe_insert("location", index=index, frame=origin_frame)

                orig_pos_rot_scale[0][obj.name] = orig_pos

                # Rotation keyframes
                for index in [0, 1, 2]:
                    fcurve = fcurves.find("rotation_euler", index=index)
                    if fcurve is not None:
                        default_keyframe_point = -1
                        # Look for a keyframe that exists on the currently selected frame
                        for keyframe_index in range(len(fcurve.keyframe_points)):
                            if fcurve.keyframe_points[keyframe_index].co[0] == float(origin_frame):
                                default_keyframe_point = keyframe_index
                                break

                        # If a keyframe already exists on the currently selected frame, set its value to 0
                        if default_keyframe_point != -1:
                            orig_rot[index] = obj.rotation_euler[index]
                            fcurve.keyframe_points[default_keyframe_point].co[1] = 0

                        else:
                            obj.rotation_euler[index] = 0
                            obj.keyframe_insert("rotation_euler", index=index, frame=origin_frame)

                orig_pos_rot_scale[1][obj.name] = orig_rot

                # Scale keyframes
                for index in [0, 1, 2]:
                    fcurve = fcurves.find("scale", index=index)
                    if fcurve is not None:
                        default_keyframe_point = -1
                        # Look for a keyframe that exists on the currently selected frame
                        for keyframe_index in range(len(fcurve.keyframe_points)):
                            if fcurve.keyframe_points[keyframe_index].co[0] == float(origin_frame):
                                default_keyframe_point = keyframe_index
                                break

                        # If a keyframe already exists on the currently selected frame, set its value to 0
                        if default_keyframe_point != -1:
                            orig_scale[index] = obj.scale[index]
                            fcurve.keyframe_points[default_keyframe_point].co[1] = 1
                        else:
                            obj.scale[index] = 1
                            obj.keyframe_insert("scale", index=index)

                orig_pos_rot_scale[2][obj.name] = orig_scale

                # For non-animated channels
                obj.location = (0,0,0)
                obj.rotation_quaternion = (1, 0, 0, 0)
                obj.scale = (1, 1, 1)

        print("Exporting OBJ...")

        # Dumb hacky way to not export path curves since they screw everything up
        bpy.ops.object.select_all(action='DESELECT')
        for obj in context.scene.objects:
            if '[PATH]' not in obj.name:
                obj.select_set(True)

        bpy.ops.export_scene.obj(
                filepath = bpy.path.abspath(context.scene.export_model_path),
                use_triangles=True,
                use_selection=True,
                path_mode="RELATIVE",
            )

        bpy.ops.object.select_all(action='DESELECT')

        # Restore original position and animation
        for obj in bg_fg_models:
            if obj.animation_data is not None and obj.animation_data.action is not None:
                print("\tRestoring position and animation of " + obj.name)
                fcurves  = obj.animation_data.action.fcurves
                # Position keyframes
                for index in [0, 1, 2]:
                    fcurve = fcurves.find("location", index=index)
                    if fcurve is not None:
                        if orig_pos_rot_scale[0][obj.name][index] is not None:
                            default_keyframe_point = -1
                            # Look for a keyframe that exists on the currently selected frame
                            for keyframe_index in range(len(fcurve.keyframe_points)):
                                if fcurve.keyframe_points[keyframe_index].co[0] == float(origin_frame):
                                    default_keyframe_point = keyframe_index
                                    break
                        # If a keyframe already exists on the currently selected frame, set its value to 0
                            fcurve.keyframe_points[default_keyframe_point].co[1] = orig_pos_rot_scale[0][obj.name][index]
                        else:
                            obj.keyframe_delete("location", index=index, frame=origin_frame)

                # Rotation keyframes
                for index in [0, 1, 2]:
                    fcurve = fcurves.find("rotation_euler", index=index)
                    if fcurve is not None:
                        if orig_pos_rot_scale[1][obj.name][index] is not None:
                            default_keyframe_point = -1
                            # Look for a keyframe that exists on the currently selected frame
                            for keyframe_index in range(len(fcurve.keyframe_points)):
                                if fcurve.keyframe_points[keyframe_index].co[0] == float(origin_frame):
                                    default_keyframe_point = keyframe_index
                                    break
                        # If a keyframe already exists on the currently selected frame, set its value to 0
                            fcurve.keyframe_points[default_keyframe_point].co[1] = orig_pos_rot_scale[1][obj.name][index]
                        else:
                            obj.keyframe_delete("rotation_euler", index=index, frame=origin_frame)

                # Scale keyframes
                for index in [0, 1, 2]:
                    fcurve = fcurves.find("scale", index=index)
                    if fcurve is not None:
                        if orig_pos_rot_scale[2][obj.name][index] is not None:
                            default_keyframe_point = -1
                            # Look for a keyframe that exists on the currently selected frame
                            for keyframe_index in range(len(fcurve.keyframe_points)):
                                if fcurve.keyframe_points[keyframe_index].co[0] == float(origin_frame):
                                    default_keyframe_point = keyframe_index
                                    break
                        # If a keyframe already exists on the currently selected frame, set its value to 0
                            fcurve.keyframe_points[default_keyframe_point].co[1] = orig_pos_rot_scale[2][obj.name][index]
                        else:
                            obj.keyframe_delete("scale", index=index, frame=origin_frame)

                obj.matrix_world = orig_matrix_dict[obj.name]

        print("Finished exporting OBJ")
        return {'FINISHED'}

# Operator for calling GxModelViewer to export the stage model as a .GMA and .TPL file
class OBJECT_OT_export_gmatpl(bpy.types.Operator):
    bl_idname = "object.export_gmatpl"
    bl_label = "Export OBJ"
    bl_description = "Export an OBJ, then call GxModelViewer to export a GMA/TPL to the specified path"
    bl_options={'UNDO'} 

    def execute(self, context):
        bpy.ops.object.export_obj("INVOKE_DEFAULT")
        obj_path = bpy.path.abspath(context.scene.export_model_path)
        gma_path = bpy.path.abspath(context.scene.export_gma_path)
        tpl_path = bpy.path.abspath(context.scene.export_tpl_path)
        gx_path = bpy.utils.script_path_user() + "/addons/BlendToSMBStage2/GxUtils/GxModelViewer.exe"

        args = []
        args.append(gx_path)
        args.append("-importObjMtl")
        args.append(obj_path)
        args.append("-removeUnusedTextures")

        import_gma_path = bpy.path.abspath(context.scene.import_gma_path) 
        import_tpl_path = bpy.path.abspath(context.scene.import_tpl_path)
        if os.path.exists(import_gma_path) and os.path.exists(import_tpl_path):
            args.append("-mergeGmaTpl")
            args.append(import_gma_path + "," + import_tpl_path)

        args.append("-exportGma")
        args.append(gma_path)
        args.append("-exportTpl")
        args.append(tpl_path)

        subprocess.run(args)
        
        return {'FINISHED'}

# Operator for calling Workshop 2 to export the stage config as a .LZ or .LZ.RAW file
class OBJECT_OT_export_stagedef(bpy.types.Operator):
    bl_idname = "object.export_stagedef"
    bl_label = "Export OBJ"
    bl_description = "Export an OBJ, then call Workshop 2 to export a LZ/LZ.RAW to the specified path"
    bl_options={'UNDO'} 

    compressed: bpy.props.BoolProperty(default=True)
    def execute(self, context):
        bpy.ops.object.export_obj("INVOKE_DEFAULT")
        bpy.ops.object.generate_config("INVOKE_DEFAULT")
        config_path = bpy.path.abspath(context.scene.export_config_path)
        stagedef_path = bpy.path.abspath(context.scene.export_stagedef_path)
        raw_stagedef_path = bpy.path.abspath(context.scene.export_raw_stagedef_path)

        if platform == "linux" or platform == "linux2":
            ws_path = bpy.utils.script_path_user() + "/addons/BlendToSMBStage2/ws2lzfrontend/ws2lzfrontend"
        else:
            ws_path = bpy.utils.script_path_user() + "/addons/BlendToSMBStage2/ws2lzfrontend/ws2lzfrontend.exe"

        command_args = [ws_path,
                        "-c" + config_path]

        if self.compressed:
            command_args.append("-s" + stagedef_path)
        else:
            command_args.append("-o" + raw_stagedef_path)

        subprocess.run(command_args)

        return {'FINISHED'}

# Operator for importing a background from a .XML file
class OBJECT_OT_import_background(bpy.types.Operator):
    bl_idname ="object.import_background"
    bl_label = "Import Background"
    bl_description = "Import background from the specified .XML file."
    bl_options={'UNDO'}
    
    def execute(self, context):
        bg_path = bpy.path.abspath(context.scene.background_import_path)
        if not (os.path.exists(bg_path)):
            self.report({'ERROR'}, "Invalid background file path selected!")
            return {'CANCELLED'}
        
        bg = etree.parse(bg_path)
        bg_root = bg.getroot()

        if bg_root.tag != 'superMonkeyBallBackground':
            self.report({'ERROR'}, "Imported background XML not an exported background XML")
            return {'CANCELLED'}

        if context.scene.background_import_preview:
            convert = lambda v, n: Vector((float(v[0]), (-1+int(2*(not n)))*float(v[2]), float(v[1])))
            rad = lambda v: Vector((math.radians(v[0]), math.radians(v[1]), math.radians(v[2])))

            for i, imported_bg_model in enumerate(bg_root.getchildren()):
                preview_name = imported_bg_model.find('name').text
                preview_pos = convert(imported_bg_model.find('position').attrib.values(), True)
                preview_rot = rad(convert(imported_bg_model.find('rotation').attrib.values(), True))
                preview_scale = convert(imported_bg_model.find('scale').attrib.values(), False)
                preview_dimensions = Vector((1,1,1))

                print("Importing model " + str(preview_name))

                if (preview_name in dimension_dict.dimensions.keys()):
                    preview_dimensions = convert(dimension_dict.dimensions[preview_name], False)

                newEmpty = bpy.data.objects.new("[EXT_IMPORTED:{}:{}]".format(preview_name, i), None)
                newEmpty.location = preview_pos
                newEmpty.rotation_euler = preview_rot
                if context.scene.background_import_use_cubes:
                    newEmpty.empty_display_size = 0.5
                    newEmpty.scale[0] = preview_scale[0] * preview_dimensions[0]
                    newEmpty.scale[1] = preview_scale[1] * preview_dimensions[1]
                    newEmpty.scale[2] = preview_scale[2] * preview_dimensions[2]
                    newEmpty.empty_display_type = "CUBE"
                else:
                    newEmpty.empty_display_type = "ARROWS"
                bpy.context.collection.objects.link(newEmpty)
            
                effects = imported_bg_model.find('effectKeyframes')
                if effects is not None: 
                    for effect in effects:
                        if effect.tag == 'effectType1':
                            for j, ef1 in enumerate(effect.getchildren()):
                                effect_pos = convert([ef1.attrib['posX'], ef1.attrib['posY'], ef1.attrib['posZ']], True)
                                effect_rot = rad(convert([ef1.attrib['rotX'], ef1.attrib['rotY'], ef1.attrib['rotZ']], True))

                                newEmpty = bpy.data.objects.new("[EXT_IMPORTED_FX:{}:{}:{}]".format(preview_name, i, j), None)
                                newEmpty.location = effect_pos
                                newEmpty.rotation_euler = effect_rot
                                newEmpty.empty_display_type = "ARROWS"
                                bpy.context.collection.objects.link(newEmpty)

                        elif effect.tag == 'effectType2':
                            for j, ef2 in enumerate(effect.getchildren()):
                                effect_pos = convert([ef2.attrib['posX'], ef2.attrib['posY'], ef2.attrib['posZ']], True)
                                effect_rot = Vector((0,0,0))

                                newEmpty = bpy.data.objects.new("[EXT_IMPORTED_FX:{}:{}:{}]".format(preview_name, i, j), None)
                                newEmpty.location = effect_pos
                                newEmpty.rotation_euler = effect_rot
                                newEmpty.empty_display_type = "ARROWS"
                                bpy.context.collection.objects.link(newEmpty)

        return {'FINISHED'}

# Operator for exporting a background to a .XML file
class OBJECT_OT_export_background(bpy.types.Operator):
    bl_idname ="object.export_background"
    bl_label = "Export Background"
    bl_description = "Export background to the specified .XML file."
    bl_options={'UNDO'}
    
    def execute(self, context):
        print("Generating background/foreground config...")
        
        root = etree.Element("superMonkeyBallBackground", version="1.3.0")

        # Iterate over all top-level objects
        for obj in [obj for obj in bpy.context.scene.objects if (obj.type == 'EMPTY' or obj.type == 'MESH' or obj.type == 'CURVE')]:
            # Non-item groups (start, BG/FG objects, etc)
            for desc in [descriptors.DescriptorBG, descriptors.DescriptorFG]: 
                match_descriptor = False
                if obj.name.startswith(desc.get_object_name()): 
                    match_descriptor = True
                    desc.generate_xml(root, obj)
                    continue

        # Import background and foreground objects from a .XML file, if it exists
        obj_names = [obj.name for obj in context.scene.objects]
        bg_path = bpy.path.abspath(context.scene.background_import_path)
        if (os.path.exists(bg_path)):
            bg = etree.parse(bg_path)
            bg_root = bg.getroot()

            if bg_root.tag != 'superMonkeyBallBackground':
                self.report({'ERROR'}, "Imported background XML not an exported background XML")
                return {'CANCELLED'}

            append_imported_bg_objects(self, context, bg_root, root, obj_names)

        print("Completed, saving...")
        if platform == "linux" or platform == "linux2":
            config = etree.tostring(root, pretty_print=True, encoding="unicode")
        else:
            config = etree.tostring(root, encoding="unicode")
        config_file = open(bpy.path.abspath(context.scene.export_background_path), "w")
        config_file.write(config)
        config_file.close()
        print("Finished generating config")

        return {'FINISHED'}
# Operator for appending all imported background objects in an XML to a config root
def append_imported_bg_objects(self, context, bg_root, dest_root, obj_names):
    convert = lambda v, n: Vector((float(v[0]), (-1+int(2*(not n)))*float(v[2]), float(v[1])))
    deg = lambda v: Vector((math.degrees(v[0]), math.degrees(v[1]), math.degrees(v[2])))

    for index, imported_bg_model in enumerate(bg_root.getchildren()):
        name = imported_bg_model.find('name')
        ported_name = "[EXT_IMPORTED:" + name.text + ":" + str(index) + "]" 
        print("Exporting imported background object " + ported_name + "...")
        if ported_name in obj_names:
            bg_obj = context.scene.objects[ported_name]

            orig_pos = convert(imported_bg_model.find('position').attrib.values(), True) 
            orig_rot = convert(imported_bg_model.find('rotation').attrib.values(), True) 
            orig_scale = convert(imported_bg_model.find('scale').attrib.values(), False) 

            bg_pos = imported_bg_model.find('position').attrib
            bg_pos['x'] = str(bg_obj.location[0])
            bg_pos['y'] = str(bg_obj.location[2])
            bg_pos['z'] = str(-1 * bg_obj.location[1])
            
            bg_rot = imported_bg_model.find('rotation').attrib
            bg_rot['x'] = str(math.degrees(bg_obj.rotation_euler[0]))
            bg_rot['y'] = str(math.degrees(bg_obj.rotation_euler[2]))
            bg_rot['z'] = str(-1 * math.degrees(bg_obj.rotation_euler[1]))

            bg_dimensions = Vector((1,1,1))
            if name.text in dimension_dict.dimensions.keys():
                bg_dimensions = dimension_dict.dimensions[name.text]

            bg_scale = imported_bg_model.find('scale').attrib
            bg_scale['x'] = str(bg_obj.scale[0] / bg_dimensions[0])
            bg_scale['y'] = str(bg_obj.scale[2] / bg_dimensions[1])
            bg_scale['z'] = str(bg_obj.scale[1] / bg_dimensions[2])
            
            posXDelta = bg_obj.location[0] - orig_pos[0] 
            posYDelta = bg_obj.location[2] - orig_pos[2]
            posZDelta = bg_obj.location[1] - orig_pos[1]
            rotXDelta = math.degrees(bg_obj.rotation_euler[0]) - orig_rot[0] 
            rotYDelta = math.degrees(bg_obj.rotation_euler[2]) - orig_rot[2]
            rotZDelta = math.degrees(bg_obj.rotation_euler[1]) - orig_rot[1]
            scaleXDelta = float(bg_scale['x']) / orig_scale[0] 
            scaleYDelta = float(bg_scale['y']) / orig_scale[2]
            scaleZDelta = float(bg_scale['z']) / orig_scale[1]

            effects = imported_bg_model.find('effectKeyframes')
            if effects is not None:
                for effect in effects:
                    if effect.tag == 'effectType1':
                        for j, ef1 in enumerate(effect.getchildren()):
                            ported_name = "[EXT_IMPORTED_FX:" + name.text + ":" + str(index) + ":" + str(j) + "]" 
                            effect_obj = context.scene.objects[ported_name]
                            attr = ef1.attrib
                            attr['posX'] = str(effect_obj.location[0]) 
                            attr['posY'] = str(effect_obj.location[2])
                            attr['posZ'] = str(-1*effect_obj.location[1]) 
                            attr['rotX'] = str(math.degrees(effect_obj.rotation_euler[0]))
                            attr['rotY'] = str(math.degrees(effect_obj.rotation_euler[2]))
                            attr['rotZ'] = str(math.degrees(-1*effect_obj.rotation_euler[1])) 

                    elif effect.tag == 'effectType2':
                        for j, ef2 in enumerate(effect.getchildren()):
                            ported_name = "[EXT_IMPORTED_FX:" + name.text + ":" + str(index) + ":" + str(j) + "]" 
                            effect_obj = context.scene.objects[ported_name]
                            attr = ef2.attrib
                            attr['posX'] = str(effect_obj.location[0]) 
                            attr['posY'] = str(effect_obj.location[2])
                            attr['posZ'] = str(-1*effect_obj.location[1]) 
            anim = imported_bg_model.find('animKeyframes')
            if anim is not None:
                for tag in anim.getchildren():
                    for tag_name, delta in [('posX', posXDelta), ('posY', posYDelta), ('posZ', posZDelta), ('rotX', rotXDelta), ('rotY', rotYDelta), ('rotZ', rotZDelta), ('scaleX', scaleXDelta), ('scaleY', scaleYDelta), ('scaleZ', scaleZDelta)]:
                        if tag.tag == tag_name:
                            for keyframe in tag.getchildren():
                                if "scale" not in tag_name:
                                    keyframe.attrib['value'] = str(float(keyframe.attrib['value']) + delta)
                                else:
                                    keyframe.attrib['value'] = str(float(keyframe.attrib['value']) * delta)
                            break

        dest_root.append(imported_bg_model)

# Operator for exporting the stage config as a .XML file
class OBJECT_OT_generate_config(bpy.types.Operator):
    bl_idname = "object.generate_config"
    bl_label = "Generate Config"
    bl_description = "Generate .XML file for config export"
    bl_options={'UNDO'} 

    def execute(self, context):
        print("Generating config...")

        root = etree.Element("superMonkeyBallStage", version="1.3.0")
        
        # OBJ file path
        modelImport = etree.SubElement(root, "modelImport")
        modelImport.text = context.scene.export_model_path

        # Game mode type
        mode = etree.SubElement(root, "stageType")
        mode.text = context.scene.stage_game_mode

        # Fallout plane height
        etree.SubElement(root, "falloutPlane", y=str(context.scene.falloutProp))

        # Fog 
        if context.scene.fog_type != 'GX_FOG_NONE':
            fog_type = context.scene.fog_type
            fog_start = context.scene.fog_start_distance
            fog_end = context.scene.fog_end_distance
            fog_red = context.scene.fog_color.r
            fog_green = context.scene.fog_color.g
            fog_blue = context.scene.fog_color.b 

            fog = etree.SubElement(root, "fog")
            fogType = etree.SubElement(fog, "type")
            fogType.text = str(fog_type)
            fogStart = etree.SubElement(fog, "start")
            fogStart.text = str(fog_start)
            fogEnd = etree.SubElement(fog, "end")
            fogEnd.text = str(fog_end)
            fogRed = etree.SubElement(fog, "red")
            fogRed.text = str(fog_red)
            fogGreen = etree.SubElement(fog, "green")
            fogGreen.text = str(fog_green)
            fogBlue = etree.SubElement(fog, "blue")
            fogBlue.text = str(fog_blue)
            
            # Fog Animation (1 keyframe required to make it work
            fogAnimation = etree.SubElement(root, "fogAnimationKeyframes")
            for element_name, element_value in [("start", fog_start), ("end", fog_end), ("red", fog_red), ("green", fog_green), ("blue", fog_blue)]:
                element = etree.SubElement(fogAnimation, element_name)
                keyframe = etree.Element("keyframe")
                keyframe.set("time", str(0.0))
                keyframe.set("value", str(element_value))
                keyframe.set("easing", "LINEAR")
                element.append(keyframe)

        #TODO: This is kind-of a hack to work around stuff being funky with the first item group
        dummyIg = etree.SubElement(root, "itemGroup") 
        grid = etree.SubElement(dummyIg, "collisionGrid")

        etree.SubElement(grid, "start", x = "-256", z = "-256")
        etree.SubElement(grid, "step", x = "32", z = "32")
        etree.SubElement(grid, "count", x = "16", z = "16")

        igs = []
        
        # Start frame of animation
        begin_frame = context.scene.frame_start

        # Marks objects that don't have keyframes on frame 0
        remove_beginframe_objs = []

        # Iterate over all top-level objects
        for obj in [obj for obj in bpy.context.scene.objects if (obj.type == 'EMPTY' or obj.type == 'MESH' or obj.type == 'CURVE')]:
            if "[IG]" in obj.name: 
                igs.append(obj)
                context.scene.frame_set(begin_frame)

                # Semi-hacky way to get the object's center of rotation to work properly
                # B2SMB1 inadvertently fixed this by baking *all* keyframes
                begin_keyframe_exists = False
                if obj.animation_data is not None and obj.animation_data.action is not None:
                    fcurves = obj.animation_data.action.fcurves
                    for index in [0, 1, 2]:
                        for curve_type in ["location", "rotation_euler"]:
                            fcurve = fcurves.find(curve_type, index=index)
                            if fcurve is not None:
                                for keyframe_index in range(len(fcurve.keyframe_points)):
                                    if fcurve.keyframe_points[keyframe_index].co[0] == float(begin_frame):
                                        begin_keyframe_exists = True
                                        break
                        else: continue
                        break

                # Remove the beginning keyframe if it didn't exist prior to it being added
                if not begin_keyframe_exists:
                    remove_beginframe_objs.append(obj)

                print("\tInserted frame zero keyframe for item group " + obj.name)
                obj.keyframe_insert("location", frame=begin_frame, options={'INSERTKEY_NEEDED'})
                obj.keyframe_insert("rotation_euler", frame=begin_frame, options={'INSERTKEY_NEEDED'})

            else:
                # Non-item groups (start, BG/FG objects, etc)
                for desc in descriptors.descriptors_root:
                    match_descriptor = False
                    if obj.name.startswith(desc.get_object_name()): 
                        match_descriptor = True
                        desc.generate_xml(root, obj)
                        continue

        # Iterator over all item groups
        for ig in igs: 
            context.scene.frame_set(begin_frame)
            # Children list
            ig_children = [obj for obj in bpy.context.scene.objects if obj.parent == ig]
            ig_children.append(ig)

            # Generate item group XML elements
            if 'collisionStartX' in ig.keys():
                xig = descriptor_item_group.DescriptorIG.generate_xml(root, ig)

            else:
                continue

            # Animation
            if ig.animation_data is not None and ig.animation_data.action is not None:
                generate_config.addAnimation(ig, xig)

            # Children of item groups
            for child in ig_children:
                context.scene.frame_set(begin_frame)
                match_descriptor = False

                # Generate elements for listed descriptors (except IGs)
                for desc in descriptors.descriptors:
                    if desc.get_object_name() in child.name and not "[IG]" in child.name:
                        match_descriptor = True
                        desc.generate_xml(xig, child)
                        break
                
                # Object is not a listed descriptor
                if match_descriptor == False:
                    if child.data != None:
                        descriptor_model_stage.DescriptorModel.generate_xml(xig, child)


        context.scene.frame_set(begin_frame)

        # Import background and foreground objects from a .XML file, if it exists
        bg_path = bpy.path.abspath(context.scene.background_import_path)
        obj_names = [obj.name for obj in context.scene.objects]
        if (os.path.exists(bg_path)):
            bg = etree.parse(bg_path)
            bg_root = bg.getroot()

            if bg_root.tag != 'superMonkeyBallBackground':
                self.report({'ERROR'}, "Imported background XML not an exported background XML")
                return {'CANCELLED'}

            append_imported_bg_objects(self, context, bg_root, root, obj_names)

        print("Completed, saving...")
        if platform == "linux" or platform == "linux2":
            config = etree.tostring(root, pretty_print=True, encoding="unicode")
        else:
            config = etree.tostring(root, encoding="unicode")
        config_file = open(bpy.path.abspath(context.scene.export_config_path), "w")
        config_file.write(config)
        config_file.close()
        print("Finished generating config")

        # Remove the beginning keyframe if it didn't exist prior to it being added
        for obj in remove_beginframe_objs:
            print("Deleted frame zero keyframe for item group " + obj.name)
            obj.keyframe_delete("location", frame=begin_frame)
            obj.keyframe_delete("rotation_euler", frame=begin_frame)

        return {'FINISHED'}

# Fucntion for updating the properties of an active object
def update_prop(self, context, prop):
    if context.active_object is not None:
        prop_value = getattr(self, prop)

        # Cast string properties to ints (for enums)
        if isinstance(prop_value, str):
            prop_value = int(prop_value)

        context.active_object[prop] = prop_value

        # Handles linked IDs
        if prop == "linkedObject":
            if "[SW_" in context.active_object.name:
                context.active_object["linkedId"] = prop_value["animId"] 
            elif "[WH]" in context.active_object.name:
                context.active_object["linkedId"] = prop_value["whId"] 

        updateUIProps(context.active_object)

# Function for getting a list of collision triangle types depending on the game mode
def get_collision_triangle_list(self, context):
    game_mode = context.scene.stage_game_mode
    items = [('0', 'Normal', '')]

    if game_mode == 'MONKEY_GOLF_2':
        items.append(('2', 'Green', ''))
        items.append(('4', 'Rough', ''))
        items.append(('8', 'Bunker', ''))

    #TODO: Figure out flags (if any) Monkey Target and other games use

    return items
    
# Properties for item groups
class ItemGroupProperties(bpy.types.PropertyGroup):
    collisionStartX: FloatProperty(name="Collision Grid Start X",
                              update=lambda s,c: update_prop(s, c, "collisionStartX"))
    collisionStartY: FloatProperty(name="Collision Grid Start Y",
                              update=lambda s,c: update_prop(s, c, "collisionStartY"))
    collisionStepX: FloatProperty(name="Collision Grid Step X",
                              update=lambda s,c: update_prop(s, c, "collisionStepX"))
    collisionStepY: FloatProperty(name="Collision Grid Step Y",
                              update=lambda s,c: update_prop(s, c, "collisionStepY"))
    collisionStepCountX: IntProperty(name="Collision Grid Step Count X",
                              update=lambda s,c: update_prop(s, c, "collisionStepCountX"))
    collisionStepCountY: IntProperty(name="Collision Grid Step Count Y",
                              update=lambda s,c: update_prop(s, c, "collisionStepCountY"))
    animId: IntProperty(name="Animation ID",
                              update=lambda s,c: update_prop(s, c, "animId"))
    initPlaying: EnumProperty(name="Initial Anim State", 
                              update=lambda s,c: update_prop(s, c, "initPlaying"),
                              items=[('0','Paused',''),
                                     ('1','Playing',''),
                                     ('2','Reverse',''),
                                     ('3','Fast Forward',''),
                                     ('4','Fast Reverse',''),],
                              default='1')
    loopAnim: EnumProperty(name="Animation Type",
                            update=lambda s,c: update_prop(s, c, "loopAnim"),
                            items=[('0','Play Once Animation',''),
                                   ('1','Looping Animation',''),
                                   ('2','Seesaw','')],
                            default='1')
    animLoopTime: FloatProperty(name="Loop Time (s)",
                              update=lambda s,c: update_prop(s, c, "animLoopTime"))
    conveyorX: FloatProperty(name="Conveyor X Force",
                              update=lambda s,c: update_prop(s, c, "conveyorX"))
    conveyorY: FloatProperty(name="Conveyor Y Force",
                              update=lambda s,c: update_prop(s, c, "conveyorY"))
    conveyorZ: FloatProperty(name="Conveyor Z Force",
                              update=lambda s,c: update_prop(s, c, "conveyorZ"))
    seesawSensitivity: FloatProperty(name="Seesaw Sensitivity",
                              update=lambda s,c: update_prop(s, c, "seesawSensitivity"))
    seesawFriction: FloatProperty(name="Seesaw Friction",
                              update=lambda s,c: update_prop(s, c, "seesawFriction"))
    seesawSpring: FloatProperty(name="Seesaw Spring",
                              update=lambda s,c: update_prop(s, c, "seesawSpring"))
    texScrollUSpeed:   FloatProperty(name="Horizontal Tex. Scroll Speed",
                              update=lambda s,c: update_prop(s, c, "texScrollUSpeed"),
                              default=-1.0)
    texScrollVSpeed:   FloatProperty(name="Vertical Tex. Scroll Speed",
                              update=lambda s,c: update_prop(s, c, "texScrollVSpeed"),
                              default=-1.0)
    exportTimestep: IntProperty(name="Export Timestep",
                              update=lambda s,c: update_prop(s, c, "exportTimestep"))
    collisionTriangleFlag: EnumProperty(name="Collision Triangle Flag",
                              update=lambda s,c: update_prop(s, c, "collisionTriangleFlag"),
                              items=lambda s,c: get_collision_triangle_list(s, c))

# Properties for non-stage models (background, foreground objects)
class AltModelProperties(bpy.types.PropertyGroup):
    animLoopTime: FloatProperty(name="Loop Time (s)",
                              update=lambda s,c: update_prop(s, c, "animLoopTime"))
    meshType:      IntProperty(name="Model Type",
                              update=lambda s,c: update_prop(s, c, "meshType"))
    texScrollUSpeed:   FloatProperty(name="Horizontal Tex. Scroll Speed",
                              update=lambda s,c: update_prop(s, c, "texScrollUSpeed"))
    texScrollVSpeed:   FloatProperty(name="Vertical Tex. Scroll Speed",
                              update=lambda s,c: update_prop(s, c, "texScrollVSpeed"))
# Properties for stage models
class StageModelProperties(bpy.types.PropertyGroup):
    cast_shadow: BoolProperty(name="Casts Shadow",
                              update=lambda s,c: update_prop(s, c, "cast_shadow"))
    receive_shadow: BoolProperty(name="Receives Shadow",
                              update=lambda s,c: update_prop(s, c, "receive_shadow"))
    unk3: BoolProperty(name="Unknown Flag 3",
                              update=lambda s,c: update_prop(s, c, "unk3"))
    transparencyA: BoolProperty(name="Transparency Type A",
                              update=lambda s,c: update_prop(s, c, "transparencyA"))
    transparencyB: BoolProperty(name="Transparency Type B",
                              update=lambda s,c: update_prop(s, c, "transparencyB"))
    unk6: BoolProperty(name="Unknown Flag 6",
                              update=lambda s,c: update_prop(s, c, "unk6"))
    unk7: BoolProperty(name="Unknown Flag 7",
                              update=lambda s,c: update_prop(s, c, "unk7"))
    unk8: BoolProperty(name="Unknown Flag 8",
                              update=lambda s,c: update_prop(s, c, "unk8"))

# Properties for goals
class GoalProperties(bpy.types.PropertyGroup):
    cast_shadow: BoolProperty(name="Casts Shadow",
                              update=lambda s,c: update_prop(s, c, "cast_shadow"))

# Properties for starting positions
class StartProperties(bpy.types.PropertyGroup):
    playerID: IntProperty(name="Player #",
                              update=lambda s,c: update_prop(s, c, "playerID"))

# Properties for wormholes
class WormholeProperties(bpy.types.PropertyGroup):
    whId: IntProperty(name="Wormhole ID",
                              update=lambda s,c: update_prop(s, c, "whId"))
    linkedId: IntProperty(name="Linked ID",
                              update=lambda s,c: update_prop(s, c, "linkedId"))
    linkedObject: PointerProperty(name="Linked Object",
                              type=bpy.types.Object,
                              update=lambda s,c: update_prop(s, c, "linkedObject"))

# Properties for switches
class SwitchProperties(bpy.types.PropertyGroup):
    linkedId: IntProperty(name="Linked ID",
                              update=lambda s,c: update_prop(s, c, "linkedId"))
    linkedObject: PointerProperty(name="Linked Object",
                              type=bpy.types.Object,
                              update=lambda s,c: update_prop(s, c, "linkedObject"))
