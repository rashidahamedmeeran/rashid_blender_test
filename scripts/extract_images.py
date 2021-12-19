import bpy
import json
import sys
import os
current_dir = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current_dir)
sys.path.append(parent)
from settings import config


def render_all_images():
    """
    This is the base function that adds all the objects into the blender by
    calling other functions
    :return: none
    """
    delete_objects()

    global scene
    global tree
    global links

    scene = bpy.context.scene
    scene.use_nodes = True
    tree = scene.node_tree
    links = tree.links

    add_plane()
    add_lights()
    add_camera('camera',
               config["cam_loc"],
               config["cam_mode"],
               config["cam_scale"])

    generate_spheres(config["sphere_grid_size"],
                     config["sphere_grid_res"])


def delete_objects():
    """
    This function deletes every object present
    :return: none
    """
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    

def add_plane():
    """
    This function adds a plane into the blender
    :return:
    """
    bpy.ops.mesh.primitive_plane_add()
    mat = add_material("plane_mat")    
    diffuse_bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfDiffuse")
    mat_out = mat.node_tree.nodes["Material Output"]
    links.new(diffuse_bsdf.outputs["BSDF"], mat_out.inputs["Surface"])


def add_material(mat_name):
    """
    This function adds a material to the active object
    :param mat_name: The name of the material to be added (string)
    :return: the material data
    """
    ob = bpy.context.active_object
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
    if ob.data.materials:
        ob.data.materials[0] = mat
    else:
        ob.data.materials.append(mat)
    mat.use_nodes = True
    return mat


def add_lights():
    """
    This function calls the function to add lights at the locations
    specified in config file
    :return: none
    """
    lt_type = config["light_type"]
    loc = config["light_loc"]
    energy = config["light_energy"]
    color = config["light_color"]
    rad = config["light_rad"]
    add_single_light("light_R", lt_type, loc[0], energy, color[0], rad)
    add_single_light("light_G", lt_type, loc[1], energy, color[1], rad)
    add_single_light("light_B", lt_type, loc[2], energy, color[2], rad)


def add_single_light(name, lt_type, loc, energy, color, rad):
    """
    This function adds light with the called specifications into the blender
    :param name: name of the light object
    :param lt_type: type of light 'POINT'/'SUN'/...  (string)
    :param loc: location of the light source  (list of len 3)
    :param energy: the brightness of the light source, 0-100 (int)
    :param color: The color of the light source  (list of len 3)
    :param rad: The radius/shadow_soft_size of the light source (float)
    :return: none
    """
    light_data = bpy.data.lights.new(name=name, type=lt_type)
    light_object = bpy.data.objects.new(name=name, object_data=light_data)
    bpy.context.collection.objects.link(light_object)
    light_object.location = loc
    light_data.energy = energy
    light_data.shadow_soft_size = rad
    light_data.color[0] = color[0]
    light_data.color[1] = color[1]
    light_data.color[2] = color[2]
    

def add_camera(name, loc, cam_type, scale):
    """
    This function adds camera with the called specifications into the blender
    :param name: name of the camera object
    :param loc: location of the camera (list of len 3)
    :param cam_type: type of camera 'ORTHO'/'PERSP'/... (string)
    :param scale: the scale of the camera view
    :return: none
    """
    cam_data = bpy.data.cameras.new(name)
    cam_object = bpy.data.objects.new(name, cam_data)
    bpy.context.collection.objects.link(cam_object)
    cam_object.location = loc
    cam_object.data.type = cam_type
    cam_object.data.ortho_scale = scale
    scene.camera = cam_object


def extract_camera_parameters():
    """
    This function calculates the camera parameters
    :return: the camera parameters
    """
    scale = scene.render.resolution_percentage / 100
    width = scene.render.resolution_x * scale
    height = scene.render.resolution_y * scale

    camdata = scene.camera.data

    focal = camdata.lens
    sensor_width = camdata.sensor_width
    sensor_height = camdata.sensor_height
    pix_aspect_ratio = scene.render.pixel_aspect_x / scene.render.pixel_aspect_y

    if camdata.sensor_fit == 'VERTICAL':
        s_u = width / sensor_width / pix_aspect_ratio
        s_v = height / sensor_height
    else:
        s_u = width / sensor_width
        s_v = height * pix_aspect_ratio / sensor_height

    alpha_u = focal * s_u
    alpha_v = focal * s_v
    u_0 = width / 2
    v_0 = height / 2
    skew = 0
    
    return focal, alpha_u, alpha_v, skew, u_0, v_0


def generate_spheres(sphere_grid_size, sphere_grid_res):
    """
    This function generates a number of spheres(specified by the grid size)
    one by one and calls functions to save the data and rendered images
    :param sphere_grid_size: a list containing the req number of rows
                             and columns where the sphere has to be rendered
                             (list of len 2)
    :param sphere_grid_res: the distance between each row and col (float)
    :return: none
    """
    for col in range(sphere_grid_size[0]):
        for row in range(sphere_grid_size[1]):
            loc = (-(sphere_grid_size[0]//2)+col,
                   -(sphere_grid_size[1]//2)+row,
                   0)
            loc = tuple(i*sphere_grid_res for i in loc)

            if scene.objects.get("sphere"):
                bpy.data.objects["sphere"].location.x = loc[0]
                bpy.data.objects["sphere"].location.y = loc[1]
            else:
                add_sphere(7, config["rad"], loc, 'sphere')

            img_name = str(sphere_grid_size[0])+"x"+str(sphere_grid_size[0])+'_'
            img_name += str(col)+'_'+str(row)

            write_varying_data(img_name, loc)

            render_surface_image('output/surface-images/'+img_name+'.png')
            render_normal_map('output/normal-maps/'+img_name+'.png')
            render_depth_map('output/depth-maps/'+img_name+'.png')

            write_const_data()


def add_sphere(subdiv, rad, loc, name):
    """
    This function adds a sphere with the called specifications into the blender
    :param subdiv: value for the intensity of the triangles in the sphere (0-10)
    :param rad: the radius of the sphere (float)
    :param loc: the location of the sphere (tuple of len 3)
    :param name: the name of the sphere object
    :return: none
    """
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv,
                                          radius=rad,
                                          location=loc)
    sph = bpy.context.selected_objects[0]
    sph.name = name
    mat = add_material("sphere_mat")
    bsdf = mat.node_tree.nodes.get("Diffuse BSDF")
    if bsdf:
        mat.node_tree.nodes.remove(bsdf)
    diffuse_bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfDiffuse")
    mat_out = mat.node_tree.nodes["Material Output"]
    links.new(diffuse_bsdf.outputs["BSDF"], mat_out.inputs["Surface"])


def write_varying_data(file_name, loc):
    """
    This functions writes the location of the current sphere into a json file
    :param file_name: the json filename matching the rendered
                      image name (string)
    :param loc: the location of the sphere (tuple of len 3)
    :return: none
    """
    with open('output/data/'+file_name+'.json', mode='w') as json_file:
        out_data_varying = {'sph_x': loc[0],
                            'sph_y': loc[1],
                            'sph_z': loc[2]}
        json.dump(out_data_varying, json_file)


def render_surface_image(save_loc):
    """
    This functions renders the surface image and saves it in the loc specified
    :param save_loc: the save location of the image (string)
    :return: none
    """
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = save_loc
    bpy.context.view_layer.use_pass_normal = True
    bpy.ops.render.render(write_still=1)
    

def render_normal_map(save_loc):
    """
    This functions renders the normal map and saves it in the location specified
    :param save_loc: the save location of the image (string)
    :return: none
    """
    area = next(ar for ar in bpy.context.screen.areas if ar.type == 'VIEW_3D')
    for sp in area.spaces:
        if sp.type == 'VIEW_3D':
            scene.render.engine = 'BLENDER_WORKBENCH'
            scene.display.shading.light = 'MATCAP'
            scene.display.shading.studio_light = 'check_normal+y.exr'
    scene.render.filepath = save_loc
    bpy.ops.render.render(write_still=1)


def render_depth_map(save_loc):
    """
    This functions renders the depth map and saves it in the location specified
    :param save_loc: the save location of the image (string)
    :return: none
    """
    scene.render.engine = 'BLENDER_EEVEE'
    #scene.view_layers["ViewLayer"].use_pass_z = True
    
    for n in tree.nodes:
        tree.nodes.remove(n)

    rl = tree.nodes.new('CompositorNodeRLayers')

    map_range = tree.nodes.new(type="CompositorNodeMapRange")
    map_range.inputs[1].default_value = config["min_ht"]
    map_range.inputs[2].default_value = config["max_ht"]
    map_range.inputs[3].default_value = config["map_min_val"]
    map_range.inputs[4].default_value = config["map_max_val"]
    links.new(rl.outputs['Depth'], map_range.inputs[0])

    invert = tree.nodes.new(type="CompositorNodeInvert")
    links.new(map_range.outputs[0], invert.inputs[1])

    composite = tree.nodes.new(type="CompositorNodeComposite")
    links.new(map_range.outputs[0], composite.inputs[0])
    links.new(rl.outputs['Depth'], composite.inputs[1])
    
    scene.render.filepath = save_loc
    bpy.ops.render.render(write_still=1)
    tree.nodes.remove(composite)


def write_const_data():
    """
    This functions writes the constant data corresponding to the created
    blender file
    :return: none
    """
    focal, alpha_u, alpha_v, skew, u_0, v_0 = extract_camera_parameters()

    with open('output/data/const.json', mode='w') as json_file:
        out_data_const = {'sph_rad': config["rad"],
                          'R_loc': list(bpy.data.objects["light_R"].location),
                          'G_loc': list(bpy.data.objects["light_G"].location),
                          'B_loc': list(bpy.data.objects["light_B"].location),
                          'cam_loc': list(bpy.data.objects["camera"].location),
                          'mode': config["cam_mode"],
                          'focal': focal,
                          'alpha_u': alpha_u,
                          'alpha_v': alpha_v,
                          'skew': skew,
                          'u_0': u_0,
                          'v_0': v_0,
                          'min_ht': config["min_ht"],
                          'max_ht': config["max_ht"]}
        json.dump(out_data_const, json_file)


render_all_images()
