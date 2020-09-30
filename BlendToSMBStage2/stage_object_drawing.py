import math
import mathutils
import gpu
import bgl
import bmesh

from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Vector

COLOR_BLACK = (0.0, 0.0, 0.0, 0.8)
COLOR_BLUE = (0.13, 0.59, 0.95, 0.8)
COLOR_RED = (0.96, 0.26, 0.21, 0.8)
COLOR_RED_FAINT = (0.96, 0.26, 0.21, 0.3)
COLOR_YELLOW = (1.0, 0.92, 0.23, 0.8)
COLOR_GREEN = (0.18, 0.83, 0.11, 0.8)
COLOR_GREEN_FAINT = (0.18, 0.83, 0.11, 0.5)
COLOR_PURPLE = (0.40, 0.23, 0.72, 0.8)
ZERO_VEC = (0.0, 0.0, 0.0)

def norm(vec):
    return [float(i) / sum(vec) for i in vec]

def rotate_gl(euler_rot):
    x_rot = Matrix.Rotation(euler_rot[0], 4, 'X')
    y_rot = Matrix.Rotation(euler_rot[1], 4, 'Y')
    z_rot = Matrix.Rotation(euler_rot[2], 4, 'Z')
    final_rot = x_rot @ y_rot @ z_rot
    gpu.matrix.multiply_matrix(final_rot)

def draw_batch(coord, color, primitive_type):
    shader = gpu.shader.from_builtin("3D_UNIFORM_COLOR")
    batch = batch_for_shader(shader, primitive_type, {"pos": coord})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)
    coord.clear()

# Draws a circle on the XY plane. 'rot' is a XYZ Vector in degrees
# Probably a smarter way to do this, like drawing it orthagonal to a unit vector
def draw_circle(pos, rot, radius, color, segments, radians=(2*math.pi)):
    gpu.matrix.push()

    coord = []
    for i in range(0, segments+1):
        segment = (i / segments)*radians

        x = pos[0] + radius * math.cos(segment)
        y = pos[1] + radius * math.sin(segment)
        coord.append((x, y, pos[2]))

    rotate_gl(rot)
    draw_batch(coord, color, 'LINE_STRIP')

    gpu.matrix.pop()

def draw_sphere(pos, radius, color, detailed=False):
    detailed_rotations = [
            Vector((45,0,0)),
            Vector((-45,0,0)),
            Vector((0,45,0)),
            Vector((0,-45,0)),
            Vector((90,45,0)),
            Vector((90,-45,0))
    ]

    sphere_rotations = [
            Vector((0,0,0)),
            Vector((90,0,0)),
            Vector((0,90,0)),
    ]

    if detailed: sphere_rotations.extend(detailed_rotations)

    for rot in sphere_rotations:
        rot_radian = ((math.radians(rot[0]), math.radians(rot[1]), math.radians(rot[2])))
        draw_circle(pos, rot_radian, radius, color, 32)

def draw_box_scaled(pos, scale, color):
    gpu.matrix.push()
    gpu.matrix.translate(pos)
    gpu.matrix.scale(scale)

    coord1 = []

    coord1.append((-0.5, -0.5, -0.5))
    coord1.append((-0.5, -0.5, +0.5))
    coord1.append((-0.5, +0.5, +0.5))
    coord1.append((-0.5, +0.5, -0.5))
    coord1.append((-0.5, -0.5, -0.5))

    coord1.append((+0.5, -0.5, -0.5))
    coord1.append((+0.5, -0.5, +0.5))
    coord1.append((-0.5, -0.5, +0.5))

    coord2 = []
    coord2.append((+0.5, +0.5, +0.5))
    coord2.append((+0.5, +0.5, -0.5))
    coord2.append((+0.5, -0.5, -0.5))
    coord2.append((+0.5, -0.5, +0.5))
    coord2.append((+0.5, +0.5, +0.5))

    coord2.append((-0.5, +0.5, +0.5))
    coord2.append((-0.5, +0.5, -0.5))
    coord2.append((+0.5, +0.5, -0.5))

    draw_batch(coord1, color, "LINE_STRIP")
    draw_batch(coord2, color, "LINE_STRIP")
    gpu.matrix.pop()
    
# Draw prism or a cone with a base having the number of sides provided by arg 'segments'
def draw_cylinder(pos, rot, radius, height, segments, color, *, cone=False, radians=(2*math.pi)):
    gpu.matrix.push()
    top_origin = Vector((pos[0], pos[1], pos[2]+height))

    draw_circle(pos, rot, radius, color, segments, radians)
    if not cone: draw_circle(top_origin, rot, radius, color, segments, radians)

    coord = []
    for i in range(0, segments+1):
        segment = (i / segments)*radians

        x = pos[0] + radius * math.cos(segment)
        y = pos[1] + radius * math.sin(segment)
        coord.append((x, y, pos[2]))
        if cone:
            coord.append(top_origin)
        else:
            coord.append((x, y, top_origin.z)) 
        
    rotate_gl(rot)
    draw_batch(coord, color, 'LINES')
    
    gpu.matrix.pop()

def draw_grid(start_x, start_y, space_x, space_y, repeat_x, repeat_y, z, color):

    coord = []
    for i in range(0, repeat_x + 1):
        coord.append((start_x + space_x * i, start_y, z))
        coord.append((start_x + space_x * i, start_y + space_y * repeat_y, z))

    draw_batch(coord, color, 'LINES')
    coord.clear()

    for i in range(0, repeat_y + 1):
        coord.append((start_x, start_y + space_y * i, z))
        coord.append((start_x + space_x * repeat_x, start_y + space_y * i, z))

    draw_batch(coord, color, 'LINES')

def draw_arrow(start_pos, end_pos, color):
    gpu.matrix.push()
    coord = []

    coord.append(start_pos)
    coord.append(end_pos)

    coord.append(end_pos)
    coord.append((end_pos[0] - 0.2, end_pos[1] - 0.2, end_pos[2]))

    coord.append(end_pos)
    coord.append((end_pos[0] + 0.2, end_pos[1] - 0.2, end_pos[2]))

    draw_batch(coord, color, "LINES")
    gpu.matrix.pop()

def draw_start(obj):
    gpu.matrix.push()
    gpu.matrix.multiply_matrix(obj.matrix_world)
    gpu.matrix.scale((1 / obj.scale.x, 1 / obj.scale.y, 1 / obj.scale.z))  # No scaling

    bgl.glLineWidth(6)
    draw_sphere(ZERO_VEC, 0.5, COLOR_BLACK)
    draw_arrow(ZERO_VEC, (0.0, 1.5, 0.0), COLOR_BLACK)

    bgl.glLineWidth(2)
    draw_sphere(ZERO_VEC, 0.5, COLOR_BLUE)
    draw_arrow(ZERO_VEC, (0.0, 1.5, 0.0), COLOR_BLUE)
    gpu.matrix.pop()

def draw_goal(obj, goal_color):
    gpu.matrix.push()
    gpu.matrix.multiply_matrix(obj.matrix_world)
    gpu.matrix.scale((1/obj.scale.x, 1/obj.scale.y, 1/obj.scale.z)) # No scaling

    bgl.glLineWidth(6)
    # Goal ring
    draw_cylinder((-2.95,1.22,-0.1), ((math.pi*1/2),0,-(math.pi*3/8)), 2.35, 0.2, 16, COLOR_BLACK, radians=((7/4)*math.pi))
    draw_cylinder((-2.95,1.22,-0.1), ((math.pi*1/2),0,-(math.pi*3/8)), 2.15, 0.2, 16, COLOR_BLACK, radians=((7/4)*math.pi))
    # Goal posts
    draw_box_scaled((-1.11,0,0.6), (0.5,0.2,1.2), COLOR_BLACK)
    draw_box_scaled((1.11,0,0.6), (0.5,0.2,1.2), COLOR_BLACK)
    draw_arrow((0,0,0.6), (0.0, 1.5, 0.6), COLOR_BLACK)
    # Party ball box
    draw_box_scaled((-1.2,0,2.2), (0,0.2,1.6), COLOR_BLACK)
    draw_box_scaled((1.2,0,2.2), (0,0.2,1.6), COLOR_BLACK)
    draw_box_scaled((0,0,3),(2.4,0.2,0), COLOR_BLACK)
    # Timer display
    draw_box_scaled((-0.3,0,4.1), (2.2, 0.2, 1.2), COLOR_BLACK)
    draw_box_scaled((1.25,0,3.9), (0.9, 0.2, 0.8), COLOR_BLACK)

    bgl.glLineWidth(2)
    # Goal ring
    draw_cylinder((-2.95,1.22,-0.1), ((math.pi*1/2),0,-(math.pi*3/8)), 2.35, 0.2, 16, goal_color, radians=((7/4)*math.pi))
    draw_cylinder((-2.95,1.22,-0.1), ((math.pi*1/2),0,-(math.pi*3/8)), 2.15, 0.2, 16, goal_color, radians=((7/4)*math.pi))
    # Goal posts
    draw_box_scaled((-1.11,0,0.6), (0.5,0.2,1.2), goal_color)
    draw_box_scaled((1.11,0,0.6), (0.5,0.2,1.2), goal_color)
    draw_arrow((0,0,0.6), (0.0, 1.5, 0.6), goal_color)
    # Party ball box
    draw_box_scaled((-1.2,0,2.2), (0,0.2,1.6), goal_color)
    draw_box_scaled((1.2,0,2.2), (0,0.2,1.6), goal_color)
    draw_box_scaled((0,0,3),(2.4,0.2,0), goal_color)
    # Timer display
    draw_box_scaled((-0.3,0,4.1), (2.2, 0.2, 1.2), goal_color)
    draw_box_scaled((1.25,0,3.9), (0.9, 0.2, 0.8), goal_color)

    gpu.matrix.pop()   

def draw_bumper(obj):
    gpu.matrix.push()
    gpu.matrix.multiply_matrix(obj.matrix_world)

    bgl.glLineWidth(6)
    draw_cylinder(ZERO_VEC, ZERO_VEC, 0.25, 0.7, 8, COLOR_BLACK)
    draw_cylinder((0, 0, 0.28), ZERO_VEC, 0.4, 0.14, 8, COLOR_BLACK)
    #draw_cylinder((0, 0, 0.28), ZERO_VEC, 0.25, 0.14, 8, COLOR_BLACK) 

    bgl.glLineWidth(2)
    draw_cylinder(ZERO_VEC, ZERO_VEC, 0.25, 0.7, 8, COLOR_BLUE)
    draw_cylinder((0, 0, 0.28), ZERO_VEC, 0.4, 0.14, 8, COLOR_BLUE)
    #draw_cylinder((0, 0, 0.28), ZERO_VEC, 0.25, 0.14, 8, COLOR_BLUE) 

    gpu.matrix.pop()

def draw_jamabar(obj):
    gpu.matrix.push()
    gpu.matrix.multiply_matrix(obj.matrix_world)

    bgl.glLineWidth(6)
    draw_box_scaled((0, 0, 0.5), (1, 1.35, 0.4), COLOR_BLACK)
    #draw_box_scaled((0, -1.21, 0.5), (1, 2.5, 1), COLOR_BLACK)
    draw_box_scaled((0, -1.21, 0.5), (1, 1.075, 1), COLOR_BLACK)
    draw_box_scaled((0, 1.21, 0.5), (1, 1.075, 1), COLOR_BLACK)
    draw_arrow((0, 1.75, 0.5), (0, 4, 0.5), COLOR_BLACK)

    bgl.glLineWidth(2)
    draw_box_scaled((0, 0, 0.5), (1, 1.35, 0.4), COLOR_BLUE)
    draw_box_scaled((0, 3, 0.5), (1, 2.5, 1), COLOR_BLUE)
    draw_box_scaled((0, -1.21, 0.5), (1, 1.075, 1), COLOR_BLUE)
    draw_box_scaled((0, 1.21, 0.5), (1, 1.075, 1), COLOR_BLUE)
    draw_arrow((0, 1.75, 0.5), (0, 4.0, 0.5), COLOR_BLUE)

    gpu.matrix.pop()

def draw_cone_col(obj):
    gpu.matrix.push()
    gpu.matrix.multiply_matrix(obj.matrix_world)
    gpu.matrix.scale((1, obj.scale.x/obj.scale.y, 1)) # No Y scaling

    bgl.glLineWidth(6)
    draw_cylinder(ZERO_VEC, ZERO_VEC, 1, 1, 16, COLOR_BLACK, cone=True)

    bgl.glLineWidth(2)
    draw_cylinder(ZERO_VEC, ZERO_VEC, 1, 1, 16, COLOR_PURPLE, cone=True)

    gpu.matrix.pop()

def draw_sphere_col(obj):
    gpu.matrix.push()
    gpu.matrix.multiply_matrix(obj.matrix_world)
    gpu.matrix.scale((1, obj.scale.x/obj.scale.y, obj.scale.x/obj.scale.z)) # No Y/Z scaling

    bgl.glLineWidth(6)
    draw_sphere(ZERO_VEC, 1, COLOR_BLACK, detailed=True)

    bgl.glLineWidth(2)
    draw_sphere(ZERO_VEC, 1, COLOR_PURPLE, detailed=True)

    gpu.matrix.pop()

def draw_cylinder_col(obj):
    gpu.matrix.push()
    gpu.matrix.multiply_matrix(obj.matrix_world)
    gpu.matrix.scale((1, obj.scale.x/obj.scale.y, 1)) # No Y scaling

    bgl.glLineWidth(6)
    draw_cylinder((0,0,-0.5), ZERO_VEC, 1, 1, 16, COLOR_BLACK)

    bgl.glLineWidth(2)
    draw_cylinder((0,0,-0.5), ZERO_VEC, 1, 1, 16, COLOR_PURPLE)

    gpu.matrix.pop()

def draw_fallout_volume(obj):
    gpu.matrix.push()
    gpu.matrix.multiply_matrix(obj.matrix_world)

    bgl.glLineWidth(6)
    draw_box_scaled(ZERO_VEC, (1,1,1), COLOR_BLACK)

    bgl.glLineWidth(2)
    draw_box_scaled(ZERO_VEC, (1,1,1), COLOR_RED_FAINT)

    gpu.matrix.pop()

def draw_switch(obj):
    gpu.matrix.push()
    gpu.matrix.multiply_matrix(obj.matrix_world)
    gpu.matrix.scale((1/obj.scale.x, 1/obj.scale.y, 1/obj.scale.z)) # No scaling

    rotation_rad = (0,0,math.radians(22.5))

    bgl.glLineWidth(6)
    draw_cylinder(ZERO_VEC, rotation_rad, 0.925, 0.15, 8, COLOR_BLACK)
    draw_cylinder(ZERO_VEC, rotation_rad, 0.725, 0.15, 8, COLOR_BLACK)

    bgl.glLineWidth(2)
    draw_cylinder(ZERO_VEC, rotation_rad, 0.925, 0.15, 8, COLOR_BLUE)
    draw_cylinder(ZERO_VEC, rotation_rad, 0.725, 0.15, 8, COLOR_BLUE)
    
    gpu.matrix.pop()

def draw_wh(obj):
    gpu.matrix.push()
    gpu.matrix.multiply_matrix(obj.matrix_world)
    gpu.matrix.scale((1/obj.scale.x, 1/obj.scale.y, 1/obj.scale.z)) # No scaling

    lineWidth = [(6, COLOR_BLACK), (2, COLOR_BLUE)]

    for width, color in lineWidth:
        wh_frame = [(2.15, 0,0),
                    (1.15, 0, 4.23),
                    (0.87929, 0, 4.55),
                    (-0.87929, 0, 4.55),
                    (-1.15, 0, 4.3),
                    (-2.15, 0, 0),
                    (2.15, 0, 0)]
        bgl.glLineWidth(width)
        draw_batch(wh_frame, color, "LINE_STRIP")
        gpu.matrix.push()
        gpu.matrix.multiply_matrix(Matrix.Rotation(math.radians(180), 4, 'Z'))
        gpu.matrix.multiply_matrix(Matrix.Translation(Vector((0,-0.75,1))))
        draw_arrow(ZERO_VEC, (0.0, 1.5, 0.0), color)
        gpu.matrix.pop()

    gpu.matrix.pop()

def draw_ig(obj, draw_collision_grid):
    if "collisionStartX" not in obj.keys():
        return

    startX = obj["collisionStartX"]
    startY = -obj["collisionStartY"]
    stepX = obj["collisionStepX"]
    stepY = -obj["collisionStepY"]
    stepCountX = obj["collisionStepCountX"]
    stepCountY = obj["collisionStepCountY"]

    conveyorEndPos = (obj["conveyorX"]*40, obj["conveyorZ"]*-40, obj["conveyorY"]*40)

    # Draw collision grid
    if obj.animation_data is not None and obj.animation_data.action is not None:
        gpu.matrix.push()
        gpu.matrix.multiply_matrix(obj.matrix_world)
        gpu.matrix.scale((1/obj.scale.x, 1/obj.scale.y, 1/obj.scale.z)) # No scaling

    bgl.glLineWidth(2)
    if draw_collision_grid:
        draw_grid(startX, startY, stepX, stepY, stepCountX, stepCountY, 0, COLOR_GREEN_FAINT)

    if obj.animation_data is not None and obj.animation_data.action is not None:
        gpu.matrix.pop()

    # Draw conveyor arrow
    conveyorObjects = [child for child in obj.children if child.data is not None]
    if obj.data is not None: conveyorObjects.append(obj)

    for conveyorObject in conveyorObjects:
        gpu.matrix.push()
        gpu.matrix.multiply_matrix(conveyorObject.matrix_world)
        gpu.matrix.scale((1/conveyorObject.scale.x, 1/conveyorObject.scale.y, 1/conveyorObject.scale.z)) # No scaling
        lineWidth = [(6, COLOR_BLACK), (2, COLOR_GREEN)]
        for (width, color) in lineWidth:
            coords = [ZERO_VEC, conveyorEndPos]
            bgl.glLineWidth(width)
            draw_batch(coords, color, 'LINES')
        gpu.matrix.pop()

def draw_generic_sphere(obj, radius, color):
    gpu.matrix.push()
    gpu.matrix.multiply_matrix(obj.matrix_world)
    gpu.matrix.scale((1/obj.scale.x, 1/obj.scale.y, 1/obj.scale.z)) # No scaling

    bgl.glLineWidth(6)
    draw_sphere(ZERO_VEC, radius, COLOR_BLACK)

    bgl.glLineWidth(2)
    draw_sphere(ZERO_VEC, radius, color)
    gpu.matrix.pop()

def draw_booster(obj):
    gpu.matrix.push()
    gpu.matrix.multiply_matrix(obj.matrix_world)
    gpu.matrix.scale((1/obj.scale.x, 1/obj.scale.y, 1/obj.scale.z)) # No scaling

    lineWidth = [(6, COLOR_BLACK), (2, COLOR_RED)]

    for width, color in lineWidth:
        bgl.glLineWidth(width)
        draw_box_scaled(ZERO_VEC, (2,1.0,0), color)
        draw_arrow((0, 0.1, 0), (0, 0.1, 0), color)

    gpu.matrix.pop()

def draw_golf_hole(obj):
    gpu.matrix.push()
    gpu.matrix.multiply_matrix(obj.matrix_world)
    gpu.matrix.scale((1/obj.scale.x, 1/obj.scale.y, 1/obj.scale.z)) # No scaling

    lineWidth = [(6, COLOR_BLACK), (2, COLOR_BLUE)]

    for width, color in lineWidth:
        bgl.glLineWidth(width)
        draw_cylinder(ZERO_VEC, ZERO_VEC, 1, 0, 12, color)

    gpu.matrix.pop()
