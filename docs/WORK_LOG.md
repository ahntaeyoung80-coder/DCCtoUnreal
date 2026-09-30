# 작업 로그

결정과 작업을 날짜별로 누적한다. 현재 상태와 바로 다음 단계는 `HANDOFF.md`에 짧게 유지한다.

## 2026-09-30

### Content 경로 정리 및 그래프 자동화 보류

- 사용자가 `/Game/Imports/<BundleName>/{Meshes,Materials,Textures}`와 `/Game/Materials/Master/MM_MasterSurface` 구조를 승인함. 생성기와 임포터, 안내 문서 경로를 이에 맞춤.
- 그래프 자동 재구성 초안은 실제 Unreal Editor에서 제대로 작동하지 않았고 기존 그래프 연결을 보존하지 못함. 앞서 구현한 백업 후 삭제·재구성 방식은 사용하지 않기로 함.
- 생성기는 기존 마스터 머티리얼 그래프를 보존하도록 수정. 기존 그래프를 사용자가 직접 구성한 뒤 검토를 거쳐서만 자동화하기로 함.
- 구 API 문서상 노드 연결·재컴파일 함수는 있으나, 문서 확인만으로 실제 그래프 연결 성공을 검증할 수 없음을 기록. UE 5.8 실제 실행 검증은 미완료.

### 기본 템플릿 생성기 구현 초안

- 사용자가 구현을 요청했고 `.upack` 제작은 별도 담당하기로 함. 생성기는 기존 Unreal 프로젝트에서 실행.
- `unreal_dcc_material_builder.py`를 `unreal_dcc_basic_template_generator.py`로 교체해 `/Game/DCC/Shared/Materials/MM_MasterSurface` 및 기본 폴더를 생성하도록 함.
- 마스터 머티리얼은 Opaque + Default Lit으로 구성. Base Color, Normal, 개별 AO/Roughness/Metallic, ORM Pack, 선택형 Emissive Color/Mask 입력을 준비하고 Skin SSS/Opacity는 제외.
- 임포터 경로를 `/Game/DCC/Imports/<BundleName>/{Meshes,Materials,Textures}`로 맞추고 텍스처 이름을 `T_<Material>_<Role>`로 정규화하도록 수정.
- 소스 우선순위를 ORM Pack → Substance PBR → Blender 이미지 → Blender scalar → 마스터 기본값으로 반영. Blender 익스포터 JSON에 Emission Color/Strength 기록을 추가.
- Unreal Editor에서 실행 검증하지 않음. Static Switch API, Material Expression 생성, 노멀 그린 채널 방향은 UE 5.8 프로젝트에서 확인 필요.
- 같은 원본 이미지가 서로 다른 텍스처 역할에 쓰일 경우 sRGB/압축 설정이 충돌하지 않도록 임포터에서 역할별 텍스처 에셋을 만들도록 보완.

### Unreal Content 계층구조 설계 논의

- 여러 프로젝트에서 공용 에셋을 공유하는 플러그인 구조는 현재 목표에 시기상조로 보고, 우선 단일 프로젝트 안의 Content 구조를 설계하기로 함. Game Feature Plugin은 기능을 켜고 끄는 요구가 있을 때 재검토.
- 한 번의 내보내기 묶음 아래에서 에셋 종류별로 파일을 나누고, 같은 묶음의 메시·머티리얼·텍스처는 각각 한 번만 보관하는 혼합 구조를 초안으로 정리: `/Game/DCC/Imports/<BundleName>/{Meshes,Materials,Textures}`.
- 배경과 캐릭터를 별도 최상위 폴더 규칙으로 나누지 않기로 함. 메시 에셋은 `Meshes/` 바로 아래에 두기로 함.
- 폴더 계층구조는 아직 전체 확정 전. 네이밍 규칙과 공용 머티리얼/텍스처 배치, 마스터 머티리얼 설계가 남음.

### 프로젝트 구조 정리

- 역할별 폴더로 정리: `docs/`, `blender/`, `unreal/`.
- 루트 `README.md`를 추가하고 기존 안내서의 경로를 갱신.
- 비어 있던 `outputs/`, `work/` 폴더 제거. 샘플이 없어 `examples/`는 만들지 않음.
- 인수인계 문서 이름을 `docs/HANDOFF.md`로 변경.

### Git 초기 설정

- 프로젝트 루트에서 Git 저장소를 초기화.
- `8a21514` — 프로젝트 초기 파일 저장.
- `.gitignore`를 추가해 Python 캐시, Blender 백업, OS 메타데이터를 제외.
- `cf85ed8` — 임시 파일 제외 규칙 추가.
- Git 명령은 파일 탐색기 터미널에서 동작했고, Codex 터미널에는 Git 경로 문제가 있어 사용자 PATH에 `C:\Program Files\Git\cmd`를 추가.

### 작업 방식 합의

- 구상과 요구사항 정리는 채팅에서 진행하고, 설계가 확정된 뒤 실제 파일 구현은 Codex에서 진행.
- 새 세션마다 같은 프로젝트 폴더를 사용하며 세션별 코드 복사본은 만들지 않음.
- `AGENTS.md`를 통해 Codex가 세션 시작 시 `HANDOFF.md`와 `README.md`를 읽도록 함.
- 인수인계는 간결한 체크포인트로 유지하고, 누적 작업 내역은 `WORK_LOG.md`에 분리.
- 사용자가 명확히 세션 마감을 요청하면 HANDOFF/WORK_LOG 갱신과 변경 검토 후 해당 세션의 관련 변경을 자동 커밋하도록 절차를 정함. 작업이 미완료이거나 무관한 변경이 섞이면 자동 커밋하지 않음.

### 제품 방향 합의

- 우선순위를 기존 임포터 개선에서 Unreal 템플릿/초기 설정 생성기 설계로 변경.
- 장기 목표는 Unreal 계층구조를 함께 학습·확정하고, 마스터 머티리얼을 포함하는 재사용 가능한 마스터 프로젝트/템플릿을 만들어 배포하는 것.
- 사용자가 배포 형식으로 `.upack`을 언급함. 실제 Unreal 배포 형식과 적합성은 구현 전에 확인 필요.
- 생성기는 사용자가 먼저 만든 Unreal 프로젝트 안에서 실행. 새 `.uproject` 생성은 현재 범위 밖.
- 템플릿 생성기, Blender 익스포터, Unreal 임포터는 각각 별도 도구로 유지하되 현재는 한 Git 저장소에서 관리.
- 먼저 계층구조, 네이밍 규칙, 마스터 머티리얼을 설계하고 확정한 뒤 생성기를 구현. 익스포터와 임포터는 그 규칙에 맞춰 후속 정렬.

### 미확정 설계

- `/Game/DCC/Shared/Materials`와 `/Game/DCC/Imports/<BundleName>/{Static,Skeletal,Materials,Textures}` 구조를 제안했지만 사용자가 승인하지 않음.
- Base Color 텍스처와 단색 경로를 엄격히 분리하는 방법 미정.
- ORM과 개별 Roughness/Metallic 맵 분기 방식 미정. 현재 프로토타입의 Multiply/Lerp 그래프는 최종안이 아님.
- SSS, Opacity, Emissive의 향후 머티리얼/레이어 구조 미정.
- 기존 코드 흐름은 실제 Unreal 프로젝트에서 재검증되지 않음.
