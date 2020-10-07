# Blend2SMBStage2 

This is a Blender plugin that allows you to map out a Super Monkey Ball stage 
in Blender, and export the model, stage configuration, and animation to 
files usable by the custom level tools [SMB Workshop 2](https://gitlab.com/CraftedCart/smblevelworkshop2) 
and [GxUtils](https://github.com/TheBombSquad/GxUtils). This plugin is a port of CraftedCart's 
Blend2SMBStage plugin for Blender 2.7x to the latest version of Blender, with support for new 
Workshop 2 functionality not found in previous versions, along with other usability improvements. 
The original version  of the plugin can be found [here.](https://gitlab.com/CraftedCart/BlendToSMBStage)

The latest version of SMB Workshop 2 is highly recommended, and can be downloaded [here.](https://craftedcart.gitlab.io/ws2web/#/download)

A guide ot the usage of this tool, along with documentation in regards to Monkey Ball modding as a whole, can be found [here.](https://docs.google.com/document/d/194QZxrimkjHEzSSMKbafs86PnmiYmFBZUnoaEnks4es/edit)

## Setup
To download the plugin, [click here to get the latest list of releases,](https://github.com/TheBombSquad/BlendToSMBStage2/releases), then download the latest .ZIP file. You don't need to extract the files in the downloaded .zip file. Open Blender 2.80, and go to Edit-\>Preferences in the menu bar. Go to the 'Add-ons' tab, and select 'Install...'. Navigate to, and select the downloaded .zip file. Search for "BlendToSMBStage2" in the Add-ons list, and then tick the checkmark next to the addon. The add-on will then be installed. You can access the stage object functionality through the 'Blend2SMB' tab on the right of the 3D viewport. If you can't see it, click the grey `+` icon in the top right of the 3D viewport.

If you want to import an old Blend file from 2.79 or earlier, you will need to convert the file to Cycles in order to get materials to show up properly. You can use the plugin 'Material Utils Special' in 2.79 to achieve this. This is an add-on that can be installed in a default installation of 2.79. You can go to File-\>User Preferences and locate it in the Add-ons tab. If this process is not done, you'll need to re-assign textures to your stage.

[Here is a script you can paste into the text editor](https://github.com/TheBombSquad/batch-convert-to-cycles/blob/master/batch_convert_to_cycles.py) that takes a folder as input, and converts all of the Blend files in the folder to ones compatible with 2.8. This script uses the 'Material Utils Special' plugin, and it needs to be enabled before running the script. You can modify the folder that is to be used in the text editor. 

## Changes
### Change List
* Now supports Blender versions 2.80 and higher. Not compatible with 2.79b or earlier versions of Blender.
* Added support for the following stage objects:
    - Jamabars
    - Cone collision objects
    - Sphere collision objects
    - Cylinder collision objects
    - Animated background objects (including scale keyframes)
    - Animated and non-animated foreground objects (including scale keyframes)
* Added the ability to add texture scroll to item groups, background and foreground objects.
* Added the ability to export animation for background and foreground objects.
  Background and foreground objects support scale keyframe animation.
* A toggle for whether or not goals cast shadows has been added.
* Level models can now have special properties toggled, including
  casting/receiving shadows, and type A and B transparency.
* Initial animation state and animation type are now selectable from a list.
* Seesaw properties are now configurable for item groups.
* Linking switches to item groups can now be done by selecting the item group
  empty from a list, rather than using IDs.
* Linking wormholes to other wormholes can now be done by selecting the
  wormhole empty from a list, rather than using IDs.
* Added visual representations for all stage objects.
* Properties of stage objects have been given more readable names, and are
  accessible through the 'Active Object Settings' panel.
* Keyframe generation has been optimized, such that redundant keyframes are no
  longer generated, resulting in reduced file size.
* Keyframe generation timestep can now be defined per item group. Item groups
  that do not have a defined timestep will use the global setting.
* Defining item groups or other objects as animated is no longer an option.
  Whether or not an object is animated is determined automatically on export,
  and is based on present animation channels.
* 'Degenerate Dissolve' is now performed automatically on OBJ export, to
  reduce the likelihood of zero-area-face-related crashes in Monkey Ball.
* The current frame is automatically set to frame 0 on OBJ export.
* (WS2 change) Setting objects as 'runtime reflective' no longer causes mirror
  planes to appear darker than normal.

### Wormholes and Switches
Connecting wormholes has been simplified. In order to link two wormholes
together, all that you need to do is select the destination wormhole from
the 'Linked' list in the 'Active Object Settings' panel. The wormholes will
then be linked. You can link a wormhole to itself, several wormholes to a single
wormhole, or a wormhole to another wormhole. A wormhole cannot be unlinked.
If you are importing an old Blend file with wormholes that were previously
linked before this update, the wormholes will remain linked. However, the
'Linked' attribute  will appear empty. This will not affect exporting. You can
re-select the destination wormhole if you wish.

Linking switches to item groups has also been simplified in a similar manner.
Simply select an item group from the 'Linked' list under the 'Active Object
Settings' panel, and the switch will control the animation of the linked
item group. Switches *must* be linked to an *item group* - no other object
will work, and they cannot be left unlinked. Switches imported from old an old
Blend file will remain linked, although the 'Linked' attribute will appear empty.
This will not affect exporting.

### Cone, Sphere, Cylinder Collision
Cone, sphere, and cylinder collision objects are invisible objects that
represent a collidable object of their respective shape. These can be used to
give rounded objects more accurate collision, and reduce the lag associated
with the high collision triangle count of these rounded objects. When using
these objects, the visible object you wish to define the collision for should
be made non-collidable (NOCOLI). Examples of stages which use these in the
vanilla game include  Domes (sphere collision objects), 5 Drums (cone collision objects), 
and Drums (cylinder collision objects).

### Background Objects
Background objects can now be animated. If a background object has an
animation associated with it, it will automatically be exported, with the
specified timestep, or the global timestep if none is specified. Background objects
are unique in that they allow for scaling keyframes, in addition to position
and rotation keyframes. Background object animation requires the OBJ file to be
exported through the plugin, as the origin of the object must be at the world
origin.

### Foreground Objects
Foreground objects are similar to background objects. They are not parented 
to an item group, and behave exactly the same as background objects, with 
the exception that the model tilts with the stage itself. They do not appear 
on the minimap, either.

### Level Model Flags
Level models can have specific flags that can effect their visual appearance.
Shadows in Monkey Ball are handled using a system of shadow receiving and
shadow casting objects. By default, models do not cast or receive shadows.
If a model is flagged to receive shadows, certain stage objects will cast
shadows on them if they are set to cast shadows, including goals or other
level models if they are flagged to cast shadows. (It is important to note 
that, in GxModelViewer, all shadow casting objects must come *before* the 
shadow receiving object, otherwise, the shadows will not show up.) Transparency 
is also possible using these  flags. To add custom flags to a model, click 
the "Add Custom Model Properties" button under the 'Active Object Settings' 
panel. Background and foreground objects cannot have these flags applied to them. 

### Texture Scroll
Texture scroll is relatively easy to implement. Just set U (horizontal) and V
(vertical) scroll speed for an item groups, a background object, or a foreground
object. The speed of the texture scroll is dependent on the item group or
background/foreground model. The location of the scrolling texture is dependent
on the material. After exporting, you can mark one or more materials for
texture scroll in GxModelViewer by changing the material flag for each material
in a mesh. You'll need to add `00020000` to the material flag of the material you
wish to apply texture scroll to. So, for example, if the default material
flag is `000007D4`, you'll want to change it to `000207D4`. You do not have to mark
every single material in a mesh with this flag - only the ones you wish to
apply texture scroll to. This allows you to have an item group that has both
scrolling and non-scrolling textures.

## Known Bugs
There are some bugs present that I'm not quite sure how to fix yet. 
* Fallout plane height is not transferred from old Blend files, and will 
default to -10.
* Stage objects do not automatically draw on file load. You need to press
the "Draw Stage Objects" button to make them show up.
* Conveyor vectors don't look very pretty
