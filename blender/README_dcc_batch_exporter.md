# DCC Batch Exporter (FBX + JSON)

Initial Blender add-on prototype for the agreed export workflow.

## Install

1. In Blender, open **Edit → Preferences → Get Extensions → Install from Disk** (or the add-on installation control available in your Blender build).
2. Select `blender/dcc_batch_exporter.py` and enable **DCC Batch Exporter (FBX + JSON)** in Preferences.
3. In the 3D View, open the sidebar with `N` and select **DCC Export**.

If your Blender build does not expose Install from Disk for add-ons, use **Preferences → Add-ons → Install…**, then select the same `.py` file.

## Use

1. Select the mesh objects to export.
2. In **DCC Export**, set **FBX File Name** and the output folder, then click **Refresh Selected Meshes**. This name is used for the FBX and matching JSON bundle; individual mesh names are controlled separately in the preview.
3. Review and edit each Export Name. The preview includes the final prefix: `SM_` for static meshes and `SK_` for meshes parented to an Armature or using an Armature modifier.
4. Use the selection/frame button in a row to locate that source object in the viewport.
5. Click **Export FBX + JSON**.

The FBX File Name is the shared bundle name. The add-on separates the selected objects by type and creates up to two FBX/JSON pairs:

```text
<Bundle>_SM.fbx
<Bundle>_SM.json
<Bundle>_SK.fbx
<Bundle>_SK.json
textures/
```

The `_SM` pair contains static meshes; the `_SK` pair contains meshes linked to armatures and their armatures. Empty groups are omitted. Both JSON files use schema version 2 and include `asset_type`. Per-mesh names remain separate inside each FBX. Referenced image files are copied into the shared `textures/` directory and JSON stores relative paths. Blender source object and material names are not changed. Material names in the manifest receive an `MI_` prefix.

## Current scope and limitations

- Selected mesh objects only; collection export is not included yet. Static and armature-linked meshes are exported as separate FBX/JSON pairs. Armatures linked through parentage or Armature modifiers are included in the skeletal FBX.
- Up to two FBX files per operation (one static and one skeletal); mesh objects remain separate in their FBX.
- Principled BSDF only. Base Color, Normal, Roughness and Metallic are recorded as either a directly connected image (Normal Map nodes are followed to their image input) or the socket's constant value.
- Arbitrary node graphs, generated images, procedural textures, channel extraction, and texture baking are outside this first prototype. If a linked image file is missing or unreadable, export continues with that input recorded as `value: null`; the JSON `warnings` array records the material, input, image, and source path.
- Exported names are previewed and editable. Original names are recorded in JSON for lookup.
- Existing FBX/JSON files cause an error unless **Overwrite Existing Files** is enabled.
- This prototype has not yet been exercised in the user's Blender installation. The FBX exporter operator must be available in that Blender build.

## JSON outline

`meshes` records each exported mesh, its Blender source name, and material slot order. `materials` records a shared material once and lists the supported PBR inputs. Image references are relative to the export folder.

## 한국어 안내

### 설치

1. Blender에서 **Edit → Preferences**를 열고 애드온 설치 기능에서 `blender/dcc_batch_exporter.py`를 선택합니다.
2. **DCC Batch Exporter (FBX + JSON)**를 활성화합니다.
3. 3D 뷰포트에서 `N` 키로 사이드바를 열고 **DCC Export** 탭을 선택합니다.

### 사용

1. 내보낼 메시 오브젝트를 선택합니다.
2. **FBX File Name**과 출력 폴더를 정하고 **Refresh Selected Meshes**를 누릅니다. FBX File Name은 출력 묶음의 이름이며 개별 메시 이름과는 별개입니다.
3. 미리보기에서 각 메시의 Export 이름을 확인하거나 수정합니다. 정적 메시에는 `SM_`, Armature에 연결된 메시에는 `SK_`가 붙습니다. 행의 선택 버튼은 뷰포트에서 해당 원본 메시를 찾아줍니다.
4. **Export FBX + JSON**을 누릅니다.

선택한 메시 종류에 따라 다음 파일을 최대 두 쌍 만듭니다. 해당 종류의 메시가 없으면 그 쌍은 생략합니다.

```text
<묶음이름>_SM.fbx / <묶음이름>_SM.json
<묶음이름>_SK.fbx / <묶음이름>_SK.json
textures/
```

JSON은 각 메시의 원본 이름, Export 이름, 머티리얼 슬롯 순서와 PBR 텍스처/상수값을 기록합니다. 텍스처는 출력 폴더의 `textures/`에 복사하고 JSON은 상대 경로로 참조합니다. Blender 원본 이름은 변경하지 않습니다.

### 현재 지원 범위

- 선택한 오브젝트만 지원합니다. 컬렉션 내보내기는 아직 없습니다.
- Principled BSDF의 Base Color, Normal, Roughness, Metallic 입력을 처리합니다. 직접 연결된 이미지와 상수값을 기록합니다. Normal Map 노드는 입력 이미지를 따라갑니다.
- 복잡한 노드 그래프, 절차적 텍스처, 채널 분리, 베이킹은 지원하지 않습니다.
- 연결 이미지 파일을 찾지 못해도 내보내기는 계속합니다. 해당 입력을 빈 값으로 기록하고 JSON `warnings`에 누락 경로를 남깁니다.
- 동일한 소스 이미지 파일은 한 번만 복사합니다.
- 같은 이름의 FBX/JSON이 있으면 **Overwrite Existing Files**를 켜지 않는 한 내보내기를 중단합니다.

내보낸 결과를 Unreal에서 읽으려면 별도 임포터 `unreal/unreal_dcc_importer.py`가 필요합니다. 해당 파일은 Unreal Editor 안에서 실행하는 Python 스크립트이며 플러그인이 아닙니다.
