import sys
import bpy
import math
import random

#from lxml import etree
import xml.etree.ElementTree as etree

from . import stage_object_drawing, property_dict, statics

# Generate an object entry with any of the following: position, rotation, scale 
def generate_generic_obj_element(obj, obj_type, parent, *, position=False, rotation=False, scale=False, name=True):
    loc = obj.matrix_world.to_translation()
    rot = obj.matrix_world.to_euler("XZY")

    print("\tObject of type: " + obj_type)
    sub = etree.SubElement(parent, obj_type)
    if name:
        nameE = etree.SubElement(sub, "name")
        if '[WH]' in obj.name:
            nameE.text = str(obj["whId"])
        else:
            nameE.text = obj.name

    if position:
        etree.SubElement(sub, "position", x=str(loc.x), y=str(loc.z), z=str(-loc.y))
    if rotation:
        etree.SubElement(sub, "rotation", x=str(math.degrees(rot.x)), y=str(math.degrees(rot.z)), z=str(math.degrees(-rot.y)))
    if scale:
        etree.SubElement(sub, "scale", x=str(obj.scale.x), y=str(obj.scale.z), z=str(obj.scale.y))

    return sub


def addKeyframes(parent, selector, fcurve):
    startFrame = bpy.context.scene.frame_start
    endFrame = bpy.context.scene.frame_end
    active = bpy.context.view_layer.objects.active

    if "animLoopTime" in active:
        if active["animLoopTime"] != -1.0:
            endFrame = startFrame + int(round(active["animLoopTime"]*60))-1

    bpy.context.scene.frame_set(0)
    prev_val = None
    
    timestep = bpy.context.scene.export_timestep

    if "exportTimestep" in active: 
        if active["exportTimestep"] != -1:
            timestep = bpy.context.view_layer.objects.active["exportTimestep"]

    for i in range(startFrame, endFrame, timestep):
        bpy.context.scene.frame_set(i)
        seconds = round((i-startFrame)/bpy.context.scene.render.fps, bpy.context.scene.export_time_round)
        val = round(selector(bpy.context.view_layer.objects.active), bpy.context.scene.export_value_round)
        current_fcurve = fcurve(bpy.context.view_layer.objects.active.animation_data.action)

        if val == prev_val:
            if current_fcurve is not None:
                for keyframe_point in current_fcurve.keyframe_points:
                    if keyframe_point.co[0] == float(bpy.context.scene.frame_current): 
                        keyframe = etree.Element("keyframe")
                        keyframe.set("time", str(seconds))
                        keyframe.set("value", str(keyframe_point.co[1]))
                        keyframe.set("easing", "LINEAR")
                        parent.append(keyframe)
        else:
            prev_val = val
            keyframe = etree.Element("keyframe")
            keyframe.set("time", str(seconds))
            keyframe.set("value", str(val))
            keyframe.set("easing", "LINEAR")
            parent.append(keyframe)

def addPosXAnim(parent):
    addKeyframes(parent, lambda i: i.location.x, lambda f: f.fcurves.find("location", index=0))

def addPosYAnim(parent):
    addKeyframes(parent,lambda i: -i.location.y, lambda f: f.fcurves.find("location", index=1))

def addPosZAnim(parent):
    addKeyframes(parent,lambda i: i.location.z, lambda f: f.fcurves.find("location", index=2))

def addRotXAnim(parent):
    addKeyframes(parent,lambda i: math.degrees(i.rotation_euler.x), lambda f: f.fcurves.find("rotation_euler", index=0))

def addRotYAnim(parent):
    addKeyframes(parent,lambda i: -math.degrees(i.rotation_euler.y), lambda f: f.fcurves.find("rotation_euler", index=1))

def addRotZAnim(parent):
    addKeyframes(parent,lambda i: math.degrees(i.rotation_euler.z), lambda f: f.fcurves.find("rotation_euler", index=2))

def addScaleXAnim(parent):
    addKeyframes(parent, lambda i: i.scale.x, lambda f: f.fcurves.find("scale", index=0))

def addScaleYAnim(parent):
    addKeyframes(parent,lambda i: i.scale.y, lambda f: f.fcurves.find("scale", index=1))

def addScaleZAnim(parent):
    addKeyframes(parent,lambda i: i.scale.z, lambda f: f.fcurves.find("scale", index=2))

def addAnimation(obj, parent):
    print("\tChecking for animation...")
    bpy.context.view_layer.objects.active = obj

    animKeyframes = etree.Element("animKeyframes")
    hasInserted = False

    fcurves = obj.animation_data.action.fcurves

    if fcurves.find("location", index=0):
        print("\t\tAdding X Pos keyframes...")
        posX = etree.SubElement(animKeyframes, "posX")
        addPosXAnim(posX)
        if not hasInserted:
            parent.append(animKeyframes)
            hasInserted = True
    if fcurves.find("location", index=1):
        print("\t\tAdding Y Pos keyframes...")
        posZ = etree.SubElement(animKeyframes, "posZ")
        addPosYAnim(posZ)
        if not hasInserted:
            parent.append(animKeyframes)
            hasInserted = True
    if fcurves.find("location", index=2):
        print("\t\tAdding Z Pos keyframes...")
        posY = etree.SubElement(animKeyframes, "posY")
        addPosZAnim(posY)
        if not hasInserted:
            parent.append(animKeyframes)
            hasInserted = True
    if fcurves.find("rotation_euler", index=0):
        print("\t\tAdding X Rot keyframes...")
        rotX = etree.SubElement(animKeyframes, "rotX")
        addRotXAnim(rotX)
        if not hasInserted:
            parent.append(animKeyframes)
            hasInserted = True
    if fcurves.find("rotation_euler", index=1):
        print("\t\tAdding Y Rot keyframes...")
        rotZ = etree.SubElement(animKeyframes, "rotZ")
        addRotYAnim(rotZ)
        if not hasInserted:
            parent.append(animKeyframes)
            hasInserted = True
    if fcurves.find("rotation_euler", index=2):
        print("\t\tAdding Z Rot keyframes...")
        rotY = etree.SubElement(animKeyframes, "rotY")
        addRotZAnim(rotY)
        if not hasInserted:
            parent.append(animKeyframes)
            hasInserted = True
    if fcurves.find("scale", index=0):
        print("\t\tAdding X Scale keyframes...")
        scaleX = etree.SubElement(animKeyframes, "scaleX")
        addScaleXAnim(scaleX)
        if not hasInserted:
            parent.append(animKeyframes)
            hasInserted = True
    if fcurves.find("scale", index=1):
        print("\t\tAdding Y Scale keyframes...")
        scaleZ = etree.SubElement(animKeyframes, "scaleZ")
        addScaleYAnim(scaleZ)
        if not hasInserted:
            parent.append(animKeyframes)
            hasInserted = True
    if fcurves.find("scale", index=2):
        print("\t\tAdding Z Scale keyframes...")
        scaleY = etree.SubElement(animKeyframes, "scaleY")
        addScaleZAnim(scaleY)
        if not hasInserted:
            parent.append(animKeyframes)
            hasInserted = True

# Object base class
class DescriptorBase:
    # Returns the object name
    @staticmethod
    def get_object_name():
        pass

    # Generates the XML element for the object
    @staticmethod
    def generate_xml(parent_element, obj):
        pass

    # Renders the object in the 3D viewport through OpenGL
    @staticmethod
    def render(obj):
        pass

    # Assigns custom properties to the object
    @staticmethod
    def construct(obj):
        pass

    # Returns custom properties of an object as Blender properties for UI
    @staticmethod
    def return_properties(obj):
        for key in obj.keys():
            layout_panel.prop(obj, "[\"" + key + "\"]") 

    # Sets up the _RNA_UI tag to display non-slider properties in the UI properly
    def rna_ui_setup(obj):
        obj['_RNA_UI'] = {}
        rna_ui = obj['_RNA_UI']
        properties = obj.keys()

        # Assign names and types
        for prop in properties:
            if prop != '_RNA_UI':
                rna_ui[prop] = {}
                # Custom names
                if prop in property_dict.names:
                    rna_ui[prop]['name'] = property_dict.names[prop] 
                # Custom appearances (enum dropdown, bool checkmark, object selector, etc)
                if prop in property_dict.types:
                    rna_ui[prop]['type'] = property_dict.types[prop]
                # Default 
                else:
                    rna_ui[prop]['type'] = 'int'

        # Set up the actual properties
        for prop in properties:
            try: prop_type = rna_ui[prop]['type']
            except KeyError:
                continue
            else:
                if prop_type != 'int':
                    proxy_prop = obj.stage_object_properties.add()
                    sanitized_name = prop[1::]
                    proxy_prop.name = sanitized_name
                    proxy_prop.value = obj[prop]

# Item group
class DescriptorIG(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[IG]"

    @staticmethod
    def generate_xml(parent_element, obj):
        print("\tProcessing item group " + obj.name)
        xig = etree.SubElement(parent_element, "itemGroup")

        # Name
        igName = etree.SubElement(xig, "name")
        igName.text = obj.name

        # Position/Rotation
        etree.SubElement(xig, "rotationCenter", x=str(obj.location.x),
                                                y=str(obj.location.z),
                                                z=str(-obj.location.y))
        etree.SubElement(xig, "initialRotation", x=str(math.degrees(obj.rotation_euler.x)),
                                                 y=str(math.degrees(obj.rotation_euler.z)),
                                                 z=str(math.degrees(-obj.rotation_euler.y)))

        # Animation loop time, ID, initial state, type

        loopTime = (bpy.context.scene.frame_end - bpy.context.scene.frame_start+1)/bpy.context.scene.render.fps
        if "animLoopTime" in obj.keys() and obj["animLoopTime"] != -1:
            loopTime = obj["animLoopTime"]

        animLoopTime = etree.SubElement(xig, "animLoopTime")
        animLoopTime.text = str(loopTime) 

        animIdE = etree.SubElement(xig, "animGroupId")
        animIdE.text = str(obj["animId"])

        animInitState = obj["_initPlaying"]
        if animInitState == 0: animInitStateStr = "PAUSE"
        elif animInitState == 1: animInitStateStr = "PLAY"
        elif animInitState == 2: animInitStateStr = "PLAY_BACKWARDS"
        elif animInitState == 3: animInitStateStr = "FAST_FORWARD"
        elif animInitState == 4: animInitStateStr = "REWIND"
        
        animInitStateE = etree.SubElement(xig, "animInitialState")
        animInitStateE.text = animInitStateStr

        animType = obj["_loopAnim"]
        if animType == 0: animTypeStr = "PLAY_ONCE_ANIMATION"
        elif animType == 1: animTypeStr = "LOOPING_ANIMATION"
        elif animType == 2: animTypeStr = "SEESAW"

        animTypeE = etree.SubElement(xig, "animSeesawType")
        animTypeE.text = animTypeStr

        conv = etree.SubElement(xig, "conveyorSpeed", x=str(obj["conveyorX"]),
                                                      y=str(obj["conveyorY"]),
                                                      z=str(obj["conveyorZ"]))

        seesawSens = etree.SubElement(xig, "seesawSensitivity")
        seesawSens.text = str(obj["seesawSensitivity"])
        seesawFriction = etree.SubElement(xig, "seesawFriction")
        seesawFriction.text = str(obj["seesawFriction"]) 
        seesawSpring = etree.SubElement(xig, "seesawSpring")
        seesawSpring.text = str(obj["seesawSpring"])

        if "texScrollUSpeed" in obj.keys():
            texScroll = etree.SubElement(xig, "textureScroll", x=str(obj["texScrollUSpeed"]),
                                                           y=str(obj["texScrollVSpeed"]))

        grid = etree.SubElement(xig, "collisionGrid")
        etree.SubElement(grid, "start", x=str(obj["collisionStartX"]), z=str(obj["collisionStartY"]))
        etree.SubElement(grid, "step", x=str(obj["collisionStepX"]), z=str(obj["collisionStepY"]))
        etree.SubElement(grid, "count", x=str(obj["collisionStepCountX"]), z=str(obj["collisionStepCountY"]))

        if obj.animation_data is not None: addAnimation(obj, xig)        
        return xig

    @staticmethod
    def render(obj):
        draw_grid = bpy.context.scene.draw_collision_grid
        stage_object_drawing.draw_ig(obj, draw_grid) 

    @staticmethod
    def construct(obj):
        obj["collisionStartX"] = -256
        obj["collisionStartY"] = -256
        obj["collisionStepX"] = 32
        obj["collisionStepY"] = 32
        obj["collisionStepCountX"] = 16
        obj["collisionStepCountY"] = 16

        new_id = random.randint(1, 65535)
        while new_id in statics.anim_id_list:
            new_id = random.randint(1, 65535)

        statics.anim_id_list.append(new_id)

        obj["animId"] = new_id 
        obj["_initPlaying"] = 1 
        obj["_loopAnim"] = 1
        obj["animLoopTime"] = -1.0

        obj["conveyorX"] = 0.0
        obj["conveyorY"] = 0.0
        obj["conveyorZ"] = 0.0

        obj["seesawSensitivity"] = 0.0
        obj["seesawFriction"] = 0.0
        obj["seesawSpring"] = 0.0

        obj["texScrollUSpeed"] = 0.0
        obj["texScrollVSpeed"] = 0.0

        obj["exportTimestep"] = -1

        DescriptorBase.rna_ui_setup(obj)

# Background model
class DescriptorBG(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[BG]"

    @staticmethod
    def generate_xml(parent_element, obj):
        print("\tBackground model: " + obj.name)
        
        if obj.animation_data is not None and obj.animation_data.action is not None:
            bg = generate_generic_obj_element(obj, "backgroundModel", parent_element, position=True, rotation=True, scale=True, name=False)
        else:
            bg = generate_generic_obj_element(obj, "backgroundModel", parent_element, name=False)

        if obj.data == None or obj.name == obj.data.name:
            if "[EXT:" in obj.name:
                model = etree.SubElement(bg, "name")
                model.text = re.search(r".*\[EXT:(.*)\].*", obj.name).group(1)
            else:
                model = etree.SubElement(bg, "name")
                model.text = obj.name.replace(" ", "_")
        else:
            model = etree.SubElement(bg, "name")
            model.text = (obj.name + "_" + obj.data.name).replace(" ", "_")

        if "meshType" in obj.keys():
            meshTypeE = etree.SubElement(bg, "meshType")
            meshTypeE.text = str(obj['meshType'])

        if "animLoopTime" in obj.keys():
            loopTime = (bpy.context.scene.frame_end - bpy.context.scene.frame_start+1)/bpy.context.scene.render.fps
            if obj["animLoopTime"] != -1: loopTime = obj["animLoopTime"]
            animLoopTimeE = etree.SubElement(bg, "animLoopTime")
            animLoopTimeE.text = str(loopTime)
                    
        if "texScrollUSpeed" in obj.keys():
            texScroll = etree.SubElement(bg, "textureScroll", x=str(obj["texScrollUSpeed"]),
                                                               y=str(obj["texScrollVSpeed"]))
        if obj.animation_data is not None and obj.animation_data.action is not None: addAnimation(obj, bg)

    @staticmethod
    def construct(obj):
        obj["animLoopTime"] = -1.0
        obj["meshType"] = 0x1f
        obj["texScrollUSpeed"] = 0.0
        obj["texScrollVSpeed"] = 0.0

        DescriptorBase.rna_ui_setup(obj)

# Foreground model
class DescriptorFG(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[FG]"

    @staticmethod
    def generate_xml(parent_element, obj):
        print("\tForeground model: " + obj.name)
        
        if obj.animation_data is not None and obj.animation_data.action is not None:
            fg = generate_generic_obj_element(obj, "foregroundModel", parent_element, position=True, rotation=True, scale=True, name=False)
        else:
            fg = generate_generic_obj_element(obj, "foregroundModel", parent_element, name=False)

        if obj.data == None or obj.name == obj.data.name:
            if "[EXT:" in obj.name:
                model = etree.SubElement(fg, "name")
                model.text = re.search(r".*\[EXT:(.*)\].*", obj.name).group(1)
            else:
                model = etree.SubElement(fg, "name")
                model.text = obj.name.replace(" ", "_")
        else:
            model = etree.SubElement(fg, "name")
            model.text = (obj.name + "_" + obj.data.name).replace(" ", "_")

        if "meshType" in obj.keys():
            meshTypeE = etree.SubElement(fg, "meshType")
            meshTypeE.text = str(obj['meshType'])

        if "animLoopTime" in obj.keys():
            loopTime = (bpy.context.scene.frame_end - bpy.context.scene.frame_start+1)/bpy.context.scene.render.fps
            if obj["animLoopTime"] != -1: loopTime = obj["animLoopTime"]
            animLoopTimeE = etree.SubElement(fg, "animLoopTime")
            animLoopTimeE.text = str(loopTime)
                    
        if "texScrollUSpeed" in obj.keys():
            texScroll = etree.SubElement(fg, "textureScroll", x=str(obj["texScrollUSpeed"]),
                                                               y=str(obj["texScrollVSpeed"]))

        if obj.animation_data is not None and obj.animation_data.action is not None: addAnimation(obj, fg)

    @staticmethod
    def construct(obj):
        obj["animLoopTime"] = -1.0
        obj["meshType"] = 0x1f
        obj["texScrollUSpeed"] = 0.0
        obj["texScrollVSpeed"] = 0.0

        DescriptorBase.rna_ui_setup(obj)

# Level model
class DescriptorModel(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[MODEL]"

    @staticmethod
    def generate_xml(parent_element, obj):
        print("\tLevel model: " + obj.name)
        if obj.name == obj.data.name:
            name = obj.name.replace(" ", "_")
        else:
            name = (obj.name + "_" + obj.data.name).replace(" ", "_")

        if "[NODISP]" in name:
            dispName = "__" + name
        else:
            dispName = name

        model = etree.SubElement(parent_element, "stageModel")
        modelName = etree.SubElement(model, "name")
        modelName.text = dispName

        if not "[NOCOLI]" in obj.name:
            modelCollision = etree.SubElement(model, "collision")
            modelMeshCol = etree.SubElement(modelCollision, "meshCollision")
            modelMeshName = etree.SubElement(modelMeshCol, "name")
            modelMeshName.text = name

        if "[MIR]" in obj.name:
            mm = etree.SubElement(model, "runtimeReflective")
            mm.text = "true"

        if "[MODEL]" in obj.name and "_cast_shadow" in obj.keys():
            bitflag = 0
            bitflag = bitflag + (obj["_cast_shadow"] << 0)
            bitflag = bitflag + (obj["_receive_shadow"] << 1)
            bitflag = bitflag + (obj["_unk3"] << 2)
            bitflag = bitflag + (obj["_transparencyA"] << 3)
            bitflag = bitflag + (obj["_transparencyB"] << 4)
            bitflag = bitflag + (obj["_unk6"] << 5)
            bitflag = bitflag + (obj["_unk7"] << 6)
            bitflag = bitflag + (obj["_unk8"] << 7)

            bitflagE = etree.SubElement(model, "bitflag")
            bitflagE.text = str(bitflag) 


    @staticmethod
    def construct(obj):
        obj["_cast_shadow"] = False
        obj["_receive_shadow"] = False
        obj["_unk3"] = False
        obj["_transparencyA"] = False
        obj["_transparencyB"] = False
        obj["_unk6"] = False
        obj["_unk7"] = False
        obj["_unk8"] = False

        DescriptorBase.rna_ui_setup(obj)

# Starting position
class DescriptorStart(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[START]"

    @staticmethod
    def generate_xml(parent_element, obj):
        generate_generic_obj_element(obj, "start", parent_element, position=True, rotation=True, name=False)

    @staticmethod
    def render(obj):
        stage_object_drawing.draw_start(obj)

# Bumper
class DescriptorBumper(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[BUMPER]"

    @staticmethod
    def generate_xml(parent_element, obj):
        generate_generic_obj_element(obj, "bumper", parent_element, position=True, rotation=True, scale=True)

    @staticmethod
    def render(obj):
        stage_object_drawing.draw_bumper(obj)

# Jamabar
class DescriptorJamabar(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[JAMABAR]"

    @staticmethod
    def generate_xml(parent_element, obj):
        generate_generic_obj_element(obj, "jamabar", parent_element, position=True, rotation=True, scale=True)

    @staticmethod
    def render(obj):
        stage_object_drawing.draw_jamabar(obj)

# ConeCol
class DescriptorConeCol(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[CONE_COL]"

    @staticmethod
    def generate_xml(parent_element, obj):
        sub = generate_generic_obj_element(obj, "cone", parent_element, position=True, rotation=True)
        radius = etree.SubElement(sub, "radius")
        radius.text = str(obj.scale.x)
        height = etree.SubElement(sub, "height")
        height.text = str(obj.scale.z)

    @staticmethod
    def render(obj):
        stage_object_drawing.draw_cone_col(obj)

# SphereCol
class DescriptorSphereCol(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[SPHERE_COL]"

    @staticmethod
    def generate_xml(parent_element, obj):
        sub = generate_generic_obj_element(obj, "sphere", parent_element, position=True)
        radius = etree.SubElement(sub, "radius")
        radius.text = str(obj.scale.x)

    @staticmethod
    def render(obj):
        stage_object_drawing.draw_sphere_col(obj)

# CylinderCol
class DescriptorCylinderCol(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[CYLINDER_COL]"

    @staticmethod
    def generate_xml(parent_element, obj):
        sub = generate_generic_obj_element(obj, "cylinder", parent_element, position=True, rotation=True)
        radius = etree.SubElement(sub, "radius")
        radius.text = str(obj.scale.x)
        height = etree.SubElement(sub, "height")
        height.text = str(obj.scale.z) 

    @staticmethod
    def render(obj):
        stage_object_drawing.draw_cylinder_col(obj)

# FalloutVolume
class DescriptorFalloutVolume(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[FALLOUT_VOL]"

    @staticmethod
    def generate_xml(parent_element, obj):
        generate_generic_obj_element(obj, "falloutVolume", parent_element, position=True, rotation=True, scale=True)

    @staticmethod
    def render(obj):
        stage_object_drawing.draw_fallout_volume(obj)

# Banana
class DescriptorBanana(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[BANANA_"

    @staticmethod
    def generate_xml(parent_element, obj):
        banana_type = DescriptorBanana.get_object_type(obj)
        sub = generate_generic_obj_element(obj, "banana", parent_element, position=True)
        type = etree.SubElement(sub, "type")
        type.text = banana_type

    @staticmethod
    def render(obj):
        banana_type = DescriptorBanana.get_object_type(obj)
        radius = 0.5 if (banana_type == 'SINGLE') else 1.0
        stage_object_drawing.draw_generic_sphere(obj, radius, stage_object_drawing.COLOR_YELLOW)

    @staticmethod
    def get_object_type(obj):
        banana_type_char =  obj.name[8] 
        banana_type_string = "SINGLE" if (banana_type_char == 'S') else "BUNCH"
        return banana_type_string

# Switch
class DescriptorSwitch(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[SW_"

    @staticmethod
    def generate_xml(parent_element, obj):
        switch_type = DescriptorSwitch.get_object_type(obj)
        sub = generate_generic_obj_element(obj, "switch", parent_element, position=True, rotation=True)
        type = etree.SubElement(sub, "type")
        type.text = switch_type
        group = etree.SubElement(sub, "animGroupId")
        if obj['_linkedObject'] is not None:
            group.text = str(obj['_linkedObject']['animId'])
        else: 
            if "linkedId" in obj.keys():
                group.text = str(obj["linkedId"])
            else:
                raise Exception("Switch not linked to an item group")

    @staticmethod
    def render(obj):
        stage_object_drawing.draw_switch(obj)

    @staticmethod
    def construct(obj):
        obj["_linkedObject"] = None
        obj["linkedId"] = 0

        DescriptorBase.rna_ui_setup(obj)

    @staticmethod
    def get_object_type(obj):
        types = {"RW": "REWIND", 
                "PLAY_BACKWARDS":"PLAY_BACKWARDS", 
                "PAUSE":"PAUSE", 
                "PLAY":"PLAY", 
                "FF":"FAST_FORWARD"}
        switch_name = obj.name
        switch_type = switch_name[4:switch_name.index(']')]
        return types[switch_type]

# Wormhole
class DescriptorWH(DescriptorBase):
    # Returns the object name
    @staticmethod
    def get_object_name():
        return "[WH"

    # Generates the XML element for the object
    @staticmethod
    def generate_xml(parent_element, obj):
        whId = str(obj["whId"])
        if obj["_linkedObject"] is not None:
            whLinkedId = obj["_linkedObject"]["whId"]
        else:
            if "linkedId" in obj.keys():
                whLinkedId = obj["linkedId"]
            else:
                raise Exception("Wormhole not linked to another wormhole")

        sub = generate_generic_obj_element(obj, "wormhole", parent_element, position=True, rotation=True, name=whId)

        whLinkedIdE = etree.SubElement(sub, "destinationName")
        whLinkedIdE.text = str(whLinkedId)


    # Renders the object in the 3D viewport through OpenGL
    @staticmethod
    def render(obj):
        stage_object_drawing.draw_wh(obj)

    # Assigns custom properties to the object
    @staticmethod
    def construct(obj):
        obj["whId"] = random.randint(1, 100000001)
        obj["linkedId"] = 0
        obj["_linkedObject"] = None

        DescriptorBase.rna_ui_setup(obj)

# Goal
class DescriptorGoal(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[GOAL_"

    @staticmethod
    def generate_xml(parent_element, obj):
        goal_type = DescriptorGoal.get_object_type(obj)
        cast_shadow = obj["_cast_shadow"]
        sub = generate_generic_obj_element(obj, "goal", parent_element, position=True, rotation=True)
        typeE = etree.SubElement(sub, "type")
        typeE.text = goal_type
        shadowE = etree.SubElement(sub, "castShadow")
        if cast_shadow: shadowE.text = "true"
        else: shadowE.text = "false"

    @staticmethod
    def render(obj):
        goal_type = DescriptorGoal.get_object_type(obj)
        
        if goal_type == "BLUE": stage_color = stage_object_drawing.COLOR_BLUE
        elif goal_type == "GREEN": stage_color = stage_object_drawing.COLOR_GREEN
        elif goal_type == "RED": stage_color = stage_object_drawing.COLOR_RED
        stage_object_drawing.draw_goal(obj, stage_color)

    @staticmethod
    def construct(obj):
        obj["_cast_shadow"] = True

        DescriptorBase.rna_ui_setup(obj)

    @staticmethod
    def get_object_type(obj):
        types = {"B": "BLUE",
                 "G": "GREEN",
                 "R": "RED"}
        goal_name = obj.name
        goal_type = goal_name[6:goal_name.index(']')]
        return types[goal_type]

# List of all objects
descriptors = [
    DescriptorIG,
    DescriptorBumper,
    DescriptorJamabar,
    DescriptorConeCol,
    DescriptorSphereCol,
    DescriptorCylinderCol,
    DescriptorBanana,
    DescriptorFalloutVolume,
    DescriptorSwitch,
    DescriptorWH,
    DescriptorGoal,
]

descriptors_nonig = {
    DescriptorStart,
    DescriptorBG,
    DescriptorFG,
}

descriptors_all = {
    DescriptorIG,
    DescriptorModel,
    DescriptorBumper,
    DescriptorJamabar,
    DescriptorConeCol,
    DescriptorSphereCol,
    DescriptorCylinderCol,
    DescriptorBanana,
    DescriptorFalloutVolume,
    DescriptorSwitch,
    DescriptorWH,
    DescriptorGoal,
    DescriptorStart,
    DescriptorBG,
    DescriptorFG,
}
