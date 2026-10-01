"""Export a selected Unreal material graph as a read-only JSON report.

Run inside Unreal Editor with Tools > Execute Python Script... after selecting
exactly one Material asset in the Content Browser. The script does not save,
compile, or modify Unreal assets.
"""

import json
import os
import re
import traceback
import unreal


REPORT_SUBDIR = "MaterialGraphReports"
# Set this to an absolute directory to write outside the Unreal project.
# Leave as None to use <Project>/Saved/MaterialGraphReports.
OUTPUT_DIRECTORY = None
SCHEMA_VERSION = 2


def safe_get(obj, property_name, default=None):
    try:
        return obj.get_editor_property(property_name)
    except Exception:
        return default


def object_path(obj):
    if obj is None:
        return None
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def expression_label(expression, index):
    description = safe_get(expression, "desc", "") or ""
    name = expression.get_name()
    return description.strip() or name or "Node_{:03d}".format(index)


def extract_input_connection(material, expression, input_name):
    """Read an FExpressionInput-like property when exposed by UE Python."""
    property_name = re.sub(r"[^a-zA-Z0-9_]", "", input_name).lower()
    input_value = safe_get(expression, property_name)
    if input_value is None:
        return {"status": "unavailable", "source_node": None, "output_name": None}

    source = safe_get(input_value, "expression")
    if source is None:
        return {"status": "unconnected", "source_node": None, "output_name": None}

    try:
        output_name = unreal.MaterialEditingLibrary.get_input_node_output_name_for_material_expression(
            expression, source
        )
    except Exception:
        output_name = None

    return {
        "status": "connected",
        "source_node": source.get_name(),
        "output_name": str(output_name) if output_name else None,
    }


def parameter_info(expression, class_name):
    info = {}
    parameter_name = safe_get(expression, "parameter_name")
    if parameter_name is not None:
        info["name"] = str(parameter_name)

    if "ScalarParameter" in class_name:
        value = safe_get(expression, "default_value")
        if value is not None:
            info["default"] = float(value)
    elif "VectorParameter" in class_name:
        value = safe_get(expression, "default_value")
        if value is not None:
            try:
                info["default"] = {"r": value.r, "g": value.g, "b": value.b, "a": value.a}
            except Exception:
                info["default"] = str(value)
    elif "TextureSampleParameter" in class_name or "TextureObjectParameter" in class_name:
        texture = safe_get(expression, "texture")
        info["default_texture"] = object_path(texture)
    elif "StaticSwitchParameter" in class_name:
        value = safe_get(expression, "default_value")
        if value is not None:
            info["default"] = bool(value)
    return info or None


def expression_value_info(expression, class_name):
    """Capture literal values and sampling options that affect node behavior."""
    values = {}
    if class_name == "MaterialExpressionConstant":
        value = safe_get(expression, "r")
        if value is not None:
            values["constant"] = float(value)
    elif class_name == "MaterialExpressionConstant2Vector":
        for component in ("r", "g"):
            value = safe_get(expression, component)
            if value is not None:
                values[component] = float(value)
    elif class_name in ("MaterialExpressionConstant3Vector", "MaterialExpressionConstant4Vector"):
        value = safe_get(expression, "constant")
        if value is not None:
            try:
                values["constant"] = {"r": value.r, "g": value.g, "b": value.b, "a": value.a}
            except Exception:
                values["constant"] = str(value)

    if "TextureSample" in class_name:
        for property_name in ("sampler_type", "sampler_source", "mip_value_mode", "const_mip_value"):
            value = safe_get(expression, property_name)
            if value is not None:
                values[property_name] = str(value) if not isinstance(value, (bool, int, float, str)) else value
    return values or None


def material_settings(material):
    settings = {}
    for key in ("blend_mode", "shading_model", "two_sided", "opacity_mask_clip_value"):
        value = safe_get(material, key)
        if value is not None:
            settings[key] = str(value) if key.endswith("mode") or key == "shading_model" else value
    return settings


def build_report(material):
    library = unreal.MaterialEditingLibrary
    expressions = list(library.get_material_expressions(material))
    nodes = []
    connections = []
    warnings = []
    unavailable_pin_count = 0
    unconnected_pin_count = 0
    known_source_target_pairs = set()
    source_node_only_pairs = set()
    aligned_expression_count = 0
    unaligned_expression_count = 0

    for index, expression in enumerate(expressions):
        class_name = expression.get_class().get_name()
        node_id = expression.get_name()
        try:
            input_names = list(library.get_material_expression_input_names(expression))
        except Exception:
            input_names = []
            warnings.append("입력 핀 이름 조회 실패: " + node_id)
        try:
            incoming = library.get_inputs_for_material_expression(material, expression)
            incoming = list(incoming) if incoming is not None else []
        except Exception:
            incoming = None
            warnings.append("입력 노드 조회 실패: " + node_id)

        # The UE Python API returns an entry for each input in the current
        # observed UE 5.8.3 graph (None for empty pins). Epic's docs do not
        # guarantee that this array order matches the pin-name array, so mark
        # the positional mapping as unverified in the report.
        arrays_align = incoming is not None and len(incoming) == len(input_names)
        if input_names and arrays_align:
            aligned_expression_count += 1
        elif input_names:
            unaligned_expression_count += 1

        try:
            output_names = list(library.get_material_expression_output_names(expression))
        except Exception:
            output_names = []

        inputs = []
        for input_index, input_name in enumerate(input_names):
            link = extract_input_connection(material, expression, input_name)
            resolution = "expression_input_property"

            # Prefer the direct FExpressionInput property when UE exposes it.
            # Otherwise, use the matching array position only when the two
            # arrays have equal lengths; the report preserves this assumption.
            if link["status"] == "unavailable" and arrays_align:
                source = incoming[input_index]
                if source is None:
                    link = {
                        "status": "unconnected",
                        "source_node": None,
                        "output_name": None,
                    }
                    resolution = "index_aligned_unverified"
                    unconnected_pin_count += 1
                else:
                    try:
                        output_name = library.get_input_node_output_name_for_material_expression(
                            expression, source
                        )
                    except Exception:
                        output_name = None
                    link = {
                        "status": "connected",
                        "source_node": source.get_name(),
                        "output_name": str(output_name) if output_name else None,
                    }
                    resolution = "index_aligned_unverified"
            elif link["status"] == "unconnected":
                unconnected_pin_count += 1

            inputs.append({"name": input_name, **link, "resolution": resolution})
            if link["status"] == "connected":
                known_source_target_pairs.add((link["source_node"], node_id))
                connections.append({
                    "from_node": link["source_node"],
                    "from_output": link["output_name"],
                    "to_node": node_id,
                    "to_input": input_name,
                    "resolution": resolution,
                })
            elif link["status"] == "unavailable":
                unavailable_pin_count += 1

        # Preserve node-level connections if array lengths differ; in that
        # case it is unsafe to guess which named pin owns each source node.
        if not arrays_align and incoming:
            for source in incoming:
                if source is None:
                    continue
                source_id = source.get_name()
                pair = (source_id, node_id)
                if pair in known_source_target_pairs or pair in source_node_only_pairs:
                    continue
                try:
                    output_name = library.get_input_node_output_name_for_material_expression(
                        expression, source
                    )
                except Exception:
                    output_name = None
                source_node_only_pairs.add(pair)
                connections.append({
                    "from_node": source_id,
                    "from_output": str(output_name) if output_name else None,
                    "to_node": node_id,
                    "to_input": None,
                    "resolution": "source_node_only",
                })

        try:
            pos_x, pos_y = library.get_material_expression_node_position(expression)
            position = {"x": int(pos_x), "y": int(pos_y)}
        except Exception:
            position = None

        node = {
            "id": node_id,
            "class": class_name,
            "label": expression_label(expression, index),
            "position": position,
            "inputs": inputs,
            "outputs": [str(name) for name in output_names],
            "input_alignment": {
                "pin_name_count": len(input_names),
                "input_node_entry_count": len(incoming) if incoming is not None else None,
                "array_lengths_match": arrays_align,
            },
        }
        params = parameter_info(expression, class_name)
        if params:
            node["parameter"] = params
        values = expression_value_info(expression, class_name)
        if values:
            node["values"] = values
        nodes.append(node)

    root_properties = {}
    root_connections = {}
    property_enum = getattr(unreal, "MaterialProperty", None)
    if property_enum is not None:
        for property_name in ("MP_BASE_COLOR", "MP_METALLIC", "MP_SPECULAR", "MP_ROUGHNESS",
                              "MP_EMISSIVE_COLOR", "MP_OPACITY", "MP_NORMAL", "MP_AMBIENT_OCCLUSION"):
            prop = getattr(property_enum, property_name, None)
            if prop is None:
                continue
            try:
                expression = library.get_material_property_input_node(material, prop)
                root_properties[property_name] = expression.get_name() if expression else None
                try:
                    output_name = library.get_material_property_input_node_output_name(material, prop)
                except Exception:
                    output_name = None
                root_connections[property_name] = {
                    "from_node": expression.get_name() if expression else None,
                    "from_output": str(output_name) if output_name else None,
                }
            except Exception:
                root_properties[property_name] = None
                root_connections[property_name] = {"from_node": None, "from_output": None}

    if unaligned_expression_count:
        warnings.append(
            "{}개 노드는 핀 이름과 입력 노드 배열 길이가 달라 핀 단위 대응을 하지 않았습니다.".format(
                unaligned_expression_count
            )
        )
    if aligned_expression_count and (connections or unconnected_pin_count):
        warnings.append(
            "길이가 같은 핀/노드 배열은 인덱스로 대응했지만, UE API 문서가 순서 일치를 보장하지 않아 "
            "Static Switch의 True/False를 에디터에서 대조해야 합니다."
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "asset": {"name": material.get_name(), "path": object_path(material)},
        "settings": material_settings(material),
        "graph": {
            "nodes": nodes,
            "connections": connections,
            "material_inputs": root_properties,
            "material_input_connections": root_connections,
        },
        "compile_status": {"status": "not_queried", "note": "읽기 전용 실행에서 머티리얼을 재컴파일하지 않습니다."},
        "extraction": {
            "node_count": len(nodes),
            "connection_count": len(connections),
            "index_aligned_connection_count": sum(
                1 for item in connections if item["resolution"] == "index_aligned_unverified"
            ),
            "source_node_only_connection_count": len(source_node_only_pairs),
            "unavailable_pin_count": unavailable_pin_count,
            "unconnected_pin_count": unconnected_pin_count,
            "aligned_expression_count": aligned_expression_count,
            "unaligned_expression_count": unaligned_expression_count,
            "connection_api": "MaterialEditingLibrary + expression input properties",
            "index_alignment_status": (
                "unverified_assumption" if aligned_expression_count else "not_used"
            ),
            "warnings": warnings,
        },
    }


def main():
    selected = list(unreal.EditorUtilityLibrary.get_selected_assets())
    materials = [asset for asset in selected if isinstance(asset, unreal.Material)]
    if len(materials) != 1:
        unreal.log_error(
            "머티리얼 그래프 내보내기는 Content Browser에서 Material 하나만 선택해야 합니다. "
            "현재 선택한 에셋: {}, Material: {}".format(len(selected), len(materials))
        )
        return

    material = materials[0]
    report = build_report(material)
    output_dir = OUTPUT_DIRECTORY or os.path.join(unreal.Paths.project_saved_dir(), REPORT_SUBDIR)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, material.get_name() + ".material_graph.json")
    with open(output_path, "w", encoding="utf-8") as report_file:
        json.dump(report, report_file, ensure_ascii=False, indent=2)

    unreal.log("머티리얼 읽기 보고서 저장: " + output_path)
    unreal.log("노드 {}개, 연결 {}개".format(
        report["extraction"]["node_count"], report["extraction"]["connection_count"]
    ))


try:
    main()
except Exception as error:
    unreal.log_error("머티리얼 그래프 보고서 실패: {}".format(error))
    unreal.log_error(traceback.format_exc())
