import sys
import bpy

from sys import platform
from .descriptor_base import DescriptorBase
from .. import stage_object_drawing, generate_config

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
        player_id.text = str(int(obj.get("playerID", 1))-1)

        # Track paths are comprised of spline points, and a delta value associated with handleA/handleB
        # The delta value for the first and last keyframes is zero
        # For everything else, it's the difference between the avg. of the last/current value, and
        # the average of the current/next value.

        spline_points = obj.data.splines[0].points
        for index, axisType in [(0, "posX"), (2,  "posY"), (1, "posZ")]:
            axis = etree.SubElement(track_path_element, axisType)
            for i, point in enumerate(spline_points):
                value = round(point.co[index], 4)

                # Blender to SMB conversion for posZ
                if index == 1: value = -1*value

                # Delta for first/last is zero
                if (i == 0 or i == len(spline_points)-1):
                    delta = 0.0

                else:
                    prev_value = round(spline_points[i-1].co[index], 4)
                    current_value = round(spline_points[i].co[index], 4)
                    next_value = round(spline_points[i+1].co[index], 4)
                    
                    if index == 1:
                        prev_value = prev_value * -1
                        current_value = current_value * -1
                        next_value = next_value * -1
                    
                    cur_prev_avg = (current_value + prev_value)/2
                    cur_next_avg = (current_value + next_value)/2

                    delta = cur_next_avg - cur_prev_avg
                    
                keyframe = etree.Element("keyframe")
                keyframe.set("time", str(float(i)))
                keyframe.set("value", str(value))
                keyframe.set("easing", "LINEAR")
                keyframe.set("handleA", str(round(delta, 4))) 
                keyframe.set("handleB", str(round(delta, 4))) 
                axis.append(keyframe)
    
    @staticmethod
    def construct(obj):
        obj["playerID"] = 1

    @staticmethod
    def return_properties(obj):
        return obj.start_properties

