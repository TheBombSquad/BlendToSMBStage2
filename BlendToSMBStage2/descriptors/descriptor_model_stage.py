import sys

from sys import platform
from .descriptor_base import DescriptorBase
from .. import stage_object_drawing, generate_config

import xml.etree.ElementTree as etree
    
# Level model
class DescriptorModel(DescriptorBase):
    @staticmethod
    def get_object_name():
        return "[MODEL]"

    @staticmethod
    def generate_xml(parent_element, obj):
        print("\tLevel model: " + obj.name)

        # Clean up model name
        if obj.name == obj.data.name:
            name = obj.name.replace(" ", "_")
        else:
            name = (obj.name + "_" + obj.data.name).replace(" ", "_")

        if "[NODISP]" in name:
            dispName = "__" + name
        else:
            dispName = name

        model = etree.SubElement(parent_element, "stageModel")
        modelName = etree.SubElement(model, "name")
        modelName.text = dispName

        if not "[NOCOLI]" in obj.name:
            modelCollision = etree.SubElement(model, "collision")
            modelMeshCol = etree.SubElement(modelCollision, "meshCollision")
            if obj.parent:
                flag = obj.parent.get("collisionTriangleFlag", 0)
            else:
                flag = obj.get("collisionTriangleFlag", 0)
            modelMeshColFlag = etree.SubElement(modelMeshCol, "collisionFlag")
            modelMeshColFlag.text = str(flag) 
            modelMeshName = etree.SubElement(modelMeshCol, "name")
            modelMeshName.text = name

        if "[MIR]" in obj.name:
            mm = etree.SubElement(model, "runtimeReflective")
            mm.text = "true"

        if "[MODEL]" in obj.name and "cast_shadow" in obj.keys():
            bitflag = 0
            bitflag = bitflag + (obj["cast_shadow"] << 0)
            bitflag = bitflag + (obj["receive_shadow"] << 1)
            bitflag = bitflag + (obj["unk3"] << 2)
            bitflag = bitflag + (obj["transparencyA"] << 3)
            bitflag = bitflag + (obj["transparencyB"] << 4)

            bitflagE = etree.SubElement(model, "bitflag")
            bitflagE.text = str(bitflag) 

    @staticmethod
    def construct(obj):
        obj["cast_shadow"] = False
        obj["receive_shadow"] = False
        obj["unk3"] = False
        obj["transparencyA"] = False
        obj["transparencyB"] = False

    @staticmethod
    def return_properties(obj):
        return obj.stage_model_properties
