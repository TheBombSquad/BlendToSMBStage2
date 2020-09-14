import bpy
import bgl
import enum
import os
import copy
import subprocess
import sys

from . import statics, descriptors, stage_object_drawing
from bpy.props import BoolProperty, PointerProperty, EnumProperty
from enum import Enum
from sys import platform

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
        for desc in descriptors.descriptors_all:
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
            
            # Properties for selected item
            for key in obj.keys():
                friendly_name = str(key)
                try:
                    rna_ui_key = obj['_RNA_UI'][key]
                    property_type = rna_ui_key['type']
                    if 'name' in rna_ui_key.keys(): 
                        friendly_name = rna_ui_key['name']
                except KeyError:
                    pass
                else:   
                    if property_type != 'int':
                        sanitized_name = key[1::]
                        for bool_prop in obj.stage_object_properties:
                            if bool_prop.name == sanitized_name:
                                properties.prop(bool_prop, sanitized_name)
                                break

                if key[0] !=  '_' :
                    custom_prop = "[\"" +  key + "\"]"
                    properties.prop(obj, custom_prop, text=friendly_name)
        
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
                for desc in descriptors.descriptors_all:
                    if desc.get_object_name() in obj.name:
                        desc.render(obj)
        # Draw fallout plane
        if bpy.context.scene.draw_falloutProp:
            FALLOUT_COLOR = (0.96, 0.26, 0.21, 0.3)
            #lineWidth = [(6, stage_object_drawing.COLOR_BLACK), (2, stage_object_drawing.COLOR_RED)]
            #for width, color in lineWidth:
                #bgl.glLineWidth(width)
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

# TODO: Replace with the more efficient implementation of this
# This is a really hacky way to get boolean custom properties to show up as checkboxes
def update_prop(self, context):
    prop_name = '_' + self.name
    context.active_object[prop_name] = self[self.name]

def update_linked_prop(self, context):
    prop_name = "_" + self.name
    linked_object = self[self.name]
    context.active_object[prop_name] = linked_object

    if "whId" in context.active_object.keys():
        context.active_object["linkedId"] = linked_object["whId"] 
    else:
        context.active_object["linkedId"] = linked_object["animId"]

class StageObjectPropertyProxy(bpy.types.PropertyGroup):
    cast_shadow: BoolProperty(name="Casts Shadow", update=update_prop)
    receive_shadow: BoolProperty(name="Receives Shadow", update=update_prop)
    unk3: BoolProperty(name="Unknown Flag 3", update=update_prop)
    transparencyA: BoolProperty(name="Transparency Type A", update=update_prop)
    transparencyB: BoolProperty(name="Transparency Type B", update=update_prop)
    unk6: BoolProperty(name="Unknown Flag 6", update=update_prop)
    unk7: BoolProperty(name="Unknown Flag 7", update=update_prop)
    unk8: BoolProperty(name="Unknown Flag 8", update=update_prop)
    initPlaying: EnumProperty(name="Initial Anim State", 
            update=update_prop,
            items=[('0','Paused',''),
                ('1','Playing',''),
                ('2','Reverse',''),
                ('3','Fast Forward',''),
                ('4','Fast Reverse',''),],
            default='1'
    )
    loopAnim: EnumProperty(name="Animation Type",
            update=update_prop,
            items=[('0','Play Once Animation',''),
                ('1','Looping Animation',''),
                ('2','Seesaw','')],
            default='1'
    )
    linkedObject: PointerProperty(name="Linked", type=bpy.types.Object, update=update_linked_prop)
