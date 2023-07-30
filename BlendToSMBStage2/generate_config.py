import bpy
import math
from sys import platform

from mathutils import Vector

import xml.etree.ElementTree as etree

class AnimData:
    class Channel:
        def __init__(self):
            self.time_val_map: dict[float, float] = {}
            self.prev_val: float | None = None

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

def _write_fcurve_keyframe_values(obj, anim_channel: AnimData.Channel, fcurve):
    start_frame = bpy.context.scene.frame_start
    end_frame = bpy.context.scene.frame_end

    # Sets up a custom animation loop time if one is specified 
    if "animLoopTime" in obj:
        if obj["animLoopTime"] != -1.0:
            end_frame = start_frame + int(round(obj["animLoopTime"]*60))-1

    # Adds all explicitly defined keyframes to the keyframe set
    for keyframe_point in fcurve.keyframe_points:
        if start_frame <= keyframe_point.co[0] <= end_frame+1:
            seconds = round(keyframe_point.co[0]/bpy.context.scene.render.fps, bpy.context.scene.export_time_round)

            fcurve_type = fcurve.data_path
            if fcurve_type == "rotation_euler":
                value = round(math.degrees(keyframe_point.co[1]), bpy.context.scene.export_value_round)
            else:
                value = round(keyframe_point.co[1], bpy.context.scene.export_value_round)

            if fcurve.array_index == 1 and fcurve_type != "scale": value = -1*value
            
            anim_channel.time_val_map[seconds] = value

def _write_obj_prop_at_current_frame(obj, anim_channel: AnimData.Channel, obj_prop):
    start_frame = bpy.context.scene.frame_start
    end_frame = bpy.context.scene.frame_end
    timestep = bpy.context.scene.export_timestep
    optimize = bpy.context.scene.optimize_keyframes

    # Sets up a custom animation loop time if one is specified 
    if "animLoopTime" in obj:
        if obj["animLoopTime"] != -1.0:
            end_frame = start_frame + int(round(obj["animLoopTime"]*60))-1

    # Sets up custom per-object timestep if one is specified
    if "exportTimestep" in obj: 
        if obj["exportTimestep"] != -1:
            timestep = obj["exportTimestep"]

    curr_frame = bpy.context.scene.frame_current
    # Ignore out-of-range frames
    if not (start_frame <= curr_frame <= end_frame and (curr_frame - start_frame) % timestep == 0):
        return

    seconds = round((curr_frame-start_frame)/bpy.context.scene.render.fps, bpy.context.scene.export_time_round)
    val = round(obj_prop, bpy.context.scene.export_value_round)
    if (optimize and (val == anim_channel.prev_val)):
        return
    anim_channel.prev_val = val

    if seconds not in anim_channel.time_val_map:
        anim_channel.time_val_map[seconds] = val

def generate_keyframe_anim_data(obj, anim_data: AnimData):
    if obj.animation_data is None or obj.animation_data.action is None:
        return

    fcurves = obj.animation_data.action.fcurves
    if (fcurve := fcurves.find("location", index=0)) is not None:
        _write_fcurve_keyframe_values(obj, anim_data.pos_x_channel, fcurve)
    if (fcurve := fcurves.find("location", index=1)) is not None:
        _write_fcurve_keyframe_values(obj, anim_data.pos_y_channel, fcurve)
    if (fcurve := fcurves.find("location", index=2)) is not None:
        _write_fcurve_keyframe_values(obj, anim_data.pos_z_channel, fcurve)
    if (fcurve := fcurves.find("rotation_euler", index=0)) is not None:
        _write_fcurve_keyframe_values(obj, anim_data.rot_x_channel, fcurve)
    if (fcurve := fcurves.find("rotation_euler", index=1)) is not None:
        _write_fcurve_keyframe_values(obj, anim_data.rot_y_channel, fcurve)
    if (fcurve := fcurves.find("rotation_euler", index=2)) is not None:
        _write_fcurve_keyframe_values(obj, anim_data.rot_z_channel, fcurve)
    if (fcurve := fcurves.find("scale", index=0)) is not None:
        _write_fcurve_keyframe_values(obj, anim_data.scale_x_channel, fcurve)
    if (fcurve := fcurves.find("scale", index=1)) is not None:
        _write_fcurve_keyframe_values(obj, anim_data.scale_y_channel, fcurve)
    if (fcurve := fcurves.find("scale", index=2)) is not None:
        _write_fcurve_keyframe_values(obj, anim_data.scale_z_channel, fcurve)

def generate_per_frame_anim_data(obj, anim_data: AnimData):
    if obj.animation_data is None or obj.animation_data.action is None:
        return

    fcurves = obj.animation_data.action.fcurves
    if fcurves.find("location", index=0) is not None:
        _write_obj_prop_at_current_frame(obj, anim_data.pos_x_channel, obj.location.x)
    if fcurves.find("location", index=1) is not None:
        _write_obj_prop_at_current_frame(obj, anim_data.pos_y_channel, -obj.location.y)
    if fcurves.find("location", index=2) is not None:
        _write_obj_prop_at_current_frame(obj, anim_data.pos_z_channel, obj.location.z)
    if fcurves.find("rotation_euler", index=0) is not None:
        _write_obj_prop_at_current_frame(obj, anim_data.rot_x_channel, math.degrees(obj.rotation_euler.x))
    if fcurves.find("rotation_euler", index=1) is not None:
        _write_obj_prop_at_current_frame(obj, anim_data.rot_y_channel, -math.degrees(obj.rotation_euler.y))
    if fcurves.find("rotation_euler", index=2) is not None:
        _write_obj_prop_at_current_frame(obj, anim_data.rot_z_channel, math.degrees(obj.rotation_euler.z))
    if fcurves.find("scale", index=0) is not None:
        _write_obj_prop_at_current_frame(obj, anim_data.scale_x_channel, obj.scale.x)
    if fcurves.find("scale", index=1) is not None:
        _write_obj_prop_at_current_frame(obj, anim_data.scale_y_channel, obj.scale.y)
    if fcurves.find("scale", index=2) is not None:
        _write_obj_prop_at_current_frame(obj, anim_data.scale_z_channel, obj.scale.z)

def _generate_anim_channel_xml(parent_xml, anim_channel: AnimData.Channel, name):
    if len(anim_channel.time_val_map) == 0:
        return
    channel_xml = etree.SubElement(parent_xml, name)

    # Create sorted XML keyframe list
    for time in sorted(list(anim_channel.time_val_map.keys())):
        val = anim_channel.time_val_map[time]
        keyframe_xml = etree.SubElement(channel_xml, "keyframe")
        keyframe_xml.set("time", str(time))
        keyframe_xml.set("value", str(val))
        keyframe_xml.set("easing", "LINEAR")

    
def generate_anim_xml(parent_xml, anim_data: AnimData):
    keyframes_xml = etree.Element("animKeyframes")
    # Y and Z need to be swapped for some reason?
    _generate_anim_channel_xml(keyframes_xml, anim_data.pos_x_channel, "posX")
    _generate_anim_channel_xml(keyframes_xml, anim_data.pos_y_channel, "posZ")
    _generate_anim_channel_xml(keyframes_xml, anim_data.pos_z_channel, "posY")
    _generate_anim_channel_xml(keyframes_xml, anim_data.rot_x_channel, "rotX")
    _generate_anim_channel_xml(keyframes_xml, anim_data.rot_y_channel, "rotZ") 
    _generate_anim_channel_xml(keyframes_xml, anim_data.rot_z_channel, "rotY")
    _generate_anim_channel_xml(keyframes_xml, anim_data.scale_x_channel, "scaleX")
    _generate_anim_channel_xml(keyframes_xml, anim_data.scale_y_channel, "scaleZ")
    _generate_anim_channel_xml(keyframes_xml, anim_data.scale_z_channel, "scaleY")
    if len(keyframes_xml) > 0:
        parent_xml.append(keyframes_xml)
