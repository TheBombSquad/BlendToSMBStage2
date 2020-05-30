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
        if obj.name.startswith("[IG]"):
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
                obj["_id"] = obj["id"]
                del obj["id"]
            if "linkedId" in obj.keys(): 
                obj["_linkedId"] = obj["linkedId"]
                del obj["linkedId"]
            if "_linkedObject" not in obj.keys():
                obj["_linkedObject"] = None

        # Switches
        if obj.name.startswith("[SW_"):
            if "animId" in obj.keys():
                obj["_animId"] = obj["animId"]
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
            if obj.name.startswith(desc.get_object_name()):
                desc.rna_ui_setup(obj)

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
            default = True,
            update=stage_editor.autoPathNames)
    
    #TODO: Maybe make this an option in the future
    #bpy.types.Scene.optimize_keyframes = bpy.props.BoolProperty(
    #        name="Optimize Keyframe Export",
    #        description="Remove redundant keyframes. Turning this off is the equivalent of baking the entire animation.",
    #        default = True,
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

