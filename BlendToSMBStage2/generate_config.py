import bpy
import sys
import math
from sys import platform

if platform == "linux" or platform == "linux2":
    from lxml import etree
else:
    import xml.etree.ElementTree as etree

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
    optimize = bpy.context.scene.optimize_keyframes

    if "exportTimestep" in active: 
        if active["exportTimestep"] != -1:
            timestep = bpy.context.view_layer.objects.active["exportTimestep"]

    for i in range(startFrame, endFrame+1, timestep):
        bpy.context.scene.frame_set(i)
        seconds = round((i-startFrame)/bpy.context.scene.render.fps, bpy.context.scene.export_time_round)
        val = round(selector(bpy.context.view_layer.objects.active), bpy.context.scene.export_value_round)
        current_fcurve = fcurve(bpy.context.view_layer.objects.active.animation_data.action)

        if (optimize and  (val == prev_val)):
            if current_fcurve is not None:
                for keyframe_point in current_fcurve.keyframe_points:
                    if keyframe_point.co[0] == float(bpy.context.scene.frame_current): 
                        fcurve_type = current_fcurve.data_path
                        if fcurve_type == "rotation_euler":
                            value = round(math.degrees(keyframe_point.co[1]), bpy.context.scene.export_value_round)
                        else:
                            value = round(keyframe_point.co[1], bpy.context.scene.export_value_round)

                        if current_fcurve.array_index == 1 and fcurve_type != "scale": value = -1*value
                        
                        keyframe = etree.Element("keyframe")
                        keyframe.set("time", str(seconds))
                        keyframe.set("value", str(value))
                        keyframe.set("easing", "LINEAR")
                        parent.append(keyframe)
                        break
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
