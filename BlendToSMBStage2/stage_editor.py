import itertools
import stat
import bpy
import bmesh
import os
import copy
import subprocess
import sys
import random
import math
import re
import locale
import gpu

from . import statics, stage_object_drawing, generate_config, dimension_dict

from .descriptors import descriptors, descriptor_item_group, descriptor_model_stage, descriptor_track_path, descriptor_model_bg, descriptor_model_fg
from bpy.props import BoolProperty, PointerProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty
from sys import platform
from mathutils import Vector, Matrix

import xml.etree.ElementTree as etree
import xml.dom.minidom as minidom

# To handle encoding shenanigans when we run GX/WS as subprocesses
if platform == "win32":
    from ctypes import windll

# Operator for adding external background objects
class OBJECT_OT_add_external_objects(bpy.types.Operator):
    bl_idname = "object.add_external_objects"
    bl_label = "Add External Objects"
    bl_description = "Add external objects, such as those found in background files"
    bl_options = {'UNDO'} 

    def execute(self, context):
        # Create the text block
        textblock = bpy.data.texts.get("blendtosmbstage:addexternalobjects")
        if textblock is None:
            textblock = bpy.data.texts.new("blendtosmbstage:addexternalobjects")

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
        bpy.ops.text.jump(line=1)  #Scroll to the top

        return {'FINISHED'}

# Operator that actually adds the listed external objects
class OBJECT_OT_confirm_add_external_objects(bpy.types.Operator):
    bl_idname = "object.confirm_add_external_objects"
    bl_label = "Confirm Add External Objects"
    bl_options = {'UNDO'} 
    
    objects: bpy.props.StringProperty()

    def execute(self, context):
        obj_list = self.objects.split("\n")
        for obj in obj_list:
            if obj == "":
                continue

            bpy.ops.object.create_new_empty_and_select("INVOKE_DEFAULT", name="[EXT:{}]".format(str(obj)))
        return {'FINISHED'}

# Operator for 'converting' the active object to a specific type
class OBJECT_OT_convert_selected(bpy.types.Operator):
    bl_idname = "object.convert_selected"
    bl_label = "Convert Selected Item"
    bl_description = "Converts selected item to a specified type"
    bl_options = {'UNDO'} 

    prefix: bpy.props.StringProperty(default="[]")

    def execute(self, context):
        selected = bpy.context.active_object
        bracket_re = re.compile(r"\[[^\]]*]")
        no_replace = ["[MODEL]", "[NODISP]", "[MIR]", "[NOCOLI]"]

        # Set rotation mode
        #selected.rotation_mode = 'XZY'

        # Clear active properties
        if self.prefix not in no_replace:
            for key in list(selected.keys()):
                del selected[key]

        # Remove existing prefixes
        if bracket_re.match(selected.name) and self.prefix not in no_replace:
            cleaned_name = bracket_re.sub(self.prefix, "")
            selected.name = cleaned_name
            if selected.data is not None and selected.data.name is not None:
                selected.data.name = cleaned_name


        # Append new prefix
        new_name = f"{self.prefix} {selected.name}"
        selected.name = new_name
        if selected.data is not None and selected.data.name is not None:
            selected.data.name = new_name

        # Construct the newly converted object
        for desc in descriptors.descriptors:
            if selected.name.startswith(desc.get_object_name()): 
                desc.construct(selected)

        updateUIProps(selected)

        return {'FINISHED'}

# Operator for creating a new empty with a specified name and setting up its properties
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
        updateUIProps(newEmpty)
        return {'FINISHED'}

# Operator for duplicating collision grid data
class OBJECT_OT_collision_grid_duplicate(bpy.types.Operator):
    bl_idname = "object.collision_grid_duplicate"
    bl_label = "Copy Collision Grid to All Selected"
    bl_description = "Applies the collision grid dimensions of the active item group to all selected item groups."
    bl_options = {'UNDO'}

    def execute(self, context):
        active_ig = bpy.context.active_object
        for obj in [ig for ig in ((obj if ("[IG]" in obj.name) else None) for obj in bpy.context.selected_objects) if ig]:
            obj["collisionStartX"] = active_ig["collisionStartX"]
            obj["collisionStartY"] = active_ig["collisionStartY"]
            obj["collisionStepX"] = active_ig["collisionStepX"] 
            obj["collisionStepY"] = active_ig["collisionStepY"]
            obj["collisionStepCountX"] = active_ig["collisionStepCountX"]
            obj["collisionStepCountY"] = active_ig["collisionStepCountY"]

            # Update visual property preview TODO: Don't rely on this having to be implemented manually
            obj.item_group_properties.collisionStartX = obj["collisionStartX"]
            obj.item_group_properties.collisionStartY = obj["collisionStartY"]
            obj.item_group_properties.collisionStepX = obj["collisionStepX"]
            obj.item_group_properties.collisionStepY = obj["collisionStepY"]
            obj.item_group_properties.collisionStepCountX = obj["collisionStepCountX"]
            obj.item_group_properties.collisionStepCountY = obj["collisionStepCountY"]

        return {'FINISHED'}


# Operator for subdividing a collision grid
class OBJECT_OT_collision_grid_subdivide(bpy.types.Operator):
    bl_idname = "object.collision_grid_subdivide"
    bl_label = "Subdivide Collision Grid"
    bl_description = "Subdivides the collision grid for an item group."
    bl_options = {'UNDO'}

    unsubdivide: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        obj = bpy.context.active_object

        if "collisionStartX" in obj.keys():
            if not self.unsubdivide:
                obj["collisionStepX"] /= 2
                obj["collisionStepY"] /= 2
                obj["collisionStepCountX"] *= 2
                obj["collisionStepCountY"] *= 2
            elif self.unsubdivide and (obj["collisionStepCountX"] > 1 and obj["collisionStepCountY"] > 1):
                obj["collisionStepX"] *= 2
                obj["collisionStepY"] *= 2
                obj["collisionStepCountX"] //= 2
                obj["collisionStepCountY"] //= 2

        # Update visual property preview TODO: Don't rely on this having to be implemented manually
        obj.item_group_properties.collisionStepX = obj["collisionStepX"]
        obj.item_group_properties.collisionStepY = obj["collisionStepY"]
        obj.item_group_properties.collisionStepCountX = obj["collisionStepCountX"]
        obj.item_group_properties.collisionStepCountY = obj["collisionStepCountY"]

        return {'FINISHED'}

# Operator for fitting a collision grid to geometry
class OBJECT_OT_collision_grid_fit(bpy.types.Operator):
    bl_idname = "object.collision_grid_fit"
    bl_label = "Fit Collision Grid"
    bl_description = "Fits the collision grid for an item group to the geometry of its models. Does not adjust step count, use the subdivision tool to assign the step count as per the complexity."
    bl_options = {'UNDO', 'REGISTER'}

    pos: FloatVectorProperty(name="Position", size=2) 
    dimensions: FloatVectorProperty(name="Dimensions", min=0.0, size=2)
    margin: FloatProperty(name="Margin (%)", default=50, soft_max=200, soft_min=0, subtype="PERCENTAGE")
    auto_fit: BoolProperty(name="Auto-fit", default=True)

    def execute(self, context):
        active_obj = bpy.context.active_object

        if self.auto_fit:
            total_max_x = None
            total_min_x = None
            total_max_y = None
            total_min_y = None

            # Get the min/max X/Y worldspace coordinates for the vertices of the IG and its children
            obj_check_list = [active_obj, *active_obj.children]
            for obj in obj_check_list:
                # Handle meshes
                if obj.data is not None:
                    bm = bmesh.new()
                    bm.from_mesh(obj.data)

                    obj_world_mtx = obj.matrix_world
                    obj_world_verts = [(obj_world_mtx @ vert.co) for vert in bm.verts]
                    obj_x_verts = [vert[0] for vert in obj_world_verts]
                    obj_y_verts = [vert[1] for vert in obj_world_verts]

                    max_x = max(obj_x_verts)
                    min_x = min(obj_x_verts)
                    max_y = max(obj_y_verts)
                    min_y = min(obj_y_verts)

                    bm.free()

                # If the object has no data (is a placeable), we assume it to be 5m x 5m
                else:
                    obj_pos = obj.matrix_world.to_translation()
                    max_x = obj_pos.x + 5 
                    min_x = obj_pos.x - 5 
                    max_y = obj_pos.y + 5
                    min_y = obj_pos.y - 5

                if (total_max_x is None) or (max_x > total_max_x): total_max_x = max_x
                if (total_min_x is None) or (min_x < total_min_x): total_min_x = min_x
                if (total_max_y is None) or (max_y > total_max_y): total_max_y = max_y
                if (total_min_y is None) or (min_y < total_min_y): total_min_y = min_y

            self.dimensions = Vector((
                    (total_max_x-total_min_x), 
                    (total_max_y-total_min_y)
                    ))

            self.pos = Vector((
                     total_min_x - (self.dimensions[0]*(0.5*self.margin/100)), 
                     total_max_y + (self.dimensions[1]*(0.5*self.margin/100)) 
                    ))

            self.dimensions = Vector(self.dimensions) * (1+self.margin/100)

        active_obj["collisionStartX"] = self.pos[0]
        active_obj["collisionStartY"] = -1*(self.pos[1])   # Adjust for SMB coordinate system
        active_obj["collisionStepX"] = self.dimensions[0] / active_obj["collisionStepCountX"]
        active_obj["collisionStepY"] = self.dimensions[1] / active_obj["collisionStepCountY"]

        updateUIProps(active_obj)

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
class VIEW3D_PT_2a_stage_object_panel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_2a_stage_object_panel"
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

        if game_mode == 'MONKEY_RACE_2':
            layout.label(text="Add Monkey Race Mechanics")

            new_booster = layout.operator("object.create_new_empty_and_select", text="Booster")
            new_booster.name = "[BOOSTER] Booster"

            new_path = layout.operator("object.generate_track_path", text="Track Path from Selected")

        elif game_mode == 'MONKEY_GOLF_2':
            layout.label(text="Add Monkey Golf Mechanics")

            new_golf_hole = layout.operator("object.create_new_empty_and_select", text="Golf Hole")
            new_golf_hole.name = "[GOLF_HOLE] Golf Hole"


# UI panel for external object creation
class VIEW3D_PT_2b_stage_object_panel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_2b_stage_object_panel"
    bl_label = "Add External Objects"
    bl_category = "Blend2SMB"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout

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

                if '[IG]' in obj.name:
                    properties.label(text="Collision Grid Properties")
                    subdivide_grid = properties.operator("object.collision_grid_subdivide", text="Subdivide Collision Grid")
                    subdivide_grid.unsubdivide = False
                    unsubdivide_grid = properties.operator("object.collision_grid_subdivide", text="Un-subdivide Collision Grid")
                    unsubdivide_grid.unsubdivide = True
                    fit_grid = properties.operator("object.collision_grid_fit", text="Fit Collision Grid")
                    duplicate_grid = properties.operator("object.collision_grid_duplicate", text="Copy Collision Grid to All Selected")

            if '[PATH]' in obj.name:
                make_cpu_paths = properties.operator("object.generate_cpu_paths", text="Make CPU Paths from Selected")

            properties.operator("object.drop_selected_objects", text="Drop Selected Objects")
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
        layout.prop(context.scene, "gx_preset_path")
        layout.prop(context.scene, "auto_path_names")
        layout.label(text="Export Operators")
        layout.operator("object.generate_config", text="Generate Config")
        layout.operator("object.export_obj", text="Export OBJ")
        layout.operator("object.export_gmatpl", text="Export GMA/TPL")
        export_lz_raw = layout.operator("object.export_stagedef", text="Export LZ.RAW")
        export_lz_raw.compressed = False
        export_lz = layout.operator("object.export_stagedef", text="Export LZ")
        export_lz.compressed = True
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
        layout.prop(context.scene, "draw_only_active_collision_grid")
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

# Panel for material modification
class MATERIAL_PT_blend2smb_material(bpy.types.Panel):
    bl_idname = "MATERIAL_PT_blend2smb_material"
    bl_label = "Blend2SMB"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.object.active_material is not None

    def draw(self, context):
        layout = self.layout

        layout.operator("material.mark_unshaded")
        layout.operator("material.mark_twosided")
        layout.operator("material.mark_nofog")
        layout.operator("material.mark_screen")
        layout.operator("material.mark_additive")
        layout.prop(context.material, "mesh_preset")
        layout.prop(context.material, "mat_preset")

        #rgb5a3 (16bit, transp)
        #rgb565 (16bit)
        #rgba8 (24 bit, 8 bit transp)
        
        #i4 (4 bit grey)
        #i8 (8 bit grey)

        #ia4 (4 bit grey, 4 bit transparency)
        layout.label(text="Texture Type")
        cmpr_tex_row = layout.row(align=True)
        cmpr = cmpr_tex_row.operator("material.set_material_flags", text="CMPR (default)")
        cmpr.name = "CMPR"
        cmpr.flag = "TEX"

        rgb_tex_row = layout.row(align=True)
        rgb5a3 = rgb_tex_row.operator("material.set_material_flags", text="RGB5A3")
        rgb5a3.name = "RGB5A3"
        rgb5a3.flag = "TEX"
        rgb565 = rgb_tex_row.operator("material.set_material_flags", text="RGB565")
        rgb565.name = "RGB565"
        rgb565.flag = "TEX"
        rgba8 = rgb_tex_row.operator("material.set_material_flags", text="RGBA8")
        rgba8.name = "RGBA8"
        rgba8.flag = "TEX"

        ia_tex_row=layout.row(align=True)
        i4 = ia_tex_row.operator("material.set_material_flags", text="I4")
        i4.name = "I4"
        i4.flag = "TEX"
        i8 = ia_tex_row.operator("material.set_material_flags", text="I8")
        i8.name = "I8"
        i8.flag = "TEX"
        ia4 = ia_tex_row.operator("material.set_material_flags", text="IA4")
        ia4.name = "IA4"
        ia4.flag = "TEX"

        layout.label(text="Texture Flags")
        scroll = layout.operator("material.set_material_flags", text="Texture Scroll")
        scroll.name = "SCROLL"
        scroll.flag = "MATFLAG"
        mask = layout.operator("material.set_material_flags", text="Alpha Masking")
        mask.name = "MASK"
        mask.flag = "MATFLAG"

# TODO: We really should make these checkboxes at some point, instead of just buttons that append text on every click
# Operator for marking a material as unshaded
class MATERIAL_OT_mark_unshaded(bpy.types.Operator):
    bl_idname = "material.mark_unshaded"
    bl_label = "Mark as Unshaded"
    bl_options = {'UNDO'}

    def execute(self, context):
        mat = context.material 
        if mat.use_nodes:
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links

            material_output_node = None
            image_texture_node = None
            principled_node = None

            for node in nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled_node = node
                elif node.type =='OUTPUT_MATERIAL':
                    material_output_node = node
                elif node.type == 'TEX_IMAGE':
                    image_texture_node = node

            # Convert Principled BSDF to Emission
            if principled_node is not None:
                print("Converting material " + mat.name + " from principled BSDF to emission")
                nodes.remove(principled_node)
                emission_node = nodes.new("ShaderNodeEmission")
                links.new(material_output_node.inputs['Surface'], emission_node.outputs['Emission'])
                links.new(emission_node.inputs['Color'], image_texture_node.outputs['Color'])
                mat.name = "[UNSHADED] " + mat.name

        return {'FINISHED'}
        
# Operator for marking a material as two-sided
class MATERIAL_OT_mark_twosided(bpy.types.Operator):
    bl_idname = "material.mark_twosided"
    bl_label = "Mark as Two-Sided"
    bl_options = {'UNDO'}

    def execute(self, context):
        mat = context.material 
        mat.name = "[TWOSIDED] " + mat.name

        return {'FINISHED'}
        
# Operator for marking a material as unaffected by fog
class MATERIAL_OT_mark_nofog(bpy.types.Operator):
    bl_idname = "material.mark_nofog"
    bl_label = "Mark as Unaffected by Fog"
    bl_options = {'UNDO'}

    def execute(self, context):
        mat = context.material 
        mat.name = "[NOFOG] " + mat.name

        return {'FINISHED'}
        
# Operator for marking a material as screen blend
class MATERIAL_OT_mark_screen(bpy.types.Operator):
    bl_idname = "material.mark_screen"
    bl_label = "Mark as Screen Blend"
    bl_options = {'UNDO'}

    def execute(self, context):
        mat = context.material 
        mat.name = "[SCREEN] " + mat.name

        return {'FINISHED'}
        
# Operator for marking a material as additive blend
class MATERIAL_OT_mark_additive(bpy.types.Operator):
    bl_idname = "material.mark_additive"
    bl_label = "Mark as Additive Blend"
    bl_options = {'UNDO'}

    def execute(self, context):
        mat = context.material 
        mat.name = "[ADDITIVE] " + mat.name

        return {'FINISHED'}
        
# Operator for setting texture type of a material
class MATERIAL_OT_set_material_flags(bpy.types.Operator):
    bl_idname = "material.set_material_flags"
    bl_label = "Set Texture Type"
    bl_description = "Sets the material flags of the selected material."
    bl_options = {'UNDO'}
    
    name: bpy.props.StringProperty(default="CMPR")
    flag: bpy.props.StringProperty(default="TEX")

    def execute(self, context):
        mat = context.material

        # Check if the flag is "TEX" and if the material name contains the flag
        if self.flag == "TEX" and f"[{self.flag}_" in mat.name:
            # Replace the part of the name following the flag
            mat.name = re.sub(fr"(?<={self.flag}_)[^\]]*", self.name, mat.name)
        elif self.flag != "TEX":
            # Append a new flag and name if the flag is not "TEX"
            mat.name = f"[{self.flag}_{self.name}] {mat.name}"
        else:
            # If the flag is "TEX" but not found in the name, append the flag and name
            mat.name = f"[{self.flag}_{self.name}] {mat.name}"

        return {'FINISHED'}
# Callback function for drawing stage objects, as well as the fallout plane grid
def draw_callback_3d(self, context):
    gpu.state.blend_set("ALPHA")
    gpu.state.depth_test_set("LESS_EQUAL")

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
                if ui_prop in obj.keys():
                    if getattr(group, ui_prop) is not None:
                        val = type(getattr(group, ui_prop))(obj[ui_prop])
                        if getattr(group, ui_prop) != val:
                            setattr(group, ui_prop, val)
                else:
                    print("Property " + ui_prop + " not found in " + obj.name)

# Operator for auto-generating keyframes for a UV warp modifier to preview texture scroll
class OBJECT_OT_generate_texture_scroll_preview(bpy.types.Operator):
    bl_idname = "object.generate_texture_scroll_preview"
    bl_label = "Generate Texture Scroll Preview"
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
                v_end = -(obj["texScrollVSpeed"] / 60) * frame_end

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
    bl_options = {'UNDO'} 

    def execute(self, context):
        obj = bpy.context.active_object
        mesh = bmesh.from_edit_mesh(obj.data)

        # TODO: Calculate this mathemagically instead of relying on selection order
        selected_faces = list(dict.fromkeys(mesh.select_history)) 

        # Track paths must begin and end at the same point, so we append the first face to the end
        selected_faces.append(selected_faces[0])

        # Track path keyframes are generated from the median point of each keyframe
        median_points = [face.calc_center_median() for face in selected_faces]

        if len(median_points) > 101:
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
        context.collection.objects.link(path_curve)
        path_curve.data.transform(obj.matrix_world)
        path_curve.matrix_world = Matrix()

        return {'FINISHED'}

# Operator for generating CPU paths based on a player track path
class OBJECT_OT_generate_cpu_paths(bpy.types.Operator):
    bl_idname = "object.generate_cpu_paths"
    bl_label = "Generate CPU Paths"
    bl_description = "Generates 7 CPU paths for the selected track path"
    bl_options = {'UNDO'} 

    def execute(self, context):
        path = bpy.context.active_object
        copies = 0
        while copies < 7:
            path_dupe = path.copy()
            path_dupe.data = path.data.copy()
            path_dupe["playerID"] = copies+2

            # CPU paths are 0.5 above player paths
            path_dupe.data.transform(Matrix.Translation(Vector((0,0,0.5))))

            context.collection.objects.link(path_dupe)
            copies = copies+1

        return {'FINISHED'}

# Operator for generating an arrangement of 7 CPU player starts
class OBJECT_OT_generate_cpu_starts(bpy.types.Operator):
    bl_idname = "object.generate_cpu_starts"
    bl_label = "Generate CPU Starts"
    bl_description = "Generates 7 CPU starting positions for the selected starting position"
    bl_options = {'UNDO'} 

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

class OBJECT_OT_drop_selected_objects(bpy.types.Operator):
    bl_idname = "object.drop_selected_objects"
    bl_label = "Drop Selected Objects"
    bl_description = "Drops the selected objects to a location 0.5 units above the nearest surface below the object."
    bl_options = {"UNDO"}

    def execute(self, context):
        for object in [obj for obj in context.selected_objects]:
            cast = context.scene.ray_cast(context.view_layer.depsgraph, object.location, Vector((0,0,-1)), distance=1000)
            if cast[0]:
                height = 0.0 

                if "[START]" in object.name or "[BANANA_S]" in object.name:
                    height = 0.5
                elif "[BANANA_B]" in object.name:
                    height = 1.0 
                elif "[SPHERE_COL]" in object.name:
                    height = object.scale.x
                elif "[CYLINDER_COL]" in object.name or "[FALLOUT_VOL]" in object.name:
                    height = object.scale.z/2

                normal = cast[2]
                object.location = cast[1]
                object.location = object.location + normal*height

                face_rotation = Vector.to_track_quat(normal, 'Z')
                object.rotation_euler = face_rotation.to_euler()

        return {'FINISHED'}

# Operator for setting backface culling on all materials of all objects
class OBJECT_OT_set_backface_culling(bpy.types.Operator):
    bl_idname = "object.set_backface_culling"
    bl_label = "Set Backface Culling"
    bl_description = "Sets the backface culling attribute on all materials"
    bl_options = {'UNDO'} 

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
    bl_options = {'UNDO'} 

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

        bg_fg_models = [obj for obj in bpy.context.scene.objects if (obj.name.startswith("[BG]") or obj.name.startswith("[FG]") and (obj.animation_data is not None and obj.animation_data.action is not None))]

        orig_matrix_dict = {}
        orig_pos_rot_scale = [{}, {}, {}]

        for obj in bg_fg_models:
            if obj.animation_data is not None and obj.animation_data.action is not None:
                orig_matrix_dict[obj.name] = copy.copy(obj.matrix_world)
                print("\tMoving object " + obj.name + " to origin for export")
                fcurves = obj.animation_data.action.fcurves
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

        # Oh gosh, more hacky stuff... this lets the unshaded material preview work since only
        # principled BSDF materials get exported by Blender's OBJ exporter
        for mat in bpy.data.materials:
            if mat.use_nodes and "[UNSHADED]" in mat.name:
                nodes = mat.node_tree.nodes
                links = mat.node_tree.links

                material_output_node = None
                image_texture_node = None
                emission_node = None

                for node in nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        continue
                    elif node.type =='OUTPUT_MATERIAL':
                        material_output_node = node
                    elif node.type == 'TEX_IMAGE':
                        image_texture_node = node
                    elif node.type == 'EMISSION':
                        emission_node = node

                # Convert emission to principled BSDF
                if emission_node is not None:
                    print("Converting material " + mat.name + " from emission to principled BSDF")
                    nodes.remove(emission_node)
                    principled_node = nodes.new("ShaderNodeBsdfPrincipled")
                    links.new(material_output_node.inputs['Surface'], principled_node.outputs['BSDF'])
                    links.new(principled_node.inputs['Base Color'], image_texture_node.outputs['Color'])

        bpy.ops.wm.obj_export(
                filepath=bpy.path.abspath(context.scene.export_model_path),
                export_triangulated_mesh=True,
                export_selected_objects=True,
                path_mode="RELATIVE",
            )

        bpy.ops.object.select_all(action='DESELECT')

        # Undoes the hacky thing
        for mat in bpy.data.materials:
            if mat.use_nodes and '[UNSHADED]' in mat.name:
                nodes = mat.node_tree.nodes
                links = mat.node_tree.links

                material_output_node = None
                image_texture_node = None
                principled_node = None

                for node in nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        principled_node = node
                    elif node.type =='OUTPUT_MATERIAL':
                        material_output_node = node
                    elif node.type == 'TEX_IMAGE':
                        image_texture_node = node

                # Convert Principled BSDF to Emission
                if principled_node is not None:
                    print("Converting material " + mat.name + " from principled BSDF to emission")
                    nodes.remove(principled_node)
                    emission_node = nodes.new("ShaderNodeEmission")
                    links.new(material_output_node.inputs['Surface'], emission_node.outputs['Emission'])
                    links.new(emission_node.inputs['Color'], image_texture_node.outputs['Color'])

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
    bl_options = {'UNDO'} 

    def execute(self, context):
        bpy.ops.object.export_obj("INVOKE_DEFAULT")
        obj_path = bpy.path.abspath(context.scene.export_model_path)
        gma_path = bpy.path.abspath(context.scene.export_gma_path)
        tpl_path = bpy.path.abspath(context.scene.export_tpl_path)

        if platform == "linux" or platform == "linux2":
            gx_path = bpy.utils.script_path_user() + "/addons/BlendToSMBStage2/GxUtils/GxModelViewer"
        else:
            gx_path = bpy.utils.script_path_user() + "/addons/BlendToSMBStage2/GxUtils/GxModelViewer.exe"

        preset_path = bpy.path.abspath(context.scene.gx_preset_path)

        args = []
        args.append(gx_path)
        args.append("-setPresetFolder")
        args.append(preset_path)
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

        if not os.path.exists(gx_path):
            self.report({'ERROR'}, "GxModelViewer not found. Ensure you have downloaded BlendToSMBStage2 from the 'Releases' section on GitHub, not from the 'Code' dropdown.")
            return {'CANCELLED'}

        try:
            gx_result = subprocess.run(args, capture_output=True)
        except PermissionError:
            try:
                os.chmod(gx_path, stat.S_IRWXU | stat.S_IROTH | stat.S_IRGRP)  # attempt to set execute permissions for the owner
                gx_result = subprocess.run(args, capture_output=True)
            except:
                self.report({'ERROR'}, f"GxModelViewer does not have the correct permissions to run. \nPlease set executable permissions on:\n{gx_path}")
                return {'CANCELLED'}
        except:
            self.report({'ERROR'}, f"GxModelViewer failed to run. See the console for more details.")
            return {'CANCELLED'}

        
        gx_stdout_bytes = gx_result.stdout

        try:
            gx_stdout_str = gx_stdout_bytes.decode().split('\r\n')
        except UnicodeDecodeError:
            try:
                if sys.platform == 'win32':
                    codepage = f"cp{windll.kernel32.GetConsoleOutputCP()}"
                    gx_stdout_str = gx_stdout_bytes.decode(encoding=codepage).split('\r\n')
                else:
                    gx_stdout_str = gx_stdout_bytes.decode(encoding=locale.getpreferredencoding(False)).split('\r\n')
            except:
                gx_stdout_str = gx_stdout_bytes.decode(errors="replace").split('\r\n')

        errors = [error for error in gx_stdout_str if ("Import Warning" in error) or ("Error" in error)]
        if len(errors) > 0:
            self.report({'ERROR'}, "GxModelViewer warnings/errors occured: " + "\n".join(errors))
        
        print('\n'.join(gx_stdout_str))
        
        return {'FINISHED'}

# Operator for calling Workshop 2 to export the stage config as a .LZ or .LZ.RAW file
class OBJECT_OT_export_stagedef(bpy.types.Operator):
    bl_idname = "object.export_stagedef"
    bl_label = "Export OBJ"
    bl_description = "Export an OBJ, then call Workshop 2 to export a LZ/LZ.RAW to the specified path"
    bl_options = {'UNDO'} 

    compressed: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        bpy.ops.object.export_obj("INVOKE_DEFAULT")
        bpy.ops.object.generate_config("INVOKE_DEFAULT")
        config_path = bpy.path.abspath(context.scene.export_config_path)
        stagedef_path = bpy.path.abspath(context.scene.export_stagedef_path)
        raw_stagedef_path = bpy.path.abspath(context.scene.export_raw_stagedef_path)

        if platform == "linux" or platform == "linux2":
            ws_path = bpy.utils.script_path_user() + "/addons/BlendToSMBStage2/ws2lzfrontend/bin/ws2lzfrontend"
        else:
            ws_path = bpy.utils.script_path_user() + "/addons/BlendToSMBStage2/ws2lzfrontend/ws2lzfrontend.exe"

        if not os.path.exists(ws_path):
            self.report({'ERROR'}, "SMB Workshop 2 executable not found. Ensure you have downloaded BlendToSMBStage2 from the 'Releases' section on GitHub, not from the 'Code' dropdown.")
            return {'CANCELLED'}

        command_args = [ws_path,
                        "-c" + config_path]

        if self.compressed:
            command_args.append("-s" + stagedef_path)
        else:
            command_args.append("-o" + raw_stagedef_path)

        try:
            ws_result = subprocess.run(command_args, capture_output=True)
        except PermissionError:
            try:
                os.chmod(ws_path, stat.S_IRWXU | stat.S_IROTH | stat.S_IRGRP)  # attempt to set execute permissions for the owner
                ws_result = subprocess.run(command_args, capture_output=True)
            except:
                self.report({'ERROR'}, f"SMB Workshop 2 does not have the correct permissions to run. \nPlease set executable permissions on:\n{ws_path}")
                return {'CANCELLED'}
        except:
            self.report({'ERROR'}, f"SMB Workshop 2 failed to run. See the console for more details.")
            return {'CANCELLED'}

        ws_stdout_bytes = ws_result.stdout

        try:
            ws_stdout_str = ws_stdout_bytes.decode().split('\r\n')
        except UnicodeDecodeError:
            try:
                if sys.platform == 'win32':
                    codepage = f"cp{windll.kernel32.GetConsoleOutputCP()}"
                    ws_stdout_str = ws_stdout_bytes.decode(encoding=codepage).split('\r\n')
                else:
                    ws_stdout_str = ws_stdout_bytes.decode(encoding=locale.getpreferredencoding(False)).split('\r\n')

            except:
                ws_stdout_str = ws_stdout_bytes.decode(errors="replace").split('\r\n')

        errors = [error for error in ws_stdout_str if ("Critical" in error) or ("Error" in error) or ("Warning" in error)]
        if len(errors) > 0:
            self.report({'ERROR'}, "Workshop 2 warnings/errors occurred: " + "\n".join(errors))

        print('\n'.join(ws_stdout_str))

        return {'FINISHED'}

# Operator for importing a background from a .XML file
class OBJECT_OT_import_background(bpy.types.Operator):
    bl_idname ="object.import_background"
    bl_label = "Import Background"
    bl_description = "Import background from the specified .XML file."
    bl_options = {'UNDO'}
    
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
            # Converts an XML attribute list from SMB coordinates to Blender coordinates,
            # 'n' is whether or not to negate the Y axis
            convert_from_smb_coords = lambda v, n: Vector((float(v[0]), (-1+int(2*(not n)))*float(v[2]), float(v[1])))

            # Converts an XML attribute list from degrees to radians
            convert_to_radians = lambda v: Vector((math.radians(v[0]), math.radians(v[1]), math.radians(v[2])))

            for i, imported_bg_model in enumerate(list(bg_root)):
                preview_name = imported_bg_model.find('name').text
                preview_pos = convert_from_smb_coords(list(imported_bg_model.find('position').attrib.values()), True)
                preview_rot = convert_to_radians(convert_from_smb_coords(list(imported_bg_model.find('rotation').attrib.values()), True))
                preview_scale = convert_from_smb_coords(list(imported_bg_model.find('scale').attrib.values()), False)
                preview_dimensions = Vector((1, 1, 1))

                print("Importing model " + str(preview_name))

                if preview_name in dimension_dict.dimensions.keys():
                    preview_dimensions = convert_from_smb_coords(list(dimension_dict.dimensions[preview_name]), False)

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
                            for j, ef1 in enumerate(list(effect)):
                                effect_pos = convert_from_smb_coords([ef1.attrib['posX'], ef1.attrib['posY'], ef1.attrib['posZ']], True)
                                effect_rot = convert_to_radians(convert_from_smb_coords([ef1.attrib['rotX'], ef1.attrib['rotY'], ef1.attrib['rotZ']], True))

                                newEmpty = bpy.data.objects.new("[EXT_IMPORTED_FX:{}:{}:{}]".format(preview_name, i, j), None)
                                newEmpty.location = effect_pos
                                newEmpty.rotation_euler = effect_rot
                                newEmpty.empty_display_type = "ARROWS"
                                bpy.context.collection.objects.link(newEmpty)

                        elif effect.tag == 'effectType2':
                            for j, ef2 in enumerate(list(effect)):
                                effect_pos = convert_from_smb_coords([ef2.attrib['posX'], ef2.attrib['posY'], ef2.attrib['posZ']], True)
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
    bl_options = {'UNDO'}
    
    def execute(self, context):
        print("Generating background/foreground config...")
        
        root = etree.Element("superMonkeyBallBackground", version="1.3.0")

        begin_frame = bpy.context.scene.frame_start
        end_frame = bpy.context.scene.frame_end

        # Curve types for f-curve iteration
        curve_types = ["location", "rotation_euler", "scale"]

        all_curve_types = []
        for ct in curve_types:
            for i in [0, 1, 2]:
                all_curve_types.append((i, ct))

        # Marks objects that don't have keyframes on frame 0, so they can be removed later
        first_frame_added_objs = []

        class ObjExport:
            def __init__(self, obj):
                self.obj = obj
                self.anim_data = generate_config.AnimData()

        fg_export_datas: list[ObjExport] = []
        bg_export_datas: list[ObjExport] = []

        fg_tag = descriptor_model_fg.DescriptorFG.get_object_name()
        bg_tag = descriptor_model_bg.DescriptorBG.get_object_name()

        # Iterate over all top-level objects
        for obj in bpy.context.scene.objects:
            if obj.type not in ["EMPTY", "MESH", "CURVE"]:
                continue
            elif fg_tag in obj.name:
                # Don't export at all otherwise
                if obj.name.startswith(descriptor_model_fg.DescriptorFG.get_object_name()):
                    fg_export_datas.append(ObjExport(obj))
            elif bg_tag in obj.name:
                # Don't export at all otherwise
                if obj.name.startswith(descriptor_model_bg.DescriptorBG.get_object_name()):
                    bg_export_datas.append(ObjExport(obj))

        # Semi-hacky way to get the object's center of rotation to work properly
        # B2SMB1 inadvertently fixed this by baking *all* keyframes
        # This is fixed by adding an initial keyframe on every curve
        # This also fixes weirdness with background and foreground objects
        for exp in itertools.chain(fg_export_datas, bg_export_datas):
            if exp.obj.animation_data is not None and exp.obj.animation_data.action is not None:
                channels_with_frame_zero_keyframes = []
                fcurves = exp.obj.animation_data.action.fcurves

                # Find existing channels with frame 0 keyframes
                for (index, curve_type) in all_curve_types:
                    fcurve = fcurves.find(curve_type, index=index)
                    if fcurve is not None:
                        for keyframe_index in range(len(fcurve.keyframe_points)):
                            if fcurve.keyframe_points[keyframe_index].co[0] == float(begin_frame):
                                channels_with_frame_zero_keyframes.append((index, curve_type))
                                # print(f"Added existing channel {curve_type}[{index}]")
                                break

                # We need to add keyframes on frame 0 if not all channels have keyframes there
                if len(channels_with_frame_zero_keyframes) != 9:
                    first_frame_added_objs.append((exp.obj, channels_with_frame_zero_keyframes))

                # Adds keyframes to needed channels
                for (index, curve_type) in all_curve_types:
                    if (index, curve_type) in channels_with_frame_zero_keyframes: continue
                    exp.obj.keyframe_insert(curve_type, index=index, frame=begin_frame)

                print("\tInserted frame zero keyframe for background/foreground object " + exp.obj.name)

        # Generate initial animation data based on fcurve keyframes
        for exp in itertools.chain(fg_export_datas, bg_export_datas):
            generate_config.generate_keyframe_anim_data(exp.obj, exp.anim_data)

        # Generate per-global-frame animation data
        for frame in range(begin_frame, end_frame + 1):
            bpy.context.scene.frame_set(frame)
            for exp in itertools.chain(fg_export_datas, bg_export_datas):
                generate_config.generate_per_frame_anim_data(exp.obj, exp.anim_data)
        context.scene.frame_set(begin_frame)

        # Generate FG/BG XML
        for fg_exp in fg_export_datas:
            descriptor_model_fg.DescriptorFG.generate_xml_with_anim(root, fg_exp.obj, fg_exp.anim_data)
        for bg_exp in bg_export_datas:
            descriptor_model_bg.DescriptorBG.generate_xml_with_anim(root, bg_exp.obj, bg_exp.anim_data)

        # Import background and foreground objects from a .XML file, if it exists
        obj_names = [obj.name for obj in context.scene.objects]
        bg_path = bpy.path.abspath(context.scene.background_import_path)
        if os.path.exists(bg_path):
            bg = etree.parse(bg_path)
            bg_root = bg.getroot()

            if bg_root.tag != 'superMonkeyBallBackground':
                self.report({'ERROR'}, "Imported background XML not an exported background XML")
                return {'CANCELLED'}

            append_imported_bg_objects(self, context, bg_root, root, obj_names)

        print("Completed, saving...")

        config_string = etree.tostring(root, encoding="unicode")
        config_dom = minidom.parseString(config_string)
        config_string_pretty = config_dom.toprettyxml()

        config_file = open(bpy.path.abspath(context.scene.export_background_path), "w")
        config_file.write(config_string_pretty)
        config_file.close()

        print("Finished generating config")

        # Remove the beginning keyframe channel if it didn't exist prior to it being added
        for (obj, obj_existing_channels) in first_frame_added_objs:
            for (idx, curve_type) in all_curve_types:
                if (idx, curve_type) in obj_existing_channels: continue
                print(f"Deleted frame zero channel {curve_type}[{idx}] for item group {obj.name}")
                obj.keyframe_delete(curve_type, index=idx, frame=begin_frame)

        return {'FINISHED'}

# Function for appending all imported background objects in an XML to a config root
def append_imported_bg_objects(self, context, imported_xml_root, destination_root, obj_names):
    # There's lots of wacky axis swapping going on here so make sure to pay attention to that

    # Converts an XML attribute list from Blender coordinates to SMB coordinates,
    # 'n' is whether or not to negate the Z axis
    convert_to_smb_coords = lambda v, n: Vector((float(v[0]), float(v[2]), (float(-1+int(2*(not n)))*float(v[1]))))

    # Converts an XML attribute list to a vector.
    convert_to_vector = lambda v: Vector((float(v[0]), float(v[1]), float(v[2])))

    # Converts an XML attribute list from radians to degrees
    convert_to_degrees = lambda v: Vector((math.degrees(v[0]), math.degrees(v[1]), math.degrees(v[2])))

    for index, imported_bg_model in enumerate(list(imported_xml_root)):
        xml_name = imported_bg_model.find('name')
        blender_name = "[EXT_IMPORTED:" + xml_name.text + ":" + str(index) + "]"

        print(f"\tExporting imported background object {blender_name}...")

        # If we're using background previews, check to see if the object exists, if it doesn't, it was probably deleted
        if context.scene.background_import_preview:
            if blender_name in obj_names:
                imported_blender_object = context.scene.objects[blender_name]
            else:
                continue
        else:
            imported_blender_object = None

        # Grabs the original pos/rot/scale from the imported XML file
        # The XML background is expected to provide vectors in SMB's coordinate system, so we do not convert here
        orig_pos = convert_to_vector(list(imported_bg_model.find('position').attrib.values()))
        orig_rot = convert_to_vector(list(imported_bg_model.find('rotation').attrib.values()))
        orig_scale = convert_to_vector(list(imported_bg_model.find('scale').attrib.values()))

        # Handles position of imported BG object
        bg_pos = imported_bg_model.find('position').attrib

        # If no empties were imported, we can just rely on the original position
        if imported_blender_object is None:
            current_bg_pos = orig_pos
        else:
            current_bg_pos = convert_to_smb_coords(imported_blender_object.location, True)

        bg_pos['x'] = str(current_bg_pos[0])
        bg_pos['y'] = str(current_bg_pos[1])
        bg_pos['z'] = str(current_bg_pos[2])

        # Handles rotation of imported BG object
        bg_rot = imported_bg_model.find('rotation').attrib

        # If no empties were imported, we can just rely on the original position
        if imported_blender_object is None:
            current_bg_rot = orig_rot
        else:
            current_bg_rot = convert_to_smb_coords(convert_to_degrees(imported_blender_object.rotation_euler), True)

        bg_rot['x'] = str(current_bg_rot[0])
        bg_rot['y'] = str(current_bg_rot[1])
        bg_rot['z'] = str(current_bg_rot[2])

        # Handles scale of imported BG object
        bg_scale = imported_bg_model.find('scale').attrib

        # If no empties were imported, we can just rely on the original position
        # Also special handling for the case of cube empty approximations, which are scaled to their in-game
        # dimensions. Since this effect is achieved through scaling, this is accounted for here, and the scaling
        # is un-done.
        if imported_blender_object is None:
            current_bg_scale = orig_scale
        else:
            bg_dimensions = Vector((1, 1, 1))

            if xml_name.text in dimension_dict.dimensions.keys():
                bg_dimensions = dimension_dict.dimensions[xml_name.text]

            adjusted_scale = Vector((imported_blender_object.scale[0]/bg_dimensions[0],
                                     imported_blender_object.scale[1]/bg_dimensions[2],
                                     imported_blender_object.scale[2]/bg_dimensions[1]))
            current_bg_scale = convert_to_smb_coords(adjusted_scale, False)

        bg_scale['x'] = str(current_bg_scale[0])
        bg_scale['y'] = str(current_bg_scale[1])
        bg_scale['z'] = str(current_bg_scale[2])

        # Handles imported effects
        effects = imported_bg_model.find('effectKeyframes')
        if effects is not None:
            for effect in effects:
                if effect.tag == 'effectType1':
                    for j, ef1 in enumerate(list(effect)):
                        blender_name = "[EXT_IMPORTED_FX:" + xml_name.text + ":" + str(index) + ":" + str(j) + "]"

                        if blender_name in obj_names:
                            effect_obj = context.scene.objects[blender_name]
                        else:
                            effect_obj = None

                        attr = ef1.attrib

                        if effect_obj is not None:
                            attr['posX'] = str(effect_obj.location[0])
                            attr['posY'] = str(effect_obj.location[2])
                            attr['posZ'] = str(-1*effect_obj.location[1])
                            attr['rotX'] = str(math.degrees(effect_obj.rotation_euler[0]))
                            attr['rotY'] = str(math.degrees(effect_obj.rotation_euler[2]))
                            attr['rotZ'] = str(math.degrees(-1*effect_obj.rotation_euler[1]))

                elif effect.tag == 'effectType2':
                    for j, ef2 in enumerate(list(effect)):
                        blender_name = "[EXT_IMPORTED_FX:" + xml_name.text + ":" + str(index) + ":" + str(j) + "]"

                        if blender_name in obj_names:
                            effect_obj = context.scene.objects[blender_name]
                        else:
                            effect_obj = None

                        attr = ef2.attrib

                        if effect_obj is not None:
                            attr['posX'] = str(effect_obj.location[0])
                            attr['posY'] = str(effect_obj.location[2])
                            attr['posZ'] = str(-1*effect_obj.location[1])

        anim = imported_bg_model.find('animKeyframes')

        # Handles updating all animation keyframes for imported object previews
        # TODO: Not perfect! Need to handle object translations properly...
        if anim is not None and imported_blender_object is not None:
            # For imported objects, determine how much the object has moved from its original position, so this change
            # can be applied to animation keyframes.
            pos_delta = current_bg_pos - orig_pos
            rot_delta = current_bg_rot - orig_rot
            scale_delta = Vector((current_bg_scale[0]/orig_scale[0],
                                  current_bg_scale[1]/orig_scale[1],
                                  current_bg_scale[2]/orig_scale[2]))

            for tag in list(anim):
                for tag_name, delta in [('posX', pos_delta[0]), ('posY', pos_delta[1]), ('posZ', pos_delta[2]),
                                        ('rotX', rot_delta[0]), ('rotY', rot_delta[1]), ('rotZ', rot_delta[2]),
                                        ('scaleX', scale_delta[0]), ('scaleY', scale_delta[1]), ('scaleZ', scale_delta[2])]:
                    if tag.tag == tag_name:
                        for keyframe in list(tag):
                            if "pos" in tag_name:
                                keyframe.attrib['value'] = str(float(keyframe.attrib['value']))
                            elif "rot" in tag_name:
                                keyframe.attrib['value'] = str(float(keyframe.attrib['value']) + delta)
                            elif "scale" in tag_name:
                                keyframe.attrib['value'] = str(float(keyframe.attrib['value']) * delta)
                        break

        destination_root.append(imported_bg_model)


# Operator for exporting the stage config as a .XML file
class OBJECT_OT_generate_config(bpy.types.Operator):
    bl_idname = "object.generate_config"
    bl_label = "Generate Config"
    bl_description = "Generate .XML file for config export"
    bl_options = {'UNDO'} 

    def execute(self, context):
        print("Generating config...")

        root = etree.Element("superMonkeyBallStage", version="1.3.0")
        
        # OBJ file path
        modelImport = etree.SubElement(root, "modelImport")
        if context.scene.export_model_path.startswith("//"):
            # It's a relative path
            modelImport.text = context.scene.export_model_path
        else:
            # It's an absolute path
            modelImport.text = "file://" + context.scene.export_model_path

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
        
        # Export w.r.t first frame of animation, except when exporting per-frame animation
        begin_frame = bpy.context.scene.frame_start
        end_frame = bpy.context.scene.frame_end
        orig_frame = bpy.context.scene.frame_current
        context.scene.frame_set(begin_frame)

        # Marks objects that don't have keyframes on frame 0, so they can be removed later
        first_frame_added_objs = []

        # Curve types for f-curve iteration
        curve_types = ["location", "rotation_euler", "scale"]

        all_curve_types = []
        for ct in curve_types:
            for i in [0, 1, 2]:
                all_curve_types.append((i, ct))

        class ObjExport:
            def __init__(self, obj):
                self.obj = obj
                self.anim_data = generate_config.AnimData()
    
        # Build ObjExport lists
        ig_export_datas: list[ObjExport] = []
        fg_export_datas: list[ObjExport] = []
        bg_export_datas: list[ObjExport] = []
        other_export_datas: list[ObjExport] = []

        ig_tag = descriptor_item_group.DescriptorIG.get_object_name()
        fg_tag = descriptor_model_fg.DescriptorFG.get_object_name()
        bg_tag = descriptor_model_bg.DescriptorBG.get_object_name()

        for obj in bpy.context.scene.objects:
            if obj.type not in ["EMPTY", "MESH", "CURVE"]:
                continue
            if ig_tag in obj.name:
                # Don't export at all otherwise
                if 'collisionStartX' in obj:
                    ig_export_datas.append(ObjExport(obj))
            elif fg_tag in obj.name:
                # Don't export at all otherwise
                if obj.name.startswith(descriptor_model_fg.DescriptorFG.get_object_name()):
                    fg_export_datas.append(ObjExport(obj))
            elif bg_tag in obj.name:
                # Don't export at all otherwise
                if obj.name.startswith(descriptor_model_bg.DescriptorBG.get_object_name()):
                    bg_export_datas.append(ObjExport(obj))
            else:
                other_export_datas.append(ObjExport(obj))

        # Semi-hacky way to get the object's center of rotation to work properly
        # B2SMB1 inadvertently fixed this by baking *all* keyframes
        # This is fixed by adding an initial keyframe on every curve
        # This also fixes weirdness with background and foreground objects
        for exp in itertools.chain(ig_export_datas, fg_export_datas, bg_export_datas):
            if exp.obj.animation_data is not None and exp.obj.animation_data.action is not None:
                channels_with_frame_zero_keyframes = []
                fcurves = exp.obj.animation_data.action.fcurves

                # Find existing channels with frame 0 keyframes
                for (index, curve_type) in all_curve_types:
                    fcurve = fcurves.find(curve_type, index=index)
                    if fcurve is not None:
                        for keyframe_index in range(len(fcurve.keyframe_points)):
                            if fcurve.keyframe_points[keyframe_index].co[0] == float(begin_frame):
                                channels_with_frame_zero_keyframes.append((index, curve_type))
                                # print(f"Added existing channel {curve_type}[{index}]")
                                break

                # We need to add keyframes on frame 0 if not all channels have keyframes there
                if len(channels_with_frame_zero_keyframes) != 9:
                    first_frame_added_objs.append((exp.obj, channels_with_frame_zero_keyframes))

                # Adds keyframes to needed channels
                for (index, curve_type) in all_curve_types:
                    if (index, curve_type) in channels_with_frame_zero_keyframes: continue
                    exp.obj.keyframe_insert(curve_type, index=index, frame=begin_frame)

                print("\tInserted frame zero keyframe for item group " + exp.obj.name)

        # Generate initial animation data based on fcurve keyframes
        for exp in itertools.chain(ig_export_datas, fg_export_datas, bg_export_datas):
            generate_config.generate_keyframe_anim_data(exp.obj, exp.anim_data)

        # Generate per-global-frame animation data
        for frame in range(begin_frame, end_frame + 1):
            bpy.context.scene.frame_set(frame)
            for exp in itertools.chain(ig_export_datas, fg_export_datas, bg_export_datas):
                generate_config.generate_per_frame_anim_data(exp.obj, exp.anim_data)
        context.scene.frame_set(begin_frame)

        # Generate FG/BG XML
        for fg_exp in fg_export_datas:
            descriptor_model_fg.DescriptorFG.generate_xml_with_anim(root, fg_exp.obj, fg_exp.anim_data)
        for bg_exp in bg_export_datas:
            descriptor_model_bg.DescriptorBG.generate_xml_with_anim(root, bg_exp.obj, bg_exp.anim_data)

        # Generate other object XML
        for other_exp in other_export_datas:
            for desc in descriptors.descriptors_root:
                if other_exp.obj.name.startswith(desc.get_object_name()): 
                    desc.generate_xml(root, other_exp.obj)

        # Generate itemgroup XML
        for ig_exp in ig_export_datas:
            ig_xml = descriptor_item_group.DescriptorIG.generate_xml_with_anim(root, ig_exp.obj, ig_exp.anim_data)

            # Children list
            ig_children = [obj for obj in bpy.context.scene.objects if obj.parent == ig_exp.obj]
            ig_children.append(ig_exp.obj)

            # Children of item groups
            for child in ig_children:
                match_descriptor = False

                # Generate elements for listed descriptors (except IGs)
                for desc in descriptors.descriptors:
                    if desc.get_object_name() in child.name and "[IG]" not in child.name:
                        match_descriptor = True
                        desc.generate_xml(ig_xml, child)
                        break
                
                # Object is not a listed descriptor
                if not match_descriptor and child.data is not None:
                    descriptor_model_stage.DescriptorModel.generate_xml(ig_xml, child)

        # Restore frame user was on before exporting
        bpy.context.scene.frame_set(orig_frame)

        # Import background and foreground objects from a .XML file, if it exists
        bg_path = bpy.path.abspath(context.scene.background_import_path)
        obj_names = [obj.name for obj in context.scene.objects]
        if os.path.exists(bg_path):
            bg = etree.parse(bg_path)
            bg_root = bg.getroot()

            if bg_root.tag != 'superMonkeyBallBackground':
                self.report({'ERROR'}, "Imported background XML not an exported background XML")
                return {'CANCELLED'}

            append_imported_bg_objects(self, context, bg_root, root, obj_names)

        print("Completed, saving...")

        config_string = etree.tostring(root, encoding="unicode")
        config_dom = minidom.parseString(config_string)
        config_string_pretty = config_dom.toprettyxml()

        config_file = open(bpy.path.abspath(context.scene.export_config_path), "w")
        config_file.write(config_string_pretty)
        config_file.close()
        print("Finished generating config")

        # Remove the beginning keyframe channel if it didn't exist prior to it being added
        for (obj, obj_existing_channels) in first_frame_added_objs:
            for (idx, curve_type) in all_curve_types:
                if (idx, curve_type) in obj_existing_channels: continue 
                print(f"Deleted frame zero channel {curve_type}[{idx}] for item group {obj.name}")
                obj.keyframe_delete(curve_type, index=idx, frame=begin_frame)

        return {'FINISHED'}

# Function for updating the properties of an active object
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
    elif game_mode == 'MONKEY_TARGET_2':
        for score in [1,10,50,100,150,200,300,400,500,750,1000]:
            # formula for target flags is 0x8000 | (2 * score)
            flag = 2 * score - 32768
            text = '{} points'.format(score) if score != 1 else '1 point'
            items.append((str(flag), text, ''))


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
    unk3: BoolProperty(name="Reflects in Mirror",
                              update=lambda s,c: update_prop(s, c, "unk3"))
    transparencyA: BoolProperty(name="Transparency Type A",
                              update=lambda s,c: update_prop(s, c, "transparencyA"))
    transparencyB: BoolProperty(name="Transparency Type B",
                              update=lambda s,c: update_prop(s, c, "transparencyB"))

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
