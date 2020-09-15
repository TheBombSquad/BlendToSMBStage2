import sys
import random
import math
import bpy

from sys import platform
from .descriptor_base import DescriptorBase
from .. import stage_object_drawing, generate_config, statics

if platform == "linux" or platform == "linux2":
    from lxml import etree
else:
    import xml.etree.ElementTree as etree

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

        # Animation loop time (converted to frames from seconds)
        loopTime = (bpy.context.scene.frame_end - bpy.context.scene.frame_start+1)/bpy.context.scene.render.fps
        if "animLoopTime" in obj.keys() and obj["animLoopTime"] != -1:
            loopTime = obj["animLoopTime"]

        animLoopTime = etree.SubElement(xig, "animLoopTime")
        animLoopTime.text = str(loopTime) 

        # Animation ID
        animIdE = etree.SubElement(xig, "animGroupId")
        animIdE.text = str(obj["animId"])

        # Initial playing state
        animInitState = obj["initPlaying"]
        if animInitState == 0: animInitStateStr = "PAUSE"
        elif animInitState == 1: animInitStateStr = "PLAY"
        elif animInitState == 2: animInitStateStr = "PLAY_BACKWARDS"
        elif animInitState == 3: animInitStateStr = "FAST_FORWARD"
        elif animInitState == 4: animInitStateStr = "REWIND"
        
        animInitStateE = etree.SubElement(xig, "animInitialState")
        animInitStateE.text = animInitStateStr

        # Type of animation
        animType = obj["loopAnim"]
        if animType == 0: animTypeStr = "PLAY_ONCE_ANIMATION"
        elif animType == 1: animTypeStr = "LOOPING_ANIMATION"
        elif animType == 2: animTypeStr = "SEESAW"
        else: raise ValueError("Object " + obj.name + " has invalid anim type " + str(animType))

        animTypeE = etree.SubElement(xig, "animSeesawType")
        animTypeE.text = animTypeStr

        # Conveyor speed
        conv = etree.SubElement(xig, "conveyorSpeed", x=str(obj.get("conveyorX", 0.0)),
                                                      y=str(obj.get("conveyorY", 0.0)),
                                                      z=str(obj.get("conveyorZ", 0.0)))

        # Seesaw properties
        seesawSens = etree.SubElement(xig, "seesawSensitivity")
        seesawSens.text = str(obj.get("seesawSensitivity", 0.0))
        seesawFriction = etree.SubElement(xig, "seesawFriction")
        seesawFriction.text = str(obj.get("seesawFriction", 0.0)) 
        seesawSpring = etree.SubElement(xig, "seesawSpring")
        seesawSpring.text = str(obj.get("seesawSpring", 0.0))

        # Texture scroll
        texScroll = etree.SubElement(xig, "textureScroll", x=str(obj.get("texScrollUSpeed", 0.0)),
                                                           y=str(obj.get("texScrollVSpeed", 0.0)))

        # Collision grid start/step/count
        grid = etree.SubElement(xig, "collisionGrid")
        etree.SubElement(grid, "start", x=str(obj["collisionStartX"]), z=str(obj["collisionStartY"]))
        etree.SubElement(grid, "step", x=str(obj["collisionStepX"]), z=str(obj["collisionStepY"]))
        etree.SubElement(grid, "count", x=str(obj["collisionStepCountX"]), z=str(obj["collisionStepCountY"]))

        return xig

    @staticmethod
    def render(obj):
        draw_grid = bpy.context.scene.draw_collision_grid
        stage_object_drawing.draw_ig(obj, draw_grid) 

    @staticmethod
    def construct(obj):
        obj["collisionStartX"] = -256.0
        obj["collisionStartY"] = -256.0
        obj["collisionStepX"] = 32.0
        obj["collisionStepY"] = 32.0
        obj["collisionStepCountX"] = 16
        obj["collisionStepCountY"] = 16

        new_id = random.randint(1, 65535)
        while new_id in statics.anim_id_list:
            new_id = random.randint(1, 65535)

        statics.anim_id_list.append(new_id)

        obj["animId"] = new_id 
        obj["initPlaying"] = 1 
        obj["loopAnim"] = 1
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

    @staticmethod
    def return_properties(obj):
        return obj.item_group_properties
