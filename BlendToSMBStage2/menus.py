import bpy
import bmesh
import math
import mathutils

class VIEW3D_OT_cube_project_smb_checker(bpy.types.Operator):
    bl_idname = "uv.cube_project_smb_checker"
    bl_label = "Cube Projection (Checkers) [b2smb]"
    
    bl_options = {'REGISTER', 'UNDO'}
    checker_size: bpy.props.IntProperty(name = "2x2 Checker Size", default=128, min=1)

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
        
        # Find scale factor
        scale_factor = bpy.context.active_object.active_material.node_tree.nodes.get("Image Texture").image.size[0]
        
        bpy.ops.uv.cube_project(
            cube_size=1.0*(self.checker_size*4.0)/scale_factor,
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

class VIEW3D_OT_checker_FAQ(bpy.types.Operator):
    bl_idname = "uv.checker_faq"
    bl_label = "Smart Follow Active Quads (Checkers) [b2smb]"
    
    bl_options = {'REGISTER', 'UNDO'}

    odd: bpy.props.BoolProperty(name = "Odd # of Checkers", default=True)
    pix_checker_size: bpy.props.IntProperty(name = "2x2 Checker Size", default=128, min=1)
    faqtype: bpy.props.EnumProperty(items=[("EVEN","Even","Space all UVs evenly."),
                                           ("LENGTH","Length","Average space UVs edge length of each loop."),
                                           ("LENGTH_AVERAGE","Length Average","Average space UVs edge length of each loop.")],
                                    name = "Edge Length Mode",
                                    default="LENGTH_AVERAGE")

    def execute(self, context):
        try:
            bpy.ops.uv.follow_active_quads(mode=self.faqtype)
        except:
            self.report({'ERROR'}, "Could not run 'Follow Active Quads', ensure at least one face is selected")
            return {"CANCELLED"}

        # Find checker size in uv units
        checker_size = 1.0/(bpy.context.active_object.active_material.node_tree.nodes.get("Image Texture").image.size[0]/(self.pix_checker_size))
        
        # First calculate all necessary vertex data
        active_obj = bpy.context.active_object        
        bm = bmesh.from_edit_mesh(active_obj.data)
        bm.verts.ensure_lookup_table() # Required after adding / removing vertices and before accessing them by index.
        bm.verts.index_update()
        
        selected_faces = [f for f in bm.faces if f.select]
        active_face = bm.faces.active
        uv_layer = bm.loops.layers.uv.verify()
        selected_loops = []
        active_loops = []
        
        if len(selected_faces) < 2:
            self.report({'ERROR'}, "Only one face selected, ensure two or more faces are selected")
            return {"CANCELLED"}

        for f in selected_faces:
            if f != active_face:
                for l in f.loops:
                    #selected_verts.append(l[uv_layer].uv)
                    selected_loops.append(l)
        
        for l in active_face.loops:
            active_loops.append(l)
            
        # Determine direction
        active_edges = [e for e in active_face.edges if len(e.link_faces) == 2]
        neighbor_faces = []
        for e in active_edges:
            neighbor_faces += [f for f in e.link_faces if (f in selected_faces) and (f != active_face)]
        adj_face = neighbor_faces[0]
        adj_loops = [l for l in adj_face.loops]
        adj_verts = [l[uv_layer].uv.copy().freeze() for l in adj_loops]
        active_verts = [l[uv_layer].uv.copy().freeze() for l in active_loops]
        intersect_verts = []
        for v in active_verts:
            for j in adj_verts:
                if (v - j).length < 0.0001:
                    intersect_verts.append(v)
        excl_verts = list(set(adj_verts) - set(intersect_verts))
        
        direction = (intersect_verts[0] - intersect_verts[1]).normalized().orthogonal()
        # Does it face the right way or must it be multiplied by -1?
        approx_direction = (excl_verts[0] - intersect_verts[0]).normalized()
        if direction.angle(approx_direction) > math.pi/2.0:
            direction = -direction
            
        # Find the scaling factor
        origin = intersect_verts[0]
        selected_verts = list(set(l[uv_layer].uv.copy().freeze() for l in selected_loops))
        max_distance = 0.0
        for n in range(len(selected_verts)):
            distance = (selected_verts[n] - origin).project(direction).length
            if distance >= max_distance:
                max_distance = distance
        
        even_scaling = (checker_size* 2.0 * round(max_distance / (checker_size * 2.0))) / max_distance
        if self.odd:
            odd_scaling = (checker_size * round(max_distance / checker_size)) / max_distance
            if abs(odd_scaling - even_scaling) < 0.0001:
                if round(max_distance / checker_size) < max_distance / checker_size:
                    scaling_factor = (checker_size * (round(max_distance / checker_size)+1.0)) / max_distance
                else:
                    scaling_factor = (checker_size * (round(max_distance / checker_size)-1.0)) / max_distance
            else:
                scaling_factor = odd_scaling
        else:
           scaling_factor = even_scaling
        
        # Scale the uv coordinates by the scaling factor in the correct direction
        
        for l in selected_loops:
            uv_vert = l[uv_layer].uv
            uv_vert = uv_vert - origin
            proj = uv_vert.project(direction)
            uv_vert = uv_vert - proj
            scaled_proj = proj * scaling_factor
            uv_vert = uv_vert + scaled_proj
            uv_vert = uv_vert + origin
            l[uv_layer].uv = uv_vert
        
        return {"FINISHED"}
        
class VIEW3D_OT_smart_FAQ(bpy.types.Operator):
    bl_idname = "uv.smart_faq"
    bl_label = "Follow Active Quads (Edges) [b2smb]"
    
    bl_options = {'REGISTER', 'UNDO'}
    include_active: bpy.props.BoolProperty(name = "Include Active Face?", default=True)
    tile_number: bpy.props.FloatProperty(name = "Number of Tiles", default=8.0)
    axis: bpy.props.EnumProperty(items=[("uaxis","U Axis", "U Axis will be tiled"),
                                        ("vaxis","V Axis", "V Axis will be tiled")],
                                name="Tiling Axis", 
                                default="uaxis")

    faqtype: bpy.props.EnumProperty(items=[("EVEN","Even","Space all UVs evenly."),
                                           ("LENGTH","Length","Average space UVs edge length of each loop."),
                                           ("LENGTH_AVERAGE","Length Average","Average space UVs edge length of each loop.")],
                                    name = "Edge Length Mode",
                                    default="LENGTH_AVERAGE")

    def execute(self, context):
        try:
            bpy.ops.uv.follow_active_quads(mode=self.faqtype)
        except:
            self.report({'ERROR'}, "Could not run 'Follow Active Quads', ensure at least one face is selected")
            return {"CANCELLED"}

        # First calculate all necessary vertex data
        active_obj = bpy.context.active_object        
        bm = bmesh.from_edit_mesh(active_obj.data)
        bm.verts.ensure_lookup_table() # Required after adding / removing vertices and before accessing them by index.
        bm.verts.index_update()
        
        selected_faces = [f for f in bm.faces if f.select]
        active_face = bm.faces.active
        uv_layer = bm.loops.layers.uv.verify()
        selected_loops = []
        active_loops = []
        
        if len(selected_faces) < 2:
            self.report({'ERROR'}, "Only one face selected, ensure two or more faces are selected")
            return {"CANCELLED"}

        for f in selected_faces:
            if f != active_face:
                for l in f.loops:
                    #selected_verts.append(l[uv_layer].uv)
                    selected_loops.append(l)
        
        for l in active_face.loops:
            active_loops.append(l)
            
        # Determine direction
        active_edges = [e for e in active_face.edges if len(e.link_faces) == 2]
        neighbor_faces = []
        for e in active_edges:
            neighbor_faces += [f for f in e.link_faces if (f in selected_faces) and (f != active_face)]
        adj_face = neighbor_faces[0]
        adj_loops = [l for l in adj_face.loops]
        adj_verts = [l[uv_layer].uv.copy().freeze() for l in adj_loops]
        active_verts = [l[uv_layer].uv.copy().freeze() for l in active_loops]
        intersect_verts = []
        for v in active_verts:
            for j in adj_verts:
                if (v - j).length < 0.0001:
                    intersect_verts.append(v)
        excl_verts = list(set(adj_verts) - set(intersect_verts))
        
        if self.axis == "uaxis":
            direction = mathutils.Vector((1.0,0.0)).freeze()
        else:
            direction = mathutils.Vector((0.0,1.0)).freeze()
        # Does it face the right way or must it be multiplied by -1?
        approx_direction = (excl_verts[0] - intersect_verts[0]).normalized()
        if direction.angle(approx_direction) > math.pi/2.0:
            direction = -direction
            
        # Find the scaling factor
        if self.include_active:
            origin = excl_verts[0]
        else:
            origin = intersect_verts[0]
        selected_verts = list(set(l[uv_layer].uv.copy().freeze() for l in selected_loops))
        max_distance = 0.0
        for n in range(len(selected_verts)):
            distance = (selected_verts[n] - origin).project(direction).length
            if distance >= max_distance:
                max_distance = distance
        
        scaling_factor = 0.5 * self.tile_number / max_distance
        
        # Scale the uv coordinates by the scaling factor in the correct direction
        if self.include_active:
            for l in active_face.loops:
                selected_loops.append(l)
        
        for l in selected_loops:
            uv_vert = l[uv_layer].uv
            uv_vert = uv_vert - origin
            proj = uv_vert.project(direction)
            uv_vert = uv_vert - proj
            scaled_proj = proj * scaling_factor
            uv_vert = uv_vert + scaled_proj
            uv_vert = uv_vert + origin
            l[uv_layer].uv = uv_vert
        
        return {"FINISHED"}

def menu_func(self, context):
    self.layout.operator(VIEW3D_OT_cube_project_smb_checker.bl_idname)
    self.layout.operator(VIEW3D_OT_checker_FAQ.bl_idname)
    self.layout.operator(VIEW3D_OT_smart_FAQ.bl_idname)

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
