from .descriptor_banana import DescriptorBanana
from .descriptor_base import DescriptorBase
from .descriptor_booster import DescriptorBooster
from .descriptor_bumper import DescriptorBumper
from .descriptor_col_object_cone import DescriptorConeCol
from .descriptor_col_object_sphere import DescriptorSphereCol
from .descriptor_col_object_cylinder import DescriptorCylinderCol
from .descriptor_fallout_volume import DescriptorFalloutVolume
from .descriptor_goal import DescriptorGoal
from .descriptor_golf_hole import DescriptorGolfHole
from .descriptor_item_group import DescriptorIG
from .descriptor_jamabar import DescriptorJamabar
from .descriptor_model_bg import DescriptorBG
from .descriptor_model_fg import DescriptorFG
from .descriptor_model_stage import DescriptorModel
from .descriptor_start import DescriptorStart
from .descriptor_switch import DescriptorSwitch
from .descriptor_wormhole import DescriptorWH
from .descriptor_track_path import DescriptorTrackPath

# List of all objects
descriptors = {
    DescriptorIG,
    DescriptorModel,
    DescriptorBumper,
    DescriptorJamabar,
    DescriptorConeCol,
    DescriptorSphereCol,
    DescriptorCylinderCol,
    DescriptorBanana,
    DescriptorFalloutVolume,
    DescriptorSwitch,
    DescriptorWH,
    DescriptorGoal,
    DescriptorStart,
    DescriptorBG,
    DescriptorFG,
    DescriptorBooster,
    DescriptorGolfHole,
    DescriptorTrackPath,
}

# List of objects that are not children of item groups
descriptors_root = {
    DescriptorStart,
    DescriptorBG,
    DescriptorFG,
    DescriptorGolfHole,
    DescriptorBooster,
    DescriptorTrackPath,
}

