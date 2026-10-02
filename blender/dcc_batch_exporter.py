bl_info = {
    "name": "DCC Batch Exporter (FBX + JSON)",
    "author": "OpenAI",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > DCC Export",
    "description": "Export selected meshes to one FBX with a material/texture JSON manifest",
    "category": "Import-Export",
}

import bpy
import json
import os
import re
import shutil
from bpy.props import (StringProperty, CollectionProperty, IntProperty,
                       BoolProperty)


def clean_name(value):
    value = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip())
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "Unnamed"


def is_skinned_mesh(obj):
    if obj.parent and obj.parent.type == 'ARMATURE':
        return True
    return any(mod.type == 'ARMATURE' and mod.object for mod in obj.modifiers)


def object_export_name(obj, row_name):
    name = clean_name(row_name)
    prefix = "SKM_" if is_skinned_mesh(obj) else "SM_"
    for old_prefix in ("SKM_", "SK_", "SM_"):
        if name.startswith(old_prefix):
            name = name[len(old_prefix):]
            break
    return prefix + name


def material_export_name(mat):
    name = clean_name(mat.name)
    return name if name.startswith("MI_") else "MI_" + name


def unique_path_name(name, used):
    base = name
    index = 2
    while name.casefold() in used:
        name = f"{base}_{index:02d}"
        index += 1
    used.add(name.casefold())
    return name


def linked_image(node_tree, socket, visited=None):
    """Return an image node connected directly, or through a Normal Map node."""
    visited = visited or set()
    if socket.as_pointer() in visited:
        return None
    visited.add(socket.as_pointer())
    if not socket.is_linked:
        return None
    link = socket.links[0]
    node = link.from_node
    if node.type == 'TEX_IMAGE' and node.image:
        return node.image
    if node.type == 'NORMAL_MAP':
        color = node.inputs.get("Color")
        if color:
            return linked_image(node_tree, color, visited)
    return None


def principled_for(mat):
    if not mat or not mat.use_nodes or not mat.node_tree:
        return None
    # Use the Principled node that feeds an active material output when possible.
    for node in mat.node_tree.nodes:
        if node.type == 'OUTPUT_MATERIAL' and node.is_active_output:
            surface = node.inputs.get("Surface")
            if surface and surface.is_linked:
                source = surface.links[0].from_node
                if source.type == 'BSDF_PRINCIPLED':
                    return source
    return next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)


def copy_image(image, destination):
    if image.source != 'FILE':
        raise RuntimeError(f"'{image.name}' is not a file image")
    source = bpy.path.abspath(image.filepath, library=image.library)
    if not source or not os.path.isfile(source):
        if image.packed_file:
            ext = os.path.splitext(image.filepath or ".png")[1] or ".png"
            target = os.path.join(destination, clean_name(image.name) + ext)
            image.save_render(target)
            return target
        raise RuntimeError(f"Image file not found for '{image.name}': {source}")
    os.makedirs(destination, exist_ok=True)
    basename = os.path.basename(source)
    target = os.path.join(destination, basename)
    stem, ext = os.path.splitext(basename)
    i = 2
    while os.path.exists(target) and os.path.normcase(os.path.abspath(target)) != os.path.normcase(os.path.abspath(source)):
        target = os.path.join(destination, f"{stem}_{i:02d}{ext}")
        i += 1
    if os.path.normcase(os.path.abspath(source)) != os.path.normcase(os.path.abspath(target)):
        shutil.copy2(source, target)
    return target


def socket_record(mat, principled, socket_name, texture_dir, copied, warnings):
    socket = principled.inputs.get(socket_name)
    if socket is None:
        return {"value": None}
    image = linked_image(mat.node_tree, socket) if socket.is_linked else None
    if image:
        image_source = bpy.path.abspath(image.filepath, library=image.library)
        # Blender can load the same disk file into several image datablocks (often .001/.002).
        # Key copies by the resolved source path so those datablocks share one exported file.
        copy_key = (os.path.normcase(os.path.abspath(image_source))
                    if image_source else "packed:" + image.name)
        if copy_key not in copied:
            try:
                copied[copy_key] = copy_image(image, texture_dir)
            except (OSError, RuntimeError) as exc:
                copied[copy_key] = None
                warning = {
                    "input": socket_name,
                    "image": image.name,
                    "source_path": image_source,
                    "message": str(exc),
                }
                if warning not in warnings:
                    warning["material"] = mat.name
                    warnings.append(warning)
        if copied[copy_key] is None:
            return {"value": None, "missing_texture": image.name}
        return {
            "texture": os.path.relpath(copied[copy_key], os.path.dirname(texture_dir)).replace("\\", "/"),
            "color_space": image.colorspace_settings.name,
            "image": image.name,
        }
    value = socket.default_value
    if hasattr(value, "__len__") and not isinstance(value, str):
        value = [float(v) for v in value]
    elif isinstance(value, (int, float)):
        value = float(value)
    else:
        value = str(value)
    return {"value": value}


def socket_record_aliases(mat, principled, socket_names, texture_dir, copied, warnings,
                          default_value):
    for socket_name in socket_names:
        if principled.inputs.get(socket_name) is not None:
            return socket_record(mat, principled, socket_name, texture_dir, copied, warnings)
    return {"value": default_value}


class DCCExportRow(bpy.types.PropertyGroup):
    source_name: StringProperty(name="Source Object", options={'HIDDEN'})
    object_name: StringProperty(name="Export Name")


class DCCExportSettings(bpy.types.PropertyGroup):
    bundle_name: StringProperty(name="FBX File Name", default="Asset")
    output_dir: StringProperty(name="Output Folder", subtype='DIR_PATH', default="//export/")
    overwrite: BoolProperty(name="Overwrite Existing Files", default=False)
    rows: CollectionProperty(type=DCCExportRow)
    active_index: IntProperty(default=0)


class DCCEXPORT_OT_refresh(bpy.types.Operator):
    bl_idname = "dcc_export.refresh"
    bl_label = "Refresh Selected Meshes"

    def execute(self, context):
        settings = context.scene.dcc_export_settings
        meshes = sorted((o for o in context.selected_objects if o.type == 'MESH'), key=lambda o: o.name.casefold())
        settings.rows.clear()
        used = set()
        for obj in meshes:
            row = settings.rows.add()
            row.source_name = obj.name
            row.object_name = unique_path_name(object_export_name(obj, obj.name), used)
        settings.active_index = min(settings.active_index, max(0, len(settings.rows) - 1))
        self.report({'INFO'}, f"Loaded {len(meshes)} selected mesh(es)")
        return {'FINISHED'}


class DCCEXPORT_OT_focus(bpy.types.Operator):
    bl_idname = "dcc_export.focus"
    bl_label = "Select and Frame"
    index: IntProperty()

    def execute(self, context):
        settings = context.scene.dcc_export_settings
        meshes = sorted((o for o in context.selected_objects if o.type == 'MESH'), key=lambda o: o.name.casefold())
        # Rows preserve the same sorted order from Refresh; fall back to name lookup.
        if self.index >= len(settings.rows):
            return {'CANCELLED'}
        target = bpy.data.objects.get(settings.rows[self.index].source_name)
        if not target:
            return {'CANCELLED'}
        bpy.ops.object.select_all(action='DESELECT')
        target.select_set(True)
        context.view_layer.objects.active = target
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.region_3d.view_perspective = 'ORTHO'
                with context.temp_override(area=area):
                    bpy.ops.view3d.view_selected(use_all_regions=False)
                break
        return {'FINISHED'}


class DCCEXPORT_OT_export(bpy.types.Operator):
    bl_idname = "dcc_export.export_fbx_json"
    bl_label = "Export FBX + JSON"
    bl_options = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.dcc_export_settings
        selected = [bpy.data.objects.get(row.source_name) for row in settings.rows]
        selected = [o for o in selected if o and o.type == 'MESH']
        if not selected:
            self.report({'ERROR'}, "Select at least one mesh object")
            return {'CANCELLED'}
        if len(settings.rows) != len(selected):
            self.report({'ERROR'}, "One or more preview objects no longer exist; refresh the preview")
            return {'CANCELLED'}
        out_dir = bpy.path.abspath(settings.output_dir)
        os.makedirs(out_dir, exist_ok=True)
        used_objects = set()
        export_names = [unique_path_name(object_export_name(obj, settings.rows[i].object_name), used_objects) for i, obj in enumerate(selected)]
        stem = clean_name(settings.bundle_name or "Asset")
        groups = {
            "static": [(obj, name) for obj, name in zip(selected, export_names) if not is_skinned_mesh(obj)],
            "skeletal": [(obj, name) for obj, name in zip(selected, export_names) if is_skinned_mesh(obj)],
        }
        output_pairs = []
        for kind, members in groups.items():
            if not members:
                continue
            suffix = "_SM" if kind == "static" else "_SKM"
            output_pairs.append((
                os.path.join(out_dir, stem + suffix + ".fbx"),
                os.path.join(out_dir, stem + suffix + ".json"),
            ))
        if not settings.overwrite and any(os.path.exists(path) for pair in output_pairs for path in pair):
            self.report({'ERROR'}, "One or more FBX/JSON files already exist; enable overwrite or choose another bundle name")
            return {'CANCELLED'}
        texture_dir = os.path.join(out_dir, "textures")
        if not settings.overwrite and os.path.isdir(texture_dir) and os.listdir(texture_dir):
            self.report({'ERROR'}, "Texture output folder is not empty")
            return {'CANCELLED'}

        rows = list(settings.rows)
        copied_images = {}
        warnings = []
        temp_objects = []
        temp_meshes = []
        temp_materials = []
        previous_selection = list(context.selected_objects)
        previous_active = context.view_layer.objects.active
        try:
            exported_count = 0
            for kind, members in groups.items():
                if not members:
                    continue
                suffix = "_SM" if kind == "static" else "_SKM"
                fbx_path = os.path.join(out_dir, stem + suffix + ".fbx")
                json_path = os.path.join(out_dir, stem + suffix + ".json")
                materials = {}
                group_objects = []
                group_rigs = set()
                mesh_manifest = []

                for obj, export_name in members:
                    if kind == "skeletal":
                        if obj.parent and obj.parent.type == 'ARMATURE':
                            group_rigs.add(obj.parent)
                        for modifier in obj.modifiers:
                            if modifier.type == 'ARMATURE' and modifier.object:
                                group_rigs.add(modifier.object)
                    duplicate = obj.copy()
                    duplicate.data = obj.data.copy()
                    duplicate.name = export_name
                    duplicate.data.name = export_name
                    context.collection.objects.link(duplicate)
                    temp_objects.append(duplicate)
                    temp_meshes.append(duplicate.data)
                    group_objects.append(duplicate)
                    slots = []
                    for slot_index, slot in enumerate(obj.material_slots):
                        mat = slot.material
                        if not mat:
                            slots.append({"slot": slot_index, "material": None})
                            continue
                        if mat.name not in materials:
                            exported_mat = mat.copy()
                            exported_mat.name = material_export_name(mat)
                            temp_materials.append(exported_mat)
                            principled = principled_for(mat)
                            if not principled:
                                raise RuntimeError(f"Material '{mat.name}' has no Principled BSDF")
                            materials[mat.name] = {
                                "name": exported_mat.name,
                                "source_name": mat.name,
                                "source_names": [mat.name],
                                "base_color": socket_record(mat, principled, "Base Color", texture_dir, copied_images, warnings),
                                "normal": socket_record(mat, principled, "Normal", texture_dir, copied_images, warnings),
                                "roughness": socket_record(mat, principled, "Roughness", texture_dir, copied_images, warnings),
                                "metallic": socket_record(mat, principled, "Metallic", texture_dir, copied_images, warnings),
                                "emission_color": socket_record_aliases(
                                    mat, principled, ("Emission Color", "Emission"),
                                    texture_dir, copied_images, warnings, [0.0, 0.0, 0.0, 1.0],
                                ),
                                "emission_strength": socket_record_aliases(
                                    mat, principled, ("Emission Strength",),
                                    texture_dir, copied_images, warnings, 0.0,
                                ),
                            }
                        duplicate.material_slots[slot_index].link = 'OBJECT'
                        duplicate.material_slots[slot_index].material = next(m for m in temp_materials if m.name == materials[mat.name]["name"])
                        slots.append({"slot": slot_index, "material": materials[mat.name]["name"]})
                    mesh_manifest.append({"name": export_name, "source_name": obj.name, "materials": slots})

                bpy.ops.object.select_all(action='DESELECT')
                for obj in group_objects:
                    obj.select_set(True)
                for rig in group_rigs:
                    rig.select_set(True)
                context.view_layer.objects.active = group_objects[0]
                object_types = {'MESH', 'ARMATURE'} if kind == "skeletal" else {'MESH'}
                bpy.ops.export_scene.fbx(
                    filepath=fbx_path, use_selection=True, object_types=object_types,
                    apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
                    use_mesh_modifiers=True, mesh_smooth_type='FACE',
                    path_mode='AUTO', embed_textures=False,
                    add_leaf_bones=False, bake_anim=False,
                )
                manifest = {
                    "schema_version": 2,
                    "asset_name": stem,
                    "asset_type": kind,
                    "fbx": os.path.basename(fbx_path),
                    "meshes": mesh_manifest,
                    "materials": list(materials.values()),
                    "warnings": warnings,
                }
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, ensure_ascii=False, indent=2)
                exported_count += len(group_objects)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        finally:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in temp_objects:
                bpy.data.objects.remove(obj, do_unlink=True)
            for mesh in temp_meshes:
                if mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
            for mat in temp_materials:
                if mat.users == 0:
                    bpy.data.materials.remove(mat)
            for obj in previous_selection:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
            if previous_active and previous_active.name in bpy.data.objects:
                context.view_layer.objects.active = previous_active
        if warnings:
            self.report({'WARNING'}, f"Exported {exported_count} mesh(es) into separate SM/SKM FBX files; {len(warnings)} texture reference(s) were omitted. See JSON warnings.")
        else:
            self.report({'INFO'}, f"Exported {exported_count} mesh(es) into separate SM/SKM FBX files")
        return {'FINISHED'}


class DCCEXPORT_PT_panel(bpy.types.Panel):
    bl_label = "DCC Export"
    bl_idname = "DCCEXPORT_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DCC Export"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.dcc_export_settings
        layout.prop(settings, "bundle_name")
        layout.prop(settings, "output_dir")
        layout.prop(settings, "overwrite")
        layout.operator("dcc_export.refresh", icon='FILE_REFRESH')
        box = layout.box()
        box.label(text="Mesh name preview (source → FBX)")
        for index, row in enumerate(settings.rows):
            source = row.get("source_name", "Refresh to load")
            r = box.row(align=True)
            op = r.operator("dcc_export.focus", text="", icon='RESTRICT_SELECT_OFF')
            op.index = index
            r.label(text=source)
            r.prop(row, "object_name", text="")
        layout.operator("dcc_export.export_fbx_json", icon='EXPORT')


CLASSES = (DCCExportRow, DCCExportSettings, DCCEXPORT_OT_refresh,
           DCCEXPORT_OT_focus, DCCEXPORT_OT_export, DCCEXPORT_PT_panel)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dcc_export_settings = bpy.props.PointerProperty(type=DCCExportSettings)

def unregister():
    del bpy.types.Scene.dcc_export_settings
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
