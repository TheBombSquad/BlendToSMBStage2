import sys

from sys import platform
from .descriptor_base import DescriptorBase
from .. import stage_object_drawing, generate_config

import xml.etree.ElementTree as etree

# Jamabar
class DescriptorJamabar(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[JAMABAR]"

    @staticmethod
    def generate_xml(parent_element, obj):
        generate_config.generate_generic_obj_element(obj, "jamabar", parent_element, position=True, rotation=True, scale=True)

    @staticmethod
    def render(obj):
        stage_object_drawing.draw_jamabar(obj)

