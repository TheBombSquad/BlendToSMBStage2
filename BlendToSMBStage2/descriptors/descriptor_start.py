import sys

from sys import platform
from .descriptor_base import DescriptorBase
from .. import stage_object_drawing, generate_config

if platform == "linux" or platform == "linux2":
    from lxml import etree
else:
    import xml.etree.ElementTree as etree

# Starting position
class DescriptorStart(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[START]"

    @staticmethod
    def generate_xml(parent_element, obj):
        generate_config.generate_generic_obj_element(obj, "start", parent_element, position=True, rotation=True, name=False)

    @staticmethod
    def render(obj):
        stage_object_drawing.draw_start(obj)

    @staticmethod
    def return_properties(obj):
        return obj.start_properties

