import bpy
import sys
import math
from sys import platform

if platform == "linux" or platform == "linux2":
    from lxml import etree
else:
    import xml.etree.ElementTree as etree

from . import descriptors

class OBJECT_OT_generate_config(bpy.types.Operator):
    bl_idname = "object.generate_config"
    bl_label = "Generate Config"
    bl_description = "Generate .XML file for config export"

    def execute(self, context):
        print("Generating config...")

        root = etree.Element("superMonkeyBallStage", version="1.2.0")
        
        # OBJ file path
        modelImport = etree.SubElement(root, "modelImport")
        modelImport.text = context.scene.export_model_path

        # Fallout plane height
        etree.SubElement(root, "falloutPlane", y=str(context.scene.falloutProp))

        # Game mode
        stageType = etree.SubElement(root, "stageType") 
        stageType.text = str(context.scene.stage_game_mode)

        #TODO: This is kind-of a hack to work around stuff being funky with the first item group
        dummyIg = etree.SubElement(root, "itemGroup") 
        grid = etree.SubElement(dummyIg, "collisionGrid")

        etree.SubElement(grid, "start", x = "-256", z = "-256")
        etree.SubElement(grid, "step", x = "32", z = "32")
        etree.SubElement(grid, "count", x = "16", z = "16")

        igs = []
        
        # Start frame of animation
        begin_frame = context.scene.frame_start

        # Marks objects that don't have keyframes on frame 0
        remove_beginframe_objs = []

        # Iterate over all top-level objects
        for obj in [obj for obj in bpy.context.scene.objects if (obj.type == 'EMPTY' or obj.type == 'MESH')]:
            if "[IG]" in obj.name: 
                igs.append(obj)
                context.scene.frame_set(begin_frame)

                # Semi-hacky way to get the object's center of rotation to work properly
                # B2SMB1 inadvertently fixed this by baking *all* keyframes
                begin_keyframe_exists = False
                if obj.animation_data is not None and obj.animation_data.action is not None:
                    fcurves = obj.animation_data.action.fcurves
                    for index in [0, 1, 2]:
                        for curve_type in ["location", "rotation_euler"]:
                            fcurve = fcurves.find(curve_type, index=index)
                            if fcurve is not None:
                                for keyframe_index in range(len(fcurve.keyframe_points)):
                                    if fcurve.keyframe_points[keyframe_index].co[0] == float(begin_frame):
                                        begin_keyframe_exists = True
                                        break
                        else: continue
                        break

                # Remove the beginning keyframe if it didn't exist prior to it being added
                if not begin_keyframe_exists:
                    remove_beginframe_objs.append(obj)

                print("\tInserted frame zero keyframe for item group " + obj.name)
                obj.keyframe_insert("location", frame=begin_frame, options={'INSERTKEY_NEEDED'})
                obj.keyframe_insert("rotation_euler", frame=begin_frame, options={'INSERTKEY_NEEDED'})

            for desc in descriptors.descriptors_nonig:
                match_descriptor = False
                if obj.name.startswith(desc.get_object_name()): 
                    match_descriptor = True
                    desc.generate_xml(root, obj)
                    continue

        # Iterator over all item groups
        for ig in igs: 
            context.scene.frame_set(begin_frame)
            # Children list
            ig_children = [obj for obj in bpy.context.scene.objects if obj.parent == ig]
            ig_children.append(ig)

            # Generate item group XML elements
            if 'collisionStartX' in ig.keys():
                xig = descriptors.DescriptorIG.generate_xml(root, ig)

            else:
                continue

            # Animation
            if ig.animation_data is not None and ig.animation_data.action is not None:
                descriptors.addAnimation(ig, xig)

            # Children of item groups
            for child in ig_children:
                context.scene.frame_set(begin_frame)
                match_descriptor = False

                # Generate elements for listed descriptors (except IGs)
                for desc in descriptors.descriptors:
                    if desc.get_object_name() in child.name and not "[IG]" in child.name:
                        match_descriptor = True
                        desc.generate_xml(xig, child)
                        break
                
                # Object is not a listed descriptor
                if match_descriptor == False:
                    if child.data != None:
                        descriptors.DescriptorModel.generate_xml(xig, child)


        context.scene.frame_set(begin_frame)

        print("Completed, saving...")
        if platform == "linux" or platform == "linux2":
            config = etree.tostring(root, pretty_print=True, encoding="unicode")
        else:
            config = etree.tostring(root, encoding="unicode")
        config_file = open(bpy.path.abspath(context.scene.export_config_path), "w")
        config_file.write(config)
        config_file.close()
        print("Finished generating config")

        # Remove the beginning keyframe if it didn't exist prior to it being added
        for obj in remove_beginframe_objs:
            print("Deleted frame zero keyframe for item group " + obj.name)
            obj.keyframe_delete("location", frame=begin_frame)
            obj.keyframe_delete("rotation_euler", frame=begin_frame)

        return {'FINISHED'}
