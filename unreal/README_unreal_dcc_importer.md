# Unreal DCC tools

These standalone Python scripts run inside Unreal Editor. They are not plugins.

## Setup

1. Enable **Python Editor Script Plugin** and **Editor Scripting Utilities** in Unreal Editor. Restart if prompted.
2. Run `unreal/unreal_dcc_basic_template_generator.py` with **Tools → Execute Python Script…**. It creates `/Game/Imports` and `/Game/Materials/Master/MM_MasterSurface` in the open project.
3. Run `unreal/unreal_dcc_importer.py`. In the single Explorer-style file dialog, browse to the DCC export folder and select one or more manifest JSON files. The importer reads each selected JSON's FBX and Blender image references. Optionally set `SUBSTANCE_TEXTURE_DIRS` near the top of the script for additional Substance Painter output folders.

The generator creates `/Game/Materials/Master` and `/Game/Imports`. The importer creates one folder per export bundle:

```text
/Game/Imports/<BundleName>/
├── Meshes/
├── Materials/
└── Textures/
```

Meshes are placed directly in `Meshes/`. If `MM_MasterSurface` already exists, the generator leaves it unchanged. A legacy master under `/Game/DCC/Shared/Materials/` is moved to the new path without changing its graph. The scripts do not create or package a `.upack` file.

## Texture source priority and file layout

Place Substance Painter maps in `<ExportFolder>/textures/Substance/`. Blender-linked images remain in the `textures/` location referenced by the selected JSON. The importer matches Substance filenames using `<Project>_<Material>_<Map>`; it ignores leading project-name tokens and matches the material name and map suffix against the manifest. For each material input, the importer selects the highest available source:

1. Unreal ORM Pack (R=AO, G=Roughness, B=Metallic)
2. Substance Painter PBR maps (`textures/Substance/`)
3. Blender image textures linked to supported Principled BSDF inputs
4. Blender scalar or color values
5. Neutral defaults in the master material

Substance textures are identified by material name and map suffix, allowing a project-name prefix. For example, `ProjectA_Wood_BaseColor.png` matches a manifest material named `Wood`. If multiple files match the same material input, the importer reports the ambiguity and falls back to the next source. The importer normalizes Unreal texture asset names to `T_<Material>_<Role>` while leaving source image filenames unchanged.

Base Color imports with sRGB enabled. Normal maps use Unreal's normal-map compression. ORM, AO, Roughness, Metallic, and mask textures are imported as linear data. Blender's and Substance Painter's normal-map green-channel conventions have not yet been verified against a real sample.

The master material supports an optional emissive path. The importer transfers Blender's Emission Color and Emission Strength, connects an available emissive color texture or mask, and enables the path only when emission data exists. Skin SSS, masked opacity, and translucent materials are outside this first background-focused draft.

## Read-only material graph report

Select exactly one Material asset in the Content Browser, then run `unreal/unreal_material_graph_reporter.py` with **Tools → Execute Python Script…**. The script reads the selected material and writes a JSON report to `<Project>/Saved/MaterialGraphReports/<MaterialName>.material_graph.json` by default. Set `OUTPUT_DIRECTORY` near the top of the script to an absolute path to write elsewhere, for example `r"C:\Users\USER\Documents\MaterialGraphReports"`. It does not save or modify the asset and does not trigger a material compile.

The report contains node classes and labels, pin names, pin connections from the UE input-node array when its length matches the pin-name array, material property outputs, material settings, parameter defaults, literal constant values, and texture sampling settings. UE documentation does not guarantee that both arrays use the same order, so connections marked `index_aligned_unverified` need a visual check in UE 5.8.3 before being treated as exact. If array lengths differ, the report preserves only source and destination nodes where possible. Compile status is `not_queried` because this read-only script does not compile the asset. Extraction caveats stay in the JSON metadata and are not printed as Output Log warnings.
## Notes

- The Blender exporter currently records supported Principled BSDF inputs and copies linked image files into the export `textures/` folder. Unsupported node graphs and procedural baking remain outside its scope.
- Each run opens one Explorer-style multi-select file picker filtered to schema-version-2 `_SM` / `_SKM` manifest JSON files. Browse to the export folder and select manifests there; the FBX is read from each selected JSON.
- The current Blender exporter still emits `_SK`; update its naming in the planned Blender add-on session before using skeletal exports with this importer.
- Existing destination assets trigger a replacement prompt. Review the Output Log for missing or ambiguous texture warnings.
- This is an initial Unreal Engine 5.8 Python draft. One user-provided editor log confirms a skeletal import and 41-asset validation, but the mesh deformation and material appearance still need visual review before production use.

## 한국어 안내

이 Python 스크립트들은 Unreal Editor 안에서 실행하는 단독 도구이며 플러그인이 아닙니다.

### 설정 및 실행

1. Unreal Editor에서 **Python Editor Script Plugin**과 **Editor Scripting Utilities**를 활성화합니다. 재시작 안내가 나오면 재시작합니다.
2. **Tools → Execute Python Script…**에서 `unreal/unreal_dcc_basic_template_generator.py`를 실행합니다. 현재 열린 프로젝트에 `/Game/Imports`와 `/Game/Materials/Master/MM_MasterSurface`를 생성합니다.
3. `unreal/unreal_dcc_importer.py`를 실행하고 하나의 파일 선택 창에서 DCC 출력 폴더로 이동해 가져올 manifest JSON 파일을 하나 이상 선택합니다. 임포터는 `_SM`/`_SKM` 파일 쌍을 받으며 각 JSON이 FBX와 Blender 연결 이미지를 지정합니다. 추가 Substance Painter 출력 폴더는 스크립트 위쪽의 `SUBSTANCE_TEXTURE_DIRS`에 지정할 수 있습니다.

생성기는 `/Game/Materials/Master`와 `/Game/Imports`를 만들고, 임포터는 묶음별 구조를 생성합니다.

```text
/Game/Imports/<묶음이름>/
├── Meshes/
├── Materials/
└── Textures/
```

메시는 `Meshes/` 바로 아래에 놓입니다. `MM_MasterSurface`가 이미 있으면 생성기는 머티리얼 그래프를 건드리지 않습니다. 예전 `/Game/DCC/Shared/Materials/` 경로의 마스터 머티리얼은 그래프를 바꾸지 않고 새 경로로 이동합니다. `.upack` 파일 생성·패키징은 이 스크립트 범위가 아닙니다.

### 텍스처 우선순위

각 머티리얼 입력은 아래 순서에서 가장 높은 우선순위의 텍스처 또는 값을 사용합니다.

1. Unreal ORM Pack (R=AO, G=Roughness, B=Metallic)
2. Substance Painter PBR 맵
3. Blender Principled BSDF에 연결된 이미지 텍스처
4. Blender 노드의 Scalar 또는 색상값
5. 마스터 머티리얼의 중립 기본값

Substance Painter 맵은 `<출력폴더>/textures/Substance/`에 둡니다. 파일명은 `<프로젝트>_<머티리얼>_<맵종류>` 형식으로 두면 됩니다. 임포터가 앞의 프로젝트 이름을 무시하고 manifest의 머티리얼 이름과 맵 접미사를 대조합니다. 예를 들어 `ProjectA_Wood_BaseColor.png`는 `Wood` 머티리얼의 Base Color로 매칭됩니다. 같은 입력에 후보가 여러 개면 임의로 선택하지 않고 Output Log에 경고한 뒤 다음 우선순위 소스를 사용합니다. Unreal 텍스처 에셋 이름은 `T_<머티리얼>_<역할>`로 만들며 원본 파일명은 유지합니다.

Base Color는 sRGB로 가져옵니다. 노멀 맵은 Unreal 노멀 압축 설정을 사용합니다. ORM, AO, Roughness, Metallic, 마스크 텍스처는 선형 데이터로 가져옵니다. Blender와 Substance Painter의 노멀 맵 초록 채널 방향은 실제 샘플로 아직 검증하지 않았습니다.

마스터 머티리얼은 선택형 Emissive 경로를 지원합니다. 임포터는 Blender의 Emission Color와 Emission Strength를 옮기고, 사용할 Emissive 색상 텍스처나 마스크가 있으면 연결하며 발광 값이 있는 경우에만 기능을 켭니다. 피부 SSS, Masked Opacity, Translucent 머티리얼은 배경 중심 첫 초안 범위에서 제외합니다.

### 읽기 전용 머티리얼 그래프 보고서

Content Browser에서 Material 에셋 하나만 선택하고 **Tools → Execute Python Script…**에서 `unreal/unreal_material_graph_reporter.py`를 실행합니다. 기본 JSON 경로는 `<프로젝트>/Saved/MaterialGraphReports/<머티리얼이름>.material_graph.json`입니다. 스크립트 위쪽의 `OUTPUT_DIRECTORY`에 절대 경로를 지정하면 프로젝트 밖으로 내보낼 수 있습니다. 에셋을 저장·수정하거나 머티리얼을 재컴파일하지 않습니다.

보고서에는 노드 종류와 이름, 핀 이름, 입력 노드 배열 길이가 일치할 때 인덱스로 대응한 연결, 머티리얼 입력과 출력, 설정, 파라미터 기본값, 상수 노드 값, 텍스처 샘플링 설정이 들어갑니다. `index_aligned_unverified` 연결은 UE API 문서에서 배열 순서가 보장되지 않으므로 UE 5.8.3 에디터에서 확인해야 합니다. 배열 길이가 다르면 가능한 경우 노드 쌍만 기록합니다. 읽기 전용 실행에서는 컴파일 상태를 조회하지 않아 `not_queried`로 남습니다. 추출 주의사항은 JSON 메타데이터에 기록하고 Output Log 경고로는 출력하지 않습니다.
### 참고

- Blender 익스포터는 지원하는 Principled BSDF 입력과 연결 이미지 파일을 기록합니다. 지원하지 않는 노드 그래프와 절차적 베이킹은 아직 범위 밖입니다.
- 임포터는 실행할 때마다 단일 파일 선택 창을 열며, 여기서 소스 폴더로 이동하고 가져올 schema version 2의 `_SM` / `_SKM` JSON을 선택합니다. 각 JSON에 적힌 FBX를 함께 가져옵니다.
- 현재 Blender 익스포터의 `_SK` 출력은 향후 별도 애드온 정리 세션에서 `_SKM`으로 맞춰야 합니다.
- 대상 폴더에 기존 에셋이 있으면 덮어쓰기 확인 창이 나옵니다. 텍스처 누락·모호성은 Output Log에서 확인하세요.
- Unreal Engine 5.8 Python 초기 초안입니다. 사용자가 제공한 로그에서 스켈레탈 임포트와 41개 에셋 검증을 확인했지만, 메시 변형과 머티리얼 외관은 에디터에서 시각 확인이 필요합니다.
