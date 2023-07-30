import sys

from sys import platform
from .descriptor_base import DescriptorBase
from .. import stage_object_drawing, generate_config

import xml.etree.ElementTree as etree

# Goal
class DescriptorGoal(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[GOAL_"

    @staticmethod
    def generate_xml(parent_element, obj):
        goal_type = DescriptorGoal.get_object_type(obj)
        cast_shadow = obj["cast_shadow"]
        sub = generate_config.generate_generic_obj_element(obj, "goal", parent_element, position=True, rotation=True)
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
        obj["cast_shadow"] = True

    @staticmethod
    def get_object_type(obj):
        if "[GOAL_B]" in obj.name:
            return "BLUE"
        elif "[GOAL_G]" in obj.name:
            return "GREEN"
        elif "[GOAL_R]" in obj.name:
            return "RED"
        else:
            raise ValueError("Bad goal type for object " + obj.name)

    @staticmethod
    def return_properties(obj):
        return obj.goal_properties

