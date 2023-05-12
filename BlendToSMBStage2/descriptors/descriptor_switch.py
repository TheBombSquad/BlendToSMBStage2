import sys

from sys import platform
from .descriptor_base import DescriptorBase
from .. import stage_object_drawing, generate_config

import xml.etree.ElementTree as etree

# Switch
class DescriptorSwitch(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[SW_"

    @staticmethod
    def generate_xml(parent_element, obj):
        sub = generate_config.generate_generic_obj_element(obj, "switch", parent_element, position=True, rotation=True)

        # Switch type
        switch_type = DescriptorSwitch.get_object_type(obj)
        type = etree.SubElement(sub, "type")
        type.text = switch_type

        # Switch linked ID
        group = etree.SubElement(sub, "animGroupId")
        if obj['linkedObject'] is not None:
            if 'animId' in obj['linkedObject'].keys():
                group.text = str(obj['linkedObject']['animId'])
            else:
                raise Exception("Switch " + obj.name + " not linked to an item group")
        else: 
            if "linkedId" in obj.keys():
                group.text = str(obj["linkedId"])
            else:
                raise Exception("Switch " + obj.name + " not linked to an item group")

    @staticmethod
    def render(obj):
        stage_object_drawing.draw_switch(obj)

    @staticmethod
    def construct(obj):
        obj["linkedObject"] = None
        obj["linkedId"] = 0

    @staticmethod
    def get_object_type(obj):
        types = {"RW": "REWIND", 
                "PLAY_BACKWARDS":"PLAY_BACKWARDS", 
                "PAUSE":"PAUSE", 
                "PLAY":"PLAY", 
                "FF":"FAST_FORWARD"}
        switch_name = obj.name
        switch_type = switch_name[4:switch_name.index(']')]
        return types[switch_type]

    @staticmethod
    def return_properties(obj):
        return obj.switch_properties
