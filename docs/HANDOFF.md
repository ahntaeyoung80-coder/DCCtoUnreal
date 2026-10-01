# 인수인계

## 현재 단계

Unreal Engine 5.8.3에서 사용자가 `/Game/Materials/Master/MM_MasterSurface` 그래프를 직접 구성 중입니다. 최신 공유 화면에서는 Base Color 텍스처/색상 선택, ORM 우선 분기, 개별 AO·Roughness·Metallic 텍스처/상수 경로, 선택형 Emissive가 보입니다. NormalTexture 노드에 `ERROR!`가 보였으므로 기본 중립 노멀 텍스처 설정과 컴파일 상태를 다음에 확인합니다.

## 합의된 방향

- 임포터가 Material Instance 파라미터를 채웁니다. 초보자가 직접 선택·보정할 입력을 최소화하고, 임포터 관리 파라미터는 명확히 이름 붙여 묶습니다.
- 입력 우선순위는 ORM Pack → Substance PBR → Blender 이미지 → Blender scalar → 마스터 기본값입니다. 임포터가 우선순위를 판정하고 Static Switch를 설정하며, 그래프에서는 텍스처와 상수값을 Multiply로 섞지 않습니다.
- ORM 채널은 현재 그래프에서 R=AO, G=Roughness, B=Metallic으로 연결되어 있습니다. 실제 텍스처 생성 규칙과 일치하는지 확인해야 합니다.
- Unreal이 텍스처 할당 여부를 자동 판단하지 않으므로, 임포터가 소스 유무에 따라 Static Switch 파라미터를 설정합니다.
- 폴더 구조: `/Game/Imports/<BundleName>/{Meshes,Materials,Textures}`; 공용 마스터: `/Game/Materials/Master/MM_MasterSurface` (`Opaque + Default Lit`). 템플릿 생성기, Blender 익스포터, Unreal 임포터는 별도 도구입니다. 그래프 자동 재구성은 보류하고 검증된 수작업 그래프만 나중에 자동화합니다.

## 다음 단계

Unreal Editor에서 읽기 전용 머티리얼 그래프 보고서를 내보내는 스크립트를 설계·작성합니다. 노드 종류와 이름, 파라미터/기본값/그룹, 머티리얼 설정, 핀 간 연결을 보고서(JSON 또는 Markdown)로 기록하고 `.uasset`을 변경하지 않도록 합니다. UE 5.8.3 Python API에서 핀 단위 연결 정보를 실제로 추출할 수 있는지 확인하고, 스크린샷 및 컴파일 오류와 대조합니다. 이어서 Normal 기본값과 전체 그래프를 검토합니다.

## 참고

- 누적 결정·작업 이력: `docs/WORK_LOG.md`
- 프로젝트 개요: `README.md`
