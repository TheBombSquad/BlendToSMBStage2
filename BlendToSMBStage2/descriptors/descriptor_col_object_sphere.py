import sys

from sys import platform
from .descriptor_base import DescriptorBase
from .. import stage_object_drawing, generate_config

if platform == "linux" or platform == "linux2":
    from lxml import etree
else:
    import xml.etree.ElementTree as etree

# SphereCol
class DescriptorSphereCol(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[SPHERE_COL]"

    @staticmethod
    def generate_xml(parent_element, obj):
        sub = generate_config.generate_generic_obj_element(obj, "sphere", parent_element, position=True)
        radius = etree.SubElement(sub, "radius")
        radius.text = str(obj.scale.x)

    @staticmethod
    def render(obj):
        stage_object_drawing.draw_sphere_col(obj)

