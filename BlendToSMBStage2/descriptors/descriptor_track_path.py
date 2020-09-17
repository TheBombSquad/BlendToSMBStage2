import sys

from sys import platform
from .descriptor_base import DescriptorBase
from .. import stage_object_drawing, generate_config

if platform == "linux" or platform == "linux2":
    from lxml import etree
else:
    import xml.etree.ElementTree as etree

# Track Path
class DescriptorTrackPath(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[PATH]"

    @staticmethod
    def generate_xml(parent_element, obj):
        print ("\tObject of type: trackPath")
        track_path_element = etree.SubElement(parent_element, "trackPath")

        player_id = etree.SubElement(track_path_element, "playerID")
        player_id.text = str(obj.get("playerID", 1))

        spline_points = obj.data.splines[0].points
        for index, axisType in [(0, "posX"), (1,  "posY"), (2, "posZ")]:
            axis = etree.SubElement(track_path_element, axisType)
            for i, point in enumerate(spline_points):
                keyframe = etree.Element("keyframe")
                keyframe.set("time", str(i))
                keyframe.set("value", str(point.co[index]))
                keyframe.set("easing", "EASED")
                axis.append(keyframe)
    
    @staticmethod
    def construct(obj):
        obj["playerID"] = 1

    @staticmethod
    def return_properties(obj):
        return obj.start_properties

