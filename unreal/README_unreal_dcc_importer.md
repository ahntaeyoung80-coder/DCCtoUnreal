# Unreal DCC Importer

`unreal/unreal_dcc_importer.py` is a standalone Unreal Editor Python script. It is not an Unreal plugin and does not need to be pasted into the editor's Python console.

## Before running

1. Update and enable the Blender add-on from `blender/dcc_batch_exporter.py`. It writes separate `_SM` and `_SK` FBX/JSON pairs.
2. In Unreal Editor, enable **Python Editor Script Plugin** and **Editor Scripting Utilities**, then restart the editor if requested.
3. Run `unreal/unreal_dcc_material_builder.py` once in each Unreal project to create `/Game/DCC/Shared/Materials/M_DCC_Master_v2`.
4. Open `unreal/unreal_dcc_importer.py` in a text editor and set `SOURCE_DIR` to the folder containing the Blender exports. Set `DEST_ROOT` if you want a different Content Browser root. Optionally set `SKELETON_PATH` to an existing compatible Skeleton asset.
5. Run **Tools → Execute Python Script…** and choose `unreal/unreal_dcc_importer.py`.

The builder creates the shared master material separately. The importer requires that material to exist, then reads each manifest and FBX pair, imports textures and meshes, makes Material Instances, and assigns them to imported mesh slots. It places imported assets under `/Game/DCC/<bundle>/`.

## Important

The Blender add-on must be reinstalled/reloaded after its update; editing the source file on disk does not automatically update an already installed add-on.

This script is a first draft for Unreal Engine 5.8 Python. It has not been run in an Unreal project, so validate it on a disposable test folder before importing into a production Content folder. Check the Output Log for import warnings or slot mismatches.

## 한국어 안내

`unreal/unreal_dcc_importer.py`는 Unreal Editor 안에서 실행하는 단독 Python 스크립트입니다. Unreal 플러그인이 아니며, Python 콘솔에 코드를 붙여넣을 필요도 없습니다.

### 실행 전 준비

1. Blender 애드온 `blender/dcc_batch_exporter.py`를 최신 파일로 교체하고 활성화합니다. `_SM`, `_SK` FBX/JSON 쌍을 출력합니다.
2. Unreal Editor에서 **Python Editor Script Plugin**과 **Editor Scripting Utilities**를 활성화하고, 재시작을 요청하면 에디터를 재시작합니다.
3. 각 Unreal 프로젝트에서 `unreal/unreal_dcc_material_builder.py`를 한 번 실행해 `/Game/DCC/Shared/Materials/M_DCC_Master_v2`를 생성합니다.
4. 텍스트 편집기에서 `unreal/unreal_dcc_importer.py`를 열어 `SOURCE_DIR`을 Blender 출력 폴더로 설정합니다. 필요하면 `DEST_ROOT`와 `SKELETON_PATH`도 설정합니다.
5. Unreal Editor에서 **Tools → Execute Python Script…**를 선택하고 `unreal/unreal_dcc_importer.py`를 실행합니다.

머티리얼 생성 스크립트가 공용 마스터 머티리얼을 별도로 만듭니다. 임포터는 해당 머티리얼이 있는지 확인한 뒤 JSON/FBX 쌍을 읽어 텍스처와 메시를 임포트하고 Material Instance를 만들어 메시 슬롯에 연결합니다. 임포트 에셋은 기본적으로 `/Game/DCC/<묶음 이름>/` 아래에 저장합니다.

Substance Painter 텍스처는 `SOURCE_DIR`과 그 하위 `textures` 폴더에서 머티리얼 이름과 맵 접미사로 검색합니다. 다른 폴더에 있다면 `SUBSTANCE_TEXTURE_DIRS`에 경로를 추가하세요. 기본 접미사는 BaseColor/Albedo/Color, Normal, Roughness/Rough, Metallic/Metalness/Metal입니다. 검색 결과가 모호하면 임의 연결하지 않고 Output Log에 경고합니다.

### 주의사항

Blender 애드온 소스 파일을 바꿔도 이미 설치된 애드온은 자동 갱신되지 않으므로 Blender에서 최신 파일을 다시 설치해야 합니다.

이 코드는 Unreal Engine 5.8 Python용 초안이며 실제 Unreal 프로젝트에서 실행 검증하지 않았습니다. 프로덕션 Content 폴더에 넣기 전에 테스트 폴더에서 실행하고 Output Log의 경고와 머티리얼 슬롯을 확인하세요.


ORM is connected automatically using the Unreal SSS Pack channel layout R=AO, G=Roughness, B=Metallic, and imported as linear data. SSS, Opacity, and Emissive maps are imported as texture assets and reported in the Output Log, but are not connected and do not change the material blend/shading model; configure those materials manually in Unreal.

ORM은 Unreal SSS Pack 채널 배치인 R=AO, G=Roughness, B=Metallic으로 자동 연결하고 선형 데이터 텍스처로 임포트합니다. SSS, Opacity, Emissive 맵은 텍스처 에셋으로 임포트하고 Output Log에 알리지만 자동 연결하거나 머티리얼의 블렌드/셰이딩 모델을 바꾸지는 않습니다. 해당 머티리얼은 Unreal에서 직접 설정합니다.



The flat normal fallback uses Unreal Engine's built-in DefaultNormal texture; no separate content pack is required.

기본 노멀 대체 텍스처는 Unreal Engine 기본 콘텐츠의 DefaultNormal을 사용하며 별도 팩 설치가 필요하지 않습니다.

