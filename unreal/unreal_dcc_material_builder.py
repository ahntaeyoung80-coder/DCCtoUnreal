"""Create the shared DCC master material in Unreal Editor.

Run this standalone Unreal Editor Python script once per project before running
unreal_dcc_importer.py. This is an intermediate builder, not the final content
plugin/package. It preserves the current prototype graph while separating
asset generation from the FBX/JSON importer.
"""

import os
import unreal


MASTER_MATERIAL_PATH = "/Game/DCC/Shared/Materials/M_DCC_Master_v2"


def ensure_folder(path):
    unreal.EditorAssetLibrary.make_directory(path)


def create_master_material():
    path = MASTER_MATERIAL_PATH
    material = unreal.EditorAssetLibrary.load_asset(path)
    if material:
        unreal.log("[DCC Material Builder] Existing master material kept: " + path)
        return material

    folder = os.path.dirname(path)
    ensure_folder(folder)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    material = tools.create_asset(
        os.path.basename(path), folder, unreal.Material, unreal.MaterialFactoryNew()
    )
    if not material:
        raise RuntimeError("Could not create " + os.path.basename(path))

    edit = unreal.MaterialEditingLibrary
    white = unreal.load_object(
        None, "/Engine/EngineResources/WhiteSquareTexture.WhiteSquareTexture"
    )
    flat_normal = unreal.load_object(
        None, "/Engine/EngineMaterials/DefaultNormal.DefaultNormal"
    )
    if not white:
        raise RuntimeError("Unreal Engine built-in WhiteSquareTexture could not be loaded.")
    if not flat_normal:
        raise RuntimeError(
            "Unreal Engine built-in DefaultNormal texture could not be loaded. "
            "Expected /Engine/EngineMaterials/DefaultNormal.DefaultNormal"
        )

    def expr(cls, x, y):
        node = edit.create_material_expression(material, cls, x, y)
        if not node:
            raise RuntimeError("Could not create material expression " + str(cls))
        return node

    def param(node, name):
        node.set_editor_property("parameter_name", name)
        return node

    # Prototype Base Color path: texture multiplied by an optional vector tint.
    base_tex = param(
        expr(unreal.MaterialExpressionTextureSampleParameter2D, -700, -80),
        "BaseColorTexture",
    )
    base_tex.set_editor_property("texture", white)
    base_tint = param(
        expr(unreal.MaterialExpressionVectorParameter, -700, 100),
        "BaseColorColor",
    )
    base_tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    base_mul = expr(unreal.MaterialExpressionMultiply, -350, 0)
    edit.connect_material_expressions(base_tex, "", base_mul, "A")
    edit.connect_material_expressions(base_tint, "", base_mul, "B")
    edit.connect_material_property(base_mul, "", unreal.MaterialProperty.MP_BASE_COLOR)

    normal_tex = param(
        expr(unreal.MaterialExpressionTextureSampleParameter2D, -350, 220),
        "NormalTexture",
    )
    normal_tex.set_editor_property("texture", flat_normal)
    edit.connect_material_property(normal_tex, "RGB", unreal.MaterialProperty.MP_NORMAL)

    orm_tex = param(
        expr(unreal.MaterialExpressionTextureSampleParameter2D, -700, 900),
        "ORMTexture",
    )
    orm_tex.set_editor_property("texture", white)
    orm_enabled = param(
        expr(unreal.MaterialExpressionScalarParameter, -700, 1400), "ORMEnabled"
    )
    orm_enabled.set_editor_property("default_value", 0.0)

    # ORM channels: R=AO, G=Roughness, B=Metallic. Individual maps/values are
    # retained as the fallback path while the graph strategy is being refined.
    for channel, y in (("R", 900), ("G", 1050), ("B", 1200)):
        if channel == "R":
            edit.connect_material_property(
                orm_tex, channel, unreal.MaterialProperty.MP_AMBIENT_OCCLUSION
            )
            continue

        role = "roughness" if channel == "G" else "metallic"
        prop = (
            unreal.MaterialProperty.MP_ROUGHNESS
            if channel == "G"
            else unreal.MaterialProperty.MP_METALLIC
        )
        fallback = param(
            expr(unreal.MaterialExpressionTextureSampleParameter2D, -700, y + 250),
            role.title() + "Texture",
        )
        fallback.set_editor_property("texture", white)
        scalar = param(
            expr(unreal.MaterialExpressionScalarParameter, -700, y + 380),
            role.title() + "Value",
        )
        scalar.set_editor_property("default_value", 0.5 if role == "roughness" else 0.0)
        mul = expr(unreal.MaterialExpressionMultiply, -350, y + 250)
        edit.connect_material_expressions(fallback, "R", mul, "A")
        edit.connect_material_expressions(scalar, "", mul, "B")
        lerp = expr(unreal.MaterialExpressionLinearInterpolate, 0, y)
        edit.connect_material_expressions(mul, "", lerp, "A")
        edit.connect_material_expressions(orm_tex, channel, lerp, "B")
        edit.connect_material_expressions(orm_enabled, "", lerp, "Alpha")
        edit.connect_material_property(lerp, "", prop)

    edit.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material)
    unreal.log("[DCC Material Builder] Created master material: " + path)
    return material


try:
    create_master_material()
    unreal.EditorDialog.show_message(
        "DCC Material Builder",
        "Master material is ready. You can now run unreal_dcc_importer.py.",
        unreal.AppMsgType.OK,
        unreal.AppReturnType.OK,
    )
except Exception as error:
    unreal.log_error("[DCC Material Builder] " + str(error))
    unreal.EditorDialog.show_message(
        "DCC Material Builder Error",
        str(error),
        unreal.AppMsgType.OK,
        unreal.AppReturnType.OK,
    )
