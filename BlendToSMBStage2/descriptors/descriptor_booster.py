import sys

from sys import platform
from .descriptor_base import DescriptorBase
from .. import stage_object_drawing, generate_config

if platform == "linux" or platform == "linux2":
    from lxml import etree
else:
    import xml.etree.ElementTree as etree

# Booster position
class DescriptorBooster(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[BOOSTER]"

    @staticmethod
    def generate_xml(parent_element, obj):
        generate_config.generate_generic_obj_element(obj, "booster", parent_element, position=True, rotation=True, name=False)

    @staticmethod
    def render(obj):
        stage_object_drawing.draw_booster(obj)

