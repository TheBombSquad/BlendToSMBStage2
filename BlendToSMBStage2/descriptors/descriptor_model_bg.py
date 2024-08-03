import sys
import bpy

from sys import platform
from .descriptor_base import DescriptorBase
from .. import stage_object_drawing, generate_config

import xml.etree.ElementTree as etree

# Background model
class DescriptorBG(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[BG]"

    @staticmethod
    def generate_xml_with_anim(parent_element, obj, anim_data):
        print("\tBackground model: " + obj.name)
        
        # Export with pos/rot/scale if BG object has animation, otherwise don't
        if obj.animation_data is not None and obj.animation_data.action is not None:
            bg_xml = generate_config.generate_generic_obj_element(obj, "backgroundModel", parent_element, position=True, rotation=True, scale=True, name=False)
        else:
            bg_xml = generate_config.generate_generic_obj_element(obj, "backgroundModel", parent_element, position=True, rotation=True, scale=True, name=False, static_bg=True)

        # Cleans up names
        if "[EXT:" in obj.name:
                model = etree.SubElement(bg_xml, "name")
                model.text = re.search(r".*\[EXT:(.*)\].*", obj.name).group(1)
        else:
            model = etree.SubElement(bg_xml, "name")
            model.text = obj.name.replace(" ", "_")

        # Model mesh type
        if "meshType" in obj.keys():
            meshTypeE = etree.SubElement(bg_xml, "meshType")
            meshTypeE.text = str(obj['meshType'])

        # Animation loop time
        if "animLoopTime" in obj.keys():
            loopTime = (bpy.context.scene.frame_end - bpy.context.scene.frame_start+1)/bpy.context.scene.render.fps
            if obj["animLoopTime"] != -1: loopTime = obj["animLoopTime"]
            animLoopTimeE = etree.SubElement(bg_xml, "animLoopTime")
            animLoopTimeE.text = str(loopTime)
                    
        # Texture scroll
        if "texScrollUSpeed" in obj.keys():
            texScroll = etree.SubElement(bg_xml, "textureScroll", x=str(obj["texScrollUSpeed"]),
                                                               y=str(obj["texScrollVSpeed"]))
        # Add animation
        generate_config.generate_anim_xml(bg_xml, anim_data)

    @staticmethod
    def construct(obj):
        obj["animLoopTime"] = -1.0
        obj["meshType"] = 0x1f
        obj["texScrollUSpeed"] = 0.0
        obj["texScrollVSpeed"] = 0.0

    @staticmethod
    def return_properties(obj):
        return obj.alt_model_properties
