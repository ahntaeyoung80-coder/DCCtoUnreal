"""DCC FBX + JSON importer for Unreal Editor Python (UE 5.8 target).

Standalone editor script, not an Unreal plugin. Configure the paths below,
then run it inside Unreal Editor with Tools > Execute Python Script.

Expected Blender exporter contract (schema 2):
  <Bundle>_SM.fbx + <Bundle>_SM.json
  <Bundle>_SK.fbx + <Bundle>_SK.json

"""

import json
import os
import re
import unreal


# ---------------------------------------------------------------------------
# User configuration
# ---------------------------------------------------------------------------

SOURCE_DIR = r"C:\Users\USER\ExportTest"
DEST_ROOT = "/Game/DCC"

# Additional Substance Painter export folders. SOURCE_DIR and its "textures"
# subfolder are searched automatically as well. Add other absolute paths here.
SUBSTANCE_TEXTURE_DIRS = []

# Substance output token aliases. ORM channel order follows the selected
# Unreal SSS Pack preset: R=AO, G=Roughness, B=Metallic.
MAP_SUFFIXES = {
    "base_color": ("BaseColor", "Base_Color", "Albedo", "Color", "Diffuse"),
    "normal": ("Normal", "Normal_OpenGL", "Normal_DirectX", "NormalGL", "NormalDX"),
    "roughness": ("Roughness", "Rough"),
    "metallic": ("Metallic", "Metalness", "Metal"),
    "orm": ("ORM", "OcclusionRoughnessMetallic", "Occlusion_Roughness_Metallic"),
}
SPECIAL_MAP_SUFFIXES = {
    "SSS": ("SSS", "Subsurface", "SubsurfaceColor", "SubsurfaceMask"),
    "Opacity": ("Opacity", "OpacityMask", "Alpha", "Transparency"),
    "Emissive": ("Emissive", "Emission"),
}
TEXTURE_EXTENSIONS = (".png", ".tga", ".tif", ".tiff", ".exr", ".jpg", ".jpeg")

# Optional path to an existing Skeleton asset, e.g.:
# /Game/DCC/Inna/Skeletal/SKEL_Inna.SKEL_Inna
# Leave empty for the first import. The first imported skeletal asset creates it.
SKELETON_PATH = ""

MASTER_MATERIAL_PATH = "/Game/DCC/Shared/Materials/M_DCC_Master_v2"
ASK_BEFORE_REPLACE = True


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------

def log(message):
    unreal.log("[DCC Import] " + str(message))


def warn(message):
    unreal.log_warning("[DCC Import] " + str(message))


def clean_name(value):
    value = re.sub(r"[^A-Za-z0-9_]+", "_", str(value).strip())
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "Unnamed"


def ensure_folder(path):
    unreal.EditorAssetLibrary.make_directory(path)


def set_optional(obj, name, value):
    try:
        obj.set_editor_property(name, value)
        return True
    except Exception as exc:
        warn("Could not set {}: {}".format(name, exc))
        return False


def show_error(message):
    unreal.EditorDialog.show_message(
        "DCC Import Error", str(message), unreal.AppMsgType.OK,
        unreal.AppReturnType.OK,
    )


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def discover_manifests():
    if not os.path.isdir(SOURCE_DIR):
        raise RuntimeError("Source folder does not exist: " + SOURCE_DIR)
    manifests = [
        os.path.join(SOURCE_DIR, name)
        for name in sorted(os.listdir(SOURCE_DIR))
        if name.endswith("_SM.json") or name.endswith("_SK.json")
    ]
    if not manifests:
        raise RuntimeError("No *_SM.json or *_SK.json files in " + SOURCE_DIR)
    return manifests


def validate_manifest(path):
    data = load_json(path)
    if data.get("schema_version") != 2:
        raise RuntimeError(
            "{} uses schema_version {}. This importer requires schema 2 and "
            "separate _SM/_SK exports. Update the Blender exporter first."
            .format(os.path.basename(path), data.get("schema_version"))
        )
    kind = data.get("asset_type")
    if kind not in ("static", "skeletal"):
        raise RuntimeError("asset_type must be 'static' or 'skeletal': " + path)
    fbx_name = data.get("fbx")
    if not fbx_name:
        raise RuntimeError("JSON has no fbx filename: " + path)
    fbx_path = os.path.join(os.path.dirname(path), fbx_name)
    if not os.path.isfile(fbx_path):
        raise RuntimeError("FBX listed by JSON is missing: " + fbx_path)
    if not isinstance(data.get("meshes"), list) or not isinstance(data.get("materials"), list):
        raise RuntimeError("JSON must contain meshes and materials arrays: " + path)
    expected = "_SM" if kind == "static" else "_SK"
    if not os.path.basename(path).startswith(clean_name(data.get("asset_name", "Asset")) + expected):
        warn("Manifest filename and asset_type suffix do not match: " + path)
    return data, fbx_path


def import_task(source_file, destination, options=None, destination_name=None,
                replace_existing=False):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", source_file)
    task.set_editor_property("destination_path", destination)
    task.set_editor_property("replace_existing", replace_existing)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", True)
    if options:
        task.set_editor_property("options", options)
    if destination_name:
        task.set_editor_property("destination_name", destination_name)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = list(task.get_editor_property("imported_object_paths") or [])
    assets = [unreal.EditorAssetLibrary.load_asset(p) for p in paths]
    return [a for a in assets if a]


def source_file_for(manifest_path, relative_path):
    if not relative_path:
        return None
    full = os.path.normpath(os.path.join(os.path.dirname(manifest_path), relative_path))
    if not os.path.isfile(full):
        warn("Texture not found; leaving that input at its master default: " + full)
        return None
    return full


def normalize_token(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def material_aliases(record):
    aliases = []
    for value in [record.get("name", ""), record.get("source_name", "")]:
        value = str(value)
        aliases.append(value)
        if value.startswith("MI_"):
            aliases.append(value[3:])
    aliases.extend(str(v) for v in record.get("source_names", []))
    return sorted(set(a for a in aliases if a), key=lambda a: (-len(normalize_token(a)), a.casefold()))


def texture_search_dirs(manifest_path):
    candidates = [
        os.path.dirname(manifest_path),
        os.path.join(os.path.dirname(manifest_path), "textures"),
    ] + list(SUBSTANCE_TEXTURE_DIRS)
    result = []
    seen = set()
    for path in candidates:
        if os.path.isdir(path):
            key = os.path.normcase(os.path.abspath(path))
            if key not in seen:
                seen.add(key)
                result.append(path)
    return result


def find_substance_texture(record, role, manifest_path, suffixes=None):
    """Find a standalone SP map by material/texture-set name plus map suffix."""
    aliases = material_aliases(record)
    expected = {}
    for alias in aliases:
        a = normalize_token(alias)
        for suffix in (suffixes or MAP_SUFFIXES[role]):
            expected.setdefault(a + normalize_token(suffix), (len(a), alias, suffix))

    matches = []
    for root in texture_search_dirs(manifest_path):
        for current, _dirs, files in os.walk(root):
            for filename in files:
                ext = os.path.splitext(filename)[1].casefold()
                if ext not in TEXTURE_EXTENSIONS:
                    continue
                stem = normalize_token(os.path.splitext(filename)[0])
                if stem in expected:
                    alias_length, alias, suffix = expected[stem]
                    matches.append((alias_length, filename, os.path.join(current, filename), alias, suffix))

    if not matches:
        return None

    # Prefer the most specific material alias (e.g. Cloth.001 over Cloth).
    longest = max(item[0] for item in matches)
    matches = [item for item in matches if item[0] == longest]
    # Prefer the first configured extension when a preset emitted duplicate formats.
    extension_rank = {ext: index for index, ext in enumerate(TEXTURE_EXTENSIONS)}
    best_rank = min(extension_rank[os.path.splitext(item[2])[1].casefold()] for item in matches)
    matches = [item for item in matches if extension_rank[os.path.splitext(item[2])[1].casefold()] == best_rank]
    unique_paths = {os.path.normcase(os.path.abspath(item[2])): item[2] for item in matches}
    if len(unique_paths) > 1:
        warn("Ambiguous {} texture for {}: {}".format(
            role, record.get("source_name", record.get("name")), ", ".join(sorted(unique_paths.values()))
        ))
        return None
    return next(iter(unique_paths.values()))


def resolve_material_textures(manifest_path, manifest):
    """JSON texture refs win; missing refs fall back to Substance filename matching."""
    result = {}
    for record in manifest["materials"]:
        name = record["name"]
        result[name] = {}
        for role in MAP_SUFFIXES:
            entry = record.get(role) or {}
            path = source_file_for(manifest_path, entry.get("texture"))
            if not path:
                path = find_substance_texture(record, role, manifest_path)
            result[name][role] = path
        result[name]["special_maps"] = {}
        for label, suffixes in SPECIAL_MAP_SUFFIXES.items():
            result[name]["special_maps"][label] = find_substance_texture(record, label, manifest_path, suffixes)
            result[name]["special_" + label.casefold()] = result[name]["special_maps"][label]
    return result


# ---------------------------------------------------------------------------
# Textures and Material Instances
# ---------------------------------------------------------------------------

def import_textures(manifest, resolved_textures, texture_folder, replace_existing):
    ensure_folder(texture_folder)
    by_source = {}
    used_names = set()
    for mat in manifest["materials"]:
        for role in list(MAP_SUFFIXES) + ["special_sss", "special_opacity", "special_emissive"]:
            src = resolved_textures.get(mat["name"], {}).get(role)
            if not src:
                continue
            key = os.path.normcase(os.path.abspath(src))
            if key in by_source:
                continue
            material_name = mat.get("source_name") or mat.get("name", "MI_Material")
            if material_name.startswith("MI_"):
                material_name = material_name[3:]
            suffix = role.title().replace("_", "")
            name = "T_{}_{}".format(clean_name(material_name), suffix)
            candidate, index = name, 2
            while candidate.casefold() in used_names:
                candidate = "{}_{:02d}".format(name, index)
                index += 1
            used_names.add(candidate.casefold())
            existing_path = texture_folder + "/" + candidate
            texture = None if replace_existing else unreal.EditorAssetLibrary.load_asset(existing_path)
            if not texture:
                assets = import_task(src, texture_folder, destination_name=candidate,
                                     replace_existing=replace_existing)
                texture = next((a for a in assets if isinstance(a, unreal.Texture2D)), None)
            if not texture:
                warn("Texture import did not return Texture2D: " + src)
                continue
            # One source used for multiple roles: keep first import's role settings.
            texture.set_editor_property("srgb", role == "base_color")
            if role == "normal":
                set_optional(texture, "compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            elif role in ("roughness", "metallic", "orm") or role.startswith("special_"):
                set_optional(texture, "compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
            unreal.EditorAssetLibrary.save_loaded_asset(texture)
            by_source[key] = texture
    return by_source


def material_signature(record, resolved):
    values = {}
    for role in ("base_color", "normal", "roughness", "metallic", "orm"):
        entry = record.get(role) or {}
        value = entry.get("value")
        if isinstance(value, list):
            value = [round(float(v), 6) for v in value]
        path = resolved.get(role)
        # A discovered file overrides a Blender constant for that input.
        values[role] = (
            os.path.normcase(os.path.abspath(path)) if path else None,
            None if path else value,
        )
    return json.dumps(values, sort_keys=True, separators=(",", ":"))


def create_material_instances(manifest, resolved_textures, texture_map, folder, master):
    ensure_folder(folder)
    aliases, canonical_records = {}, {}
    signatures = {}
    for record in manifest["materials"]:
        sig = material_signature(record, resolved_textures.get(record["name"], {}))
        canonical = signatures.get(sig)
        if canonical is None:
            canonical = record["name"]
            signatures[sig] = canonical
            canonical_records[canonical] = record
        aliases[record["name"]] = canonical
        for source_name in record.get("source_names", []):
            aliases[source_name] = canonical

    instances = {}
    for canonical, record in canonical_records.items():
        name = clean_name(canonical)
        path = folder + "/" + name
        instance = unreal.EditorAssetLibrary.load_asset(path)
        if not instance:
            instance = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                name, folder, unreal.MaterialInstanceConstant,
                unreal.MaterialInstanceConstantFactoryNew(),
            )
        if not instance:
            raise RuntimeError("Could not create Material Instance " + path)

        unreal.MaterialEditingLibrary.set_material_instance_parent(instance, master)
        unreal.MaterialEditingLibrary.clear_all_material_instance_parameters(instance)

        for role, texture_param, scalar_param in (
            ("base_color", "BaseColorTexture", None),
            ("normal", "NormalTexture", None),
            ("roughness", "RoughnessTexture", "RoughnessValue"),
            ("metallic", "MetallicTexture", "MetallicValue"),
            ("orm", "ORMTexture", None),
        ):
            entry = record.get(role) or {}
            src = resolved_textures.get(canonical, {}).get(role)
            key = os.path.normcase(os.path.abspath(src)) if src else None
            texture = texture_map.get(key) if key else None
            value = entry.get("value")

            if texture:
                unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                    instance, texture_param, texture
                )
                if scalar_param:
                    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
                        instance, scalar_param, 1.0
                    )
                if role == "orm":
                    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
                        instance, "ORMEnabled", 1.0
                    )
            elif role == "base_color" and not src and isinstance(value, list) and len(value) >= 3:
                color = unreal.LinearColor(float(value[0]), float(value[1]), float(value[2]),
                                           float(value[3]) if len(value) > 3 else 1.0)
                unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
                    instance, "BaseColorColor", color
                )
            elif role in ("roughness", "metallic") and not src and isinstance(value, (int, float)):
                unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
                    instance, scalar_param, float(value)
                )
            # No normal texture: leave the Master's neutral normal texture active.

        unreal.MaterialEditingLibrary.update_material_instance(instance)
        unreal.EditorAssetLibrary.save_loaded_asset(instance)
        instances[canonical] = instance
    return aliases, instances


# ---------------------------------------------------------------------------
# FBX import and material assignment
# ---------------------------------------------------------------------------

def make_fbx_options(kind, skeleton):
    options = unreal.FbxImportUI()
    options.set_editor_property("automated_import_should_detect_type", False)
    options.set_editor_property("import_as_skeletal", kind == "skeletal")
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_materials", False)
    options.set_editor_property("import_textures", False)
    options.set_editor_property("import_animations", False)
    if kind == "static":
        data = options.get_editor_property("static_mesh_import_data")
        data.set_editor_property("combine_meshes", False)
    else:
        data = options.get_editor_property("skeletal_mesh_import_data")
        data.set_editor_property("update_skeleton_reference_pose", False)
        if skeleton:
            options.set_editor_property("skeleton", skeleton)
    return options


def set_mesh_slot(mesh, index, material):
    prop = "static_materials" if isinstance(mesh, unreal.StaticMesh) else "materials"
    slots = list(mesh.get_editor_property(prop))
    if index >= len(slots):
        raise RuntimeError("Material slot {} is missing on {}".format(index, mesh.get_name()))
    slots[index].set_editor_property("material_interface", material)
    mesh.set_editor_property(prop, slots)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)


def import_bundle(manifest_path, replace_existing, skeleton):
    manifest, fbx_path = validate_manifest(manifest_path)
    master = unreal.EditorAssetLibrary.load_asset(MASTER_MATERIAL_PATH)
    if not master or not isinstance(master, unreal.Material):
        raise RuntimeError(
            "Master material is missing: {}. Run unreal_dcc_material_builder.py "
            "once in this Unreal project first.".format(MASTER_MATERIAL_PATH)
        )
    kind = manifest["asset_type"]
    bundle = clean_name(manifest.get("asset_name", "Asset"))
    root = DEST_ROOT + "/" + bundle
    mesh_folder = root + ("/Static" if kind == "static" else "/Skeletal")
    mat_folder = root + "/Materials"
    tex_folder = root + "/Textures"
    for folder in (mesh_folder, mat_folder, tex_folder):
        ensure_folder(folder)

    resolved_textures = resolve_material_textures(manifest_path, manifest)
    special_notices = []
    for record in manifest["materials"]:
        found = [label for label, path in resolved_textures[record["name"]]["special_maps"].items() if path]
        if found:
            special_notices.append("{}: {}".format(record.get("source_name", record["name"]), ", ".join(found)))
    texture_map = import_textures(manifest, resolved_textures, tex_folder, replace_existing)
    aliases, instances = create_material_instances(
        manifest, resolved_textures, texture_map, mat_folder, master
    )

    destination_name = "SK_" + bundle if kind == "skeletal" else None
    meshes = import_task(
        fbx_path, mesh_folder, make_fbx_options(kind, skeleton),
        destination_name, replace_existing,
    )
    if not meshes:
        raise RuntimeError("FBX import created no mesh assets: " + fbx_path)

    if kind == "static":
        by_name = {m.get_name().casefold(): m for m in meshes
                   if isinstance(m, unreal.StaticMesh)}
        for mesh_info in manifest["meshes"]:
            mesh = by_name.get(mesh_info["name"].casefold())
            if not mesh:
                warn("Could not match Static Mesh from JSON: " + mesh_info["name"])
                continue
            for slot in mesh_info.get("materials", []):
                mat_name = slot.get("material")
                canonical = aliases.get(mat_name, mat_name)
                if canonical in instances:
                    set_mesh_slot(mesh, int(slot["slot"]), instances[canonical])
    else:
        skels = [m for m in meshes if isinstance(m, unreal.SkeletalMesh)]
        if len(skels) != 1:
            raise RuntimeError("Expected one combined Skeletal Mesh; got {}".format(len(skels)))
        mesh = skels[0]
        ordered = []
        for mesh_info in manifest["meshes"]:
            for slot in mesh_info.get("materials", []):
                mat_name = slot.get("material")
                canonical = aliases.get(mat_name, mat_name)
                if canonical and canonical not in ordered:
                    ordered.append(canonical)
        for index, canonical in enumerate(ordered):
            if canonical in instances:
                set_mesh_slot(mesh, index, instances[canonical])
        if not skeleton:
            skeleton = mesh.get_editor_property("skeleton")

    unreal.EditorAssetLibrary.save_directory(root, only_if_is_dirty=True)
    log("Imported {} ({})".format(os.path.basename(fbx_path), kind))
    for notice in special_notices:
        warn("Special map found; imported without automatic material setup. Configure manually: " + notice)
    return skeleton


def run():
    manifests = discover_manifests()
    # Validate every JSON/FBX pair before importing any of them.
    bundle_names = set()
    for path in manifests:
        data, _fbx = validate_manifest(path)
        bundle_names.add(clean_name(data.get("asset_name", "Asset")))
    if len(bundle_names) != 1:
        raise RuntimeError(
            "Use one source folder per bundle/character. Found multiple asset_name values: "
            + ", ".join(sorted(bundle_names))
        )

    existing = unreal.EditorAssetLibrary.list_assets(
        DEST_ROOT, recursive=True, include_folder=False
    )
    replace_existing = False
    if existing and ASK_BEFORE_REPLACE:
        answer = unreal.EditorDialog.show_message(
            "DCC Import",
            "The destination already has assets. Replace matching imported assets?",
            unreal.AppMsgType.OK_CANCEL,
            unreal.AppReturnType.CANCEL,
        )
        if answer != unreal.AppReturnType.OK:
            log("Cancelled by user.")
            return
        replace_existing = True

    skeleton = None
    if SKELETON_PATH:
        skeleton = unreal.EditorAssetLibrary.load_asset(SKELETON_PATH)
        if not skeleton:
            raise RuntimeError("Skeleton asset not found: " + SKELETON_PATH)

    for manifest_path in manifests:
        skeleton = import_bundle(manifest_path, replace_existing, skeleton)

    special_found = any(
        resolved_textures[record["name"]]["special_maps"][label]
        for manifest_path in manifests
        for manifest, _fbx in [validate_manifest(manifest_path)]
        for resolved_textures in [resolve_material_textures(manifest_path, manifest)]
        for record in manifest["materials"]
        for label in SPECIAL_MAP_SUFFIXES
    )
    summary = "Import finished."
    if special_found:
        summary += " SSS/Opacity/Emissive maps were detected; see Output Log and configure them manually."
    summary += " Review the Output Log for warnings."
    unreal.EditorDialog.show_message(
        "DCC Import", summary,
        unreal.AppMsgType.OK, unreal.AppReturnType.OK,
    )


try:
    run()
except Exception as error:
    unreal.log_error("[DCC Import] " + str(error))
    show_error(error)

