# -*- coding: utf-8 -*-

import bpy
import bpy_extras.io_utils

import re
import logging
import logging.handlers
import traceback

from . import import_pmx
from . import import_pmd
from . import export_pmx
from . import import_vmd
from . import mmd_camera
from . import utils
from . import cycles_converter
from . import auto_scene_setup
from . import rigging
from . import properties

bl_info= {
    "name": "mmd_tools",
    "author": "sugiany",
    "version": (0, 4, 3),
    "blender": (2, 67, 0),
    "location": "View3D > Tool Shelf > MMD Tools Panel",
    "description": "Utility tools for MMD model editing.",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Object"}

if "bpy" in locals():
    import imp
    if "import_pmx" in locals():
        imp.reload(import_pmx)
    if "export_pmx" in locals():
        imp.reload(export_pmx)
    if "import_vmd" in locals():
        imp.reload(import_vmd)
    if "mmd_camera" in locals():
        imp.reload(mmd_camera)
    if "utils" in locals():
        imp.reload(utils)
    if "cycles_converter" in locals():
        imp.reload(cycles_converter)
    if "auto_scene_setup" in locals():
        imp.reload(auto_scene_setup)

def log_handler(log_level, filepath=None):
    if filepath is None:
        handler = logging.StreamHandler()
    else:
        handler = logging.FileHandler(filepath, mode='w', encoding='utf-8')
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    return handler

LOG_LEVEL_ITEMS = [
    ('DEBUG', '4. DEBUG', '', 1),
    ('INFO', '3. INFO', '', 2),
    ('WARNING', '2. WARNING', '', 3),
    ('ERROR', '1. ERROR', '', 4),
    ]

class MMDToolsPropertyGroup(bpy.types.PropertyGroup):
    pass


## Import-Export
class ImportPmx_Op(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    bl_idname = 'mmd_tools.import_model'
    bl_label = 'Import Model file (.pmd, .pmx)'
    bl_description = 'Import a Model file (.pmd, .pmx)'
    bl_options = {'PRESET'}

    filename_ext = '.pmx'
    filter_glob = bpy.props.StringProperty(default='*.pmx;*.pmd', options={'HIDDEN'})

    scale = bpy.props.FloatProperty(name='Scale', default=0.2)
    renameBones = bpy.props.BoolProperty(name='Rename bones', default=True)
    hide_rigids = bpy.props.BoolProperty(name='Hide rigid bodies and joints', default=True)
    only_collisions = bpy.props.BoolProperty(name='Ignore rigid bodies', default=False)
    ignore_non_collision_groups = bpy.props.BoolProperty(name='Ignore  non collision groups', default=False)
    distance_of_ignore_collisions = bpy.props.FloatProperty(name='Distance of ignore collisions', default=1.5)
    log_level = bpy.props.EnumProperty(items=LOG_LEVEL_ITEMS, name='Log level', default='DEBUG')
    save_log = bpy.props.BoolProperty(name='Create a log file', default=False)

    def execute(self, context):
        logger = logging.getLogger()
        logger.setLevel(self.log_level)
        if self.save_log:
            handler = log_handler(self.log_level, filepath=self.filepath + '.mmd_tools.import.log')
        else:
            handler = log_handler(self.log_level)
        logger.addHandler(handler)
        try:
            if re.search('\.pmd', self.filepath):
                import_pmd.import_pmd(
                    filepath=self.filepath,
                    scale=self.scale,
                    rename_LR_bones=self.renameBones,
                    hide_rigids=self.hide_rigids,
                    only_collisions=self.only_collisions,
                    ignore_non_collision_groups=self.ignore_non_collision_groups,
                    distance_of_ignore_collisions=self.distance_of_ignore_collisions
                    )
            else:
                importer = import_pmx.PMXImporter()
                importer.execute(
                    filepath=self.filepath,
                    scale=self.scale,
                    rename_LR_bones=self.renameBones,
                    hide_rigids=self.hide_rigids,
                    only_collisions=self.only_collisions,
                    ignore_non_collision_groups=self.ignore_non_collision_groups,
                    distance_of_ignore_collisions=self.distance_of_ignore_collisions
                    )
        except Exception as e:
            logging.error(traceback.format_exc())
            self.report({'ERROR'}, str(e))
        finally:
            logger.removeHandler(handler)

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


class ImportVmd_Op(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    bl_idname = 'mmd_tools.import_vmd'
    bl_label = 'Import VMD file (.vmd)'
    bl_description = 'Import a VMD file (.vmd)'
    bl_options = {'PRESET'}

    filename_ext = '.vmd'
    filter_glob = bpy.props.StringProperty(default='*.vmd', options={'HIDDEN'})

    scale = bpy.props.FloatProperty(name='Scale', default=0.2)
    margin = bpy.props.IntProperty(name='Margin', default=5, min=0)
    update_scene_settings = bpy.props.BoolProperty(name='Update scene settings', default=True)

    def execute(self, context):
        importer = import_vmd.VMDImporter(filepath=self.filepath, scale=self.scale, frame_margin=self.margin)
        for i in context.selected_objects:
            importer.assign(i)
        if self.update_scene_settings:
            auto_scene_setup.setupFrameRanges()
            auto_scene_setup.setupFps()

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


class ExportPmx_Op(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    bl_idname = 'mmd_tools.export_pmx'
    bl_label = 'Export PMX file (.pmx)'
    bl_description = 'Export a PMX file (.pmx)'
    bl_options = {'PRESET'}

    filename_ext = '.pmx'
    filter_glob = bpy.props.StringProperty(default='*.pmx', options={'HIDDEN'})

    scale = bpy.props.FloatProperty(name='Scale', default=0.2)

    log_level = bpy.props.EnumProperty(items=LOG_LEVEL_ITEMS, name='Log level', default='DEBUG')
    save_log = bpy.props.BoolProperty(name='Create a log file', default=False)

    def execute(self, context):
        logger = logging.getLogger()
        logger.setLevel(self.log_level)
        if self.save_log:
            handler = log_handler(self.log_level, filepath=self.filepath + '.mmd_tools.export.log')
        else:
            handler = log_handler(self.log_level)
        logger.addHandler(handler)
        try:
            export_pmx.export(
                filepath=self.filepath,
                scale=self.scale
                )
        finally:
            logger.removeHandler(handler)

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


## Others
class SeparateByMaterials_Op(bpy.types.Operator):
    bl_idname = 'mmd_tools.separate_by_materials'
    bl_label = 'Separate by materials'
    bl_description = 'Separate by materials'
    bl_options = {'PRESET'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return {'FINISHED'}

        utils.separateByMaterials(obj)
        return {'FINISHED'}

class SetFrameRange_Op(bpy.types.Operator):
    bl_idname = 'mmd_tools.set_frame_range'
    bl_label = 'Set range'
    bl_description = 'Set the frame range to best values to play the animation from start to finish. And set the frame rate to 30.0.'
    bl_options = {'PRESET'}

    def execute(self, context):
        auto_scene_setup.setupFrameRanges()
        auto_scene_setup.setupFps()
        return {'FINISHED'}

class SetGLSLShading_Op(bpy.types.Operator):
    bl_idname = 'mmd_tools.set_glsl_shading'
    bl_label = 'GLSL View'
    bl_description = ''
    bl_options = {'PRESET'}

    def execute(self, context):
        bpy.ops.mmd_tools.reset_shading()
        bpy.context.scene.render.engine = 'BLENDER_RENDER'
        for i in filter(lambda x: x.type == 'MESH', context.scene.objects):
            for s in i.material_slots:
                s.material.use_shadeless = False
        if len(list(filter(lambda x: x.is_mmd_glsl_light, context.scene.objects))) == 0:
            bpy.ops.object.lamp_add(type='HEMI', view_align=False, location=(0, 0, 0), rotation=(0, 0, 0))
            light = context.selected_objects[0]
            light.is_mmd_glsl_light = True
            light.hide = True

        context.area.spaces[0].viewport_shade='TEXTURED'
        bpy.context.scene.game_settings.material_mode = 'GLSL'
        return {'FINISHED'}

class SetShadelessGLSLShading_Op(bpy.types.Operator):
    bl_idname = 'mmd_tools.set_shadeless_glsl_shading'
    bl_label = 'Shadeless GLSL View'
    bl_description = ''
    bl_options = {'PRESET'}

    def execute(self, context):
        bpy.ops.mmd_tools.reset_shading()
        bpy.context.scene.render.engine = 'BLENDER_RENDER'
        for i in filter(lambda x: x.type == 'MESH', context.scene.objects):
            for s in i.material_slots:
                s.material.use_shadeless = True
        for i in filter(lambda x: x.is_mmd_glsl_light, context.scene.objects):
            context.scene.objects.unlink(i)

        context.area.spaces[0].viewport_shade='TEXTURED'
        bpy.context.scene.game_settings.material_mode = 'GLSL'
        return {'FINISHED'}

class SetCyclesRendering_Op(bpy.types.Operator):
    bl_idname = 'mmd_tools.set_cycles_rendering'
    bl_label = 'Cycles'
    bl_description = 'Convert blender render shader to Cycles shader'
    bl_options = {'PRESET'}

    def execute(self, context):
        bpy.ops.mmd_tools.reset_shading()
        bpy.context.scene.render.engine = 'CYCLES'
        for i in filter(lambda x: x.type == 'MESH', context.scene.objects):
            cycles_converter.convertToCyclesShader(i)
        context.area.spaces[0].viewport_shade='MATERIAL'
        return {'FINISHED'}

class ResetShading_Op(bpy.types.Operator):
    bl_idname = 'mmd_tools.reset_shading'
    bl_label = 'Reset View'
    bl_description = ''
    bl_options = {'PRESET'}

    def execute(self, context):
        bpy.context.scene.render.engine = 'BLENDER_RENDER'
        for i in filter(lambda x: x.type == 'MESH', context.scene.objects):
            for s in i.material_slots:
                s.material.use_shadeless = False
                s.material.use_nodes = False

        for i in filter(lambda x: x.is_mmd_glsl_light, context.scene.objects):
            context.scene.objects.unlink(i)

        context.area.spaces[0].viewport_shade='SOLID'
        bpy.context.scene.game_settings.material_mode = 'MULTITEXTURE'
        return {'FINISHED'}

class SetShadelessMaterials_Op(bpy.types.Operator):
    bl_idname = 'mmd_tools.set_shadeless_materials'
    bl_label = 'GLSL View'
    bl_description = 'Set the materials of selected objects to shadeless.'
    bl_options = {'PRESET'}

    def execute(self, context):
        for i in context.selected_objects:
            for s in i.material_slots:
                s.material.use_shadeless = True
        return {'FINISHED'}


## Main Panel
class MMDToolsObjectPanel(bpy.types.Panel):
    bl_idname = 'OBJECT_PT_mmd_tools_object'
    bl_label = 'MMD Tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context = ''

    def draw(self, context):
        active_obj = context.active_object

        layout = self.layout

        col = layout.column(align=True)
        col.label('Import:')
        c = col.column()
        r = c.row()
        r.operator('mmd_tools.import_model', text='Model')
        r.operator('mmd_tools.import_vmd', text='Motion')

        col.label('Export:')
        c = col.column()
        r = c.row()
        r.operator('mmd_tools.export_pmx', text='Model')

        col = layout.column(align=True)
        col.label('View:')
        c = col.column(align=True)
        r = c.row()
        r.operator('mmd_tools.set_glsl_shading', text='GLSL')
        r.operator('mmd_tools.set_shadeless_glsl_shading', text='Shadeless')
        r = c.row()
        r.operator('mmd_tools.set_cycles_rendering', text='Cycles')
        r.operator('mmd_tools.reset_shading', text='Reset')

        if active_obj is not None and active_obj.type == 'MESH':
            col = layout.column(align=True)
            col.label('Mesh:')
            c = col.column()
            c.operator('mmd_tools.separate_by_materials', text='Separate by materials')
        if active_obj is not None and active_obj.type == 'MESH':
            col = layout.column(align=True)
            col.label('Material:')
            c = col.column()
            c.operator('mmd_tools.set_shadeless_materials', text='Shadeless')

        col = layout.column(align=True)
        col.label('Scene:')
        c = col.column(align=True)
        c.operator('mmd_tools.set_frame_range', text='Set frame range')


class ShowRigidBodies_Op(bpy.types.Operator):
    bl_idname = 'mmd_tools.show_rigid_bodies'
    bl_label = 'Show Rigid Bodies'
    bl_description = 'Show Rigid bodies'
    bl_options = {'PRESET'}

    def execute(self, context):
        for i in rigging.findRididBodyObjects():
            i.hide = False
        return {'FINISHED'}

class HideRigidBodies_Op(bpy.types.Operator):
    bl_idname = 'mmd_tools.hide_rigid_bodies'
    bl_label = 'Hide Rigid Bodies'
    bl_description = 'Hide Rigid bodies'
    bl_options = {'PRESET'}

    def execute(self, context):
        for i in rigging.findRididBodyObjects():
            i.hide = True
        return {'FINISHED'}

class ShowJoints_Op(bpy.types.Operator):
    bl_idname = 'mmd_tools.show_joints'
    bl_label = 'Show joints'
    bl_description = 'Show joints'
    bl_options = {'PRESET'}

    def execute(self, context):
        for i in rigging.findJointObjects():
            i.hide = False
        return {'FINISHED'}

class HideJoints_Op(bpy.types.Operator):
    bl_idname = 'mmd_tools.hide_joints'
    bl_label = 'Hide joints'
    bl_description = 'Hide joints'
    bl_options = {'PRESET'}

    def execute(self, context):
        for i in rigging.findJointObjects():
            i.hide = True
        return {'FINISHED'}

class ShowTemporaryObjects_Op(bpy.types.Operator):
    bl_idname = 'mmd_tools.show_temporary_objects'
    bl_label = 'Show temporary objects'
    bl_description = 'Show temporary objects'
    bl_options = {'PRESET'}

    def execute(self, context):
        for i in rigging.findTemporaryObjects():
            i.hide = False
        return {'FINISHED'}

class HideTemporaryObjects_Op(bpy.types.Operator):
    bl_idname = 'mmd_tools.hide_temporary_objects'
    bl_label = 'Hide temporary objects'
    bl_description = 'Hide temporary objects'
    bl_options = {'PRESET'}

    def execute(self, context):
        for i in rigging.findTemporaryObjects():
            i.hide = True
        return {'FINISHED'}

class MMDToolsRiggingPanel(bpy.types.Panel):
    bl_idname = 'OBJECT_PT_mmd_tools_rigging'
    bl_label = 'MMD Rig Tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context = ''


    def draw(self, context):
        col = self.layout.column(align=True)
        col.label('Show/Hide:')
        c = col.column(align=True)
        r = c.row()
        r.label('Rigid:')
        r.operator('mmd_tools.show_rigid_bodies', text='Show')
        r.operator('mmd_tools.hide_rigid_bodies', text='Hide')
        r = c.row()
        r.label('Joint:')
        r.operator('mmd_tools.show_joints', text='Show')
        r.operator('mmd_tools.hide_joints', text='Hide')
        r = c.row()
        r.label('Temp:')
        r.operator('mmd_tools.show_temporary_objects', text='Show')
        r.operator('mmd_tools.hide_temporary_objects', text='Hide')

class MMDMaterialPanel(bpy.types.Panel):
    bl_idname = 'MATERIAL_PT_mmd_tools_material'
    bl_label = 'MMD Material Tools'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'material'

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def draw(self, context):
        material = context.active_object.active_material
        mmd_material = material.mmd_material

        layout = self.layout

        col = layout.column(align=True)
        col.label('Information:')
        c = col.column()
        r = c.row()
        r.prop(mmd_material, 'name_j')
        r = c.row()
        r.prop(mmd_material, 'name_e')

        col = layout.column(align=True)
        col.label('Color:')
        c = col.column()
        r = c.row()
        r.prop(material, 'diffuse_color')
        r = c.row()
        r.label('Diffuse Alpha:')
        r.prop(material, 'alpha')
        r = c.row()
        r.prop(mmd_material, 'ambient_color')
        r = c.row()
        r.prop(material, 'specular_color')
        r = c.row()
        r.label('Specular Alpha:')
        r.prop(material, 'specular_alpha')

        col = layout.column(align=True)
        col.label('Shadow:')
        c = col.column()
        r = c.row()
        r.prop(mmd_material, 'is_double_sided')
        r.prop(mmd_material, 'enabled_drop_shadow')
        r = c.row()
        r.prop(mmd_material, 'enabled_self_shadow_map')
        r.prop(mmd_material, 'enabled_self_shadow')

        col = layout.column(align=True)
        col.label('Edge:')
        c = col.column()
        r = c.row()
        r.prop(mmd_material, 'enabled_toon_edge')
        r.prop(mmd_material, 'edge_weight')
        r = c.row()
        r.prop(mmd_material, 'edge_color')

        col = layout.column(align=True)
        col.label('Other:')
        c = col.column()
        r = c.row()
        r.prop(mmd_material, 'sphere_texture_type')
        r = c.row()
        r.prop(mmd_material, 'comment')


class MMDCameraPanel(bpy.types.Panel):
    bl_idname = 'OBJECT_PT_mmd_tools_camera'
    bl_label = 'MMD Camera Tools'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and (obj.type == 'CAMERA' or mmd_camera.MMDCamera.isMMDCamera(obj))

    def draw(self, context):
        obj = context.active_object

        layout = self.layout

        if mmd_camera.MMDCamera.isMMDCamera(obj):
            mmd_cam = mmd_camera.MMDCamera(obj)
            empty = mmd_cam.object()
            camera = mmd_cam.camera()

            row = layout.row(align=True)

            c = row.column()
            c.prop(empty, 'location')
            c.prop(camera, 'location', index=1, text='Distance')

            c = row.column()
            c.prop(empty, 'rotation_euler')

            row = layout.row(align=True)
            row.prop(empty.mmd_camera, 'angle')
            row = layout.row(align=True)
            row.prop(empty.mmd_camera, 'is_perspective')
        else:
            col = layout.column(align=True)

            c = col.column()
            r = c.row()
            r.operator('mmd_tools.convert_to_mmd_camera', 'Convert')


class ConvertToMMDCamera_Op(bpy.types.Operator):
    bl_idname = 'mmd_tools.convert_to_mmd_camera'
    bl_label = 'Convert to MMD Camera'
    bl_description = 'create a camera rig for mmd.'
    bl_options = {'PRESET'}

    def execute(self, context):
        mmd_camera.MMDCamera.convertToMMDCamera(context.active_object)
        return {'FINISHED'}

class MMDBonePanel(bpy.types.Panel):
    bl_idname = 'BONE_PT_mmd_tools_bone'
    bl_label = 'MMD Bone Tools'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'bone'

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_ARMATURE' and context.active_bone is not None or context.mode == 'POSE' and context.active_pose_bone is not None

    def draw(self, context):
        if context.mode == 'EDIT_ARMATURE':
            edit_bone = context.active_bone
            pose_bone = context.active_object.pose.bones[edit_bone.name]
        else:
            pose_bone = context.active_pose_bone

        layout = self.layout
        c = layout.column(align=True)

        c.label('Information:')
        c.prop(pose_bone.mmd_bone, 'name_j')
        c.prop(pose_bone.mmd_bone, 'name_e')

        c = layout.column(align=True)
        row = c.row()
        row.prop(pose_bone.mmd_bone, 'transform_order')
        row.prop(pose_bone.mmd_bone, 'transform_after_dynamics')
        row.prop(pose_bone.mmd_bone, 'is_visible')
        row = c.row()
        row.prop(pose_bone.mmd_bone, 'is_controllable')
        row.prop(pose_bone.mmd_bone, 'is_tip')
        row.prop(pose_bone.mmd_bone, 'enabled_local_axes')

        row = layout.row(align=True)
        c = row.column()
        c.prop(pose_bone.mmd_bone, 'local_axis_x')
        c = row.column()
        c.prop(pose_bone.mmd_bone, 'local_axis_z')


class MMDBonePanel(bpy.types.Panel):
    bl_idname = 'RIGID_PT_mmd_tools_bone'
    bl_label = 'MMD Rigid Tools'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.rigid_body is not None and context.active_object.is_mmd_rigid

    def draw(self, context):
        obj = context.active_object

        layout = self.layout
        c = layout.column()
        c.prop(obj, 'name')
        c.prop(obj.mmd_rigid, 'name_e')

        row = layout.row(align=True)
        row.prop(obj.mmd_rigid, 'type')
        row.prop_search(obj, 'parent_bone', text='', search_data=obj.parent.pose, search_property='bones', icon='BONE_DATA')

        row = layout.row()

        c = row.column()
        c.prop(obj.rigid_body, 'mass')
        c.prop(obj.mmd_rigid, 'collision_group_number')
        c = row.column()
        c.prop(obj.rigid_body, 'restitution', text='Bounciness')
        c.prop(obj.rigid_body, 'friction')

        c = layout.column()
        c.prop(obj.mmd_rigid, 'collision_group_mask')

        c = layout.column()
        c.label('Damping')
        row = c.row()
        row.prop(obj.rigid_body, 'linear_damping')
        row.prop(obj.rigid_body, 'angular_damping')

class MMDJointPanel(bpy.types.Panel):
    bl_idname = 'JOINT_PT_mmd_tools_bone'
    bl_label = 'MMD Joint Tools'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'EMPTY' and obj.rigid_body_constraint is not None and context.active_object.is_mmd_joint

    def draw(self, context):
        obj = context.active_object
        rbc = obj.rigid_body_constraint

        layout = self.layout
        c = layout.column()
        c.prop(obj.mmd_joint, 'name_j')
        c.prop(obj.mmd_joint, 'name_e')

        c = layout.column()
        c.prop(rbc, 'object1')
        c.prop(rbc, 'object2')

        col = layout.column()
        row = col.row(align=True)
        row.label('X-Axis:')
        row.prop(rbc, 'limit_lin_x_lower')
        row.prop(rbc, 'limit_lin_x_upper')
        row = col.row(align=True)
        row.label('Y-Axis:')
        row.prop(rbc, 'limit_lin_y_lower')
        row.prop(rbc, 'limit_lin_y_upper')
        row = col.row(align=True)
        row.label('Z-Axis:')
        row.prop(rbc, 'limit_lin_z_lower')
        row.prop(rbc, 'limit_lin_z_upper')

        col = layout.column()
        row = col.row(align=True)
        row.label('X-Axis:')
        row.prop(rbc, 'limit_ang_x_lower')
        row.prop(rbc, 'limit_ang_x_upper')
        row = col.row(align=True)
        row.label('Y-Axis:')
        row.prop(rbc, 'limit_ang_y_lower')
        row.prop(rbc, 'limit_ang_y_upper')
        row = col.row(align=True)
        row.label('Z-Axis:')
        row.prop(rbc, 'limit_ang_z_lower')
        row.prop(rbc, 'limit_ang_z_upper')

        col = layout.column()
        col.label('Spring(Linear):')
        row = col.row()
        row.prop(obj.mmd_joint, 'spring_linear', text='')
        col.label('Spring(Angular):')
        row = col.row()
        row.prop(obj.mmd_joint, 'spring_angular', text='')


def menu_func_import(self, context):
    self.layout.operator(ImportPmx_Op.bl_idname, text="MikuMikuDance Model (.pmd, .pmx)")
    self.layout.operator(ExportPmx_Op.bl_idname, text="MikuMikuDance model (.pmx)")
    self.layout.operator(ImportVmd_Op.bl_idname, text="MikuMikuDance Motion (.vmd)")

def register():
    bpy.utils.register_class(MMDToolsPropertyGroup)
    bpy.utils.register_class(properties.MMDMaterial)
    bpy.utils.register_class(properties.MMDCamera)
    bpy.utils.register_class(properties.MMDBone)
    bpy.utils.register_class(properties.MMDRigid)
    bpy.utils.register_class(properties.MMDJoint)
    bpy.types.INFO_MT_file_import.append(menu_func_import)

    bpy.types.Scene.mmd_tools = bpy.props.PointerProperty(type=MMDToolsPropertyGroup)

    bpy.types.Object.is_mmd_camera = bpy.props.BoolProperty(name='is_mmd_camera', default=False)
    bpy.types.Object.mmd_camera = bpy.props.PointerProperty(type=properties.MMDCamera)

    # Material custom properties
    bpy.types.Material.mmd_material = bpy.props.PointerProperty(type=properties.MMDMaterial)

    bpy.types.Object.is_mmd_lamp = bpy.props.BoolProperty(name='is_mmd_lamp', default=False)

    bpy.types.Object.is_mmd_rigid = bpy.props.BoolProperty(name='is_mmd_rigid', default=False)
    bpy.types.Object.mmd_rigid = bpy.props.PointerProperty(type=properties.MMDRigid)


    bpy.types.Object.is_mmd_joint = bpy.props.BoolProperty(name='is_mmd_joint', default=False)
    bpy.types.Object.mmd_joint = bpy.props.PointerProperty(type=properties.MMDJoint)

    bpy.types.Object.is_mmd_rigid_track_target = bpy.props.BoolProperty(name='is_mmd_rigid_track_target', default=False)
    bpy.types.Object.is_mmd_non_collision_constraint = bpy.props.BoolProperty(name='is_mmd_non_collision_constraint', default=False)
    bpy.types.Object.is_mmd_spring_joint = bpy.props.BoolProperty(name='is_mmd_spring_joint', default=False)
    bpy.types.Object.is_mmd_spring_goal = bpy.props.BoolProperty(name='is_mmd_spring_goal', default=False)

    bpy.types.PoseBone.mmd_bone = bpy.props.PointerProperty(type=properties.MMDBone)

    bpy.types.PoseBone.is_mmd_shadow_bone = bpy.props.BoolProperty(name='is_mmd_shadow_bone', default=False)
    bpy.types.PoseBone.mmd_shadow_bone_type = bpy.props.StringProperty(name='mmd_shadow_bone_type')

    bpy.types.Object.is_mmd_glsl_light = bpy.props.BoolProperty(name='is_mmd_glsl_light', default=False)


    bpy.utils.register_module(__name__)

def unregister():
    bpy.types.INFO_MT_file_import.remove(menu_func_import)

    del bpy.types.Object.is_mmd_camera
    del bpy.types.Object.mmd_camera

    del bpy.types.Object.is_mmd_lamp

    del bpy.types.Object.is_mmd_rigid
    del bpy.types.Object.mmd_rigid

    del bpy.types.Object.is_mmd_joint
    del bpy.types.Object.mmd_joint

    del bpy.types.Object.is_mmd_rigid_track_target
    del bpy.types.Object.is_mmd_non_collision_constraint
    del bpy.types.Object.is_mmd_spring_joint
    del bpy.types.Object.is_mmd_spring_goal

    del bpy.types.PoseBone.mmd_bone
    del bpy.types.Material.mmd_material

    del bpy.types.PoseBone.is_mmd_shadow_bone
    del bpy.types.Object.is_mmd_glsl_light

    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()
