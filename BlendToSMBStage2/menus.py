import bpy

class VIEW3D_OT_cube_project_fixed(bpy.types.Operator):
    bl_idname = "uv.cube_project_fixed"
    bl_label = "Cube Projection (1.0 scale, fixed origin) [b2smb]"

    objects: bpy.props.StringProperty()

    def execute(self, context):
        old_cursor_loc = bpy.context.scene.cursor.location.copy()
        old_cursor_rot_euler = bpy.context.scene.cursor.rotation_euler.copy()
        old_cursor_rot_quat = bpy.context.scene.cursor.rotation_quaternion.copy()
        old_cursor_rot_mode = bpy.context.scene.cursor.rotation_mode
        old_pivot_point = bpy.context.scene.tool_settings.transform_pivot_point

        bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)
        bpy.context.scene.cursor.rotation_mode = "XYZ"
        bpy.context.scene.cursor.rotation_euler = (0.0, 0.0, 0.0)
        bpy.context.scene.tool_settings.transform_pivot_point = "CURSOR"

        bpy.ops.uv.cube_project(
            cube_size=1.0,
            correct_aspect=True,
            clip_to_bounds=False,
            scale_to_bounds=False
        )

        bpy.context.scene.cursor.location = old_cursor_loc
        bpy.context.scene.cursor.rotation_mode = old_cursor_rot_mode
        bpy.context.scene.cursor.rotation_euler = old_cursor_rot_euler
        bpy.context.scene.cursor.rotation_quaternion = old_cursor_rot_quat
        bpy.context.scene.tool_settings.transform_pivot_point = old_pivot_point

        return {"FINISHED"}
        
class VIEW3D_OT_cube_project_smb_checker(bpy.types.Operator):
    bl_idname = "uv.cube_project_smb_checker"
    bl_label = "SMB Checker Cube Projection [b2smb]"

    objects: bpy.props.StringProperty()

    def execute(self, context):
        old_cursor_loc = bpy.context.scene.cursor.location.copy()
        old_cursor_rot_euler = bpy.context.scene.cursor.rotation_euler.copy()
        old_cursor_rot_quat = bpy.context.scene.cursor.rotation_quaternion.copy()
        old_cursor_rot_mode = bpy.context.scene.cursor.rotation_mode
        old_pivot_point = bpy.context.scene.tool_settings.transform_pivot_point

        bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)
        bpy.context.scene.cursor.rotation_mode = "XYZ"
        bpy.context.scene.cursor.rotation_euler = (0.0, 0.0, 0.0)
        bpy.context.scene.tool_settings.transform_pivot_point = "CURSOR"
        
        #find scale factor
        scale_factor = bpy.context.active_object.active_material.node_tree.nodes.get("Image Texture").image.size[0]
        
        bpy.ops.uv.cube_project(
            cube_size=1.0*256.0/scale_factor,
            correct_aspect=True,
            clip_to_bounds=False,
            scale_to_bounds=False
        )

        bpy.context.scene.cursor.location = old_cursor_loc
        bpy.context.scene.cursor.rotation_mode = old_cursor_rot_mode
        bpy.context.scene.cursor.rotation_euler = old_cursor_rot_euler
        bpy.context.scene.cursor.rotation_quaternion = old_cursor_rot_quat
        bpy.context.scene.tool_settings.transform_pivot_point = old_pivot_point

        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(VIEW3D_OT_cube_project_fixed.bl_idname)
    self.layout.operator(VIEW3D_OT_cube_project_smb_checker.bl_idname)


def handle_register():
   #  bpy.utils.register_class(MyOperatorClass)
   # this adds your menu to shift-a add object menu
   bpy.types.VIEW3D_MT_uv_map.append(menu_func)
   # if you want to add to mesh menu use INFO_MT_mesh_add
   # other menu classes you can find in \scripts\startup\bl_ui\
   # by looking into the files there (i.e.: space_view3d.py)

def handle_unregister():
    #  bpy.utils.unregister_module(MyOperatorClass)
    bpy.types.VIEW3D_MT_uv_map.remove(menu_func)
