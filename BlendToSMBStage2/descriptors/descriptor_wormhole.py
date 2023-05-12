import random
import sys

from sys import platform
from .descriptor_base import DescriptorBase
from .. import stage_object_drawing, generate_config

import xml.etree.ElementTree as etree

# Wormhole
class DescriptorWH(DescriptorBase):
    # Returns the object name
    @staticmethod
    def get_object_name():
        return "[WH"

    # Generates the XML element for the object
    @staticmethod
    def generate_xml(parent_element, obj):
        # Wormhole ID
        whId = str(obj["whId"])

        # Linked ID
        if obj["linkedObject"] is not None:
            whLinkedId = obj["linkedObject"]["whId"]
        else:
            if "linkedId" in obj.keys():
                whLinkedId = obj["linkedId"]
            else:
                raise Exception("Wormhole not linked to another wormhole")

        sub = generate_config.generate_generic_obj_element(obj, "wormhole", parent_element, position=True, rotation=True, name=whId)

        whLinkedIdE = etree.SubElement(sub, "destinationName")
        whLinkedIdE.text = str(whLinkedId)

    # Renders the object in the 3D viewport through OpenGL
    @staticmethod
    def render(obj):
        stage_object_drawing.draw_wh(obj)

    # Assigns custom properties to the object
    @staticmethod
    def construct(obj):
        obj["whId"] = random.randint(1, 65535)
        obj["linkedId"] = 0
        obj["linkedObject"] = None

    @staticmethod
    def return_properties(obj):
        return obj.wormhole_properties
