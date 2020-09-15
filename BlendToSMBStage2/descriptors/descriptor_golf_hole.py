import sys

from sys import platform
from .descriptor_base import DescriptorBase
from .. import stage_object_drawing, generate_config

if platform == "linux" or platform == "linux2":
    from lxml import etree
else:
    import xml.etree.ElementTree as etree

# Golf hole position
class DescriptorGolfHole(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[GOLF_HOLE]"

    @staticmethod
    def generate_xml(parent_element, obj):
        generate_config.generate_generic_obj_element(obj, "golfHole", parent_element, position=True, rotation=True, name=False)

    @staticmethod
    def render(obj):
        stage_object_drawing.draw_golf_hole(obj)
