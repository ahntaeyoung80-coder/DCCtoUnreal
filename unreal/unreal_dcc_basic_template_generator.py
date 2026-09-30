"""Create the starter DCC content folders and master material in Unreal.

Run this standalone script from Unreal Editor with Tools > Execute Python
Script. It is intended for an existing project and does not create a .upack.
"""

import os
import unreal


CONTENT_ROOT = "/Game"
IMPORTS_ROOT = CONTENT_ROOT + "/Imports"
MASTER_MATERIALS = CONTENT_ROOT + "/Materials/Master"
MASTER_NAME = "MM_MasterSurface"
MASTER_PATH = MASTER_MATERIALS + "/" + MASTER_NAME
LEGACY_MASTER_PATH = "/Game/DCC/Shared/Materials/" + MASTER_NAME


def ensure_folder(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        if not unreal.EditorAssetLibrary.make_directory(path):
            raise RuntimeError("Could not create Content folder: " + path)


def set_optional(obj, property_name, value):
    try:
        obj.set_editor_property(property_name, value)
        return True
    except Exception as exc:
        unreal.log_warning(
            "[DCC Template] Could not set {}: {}".format(property_name, exc)
        )
        return False


def create_master_material():
    material = unreal.EditorAssetLibrary.load_asset(MASTER_PATH)
    if material:
        unreal.log("[DCC Template] Existing master material left unchanged: " + MASTER_PATH)
        return material

    legacy_material = unreal.EditorAssetLibrary.load_asset(LEGACY_MASTER_PATH)
    if legacy_material:
        if not unreal.EditorAssetLibrary.rename_asset(LEGACY_MASTER_PATH, MASTER_PATH):
            raise RuntimeError(
                "Could not move the existing master material from {} to {}."
                .format(LEGACY_MASTER_PATH, MASTER_PATH)
            )
        material = unreal.EditorAssetLibrary.load_asset(MASTER_PATH)
        if not material:
            raise RuntimeError("Could not load the relocated master material: " + MASTER_PATH)
        unreal.log("[DCC Template] Existing legacy master moved and left unchanged: " + MASTER_PATH)
        return material

    tools = unreal.AssetToolsHelpers.get_asset_tools()
    material = tools.create_asset(
        MASTER_NAME,
        MASTER_MATERIALS,
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if not material:
        raise RuntimeError("Could not create master material: " + MASTER_PATH)

    set_optional(material, "blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    set_optional(material, "shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)

    white = unreal.load_object(
        None, "/Engine/EngineResources/WhiteSquareTexture.WhiteSquareTexture"
    )
    flat_normal = unreal.load_object(
        None, "/Engine/EngineMaterials/DefaultNormal.DefaultNormal"
    )
    if not white:
        raise RuntimeError("Unreal built-in WhiteSquareTexture could not be loaded.")
    if not flat_normal:
        raise RuntimeError("Unreal built-in DefaultNormal texture could not be loaded.")

    edit = unreal.MaterialEditingLibrary

    def expression(expression_class, x, y):
        node = edit.create_material_expression(material, expression_class, x, y)
        if not node:
            raise RuntimeError("Could not create material expression: " + str(expression_class))
        return node

    def parameter(node, name, group=None, default=None):
        node.set_editor_property("parameter_name", name)
        if group:
            set_optional(node, "group", group)
        if default is not None:
            set_optional(node, "default_value", default)
        return node

    def multiply(a, a_output, b, b_input, x, y):
        node = expression(unreal.MaterialExpressionMultiply, x, y)
        connect(a, a_output, node, "A")
        connect(b, b_input, node, "B")
        return node

    def connect(source, output_name, target, input_name):
        if not edit.connect_material_expressions(source, output_name, target, input_name):
            raise RuntimeError(
                "Could not connect {}.{} to {}.{}".format(
                    source.get_name(), output_name, target.get_name(), input_name
                )
            )

    def connect_property(source, output_name, property_name):
        if not edit.connect_material_property(source, output_name, property_name):
            raise RuntimeError(
                "Could not connect {} to material property {}".format(
                    source.get_name(), property_name
                )
            )

    # Base Color: a missing texture falls back to white, so the color value
    # remains visible when the importer has no image to assign.
    base_texture = parameter(
        expression(unreal.MaterialExpressionTextureSampleParameter2D, -1000, -100),
        "BaseColorTexture", "01 Surface",
    )
    base_texture.set_editor_property("texture", white)
    base_color = parameter(
        expression(unreal.MaterialExpressionVectorParameter, -1000, 80),
        "BaseColorColor", "01 Surface",
        unreal.LinearColor(1.0, 1.0, 1.0, 1.0),
    )
    base_result = multiply(base_texture, "RGB", base_color, "", -650, -10)
    connect_property(base_result, "", unreal.MaterialProperty.MP_BASE_COLOR)

    # Normal: Unreal's neutral built-in normal is used when no map is assigned.
    normal_texture = parameter(
        expression(unreal.MaterialExpressionTextureSampleParameter2D, -1000, 250),
        "NormalTexture", "01 Surface",
    )
    normal_texture.set_editor_property("texture", flat_normal)
    connect_property(normal_texture, "RGB", unreal.MaterialProperty.MP_NORMAL)

    # Separate scalar / grayscale texture route used when there is no ORM pack.
    separate_inputs = {}
    for index, (role, property_name, default_value) in enumerate((
        ("AO", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION, 1.0),
        ("Roughness", unreal.MaterialProperty.MP_ROUGHNESS, 0.5),
        ("Metallic", unreal.MaterialProperty.MP_METALLIC, 0.0),
    )):
        y = 520 + index * 300
        texture = parameter(
            expression(unreal.MaterialExpressionTextureSampleParameter2D, -1000, y),
            role + "Texture", "02 Surface Maps",
        )
        texture.set_editor_property("texture", white)
        scalar = parameter(
            expression(unreal.MaterialExpressionScalarParameter, -1000, y + 120),
            role + "Value", "02 Surface Maps", default_value,
        )
        scaled_map = multiply(texture, "R", scalar, "", -650, y + 30)
        separate_inputs[role] = (scaled_map, property_name)

    orm_texture = parameter(
        expression(unreal.MaterialExpressionTextureSampleParameter2D, -1000, 1500),
        "ORMTexture", "02 Surface Maps",
    )
    orm_texture.set_editor_property("texture", white)
    for channel, role, y in (("R", "AO", 550), ("G", "Roughness", 850), ("B", "Metallic", 1150)):
        separate, property_name = separate_inputs[role]
        switch = expression(unreal.MaterialExpressionStaticSwitchParameter, -250, y)
        switch.set_editor_property("parameter_name", "UseORMPack")
        switch.set_editor_property("default_value", False)
        switch.set_editor_property("group", "02 Surface Maps")
        # The importer sets each switch together when an ORM pack is found.
        connect(separate, "", switch, "A")
        connect(orm_texture, channel, switch, "B")
        connect_property(switch, "", property_name)

    # All three channel switches use the same parameter name, so the Material
    # Instance exposes one UseORMPack toggle for the entire packed texture.

    # Optional emissive path: the importer enables it only when Blender provides
    # emission data or an external emissive mask. A missing mask defaults to white.
    emissive_color_texture = parameter(
        expression(unreal.MaterialExpressionTextureSampleParameter2D, -1000, 2110),
        "EmissiveColorTexture", "03 Optional Emissive",
    )
    emissive_color_texture.set_editor_property("texture", white)
    emissive_mask = parameter(
        expression(unreal.MaterialExpressionTextureSampleParameter2D, -1000, 2200),
        "EmissiveMaskTexture", "03 Optional Emissive",
    )
    emissive_mask.set_editor_property("texture", white)
    emissive_color = parameter(
        expression(unreal.MaterialExpressionVectorParameter, -1000, 2350),
        "EmissiveColor", "03 Optional Emissive",
        unreal.LinearColor(0.0, 0.0, 0.0, 1.0),
    )
    emissive_strength = parameter(
        expression(unreal.MaterialExpressionScalarParameter, -1000, 2500),
        "EmissiveStrength", "03 Optional Emissive", 0.0,
    )
    emissive_texture_color = multiply(
        emissive_color_texture, "RGB", emissive_color, "", -650, 2150
    )
    emissive_tint = multiply(
        emissive_texture_color, "", emissive_mask, "R", -350, 2220
    )
    emissive_result = multiply(emissive_tint, "", emissive_strength, "", -100, 2280)
    emissive_switch = parameter(
        expression(unreal.MaterialExpressionStaticSwitchParameter, -100, 2320),
        "UseEmissive", "03 Optional Emissive", False,
    )
    zero = expression(unreal.MaterialExpressionConstant, -350, 2510)
    zero.set_editor_property("r", 0.0)
    connect(zero, "", emissive_switch, "A")
    connect(emissive_result, "", emissive_switch, "B")
    connect_property(emissive_switch, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    compile_errors = edit.recompile_material(material)
    if compile_errors:
        raise RuntimeError(
            "Master material graph was rebuilt, but Unreal reported compile errors:\n"
            + "\n".join(str(error) for error in compile_errors)
        )
    if not unreal.EditorAssetLibrary.save_loaded_asset(material):
        raise RuntimeError("Could not save rebuilt master material: " + MASTER_PATH)
    edit.refresh_material_editor(material)
    unreal.log("[DCC Template] Master material is ready: " + MASTER_PATH)
    return material


def generate_template_content():
    ensure_folder(IMPORTS_ROOT)
    ensure_folder(MASTER_MATERIALS)
    create_master_material()
    unreal.EditorAssetLibrary.save_directory(IMPORTS_ROOT, only_if_is_dirty=True)
    unreal.EditorAssetLibrary.save_directory(MASTER_MATERIALS, only_if_is_dirty=True)


try:
    generate_template_content()
    unreal.EditorDialog.show_message(
        "DCC Basic Template Generator",
        "Import folders and MM_MasterSurface are ready.\n\n"
        "Imports: /Game/Imports\n"
        "Master material: /Game/Materials/Master/MM_MasterSurface\n"
        "Existing master materials are left unchanged.",
        unreal.AppMsgType.OK,
        unreal.AppReturnType.OK,
    )
except Exception as error:
    unreal.log_error("[DCC Template] " + str(error))
    unreal.EditorDialog.show_message(
        "DCC Basic Template Generator Error",
        str(error),
        unreal.AppMsgType.OK,
        unreal.AppReturnType.OK,
    )
