import bpy
import bgl
import bmesh
import enum
import os
import copy
import subprocess
import sys
import mathutils

from . import statics, stage_object_drawing, generate_config
from .descriptors import descriptors, descriptor_item_group, descriptor_model_stage, descriptor_track_path
from bpy.props import BoolProperty, PointerProperty, EnumProperty, FloatProperty, IntProperty
from enum import Enum
from sys import platform

if platform == "linux" or platform == "linux2":
    from lxml import etree
else:
    import xml.etree.ElementTree as etree

class OBJECT_OT_add_external_objects(bpy.types.Operator):
    bl_idname = "object.add_external_objects"
    bl_label = "Add External Objects"
    bl_description = "Add external objects, such as those found in background files"

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

class OBJECT_OT_confirm_add_external_objects(bpy.types.Operator):
    bl_idname = "object.confirm_add_external_objects"
    bl_label = "Confirm Add External Objects"
    
    objects: bpy.props.StringProperty()

    def execute(self, context):
        obj_list = self.objects.split("\n")
        for obj in obj_list:
            if obj == "":
                continue

            bpy.ops.object.create_new_empty_and_select("INVOKE_DEFAULT", name="[EXT:{}]".format(str(obj)))
        return  {'FINISHED'}

class OBJECT_OT_convert_selected(bpy.types.Operator):
    bl_idname = "object.convert_selected"
    bl_label = "Convert Selected Item"
    bl_description = "Converts selected item to a specified type"
    bl_options = {'UNDO'}
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

class OBJECT_OT_create_new_empty_and_select(bpy.types.Operator):
    bl_idname = "object.create_new_empty_and_select"
    bl_label = "Create New Empty And Select"
    bl_description = "Creates a new empty object of a specified name"
    bl_options = {'UNDO'}
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
        return {'FINISHED'}

# Panels for the UI
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

class VIEW3D_PT_2_stage_object_panel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_2_stage_object_panel"
    bl_label = "Add Stage Objects"
    bl_category = "Blend2SMB"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        game_mode = context.scene.stage_game_mode

        layout = self.layout
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

        external_objects = layout.operator("object.add_external_objects", text="External Objects")

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
                
class VIEW3D_PT_4_export_panel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_4_export_panel"
    bl_label = "Export"
    bl_category = "Blend2SMB"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "stage_game_mode")
        layout.prop(context.scene, "export_timestep")
        layout.prop(context.scene, "export_value_round")
        layout.prop(context.scene, "export_time_round")
        layout.prop(context.scene, "export_config_path")
        layout.prop(context.scene, "export_model_path")
        layout.prop(context.scene, "export_gma_path")
        layout.prop(context.scene, "export_tpl_path")
        layout.prop(context.scene, "export_raw_stagedef_path")
        layout.prop(context.scene, "export_stagedef_path")
        layout.prop(context.scene, "auto_path_names")
        layout.operator("object.generate_config", text="Generate Config")
        layout.operator("object.export_obj", text="Export OBJ")
        layout.operator("object.export_gmatpl", text="Export GMA/TPL")
        export_lz_raw = layout.operator("object.export_stagedef", text="Export LZ.RAW")
        export_lz_raw.compressed = False;
        export_lz = layout.operator("object.export_stagedef", text="Export LZ")
        export_lz.compressed = True;

class VIEW3D_PT_5_settings(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_5_settings"
    bl_label = "Settings"
    bl_category = "Blend2SMB"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "falloutProp")
        layout.operator("view3d.draw_stage_objects")
        layout.prop(context.scene, "draw_stage_objects")
        layout.prop(context.scene, "draw_falloutProp")
        layout.prop(context.scene, "draw_collision_grid")
        layout.operator("object.set_backface_culling")
        layout.prop(context.scene, "optimize_keyframes")

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

def draw_callback_3d(self, context):
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glEnable(bgl.GL_DEPTH_TEST)
    if context.scene.draw_stage_objects:
        # Draw objects
        for obj in bpy.data.objects:
            if obj.visible_get():
                for desc in descriptors.descriptors:
                    if desc.get_object_name() in obj.name:
                        desc.render(obj)
        # Draw fallout plane
        if bpy.context.scene.draw_falloutProp:
            FALLOUT_COLOR = (0.96, 0.26, 0.21, 0.3)
            stage_object_drawing.draw_grid(-512, -512, 32, 32, 32, 32, bpy.context.scene.falloutProp, FALLOUT_COLOR)

def autoPathNames(self, context):
    if context.scene.auto_path_names:
        default_filename = "//" + os.path.splitext(os.path.basename(bpy.context.blend_data.filepath))[0]
        context.scene.export_config_path = default_filename + ".xml"
        context.scene.export_model_path = default_filename + ".obj"
        context.scene.export_gma_path = default_filename + ".gma"
        context.scene.export_tpl_path = default_filename + ".tpl"
        context.scene.export_raw_stagedef_path = default_filename + ".lz.raw"
        context.scene.export_stagedef_path = default_filename + ".lz"

class OBJECT_OT_generate_track_path(bpy.types.Operator):
    bl_idname = "object.generate_track_path"
    bl_label = "Generate Track Path from Selected"
    bl_descriptions = "Generates a track path from the selected faces."

    def execute(self, context):
        obj = bpy.context.active_object
        mesh = bmesh.from_edit_mesh(obj.data)

        # TODO: Calculate this mathemagically instead of relying on selection order
        selected_faces = list(dict.fromkeys(mesh.select_history)) 

        # Track paths must begin and end at the same point, so it's added at the start
        selected_faces.append(selected_faces[0])

        median_points = [face.calc_center_median() for face in selected_faces]

        #point_kdtree = mathutils.kdtree.KDTree(len(median_points))

        #for i, point in enumerate(median_points):
        #    kd.insert(point.co, i)

        #kd.balance()

        #sorted_vertex_list = [active_median]

        #current_median = active_median
        #current_attempts = 0
        #while current_median not in sorted_vertex_list:
        #    if current_median == active_median:
        #        sorted_vertex_list.append(active_median)

        path_curve_data = bpy.data.curves.new('path', type='CURVE')
        path_curve_data.dimensions = '3D'

        path_spline = path_curve_data.splines.new('POLY')
        path_spline.points.add(len(median_points)-1)
        
        for i, point in enumerate(median_points):
            print("Added point " + str(point))
            path_spline.points[i].co = (point[0], point[1], point[2], 1)

        path_curve = bpy.data.objects.new('[PATH] Race Track Path', path_curve_data)
        descriptor_track_path.DescriptorTrackPath.construct(path_curve)
        context.collection.objects.link(path_curve)
        path_curve.select_set(True)
        return {'FINISHED'}


class OBJECT_OT_set_backface_culling(bpy.types.Operator):
    bl_idname = "object.set_backface_culling"
    bl_label = "Set Backface Culling"
    bl_description = "Sets the backface culling attribute on all materials"

    def execute(self, context):
        for mat in bpy.data.materials:
            if hasattr(mat, 'use_backface_culling'):
                mat.use_backface_culling = True

        return {'FINISHED'}

class OBJECT_OT_export_obj(bpy.types.Operator):
    bl_idname = "object.export_obj"
    bl_label = "Export OBJ"
    bl_description = "Clean up model and export OBJ to the selected path"

    def execute(self, context):
        origin_frame = context.scene.frame_start

        # Cleans up models to fix common crashes
        print("Cleaning up meshes...")
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
        bpy.ops.export_scene.obj(
                filepath = bpy.path.abspath(context.scene.export_model_path),
                use_triangles=True,
                path_mode="RELATIVE",
            )

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

class OBJECT_OT_export_gmatpl(bpy.types.Operator):
    bl_idname = "object.export_gmatpl"
    bl_label = "Export OBJ"
    bl_description = "Export an OBJ, then call GxModelViewer to export a GMA/TPL to the specified path"
    def execute(self, context):
        bpy.ops.object.export_obj("INVOKE_DEFAULT")
        obj_path = bpy.path.abspath(context.scene.export_model_path)
        gma_path = bpy.path.abspath(context.scene.export_gma_path)
        tpl_path = bpy.path.abspath(context.scene.export_tpl_path)
        gx_path = bpy.utils.script_path_user() + "/addons/BlendToSMBStage2/GxUtils/GxModelViewer.exe"

        subprocess.run([gx_path, 
                        "-importObjMtl", obj_path,
                        "-removeUnusedTextures",
                        "-exportGma", gma_path,
                        "-exportTpl", tpl_path])
        
        return {'FINISHED'}

class OBJECT_OT_export_stagedef(bpy.types.Operator):
    bl_idname = "object.export_stagedef"
    bl_label = "Export OBJ"
    bl_description = "Export an OBJ, then call Workshop 2 to export a LZ/LZ.RAW to the specified path."

    compressed: bpy.props.BoolProperty(default=True)
    def execute(self, context):
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

class OBJECT_OT_generate_config(bpy.types.Operator):
    bl_idname = "object.generate_config"
    bl_label = "Generate Config"
    bl_description = "Generate .XML file for config export"

    def execute(self, context):
        print("Generating config...")

        root = etree.Element("superMonkeyBallStage", version="1.2.0")
        
        # OBJ file path
        modelImport = etree.SubElement(root, "modelImport")
        modelImport.text = context.scene.export_model_path

        # Fallout plane height
        etree.SubElement(root, "falloutPlane", y=str(context.scene.falloutProp))

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

def update_prop(self, context, prop):
    if context.active_object is not None:
        prop_value = getattr(self, prop)

        # Cast string properties to ints (for enums)
        if isinstance(prop_value, str):
            prop_value = int(prop_value)

        context.active_object[prop] = prop_value

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
    collisionTriangleFlag: IntProperty(name="Collision Triangle Flag",
                              update=lambda s,c: update_prop(s, c, "collisionTriangleFlag"))

# Properties for non-stage models (background, foreground objects)
class AltModelProperties(bpy.types.PropertyGroup):
    animLoopTime: FloatProperty(name="Loop Time (s)",
                              update=lambda s,c: update_prop(s, c, "animLoopTime"))
    meshType:      IntProperty(name="Model Type",
                              update=lambda s,c: update_prop(s, c, "meshType"))
    texScrollUSpeed:   FloatProperty(name="Horizontal Tex. Scroll Speed",
                              update=lambda s,c: update_prop(s, c, "texScrollUSpeed"))
    texScrollVSpeedol:   FloatProperty(name="Vertical Tex. Scroll Speed",
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
    playerId: IntProperty(name="Player #",
                              update=lambda s,c: update_prop(s, c, "playerId"))

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
