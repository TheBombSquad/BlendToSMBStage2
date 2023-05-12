import sys

from sys import platform
from .descriptor_base import DescriptorBase
from .. import stage_object_drawing, generate_config

import xml.etree.ElementTree as etree

# CylinderCol
class DescriptorCylinderCol(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[CYLINDER_COL]"

    @staticmethod
    def generate_xml(parent_element, obj):
        sub = generate_config.generate_generic_obj_element(obj, "cylinder", parent_element, position=True, rotation=True)
        radius = etree.SubElement(sub, "radius")
        radius.text = str(obj.scale.x)
        height = etree.SubElement(sub, "height")
        height.text = str(obj.scale.z) 

    @staticmethod
    def render(obj):
        stage_object_drawing.draw_cylinder_col(obj)

