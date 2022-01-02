import bpy
import importlib
import inspect
import traceback
import pdb
import re

from . import developer_utils
from .BlendToSMBStage2 import stage_editor, statics, menus
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
            # Properties with _ in the beginning of their name were used for a hacky RNA property display thing
            # This isn't used anymore, so they're removed
            if "_initPlaying" in obj.keys():
                obj["initPlaying"] = obj["_initPlaying"]
                del obj["_initPlaying"]
            if "_loopAnim" in obj.keys():
                obj["loopAnim"] = obj["_loopAnim"]
                del obj["_loopAnim"]

            # "loopTime" was renamed to "animLoopTime" for clarity
            if "loopTime" in obj.keys():
                obj["animLoopTime"] = obj["loopTime"]
                del obj["loopTime"]

            # Cast collision start and step amounts to floats
            for floatKey in ["collisionStartX", "collisionStartY", "collisionStepX", "collisionStepY"]:
                if floatKey in obj.keys():
                    obj[floatKey] = float(obj[floatKey])

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
            if "conveyorX" not in obj.keys():
                obj["conveyorX"] = 0.0
            if "conveyorY" not in obj.keys():
                obj["conveyorY"] = 0.0
            if "conveyorZ" not in obj.keys():
                obj["conveyorZ"] = 0.0
            if "collisionTriangleFlag" not in obj.keys():
                obj["collisionTriangleFlag"] = 0

        # Goals
        if obj.name.startswith("[GOAL_"):
            if "_cast_shadow" in obj.keys():
                obj["cast_shadow"] = obj["_cast_shadow"]
                del obj["_cast_shadow"]
            if "cast_shadow" not in obj.keys():
                obj["cast_shadow"] = True

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
            if "_linkedObject" in obj.keys():
                obj["linkedObject"] = obj["_linkedObject"]
                del obj["_linkedObject"]
            if "linkedObject" not in obj.keys():
                obj["linkedObject"] = None

        # Switches
        if obj.name.startswith("[SW_"):
            if "_animId" in obj.keys():
                obj["linkedId"] = obj["_animId"]
                del obj["_animId"]
            if "animId" in obj.keys():
                obj["linkedId"] = obj["animId"]
                del obj["animId"]
            if "_linkedObject" in obj.keys():
                obj["linkedObject"] = obj["_linkedObject"]
                del obj["_linkedObject"]
            if "linkedObject" not in obj.keys():
                obj["linkedObject"] = None

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
                #else:
                    #print("Removing extraneous node" + str(node))
                    #nodes.remove(node)

            # Convert Diffuse BSDF nodes to Principled BSDF
            if diffuse_node is not None:
                print("Converting material " + mat.name + " diffuse BSDF node to principled BSDF...")
                nodes.remove(diffuse_node)
                principled_node = nodes.new("ShaderNodeBsdfPrincipled")
                links.new(material_output_node.inputs['Surface'], principled_node.outputs['BSDF'])
                links.new(principled_node.inputs['Base Color'], image_texture_node.outputs['Color'])
                principled_node.inputs['Specular'].default_value = 0.0

    # Sync all UI properties
    stage_editor.autoUpdateUIProps()

# Function for handling material preset updates
def update_preset(self, context, prop, flag):
    name = getattr(self, prop)

    if name is not "":
        if f"[{flag}_" in self.name:
            self.name = re.sub(fr"(?<={flag}_)[^\]]*", name, self.name)
        else:
            self.name = f"[{flag}_{name}] {self.name}"
    else:
        self.name = re.sub(fr"\[{flag}_[^\]]*] ", "", self.name)

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
    

    # Various scene properties for paths/global stage properties
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
    bpy.types.Scene.export_gma_path = bpy.props.StringProperty(
            name="GMA Export Path",
            description="The path to export the model to",
            subtype='FILE_PATH',
            default="//model.gma"
    )
    bpy.types.Scene.export_tpl_path = bpy.props.StringProperty(
            name="TPL Export Path",
            description="The path to export the model to",
            subtype='FILE_PATH',
            default="//model.tpl"
    )
    bpy.types.Scene.export_raw_stagedef_path = bpy.props.StringProperty(
            name="LZ.RAW Export Path",
            description="The path to export the raw stagedef to",
            subtype='FILE_PATH',
            default="//stagedef.lz.raw"
    )
    bpy.types.Scene.export_stagedef_path = bpy.props.StringProperty(
            name="LZ Export Path",
            description="The path to export the compressed stagedef to",
            subtype='FILE_PATH',
            default="//stagedef.lz"
    )
    bpy.types.Scene.export_background_path = bpy.props.StringProperty(
            name="Background Export Path",
            description="The path to export the background config to",
            subtype='FILE_PATH',
            default="//background.bg.xml"
    )
    bpy.types.Scene.import_gma_path = bpy.props.StringProperty(
            name="External GMA Import Path",
            description="The path to an external GMA to import",
            subtype='FILE_PATH',
            default=""
    )
    bpy.types.Scene.import_tpl_path = bpy.props.StringProperty(
            name="External TPL Import Path",
            description="The path to an external TPL to import",
            subtype='FILE_PATH',
            default=""
    )
    bpy.types.Scene.gx_preset_path = bpy.props.StringProperty(
            name="Flag Preset Folder",
            description="The path to a folder containg GxModelViewer presets.",
            subtype='DIR_PATH',
            default="//"
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

    bpy.types.Scene.draw_only_active_collision_grid = bpy.props.BoolProperty(
            name="Draw Only Active Collision Grids",
            description="Whether or not to only draw a visual representation of the active, selected collision grid",
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
    bpy.types.Scene.stage_game_mode = bpy.props.EnumProperty(
            name="Game Mode",
            description="Game mode of the stage to be exported.",
            items=[('MAIN_GAME', 'Main Game', ''),
                   ('MONKEY_RACE_2', 'Monkey Race 2', ''),
                   ('MONKEY_GOLF_2', 'Monkey Golf 2', ''),
                   ('MONKEY_TARGET_2', 'Monkey Target 2', '')],
            default='MAIN_GAME'
    )

    bpy.types.Scene.fog_type = bpy.props.EnumProperty(
            name="Fog Type",
            description="Type of fog for the stage",
            items=[('GX_FOG_NONE', 'None', ''),
                   ('GX_FOG_LIN', 'Linear', ''),
                   ('GX_FOG_EXP', 'Exponential', ''),
                   ('GX_FOG_EXP2', 'Exponential (2)', ''),
                   ('GX_FOG_REVEXP', 'Reverse Exponential', ''),
                   ('GX_FOG_REVEXP2', 'Reverse Exponential (2)', '')],
            default='GX_FOG_NONE')

    bpy.types.Scene.fog_start_distance = bpy.props.FloatProperty(
            name="Fog Start",
            description="Fog starting distance",
            default=0.0)
    
    bpy.types.Scene.fog_end_distance = bpy.props.FloatProperty(
            name="Fog End",
            description="Fog ending distance",
            default=0.0)
    
    bpy.types.Scene.fog_color = bpy.props.FloatVectorProperty(
            name="Fog Color",
            description="Fog color",
            subtype='COLOR')

    bpy.types.Scene.background_import_path = bpy.props.StringProperty(
            name="BG Import Path",
            description="The path to a .XML background file to import",
            subtype='FILE_PATH',
            default=""
    )
    bpy.types.Scene.background_import_preview = bpy.props.BoolProperty(
            name="Import Background Previews",
            default=False
    )
    bpy.types.Scene.background_import_use_cubes = bpy.props.BoolProperty(
            name="Use Cube Empty Approximations",
            default=False
    )

    # Special properties for Monkey Ball objects (also for fancy UI property display)
    bpy.types.Object.item_group_properties = bpy.props.PointerProperty(
            type=stage_editor.ItemGroupProperties)
    bpy.types.Object.alt_model_properties = bpy.props.PointerProperty(
            type=stage_editor.AltModelProperties)
    bpy.types.Object.stage_model_properties = bpy.props.PointerProperty(
            type=stage_editor.StageModelProperties)
    bpy.types.Object.goal_properties = bpy.props.PointerProperty(
            type=stage_editor.GoalProperties)
    bpy.types.Object.start_properties = bpy.props.PointerProperty(
            type=stage_editor.StartProperties)
    bpy.types.Object.wormhole_properties = bpy.props.PointerProperty(
            type=stage_editor.WormholeProperties)
    bpy.types.Object.switch_properties = bpy.props.PointerProperty(
            type=stage_editor.SwitchProperties)

    bpy.types.Material.mat_preset = bpy.props.StringProperty(name="Material Preset",
                                        update=lambda s,c: update_preset(s, c, "mat_preset", "MAT"))
    bpy.types.Material.mesh_preset = bpy.props.StringProperty(name="Mesh Preset",
                                        update=lambda s,c: update_preset(s, c, "mesh_preset", "MESH"))
    menus.handle_register()

    bpy.app.handlers.load_post.append(load_handler)
    print("Successfully registered {} with {} modules".format(bl_info["name"], len(modules)))
    for module in modules:
        print("-", module.__name__)

# Unregister
def unregister():
    menus.handle_unregister()

    del bpy.types.Scene.export_timestep
    del bpy.types.Scene.export_value_round
    del bpy.types.Scene.export_time_round
    del bpy.types.Scene.export_config_path
    del bpy.types.Scene.export_model_path
    del bpy.types.Scene.export_gma_path
    del bpy.types.Scene.export_tpl_path
    del bpy.types.Scene.export_raw_stagedef_path
    del bpy.types.Scene.export_stagedef_path
    del bpy.types.Scene.export_background_path
    del bpy.types.Scene.import_gma_path
    del bpy.types.Scene.import_tpl_path
    del bpy.types.Scene.gx_preset_path
    del bpy.types.Scene.draw_falloutProp
    del bpy.types.Scene.draw_stage_objects
    del bpy.types.Scene.draw_collision_grid
    del bpy.types.Scene.auto_path_names
    del bpy.types.Scene.optimize_keyframes
    del bpy.types.Scene.falloutProp
    del bpy.types.Scene.stage_game_mode
    del bpy.types.Object.item_group_properties 
    del bpy.types.Object.alt_model_properties 
    del bpy.types.Scene.background_import_path
    del bpy.types.Scene.background_import_preview
    del bpy.types.Scene.background_import_use_cubes

    del bpy.types.Object.stage_model_properties 
    del bpy.types.Object.goal_properties 
    del bpy.types.Object.start_properties 
    del bpy.types.Object.wormhole_properties 
    del bpy.types.Object.switch_properties 
    del bpy.types.Scene.fog_type
    del bpy.types.Scene.fog_start_distance
    del bpy.types.Scene.fog_end_distance
    del bpy.types.Scene.fog_color

    del bpy.types.Material.mat_preset
    del bpy.types.Material.mesh_preset

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

