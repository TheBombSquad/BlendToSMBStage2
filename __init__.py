import bpy
import importlib
import inspect
import traceback
from . import developer_utils
from .BlendToSMBStage2 import stage_editor, statics, descriptors
from bpy.app.handlers import persistent

bl_info = {
    "name": "BlendToSMBStage2",
    "description": "Addon for creating Super Monkey Ball stage configuration files",
    "author": "CraftedCart, The BombSquad",
    "version": (2, 0),
    "blender": (2, 82, 7),
    "location": "View3D",
    "category": "3D View",
}

# Load and reload submodules
importlib.reload(developer_utils)
modules = developer_utils.setup_addon_modules(__path__, __name__, "bpy" in locals())

@persistent
def load_handler(dummy):
    print("Loaded file")

    # Update possibly outdated properties 
    for obj in bpy.data.objects:
        # Delete old unused animation properties
        if "posXAnim" in obj.keys():
            del obj["posXAnim"]
        if "posYAnim" in obj.keys():
            del obj["posYAnim"]
        if "posZAnim" in obj.keys():
            del obj["posZAnim"]
        if "rotXAnim" in obj.keys():
            del obj["rotXAnim"]
        if "rotYAnim" in obj.keys():
            del obj["rotYAnim"]
        if "rotZAnim" in obj.keys():
            del obj["rotZAnim"]

        # Item Groups
        if "[IG]" in obj.name:
            # Properties with changed names
            if "initPlaying" in obj.keys():
                obj["_initPlaying"] = obj["initPlaying"]
                del obj["initPlaying"]
            if "loopAnim" in obj.keys():
                obj["_loopAnim"] = obj["loopAnim"]
                del obj["loopAnim"]

            if "loopTime" in obj.keys():
                obj["animLoopTime"] = obj["loopTime"]
                del obj["loopTime"]

            # Casts to float, since certain old properties don't line up correctly
            if "animLoopTime" in obj.keys():
                if type(obj["animLoopTime"]) is int:
                    obj["animLoopTime"] = float(obj["animLoopTime"])
                    if (obj["animLoopTime"] != -1.0):
                        obj["animLoopTime"] = obj["animLoopTime"]/bpy.context.scene.render.fps

            # New properties
            if "seesawSensitivity" not in obj.keys():
                obj["seesawSensitivity"] = 0.0
            if "seesawFriction" not in obj.keys():
                obj["seesawFriction"] = 0.0
            if "seesawSpring" not in obj.keys():
                obj["seesawSpring"] = 0.0
            if "texScrollUSpeed" not in obj.keys():
                obj["texScrollUSpeed"] = 0.0
            if "texScrollVSpeed" not in obj.keys():
                obj["texScrollVSpeed"] = 0.0
            if "exportTimestep" not in obj.keys():
                obj["exportTimestep"] = -1
        # Goals
        if obj.name.startswith("[GOAL_"):
            if "_cast_shadow" not in obj.keys():
                obj["_cast_shadow"] = True

        # Wormholes
        if obj.name.startswith("[WH]"):
            if "id" in obj.keys():
                obj["whId"] = obj["id"]
                del obj["id"]
            if "_id" in obj.keys():
                obj["whId"] = obj["_id"]
                del obj["_id"]
            if "_linkedId" in obj.keys(): 
                obj["linkedId"] = obj["_linkedId"]
                del obj["_linkedId"]
            if "_linkedObject" not in obj.keys():
                obj["_linkedObject"] = None

        # Switches
        if obj.name.startswith("[SW_"):
            if "_animId" in obj.keys():
                obj["linkedId"] = obj["_animId"]
                del obj["_animId"]
            if "animId" in obj.keys():
                obj["linkedId"] = obj["animId"]
                del obj["animId"]
            if "_linkedObject" not in obj.keys():
                obj["_linkedObject"] = None

        # BG objects
        if obj.name.startswith("[BG]"):
            if "animLoopTime" not in obj.keys():
                obj["animLoopTime"] = -1.0
            if "meshType" not in obj.keys():
                obj["meshType"] = 0x1f
            if "texScrollUSpeed" not in obj.keys():
                obj["texScrollUSpeed"] = 0.0
            if "texScrollVSpeed" not in obj.keys():
                obj["texScrollVSpeed"] = 0.0
        
        # Set up UI for objects
        for desc in descriptors.descriptors_all:
            if desc.get_object_name() in obj.name:
                desc.rna_ui_setup(obj)

    for mat in bpy.data.materials:
        # Enable backface culling for all materials
        if hasattr(mat, 'use_backface_culling'):
            mat.use_backface_culling = True

        if (mat.use_nodes):
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links

            material_output_node = None
            image_texture_node = None
            diffuse_node = None

            for node in nodes:
                if (node.type == 'BSDF_PRINCIPLED'):
                    continue
                elif (node.type =='OUTPUT_MATERIAL'):
                    material_output_node = node
                elif (node.type == 'TEX_IMAGE'):
                    image_texture_node = node
                elif (node.type =='BSDF_DIFFUSE'):
                    diffuse_node = node
                else:
                    print("Removing extraneous node" + str(node))
                    nodes.remove(node)

            # Convert Diffuse BSDF nodes to Principled BSDF
            if diffuse_node is not None:
                print("Converting material " + mat.name + " diffuse BSDF node to principled BSDF...")
                nodes.remove(diffuse_node)
                principled_node = nodes.new("ShaderNodeBsdfPrincipled")
                links.new(material_output_node.inputs['Surface'], principled_node.outputs['BSDF'])
                links.new(principled_node.inputs['Base Color'], image_texture_node.outputs['Color'])
                principled_node.inputs['Specular'].default_value = 0.0

# Register
def register():
    try:
        for m in modules:
            for name,cls in inspect.getmembers(m, inspect.isclass):
                if hasattr(cls, "bl_rna"):
                    bpy.utils.register_class(cls)
                    print("Registered: " + name)
    except:
        print("Failed to register: " + name)
        traceback.print_exc()
    

    bpy.types.Scene.export_timestep = bpy.props.IntProperty(
            name="Animation Timestep",
            description="Determines how often animation frames are sampled",
            default=1,
            soft_min=1
    )
    bpy.types.Scene.export_value_round = bpy.props.IntProperty(
            name="Value Decimal Places",
            description="Determines the precision of the value of animation keyframes",
            default=3,
            soft_min=0
    )
    bpy.types.Scene.export_time_round = bpy.props.IntProperty(
            name="Time Decimal Places",
            description="Determines the precision of the time of animation keyframes",
            default=3,
            soft_min=0
    )
    bpy.types.Scene.export_config_path = bpy.props.StringProperty(
            name="Config Export Path",
            description="The path to export the config to",
            subtype='FILE_PATH',
            default="//config.xml"
    )
    bpy.types.Scene.export_model_path = bpy.props.StringProperty(
            name="Model Export Path",
            description="The path to export the model to",
            subtype='FILE_PATH',
            default="//model.obj"
    )
    bpy.types.Scene.falloutProp = bpy.props.IntProperty(
            name="Fallout Plane",
            description="Height of the fallout plane",
            default=-10,
    )
    bpy.types.Scene.draw_falloutProp = bpy.props.BoolProperty(
            name="Draw Fallout Plane",
            description="Whether or not to draw a visual representation of the fallout plane",
            default=True,
    )
    bpy.types.Scene.draw_stage_objects = bpy.props.BoolProperty(
            name="Draw Stage Objects",
            description="Whether or not to draw a visual representation of stage objects",
            default=True,
    )
    bpy.types.Scene.draw_collision_grid = bpy.props.BoolProperty(
            name="Draw Collision Grids",
            description="Whether or not to draw a visual representation of collision grids",
            default=True,
    )
    bpy.types.Scene.auto_path_names = bpy.props.BoolProperty(
            name="Automatic Path Names",
            default = False,
            update=stage_editor.autoPathNames)
    
    bpy.types.Scene.optimize_keyframes = bpy.props.BoolProperty(
            name="Optimize Keyframes",
            description="Remove redundant keyframes. Turning this off is the equivalent of baking the entire animation.",
            default = True,
    )

    bpy.types.Object.stage_object_properties = bpy.props.CollectionProperty(type=stage_editor.StageObjectPropertyProxy)

    bpy.app.handlers.load_post.append(load_handler)
    print("Successfully registered {} with {} modules".format(bl_info["name"], len(modules)))
    for module in modules:
        print("-", module.__name__)

# Unregister
def unregister():
    del bpy.types.Scene.export_timestep
    del bpy.types.Scene.export_value_round
    del bpy.types.Scene.export_time_round
    del bpy.types.Scene.export_config_path
    del bpy.types.Scene.export_model_path
    del bpy.types.Scene.draw_falloutProp
    del bpy.types.Scene.draw_stage_objects
    del bpy.types.Scene.draw_collision_grid
    del bpy.types.Scene.auto_path_names
    del bpy.types.Scene.falloutProp
    del bpy.types.Object.stage_object_properties

    try:
        # Remove draw handlers
        for handler in statics.active_draw_handlers:
            bpy.types.SpaceView3D.draw_handler_remove(handler, 'WINDOW')

        for m in modules:
            for name,cls in inspect.getmembers(m, inspect.isclass):
                if hasattr(cls, "bl_rna"):
                    bpy.utils.unregister_class(cls)
                    print("Unregistered: " + name)
        bpy.app.handlers.load_post.remove(load_handler)
    except:
        print("Failed to unregister: " + name)
        traceback.print_exc()

    print("Successfully unregistered {}".format(bl_info["name"]))

