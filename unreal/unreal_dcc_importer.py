"""DCC FBX + JSON importer for Unreal Editor Python (UE 5.8 target).

Standalone editor script, not an Unreal plugin. Configure the paths below,
then run it inside Unreal Editor with Tools > Execute Python Script.

Expected Blender exporter contract (schema 2):
  <Bundle>_SM.fbx + <Bundle>_SM.json
  <Bundle>_SKM.fbx + <Bundle>_SKM.json

"""

import ctypes
import json
import os
import re
import sys
import unreal


# ---------------------------------------------------------------------------
# User configuration
# ---------------------------------------------------------------------------

DEST_ROOT = "/Game"

# Additional Substance Painter export folders. The selected source folder and
# its "textures/Substance" subfolder are searched automatically as well.
SUBSTANCE_TEXTURE_DIRS = []

# Substance output token aliases. ORM channel order follows the selected
# Unreal SSS Pack preset: R=AO, G=Roughness, B=Metallic.
MAP_SUFFIXES = {
    "base_color": ("BaseColor", "Base_Color", "Albedo", "Color", "Diffuse"),
    "normal": ("Normal", "Normal_OpenGL", "Normal_DirectX", "NormalGL", "NormalDX"),
    "roughness": ("Roughness", "Rough"),
    "metallic": ("Metallic", "Metalness", "Metal"),
    "ao": ("AO", "AmbientOcclusion", "Ambient_Occlusion", "Occlusion"),
    "orm": ("ORM", "OcclusionRoughnessMetallic", "Occlusion_Roughness_Metallic"),
}
SPECIAL_MAP_SUFFIXES = {
    "SSS": ("SSS", "Subsurface", "SubsurfaceColor", "SubsurfaceMask"),
    "Opacity": ("Opacity", "OpacityMask", "Alpha", "Transparency"),
    "EmissiveColor": ("EmissiveColor", "Emissive", "Emission"),
    "EmissiveMask": ("EmissiveMask", "EmissionMask"),
}
TEXTURE_EXTENSIONS = (".png", ".tga", ".tif", ".tiff", ".exr", ".jpg", ".jpeg")

# Optional path to an existing Skeleton asset, e.g.:
# /Game/Imports/Inna/Meshes/SKEL_Inna.SKEL_Inna
# Leave empty for the first import. The first imported skeletal asset creates it.
SKELETON_PATH = ""

MASTER_MATERIAL_PATH = "/Game/Materials/Master/MM_MasterSurface"
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
    manifests = choose_manifest_files()
    if manifests is None:
        return None
    if not manifests:
        raise RuntimeError("No supported manifest JSON files were selected.")
    return manifests


def choose_manifest_files():
    """Open one Explorer-style dialog to browse and multi-select manifests."""
    if sys.platform != "win32":
        raise RuntimeError(
            "The manifest file picker currently requires Unreal Editor on Windows."
        )

    class OPENFILENAMEW(ctypes.Structure):
        _fields_ = [
            ("lStructSize", ctypes.c_uint),
            ("hwndOwner", ctypes.c_void_p),
            ("hInstance", ctypes.c_void_p),
            ("lpstrFilter", ctypes.c_wchar_p),
            ("lpstrCustomFilter", ctypes.c_wchar_p),
            ("nMaxCustFilter", ctypes.c_uint),
            ("nFilterIndex", ctypes.c_uint),
            ("lpstrFile", ctypes.c_wchar_p),
            ("nMaxFile", ctypes.c_uint),
            ("lpstrFileTitle", ctypes.c_wchar_p),
            ("nMaxFileTitle", ctypes.c_uint),
            ("lpstrInitialDir", ctypes.c_wchar_p),
            ("lpstrTitle", ctypes.c_wchar_p),
            ("Flags", ctypes.c_uint),
            ("nFileOffset", ctypes.c_ushort),
            ("nFileExtension", ctypes.c_ushort),
            ("lpstrDefExt", ctypes.c_wchar_p),
            ("lCustData", ctypes.c_ssize_t),
            ("lpfnHook", ctypes.c_void_p),
            ("lpTemplateName", ctypes.c_wchar_p),
            ("pvReserved", ctypes.c_void_p),
            ("dwReserved", ctypes.c_uint),
            ("FlagsEx", ctypes.c_uint),
        ]

    file_buffer = ctypes.create_unicode_buffer(32768)
    title_buffer = ctypes.create_unicode_buffer(1024)
    filters = ctypes.create_unicode_buffer("DCC manifests\0*_SM.json;*_SKM.json\0\0")
    dialog = OPENFILENAMEW()
    dialog.lStructSize = ctypes.sizeof(OPENFILENAMEW)
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    dialog.hwndOwner = user32.GetForegroundWindow()
    dialog.lpstrFilter = ctypes.cast(filters, ctypes.c_wchar_p)
    dialog.nFilterIndex = 1
    dialog.lpstrFile = ctypes.cast(file_buffer, ctypes.c_wchar_p)
    dialog.nMaxFile = len(file_buffer)
    dialog.lpstrFileTitle = ctypes.cast(title_buffer, ctypes.c_wchar_p)
    dialog.nMaxFileTitle = len(title_buffer)
    dialog.lpstrInitialDir = os.path.expanduser("~")
    dialog.lpstrTitle = "Choose DCC manifest JSON file(s) to import"
    dialog.Flags = 0x00001000 | 0x00000800 | 0x00080000 | 0x00000200 | 0x00000004
    # OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_EXPLORER |
    # OFN_ALLOWMULTISELECT | OFN_HIDEREADONLY

    comdlg32 = ctypes.windll.comdlg32
    comdlg32.GetOpenFileNameW.argtypes = [ctypes.POINTER(OPENFILENAMEW)]
    comdlg32.GetOpenFileNameW.restype = ctypes.c_int
    if not comdlg32.GetOpenFileNameW(ctypes.byref(dialog)):
        log("Manifest file selection cancelled.")
        return None

    # In Explorer multi-select mode, the buffer contains either one full path,
    # or directory\0filename1\0filename2\0\0.
    values = file_buffer[:]
    first_end = values.find("\0")
    if first_end < 0:
        raise RuntimeError("Could not read selected manifest file paths.")
    first = values[:first_end]
    second_end = values.find("\0", first_end + 1)
    second = values[first_end + 1:second_end] if second_end >= 0 else ""
    if not second:
        selected = [first]
    else:
        names = [name for name in values[first_end + 1:].split("\0") if name]
        selected = [os.path.join(first, name) for name in names]

    normalized = []
    for path in selected:
        path = os.path.abspath(path)
        name = os.path.basename(path)
        if not (name.endswith("_SM.json") or name.endswith("_SKM.json")):
            raise RuntimeError("Unsupported manifest name: " + name)
        normalized.append(path)
    return sorted(set(normalized), key=str.casefold)


def validate_manifest(path):
    data = load_json(path)
    if data.get("schema_version") != 2:
        raise RuntimeError(
            "{} uses schema_version {}. This importer requires schema 2 and "
            "separate _SM/_SKM exports."
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
    expected = "_SM" if kind == "static" else "_SKM"
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
    """Return only locations reserved for Substance Painter output."""
    source_dir = os.path.dirname(os.path.abspath(manifest_path))
    candidates = [
        os.path.join(source_dir, "textures", "Substance"),
        os.path.join(source_dir, "Substance"),
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
    """Find an SP map by material name and suffix, allowing a project prefix."""
    aliases = material_aliases(record)
    expected = []
    for alias in aliases:
        alias_tokens = re.findall(r"[a-z0-9]+", alias.casefold())
        if not alias_tokens:
            continue
        for suffix in (suffixes or MAP_SUFFIXES[role]):
            suffix_tokens = re.findall(r"[a-z0-9]+", suffix.casefold())
            expected.append((alias_tokens + suffix_tokens, len(normalize_token(alias)), alias, suffix))

    matches = []
    for root in texture_search_dirs(manifest_path):
        for current, _dirs, files in os.walk(root):
            for filename in files:
                ext = os.path.splitext(filename)[1].casefold()
                if ext not in TEXTURE_EXTENSIONS:
                    continue
                stem_tokens = re.findall(
                    r"[a-z0-9]+", os.path.splitext(filename)[0].casefold()
                )
                for expected_tokens, alias_length, alias, suffix in expected:
                    if (len(stem_tokens) >= len(expected_tokens)
                            and stem_tokens[-len(expected_tokens):] == expected_tokens):
                        matches.append((
                            alias_length, filename, os.path.join(current, filename), alias, suffix
                        ))
                        break

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
    """Resolve maps in the agreed order: ORM pack, Substance, Blender image."""
    result = {}
    for record in manifest["materials"]:
        name = record["name"]
        result[name] = {}
        for role in MAP_SUFFIXES:
            entry = record.get(role) or {}
            blender_path = source_file_for(manifest_path, entry.get("texture"))
            substance_path = find_substance_texture(record, role, manifest_path)
            result[name][role] = substance_path or blender_path
        result[name]["special_maps"] = {}
        for label, suffixes in SPECIAL_MAP_SUFFIXES.items():
            result[name]["special_maps"][label] = find_substance_texture(record, label, manifest_path, suffixes)
            result[name]["special_" + label.casefold()] = result[name]["special_maps"][label]
        emission_entry = record.get("emission_color", {"value": [0.0, 0.0, 0.0, 1.0]})
        blender_emission_path = source_file_for(manifest_path, emission_entry.get("texture"))
        substance_emission_path = result[name]["special_emissivecolor"]
        result[name]["emission_color_texture"] = substance_emission_path or blender_emission_path
        result[name]["emission_color"] = emission_entry
        result[name]["emission_strength"] = record.get(
            "emission_strength", {"value": 0.0}
        )
    return result


# ---------------------------------------------------------------------------
# Textures and Material Instances
# ---------------------------------------------------------------------------

def import_textures(manifest, resolved_textures, texture_folder, replace_existing):
    ensure_folder(texture_folder)
    by_source = {}
    used_names = set()
    for mat in manifest["materials"]:
        for role in list(MAP_SUFFIXES) + [
            "special_sss", "special_opacity", "special_emissivecolor"
        ]:
            src = resolved_textures.get(mat["name"], {}).get(role)
            if role == "special_emissivecolor":
                src = resolved_textures.get(mat["name"], {}).get("emission_color_texture")
            if not src:
                continue
            key = (os.path.normcase(os.path.abspath(src)), role)
            if key in by_source:
                continue
            material_name = mat.get("source_name") or mat.get("name", "MI_Material")
            if material_name.startswith("MI_"):
                material_name = material_name[3:]
            suffix = {
                "base_color": "BaseColor",
                "normal": "Normal",
                "roughness": "Roughness",
                "metallic": "Metallic",
                "ao": "AO",
                "orm": "ORM",
                "special_sss": "SSS",
                "special_opacity": "OpacityMask",
                "special_emissivecolor": "EmissiveColor",
            }.get(role, role.title().replace("_", ""))
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
            # Keep role-specific copies when one source image feeds multiple
            # channels, because Unreal's sRGB and compression settings differ.
            texture.set_editor_property(
                "srgb", role in ("base_color", "special_emissivecolor")
            )
            if role == "normal":
                set_optional(texture, "compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            elif role in ("roughness", "metallic", "ao", "orm") or role.startswith("special_"):
                set_optional(texture, "compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
            unreal.EditorAssetLibrary.save_loaded_asset(texture)
            by_source[key] = texture
    return by_source


def material_signature(record, resolved):
    values = {}
    for role in ("base_color", "normal", "roughness", "metallic", "ao", "orm"):
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
    values["emission_color"] = (record.get("emission_color") or {}).get("value")
    values["emission_strength"] = (record.get("emission_strength") or {}).get("value")
    for label, path in (
        ("emissive_color_texture", resolved.get("emission_color_texture")),
    ):
        values[label] = os.path.normcase(os.path.abspath(path)) if path else None
    return json.dumps(values, sort_keys=True, separators=(",", ":"))


def set_static_switch(instance, name, enabled):
    unreal.MaterialEditingLibrary.set_material_instance_static_switch_parameter_value(
        instance,
        name,
        bool(enabled),
        association=unreal.MaterialParameterAssociation.GLOBAL_PARAMETER,
        update_material_instance=True,
    )


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
        resolved = resolved_textures.get(canonical, {})

        def imported_texture(role, source_key=None):
            src = resolved.get(source_key or role)
            key = (os.path.normcase(os.path.abspath(src)), role) if src else None
            return texture_map.get(key) if key else None

        def set_vector_if_valid(parameter_name, value):
            if isinstance(value, (list, tuple)) and len(value) >= 3:
                color = unreal.LinearColor(
                    float(value[0]), float(value[1]), float(value[2]),
                    float(value[3]) if len(value) > 3 else 1.0,
                )
                unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
                    instance, parameter_name, color
                )

        def set_scalar_if_valid(parameter_name, value):
            if isinstance(value, (int, float)):
                unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
                    instance, parameter_name, float(value)
                )

        # Base Color: texture when present, otherwise the vector fallback.
        base_color_texture = imported_texture("base_color")
        if base_color_texture:
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                instance, "BaseColorTexture", base_color_texture
            )
        set_vector_if_valid("BaseColorScalar", (record.get("base_color") or {}).get("value"))
        set_static_switch(instance, "UseBaseColorTexture", bool(base_color_texture))

        # Normal has a neutral texture default in the master; only override it
        # when a source texture was imported successfully.
        normal_texture = imported_texture("normal")
        if normal_texture:
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                instance, "NormalTexture", normal_texture
            )

        # ORM is a shared path for AO, Roughness and Metallic. Without it, each
        # channel independently selects its own texture or scalar fallback.
        orm_texture = imported_texture("orm")
        if orm_texture:
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                instance, "ORMTexture", orm_texture
            )
        set_static_switch(instance, "UseORMPack", bool(orm_texture))

        for role, texture_param, scalar_param, switch_param in (
            ("ao", "AOTexture", "AOValue", "UseUnpackedAO"),
            ("roughness", "RoughnessTexture", "RoughnessValue", "UseUnpackedRoughness"),
            ("metallic", "MetallicTexture", "MetallicValue", "UseUnpackedMetallic"),
        ):
            texture = imported_texture(role)
            if texture:
                unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                    instance, texture_param, texture
                )
            set_scalar_if_valid(scalar_param, (record.get(role) or {}).get("value"))
            set_static_switch(instance, switch_param, bool(texture))

        # Emissive color uses its own texture/fallback switch and an outer
        # enable switch. The current master graph has no emissive-mask input.
        emissive_texture = imported_texture(
            "special_emissivecolor", "emission_color_texture"
        )
        if emissive_texture:
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                instance, "EmissiveColorTexture", emissive_texture
            )
        emission_color = (record.get("emission_color") or {}).get("value")
        set_vector_if_valid("EmissiveColor", emission_color)
        set_static_switch(instance, "UseEmissiveTexture", bool(emissive_texture))

        emission_strength = (record.get("emission_strength") or {}).get("value")
        set_scalar_if_valid("EmissiveStrength", emission_strength)
        color_values = emission_color if isinstance(emission_color, (list, tuple)) else []
        has_emission = bool(
            isinstance(emission_strength, (int, float)) and emission_strength > 0.0
            and (
                emissive_texture
                or any(float(value) > 0.0 for value in color_values[:3])
            )
        )
        set_static_switch(instance, "UseEmissive", has_emission)

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
            "Master material is missing: {}. Run unreal_dcc_basic_template_generator.py "
            "once in this Unreal project first.".format(MASTER_MATERIAL_PATH)
        )
    kind = manifest["asset_type"]
    bundle = clean_name(manifest.get("asset_name", "Asset"))
    root = DEST_ROOT + "/Imports/" + bundle
    mesh_folder = root + "/Meshes"
    mat_folder = root + "/Materials"
    tex_folder = root + "/Textures"
    for folder in (mesh_folder, mat_folder, tex_folder):
        ensure_folder(folder)

    resolved_textures = resolve_material_textures(manifest_path, manifest)
    special_notices = []
    for record in manifest["materials"]:
        found = [
            label for label in ("SSS", "Opacity")
            if resolved_textures[record["name"]]["special_maps"].get(label)
        ]
        if found:
            special_notices.append("{}: {}".format(record.get("source_name", record["name"]), ", ".join(found)))
    texture_map = import_textures(manifest, resolved_textures, tex_folder, replace_existing)
    aliases, instances = create_material_instances(
        manifest, resolved_textures, texture_map, mat_folder, master
    )

    destination_name = "SKM_" + bundle if kind == "skeletal" else None
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
    if manifests is None:
        return
    # Validate every JSON/FBX pair before importing any of them.
    for path in manifests:
        validate_manifest(path)

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

    shared_skeleton = None
    if SKELETON_PATH:
        shared_skeleton = unreal.EditorAssetLibrary.load_asset(SKELETON_PATH)
        if not shared_skeleton:
            raise RuntimeError("Skeleton asset not found: " + SKELETON_PATH)

    skeleton_by_bundle = {}
    for manifest_path in manifests:
        manifest, _fbx = validate_manifest(manifest_path)
        bundle = clean_name(manifest.get("asset_name", "Asset"))
        skeleton = skeleton_by_bundle.get(bundle, shared_skeleton)
        skeleton_by_bundle[bundle] = import_bundle(
            manifest_path, replace_existing, skeleton
        )

    special_found = any(
        resolved_textures[record["name"]]["special_maps"].get(label)
        for manifest_path in manifests
        for manifest, _fbx in [validate_manifest(manifest_path)]
        for resolved_textures in [resolve_material_textures(manifest_path, manifest)]
        for record in manifest["materials"]
        for label in ("SSS", "Opacity")
    )
    summary = "Import finished."
    if special_found:
        summary += " SSS/Opacity maps were detected but are not part of this background master material. See Output Log."
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

