""" Contains Scene object for representing a .msh file and the function to create one
    from a Blender scene.  """

from dataclasses import dataclass, field
from typing import List, Dict
from copy import copy
import bpy
from mathutils import Vector
from .msh_model import Model, Animation, ModelType
from .msh_scene import Scene, SceneAABB
from .msh_model_gather import gather_models
from .msh_model_utilities import sort_by_parent, has_multiple_root_models, reparent_model_roots, get_model_world_matrix, inject_dummy_data
from .msh_model_triangle_strips import create_models_triangle_strips
from .msh_material import *
from .msh_material_gather import gather_materials
from .msh_material_utilities import remove_unused_materials
from .msh_utilities import *
from .msh_anim_gather import extract_anim



def create_scene(generate_triangle_strips: bool, apply_modifiers: bool, export_target: str, skel_only: bool, export_anim: bool) -> Scene:
    """ Create a msh Scene from the active Blender scene. """

    scene = Scene()

    scene.name = bpy.context.scene.name

    scene.materials = gather_materials()

    scene.models, armature_obj = gather_models(apply_modifiers=apply_modifiers, export_target=export_target, skeleton_only=skel_only)
    scene.models = sort_by_parent(scene.models)

    if generate_triangle_strips:
        scene.models = create_models_triangle_strips(scene.models)
    else:
        for model in scene.models:
            if model.geometry:
                for segment in model.geometry:
                    segment.triangle_strips = segment.triangles

    if has_multiple_root_models(scene.models):
        scene.models = reparent_model_roots(scene.models)

    scene.materials = remove_unused_materials(scene.materials, scene.models)
 

    root = scene.models[0]

    if export_anim:
        if armature_obj is not None:
            scene.animation = extract_anim(armature_obj, root.name)
        else:
            raise Exception("Export Error: Could not find an armature object from which to export an animation!")

    if skel_only and root.model_type == ModelType.NULL:
        # For ZenAsset
        inject_dummy_data(root)

    return scene


def create_scene_aabb(scene: Scene) -> SceneAABB:
    """ Create a SceneAABB for a Scene. """

    global_aabb = SceneAABB()

    for model in scene.models:
        if model.geometry is None or model.hidden:
            continue

        model_world_matrix = get_model_world_matrix(model, scene.models)
        model_aabb = SceneAABB()

        for segment in model.geometry:
            segment_aabb = SceneAABB()

            for pos in segment.positions:
                segment_aabb.integrate_position(model_world_matrix @ pos)

            model_aabb.integrate_aabb(segment_aabb)

        global_aabb.integrate_aabb(model_aabb)

    return global_aabb