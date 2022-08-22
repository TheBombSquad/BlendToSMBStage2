from collections import defaultdict
import bpy
import sys
import math
from sys import platform

from mathutils import Vector

if platform == "linux" or platform == "linux2":
    from lxml import etree
else:
    import xml.etree.ElementTree as etree

class AnimData:
    class Channel:
        def __init__(self):
            self.time_val_map = defaultdict({})
            self.last_val = None

    def __init__(self):
        # float time -> float value
        self.pos_x_channel = AnimData.Channel()
        self.pos_y_channel = AnimData.Channel()
        self.pos_z_channel = AnimData.Channel()
        self.rot_x_channel = AnimData.Channel()
        self.rot_y_channel = AnimData.Channel()
        self.rot_z_channel = AnimData.Channel()
        self.scale_x_channel = AnimData.Channel()
        self.scale_y_channel = AnimData.Channel()
        self.scale_z_channel = AnimData.Channel()


# Generate an object entry with any of the following: position, rotation, scale 
def generate_generic_obj_element(obj, obj_type, parent, *, position=False, rotation=False, scale=False, name=True, static_bg=False):
    if static_bg:
        loc = Vector((0,0,0))
        rot = Vector((0,0,0))
        scale = Vector((1,1,1))
    else:
        loc = obj.matrix_world.to_translation()
        rot = obj.matrix_world.to_euler("XZY")
        scale = obj.scale

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
        etree.SubElement(sub, "scale", x=str(scale.x), y=str(scale.z), z=str(scale.y))

    return sub

# Generates an XML keyframe list for the specified axis and fcurve type
def addKeyframes(parent, selector, fcurve):
    start_frame = bpy.context.scene.frame_start
    end_frame = bpy.context.scene.frame_end
    active = bpy.context.view_layer.objects.active
    current_fcurve = fcurve(bpy.context.view_layer.objects.active.animation_data.action)
    timestep = bpy.context.scene.export_timestep
    optimize = bpy.context.scene.optimize_keyframes

    # Sets up a custom animation loop time if one is specified 
    if "animLoopTime" in active:
        if active["animLoopTime"] != -1.0:
            end_frame = start_frame + int(round(active["animLoopTime"]*60))-1

    # Sets up custom per-object timestep if one is specified
    if "exportTimestep" in active: 
        if active["exportTimestep"] != -1:
            timestep = bpy.context.view_layer.objects.active["exportTimestep"]

    # Keyframe dict wherek keys are time in seconds and value are values
    keyframes = {}

    # Adds all explicitly defined keyframes to the keyframe list
    if current_fcurve is not None:
        for keyframe_point in current_fcurve.keyframe_points:
            if start_frame <= keyframe_point.co[0] <= end_frame+1:
                seconds = round(keyframe_point.co[0]/bpy.context.scene.render.fps, bpy.context.scene.export_time_round)

                fcurve_type = current_fcurve.data_path
                if fcurve_type == "rotation_euler":
                    value = round(math.degrees(keyframe_point.co[1]), bpy.context.scene.export_value_round)
                else:
                    value = round(keyframe_point.co[1], bpy.context.scene.export_value_round)

                if current_fcurve.array_index == 1 and fcurve_type != "scale": value = -1*value
                
                keyframes[seconds] = value

    bpy.context.scene.frame_set(0)
    prev_val = None
    
    # Iterates through the animation to add intermediate (non-explictly defined) keyframes
    for i in range(start_frame, end_frame+1, timestep):
        bpy.context.scene.frame_set(i)
        seconds = round((i-start_frame)/bpy.context.scene.render.fps, bpy.context.scene.export_time_round)
        val = round(selector(bpy.context.view_layer.objects.active), bpy.context.scene.export_value_round)

        if (optimize and (val == prev_val)):
            continue

        else:
            prev_val = val
            if seconds not in keyframes:
                keyframes[seconds] = val

    # Create sorted XML keyframe list
    for time in sorted(list(keyframes.keys())):
        val = keyframes[time]

        keyframe = etree.Element("keyframe")
        keyframe.set("time", str(time))
        keyframe.set("value", str(val))
        keyframe.set("easing", "LINEAR")
        parent.append(keyframe)

def _write_fcurve_keyframe_values(anim_data: AnimData, fcurve):
    pass

def _write_obj_prop_at_current_frame(anim_data: AnimData, ig_obj_prop):
    pass

def generate_keyframe_anim_data(ig_obj, ig_anim: AnimData):
    fcurves = ig_obj.animation_data.action.fcurves
    if fcurve := fcurves.find("location", index=0) is not None:
        _write_fcurve_keyframe_values(ig_obj, ig_anim.pos_x_channel, fcurve)
    if fcurve := fcurves.find("location", index=1) is not None:
        _write_fcurve_keyframe_values(ig_obj, ig_anim.pos_y_channel, fcurve)
    if fcurve := fcurves.find("location", index=2) is not None:
        _write_fcurve_keyframe_values(ig_obj, ig_anim.pos_z_channel, fcurve)
    if fcurve := fcurves.find("rotation_euler", index=0) is not None:
        _write_fcurve_keyframe_values(ig_obj, ig_anim.rot_x_channel, fcurve)
    if fcurve := fcurves.find("rotation_euler", index=1) is not None:
        _write_fcurve_keyframe_values(ig_obj, ig_anim.rot_y_channel, fcurve)
    if fcurve := fcurves.find("rotation_euler", index=2) is not None:
        _write_fcurve_keyframe_values(ig_obj, ig_anim.rot_z_channel, fcurve)
    if fcurve := fcurves.find("scale", index=0) is not None:
        _write_fcurve_keyframe_values(ig_obj, ig_anim.scale_x_channel, fcurve)
    if fcurve := fcurves.find("scale", index=1) is not None:
        _write_fcurve_keyframe_values(ig_obj, ig_anim.scale_y_channel, fcurve)
    if fcurve := fcurves.find("scale", index=2) is not None:
        _write_fcurve_keyframe_values(ig_obj, ig_anim.scale_z_channel, fcurve)

def generate_per_frame_anim_data(ig_obj, ig_anim: AnimData):
    fcurves = ig_obj.animation_data.action.fcurves
    if fcurves.find("location", index=0) is not None:
        _write_obj_prop_at_current_frame(ig_anim.pos_x_channel, ig_obj.location.x)
    if fcurves.find("location", index=1) is not None:
        _write_obj_prop_at_current_frame(ig_anim.pos_y_channel, -ig_obj.location.y)
    if fcurves.find("location", index=2) is not None:
        _write_obj_prop_at_current_frame(ig_anim.pos_z_channel, ig_obj.location.z)
    if fcurves.find("rotation_euler", index=0) is not None:
        _write_obj_prop_at_current_frame(ig_anim.rot_x_channel, math.degrees(ig_obj.rotation_euler.x))
    if fcurves.find("rotation_euler", index=1) is not None:
        _write_obj_prop_at_current_frame(ig_anim.rot_y_channel, -math.degrees(ig_obj.rotation_euler.y))
    if fcurves.find("rotation_euler", index=2) is not None:
        _write_obj_prop_at_current_frame(ig_anim.rot_z_channel, math.degrees(i.rotation_euler.z))
    if fcurves.find("scale", index=0) is not None:
        _write_obj_prop_at_current_frame(ig_anim.scale_x_channel, ig_obj.scale.x)
    if fcurves.find("scale", index=1) is not None:
        _write_obj_prop_at_current_frame(ig_anim.scale_y_channel, ig_obj.scale.y)
    if fcurves.find("scale", index=2) is not None:
        _write_obj_prop_at_current_frame(ig_anim.scale_z_channel, ig_obj.scale.z)

def generate_anim_xml(parent_xml, anim_data: AnimData):
    pass
