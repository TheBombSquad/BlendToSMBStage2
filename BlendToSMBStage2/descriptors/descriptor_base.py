# Object base class
class DescriptorBase:
    # Returns the object name
    @staticmethod
    def get_object_name():
        pass

    # Generates the XML element for the object
    @staticmethod
    def generate_xml(parent_element, obj):
        pass

    # Renders the object in the 3D viewport through OpenGL
    @staticmethod
    def render(obj):
        pass

    # Assigns custom properties to the object
    @staticmethod
    def construct(obj):
        pass

    # Returns custom properties of an object as Blender properties for UI
    @staticmethod
    def return_properties(obj):
        pass
