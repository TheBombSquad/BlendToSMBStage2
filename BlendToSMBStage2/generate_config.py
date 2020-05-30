import bpy
import sys
import math

#from lxml import etree
import xml.etree.ElementTree as etree

from . import descriptors

def addKeyframes(parent, selector):
    startFrame = bpy.context.scene.frame_start
    endFrame = bpy.context.scene.frame_end

    if "loopTime" in bpy.context.view_layer.objects.active:
        if bpy.context.view_layer.objects.active["loopTime"] != -1:
            endFrame = startFrame + bpy.context.view_layer.objects.active["loopTime"]-1

    bpy.context.scene.frame_set(0)
    prev_val = None
    
    for i in range(startFrame, endFrame, bpy.context.scene.export_timestep):
        bpy.context.scene.frame_set(i)
        seconds = round((i-startFrame)/bpy.context.scene.render.fps, bpy.context.scene.export_time_round)
        val = round(selector(bpy.context.view_layer.objects.active), bpy.context.scene.export_value_round)

        if val != prev_val:
            prev_val = val
            keyframe = etree.Element("keyframe")
            keyframe.set("time", str(seconds))
            keyframe.set("value", str(val))
            keyframe.set("easing", "LINEAR")
            parent.append(keyframe)

def addPosXAnim(parent):
    addKeyframes(parent, lambda i: i.location.x)

def addPosYAnim(parent):
    addKeyframes(parent,lambda i: -i.location.y)

def addPosZAnim(parent):
    addKeyframes(parent,lambda i: i.location.z)

def addRotXAnim(parent):
    addKeyframes(parent,lambda i: math.degrees(i.rotation_euler.x))

def addRotYAnim(parent):
    addKeyframes(parent,lambda i: -math.degrees(i.rotation_euler.y))

def addRotZAnim(parent):
    addKeyframes(parent,lambda i: math.degrees(i.rotation_euler.z))

def addAnimation(obj, parent):
    bpy.context.view_layer.objects.active = obj

    animKeyframes = etree.Element("animKeyframes")
    hasInserted = False

    if "_posXAnim" in obj and obj["_posXAnim"] != 0:
        posX = etree.SubElement(animKeyframes, "posX")
        addPosXAnim(posX)
        if not hasInserted:
            parent.append(animKeyframes)
            hasInserted = True
    if "_posYAnim" in obj and obj["_posYAnim"] != 0:
        posZ = etree.SubElement(animKeyframes, "posZ")
        addPosYAnim(posZ)
        if not hasInserted:
            parent.append(animKeyframes)
            hasInserted = True
    if "_posZAnim" in obj and obj["_posZAnim"] != 0:
        posY = etree.SubElement(animKeyframes, "posY")
        addPosZAnim(posY)
        if not hasInserted:
            parent.append(animKeyframes)
            hasInserted = True
    if "_rotXAnim" in obj and obj["_rotXAnim"] != 0:
        rotX = etree.SubElement(animKeyframes, "rotX")
        addRotXAnim(rotX)
        if not hasInserted:
            parent.append(animKeyframes)
            hasInserted = True
    if "_rotYAnim" in obj and obj["_rotYAnim"] != 0:
        rotZ = etree.SubElement(animKeyframes, "rotZ")
        addRotYAnim(rotZ)
        if not hasInserted:
            parent.append(animKeyframes)
            hasInserted = True
    if "_rotZAnim" in obj and obj["_rotZAnim"] != 0:
        rotY = etree.SubElement(animKeyframes, "rotY")
        addRotZAnim(rotY)
        if not hasInserted:
            parent.append(animKeyframes)
            hasInserted = True

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

        #TODO: This is kind-of a hack to work around stuff being funky with the first item group
        dummyIg = etree.SubElement(root, "itemGroup") 
        grid = etree.SubElement(dummyIg, "collisionGrid")

        etree.SubElement(grid, "start", x = "-256", z = "-256")
        etree.SubElement(grid, "step", x = "32", z = "32")
        etree.SubElement(grid, "count", x = "16", z = "16")

        igs = []
        
        # Start frame of animation
        begin_frame = context.scene.frame_start

        # Iterate over all top-level objects
        for obj in [obj for obj in bpy.context.scene.objects if (obj.type == 'EMPTY' or obj.type == 'MESH')]:
            # Hack to get center of rotation to work properly with frame zero animation
            if "[IG]" in obj.name: 
                igs.append(obj)
                context.scene.frame_set(begin_frame)
                print("\tInserted frame zero keyframe for " + obj.name + ": Position: " + str(obj.location))
                obj.keyframe_insert("location", frame=begin_frame, options={'INSERTKEY_NEEDED'}) 
                obj.keyframe_insert("rotation_euler", frame=begin_frame, options={'INSERTKEY_NEEDED'})
            for desc in descriptors.descriptors_nonig:
                match_descriptor = False
                if obj.name.startswith(desc.get_object_name()): 
                    match_descriptor = True
                    desc.generate_xml(root, obj)

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
            addAnimation(ig, xig)

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
        #config = etree.tostring(root, pretty_print=True, encoding="unicode")
        config = etree.tostring(root, encoding="unicode")
        config_file = open(bpy.path.abspath(context.scene.export_config_path), "w")
        config_file.write(config)
        config_file.close()
        print("Finished generating config")

        return {'FINISHED'}
