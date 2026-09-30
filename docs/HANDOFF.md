# 인수인계

## 현재 단계

폴더 경로와 임포터 초안은 반영했습니다. `MM_MasterSurface`의 노드 연결 자동 생성은 실패했으며, Unreal Editor에서 정상 동작을 검증하지 못했습니다. 현재는 사용자가 에디터에서 그래프를 직접 구성하기로 했습니다.

## 합의된 방향

- 생성기는 기존 Unreal 프로젝트에서 실행하며, `.upack` 제작은 사용자가 별도로 담당합니다.
- 폴더 구조: `/Game/Imports/<BundleName>/{Meshes,Materials,Textures}`. 메시 에셋은 `Meshes/` 바로 아래에 둡니다.
- 공용 마스터: `/Game/Materials/Master/MM_MasterSurface` (`Opaque + Default Lit`), Emissive 경로는 선택형입니다.
- 생성기에서 기존 `/Game/Materials/Master/MM_MasterSurface`는 변경하지 않도록 안전 처리했습니다. 사용자가 직접 연결을 만든 뒤에는 생성기를 다시 실행하지 않습니다.
- 텍스처 우선순위: ORM Pack → Substance PBR → Blender 이미지 → Blender scalar → 중립 기본값.
- Unreal 도구 이름은 `unreal/unreal_dcc_basic_template_generator.py`이며, 임포터와 Blender 익스포터는 별도 도구입니다.

## 다음 단계

사용자가 Unreal Editor에서 마스터 머티리얼 그래프를 직접 구성하고 현재 Codex 작업에 결과를 보고합니다. 다음 Codex 작업은 공유된 그래프를 먼저 검토하는 것입니다. 자동화 반영, 생성기/임포터 UE 5.8 실행 검증, 노멀 방향 확인은 그 뒤에 진행합니다.

## 참고

- 결정·작업 이력: `docs/WORK_LOG.md`
- 프로젝트 개요: `README.md`
