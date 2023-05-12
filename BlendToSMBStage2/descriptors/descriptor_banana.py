import sys

from sys import platform
from .descriptor_base import DescriptorBase
from .. import stage_object_drawing, generate_config

import xml.etree.ElementTree as etree

# Banana
class DescriptorBanana(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[BANANA_"

    @staticmethod
    def generate_xml(parent_element, obj):
        banana_type = DescriptorBanana.get_object_type(obj)
        sub = generate_config.generate_generic_obj_element(obj, "banana", parent_element, position=True)
        type = etree.SubElement(sub, "type")
        type.text = banana_type

    @staticmethod
    def render(obj):
        banana_type = DescriptorBanana.get_object_type(obj)
        radius = 0.5 if (banana_type == 'SINGLE') else 1.0
        stage_object_drawing.draw_generic_sphere(obj, radius, stage_object_drawing.COLOR_YELLOW)

    @staticmethod
    def get_object_type(obj):
        if "[BANANA_S]" in obj.name:
            return "SINGLE"
        elif "[BANANA_B]" in obj.name:
            return "BUNCH"
        else:
            raise ValueError("Bad banana type for object " + obj.name)

