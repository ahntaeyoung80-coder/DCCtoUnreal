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

## 2026-10-01

### 마스터 머티리얼 설계 세션 및 읽기 전용 그래프 보고서 계획

- Unreal Engine 5.8.3에서 사용자가 `/Game/Materials/Master/MM_MasterSurface`를 직접 구성 중이며, 설계 검토 후에만 그래프 자동화를 반영하기로 재확인.
- 목표는 임포터가 Material Instance 입력을 채우고, 초보자가 조작할 항목을 최소화하는 것. 파라미터는 임포터 인터페이스로 이름·그룹을 정리하며, 텍스처와 상수값은 곱하지 않고 Static Switch로 상호 배타 선택.
- 임포터 입력 우선순위는 ORM Pack → Substance PBR → Blender 이미지 → Blender scalar → 마스터 기본값. ORM은 화면에서 R=AO, G=Roughness, B=Metallic으로 연결됨. 실제 익스포트 채널 배치와 맞는지 검증 필요.
- 사용자는 다음 세션에서 UE Editor 안에서 실행할 읽기 전용 그래프 보고서 내보내기 스크립트를 만들기로 요청함. 노드·파라미터·머티리얼 설정·핀 연결을 기록하고 에셋은 수정하지 않는 범위.
- 마지막 공유 그래프에서 NormalTexture에 `ERROR!`가 보여 중립 노멀 기본 텍스처 지정 및 컴파일 상태 확인이 남음.
- UE 5.8.3의 `MaterialEditingLibrary`는 노드/핀 이름 및 연결 입력 조회 API를 제공함. 핀 단위 연결 정보의 완전한 추출 가능 여부는 실제 에디터에서 확인해야 함.

### 읽기 전용 Unreal 머티리얼 그래프 리포터 초안

- 사용자가 선택한 머티리얼 하나를 대상으로 JSON 보고서를 내보내는 범위를 승인하고, Unreal Editor에서 읽기 테스트까지 진행하기로 함.
- `unreal/unreal_material_graph_reporter.py`를 추가. 선택 에셋, 노드/핀 이름, 가능한 연결, 머티리얼 입력 및 설정을 읽어 `<Project>/Saved/MaterialGraphReports/`에 기록하도록 구성. 저장·수정·재컴파일 API는 호출하지 않음.
- `unreal/README_unreal_dcc_importer.md`에 실행법과 API 제한을 안내.
- 로컬 Python 문법 검사는 통과. Unreal Editor가 현재 앱 인벤토리에 표시되지 않아 UE 5.8.3 실제 읽기 검증은 아직 못 함. 실제 테스트에서 핀 연결 매핑과 파라미터 접근 결과를 확인해야 함.

### 머티리얼 그래프 보고서 첫 실행 검토

- 사용자가 UE 5.8.3에서 내보낸 `/Game/Materials/Master/MM_MasterSurface` 결과를 확인함. 노드 24개와 머티리얼 입력 노드들은 기록됐으나 연결은 0개이고 각 입력 핀은 `unavailable`로 나와 첫 보고서로 그래프 흐름을 읽을 수 없었음.
- `NormalTexture` 기본 텍스처는 `/Fab/Textures/Standard/T_DefaultNormal`로 읽힘. 설정은 Opaque/Default Lit이며 `BaseColorSclar` 파라미터 철자도 보고서에서 확인됨.
- 리포터를 보완해 입력 핀 속성을 못 읽을 때 `get_inputs_for_material_expression`으로 연결 노드 쌍을 수집하고, 핀 이름은 알 수 없다고 명시하도록 함. `OUTPUT_DIRECTORY` 설정으로 프로젝트 외부 출력 경로도 지정할 수 있게 함.
- 수정 후 로컬 Python 문법 검사 통과. 보완된 노드 연결 추출은 아직 Unreal Editor에서 재실행 검증이 필요함.

### None 입력 노드 오류 수정

- Unreal 실행 로그에서 `get_inputs_for_material_expression` 반환 배열의 `None` 항목에 `get_name()`을 호출해 리포터가 중단되는 문제를 확인.
- `None` 항목을 건너뛰고 개수와 경고를 JSON에 남기도록 수정. 로컬 문법 검사 후 에디터 재실행이 필요함.

### 리포터 두 번째 UE 실행 결과

- 사용자가 UE에서 재실행한 보고서가 정상 저장됐고 노드 24개, 연결 20개를 기록함.
- 연결 20개 모두 `source_node_only`이며 핀 단위 연결은 0개. 입력 핀 34개가 `unavailable`; API가 반환한 None 입력 14개는 건너뜀.
- Output Log의 `Warning`은 실패가 아니라 핀 이름을 읽지 못한 상태를 알리는 메시지. 연결 노드 쌍은 확보했지만 Static Switch의 True/False 어느 쪽인지 구분할 수 없음.

### 핀 이름-연결 배열 대응 구현

- 사용자가 노드 구조를 최대한 완전히 내보내도록 요청함.
- 핀 이름 배열과 `get_inputs_for_material_expression` 반환 배열의 길이가 같은 노드에서 인덱스로 대응해 연결된 핀과 None 핀을 기록하도록 구현. 대응 방식은 Epic 문서에서 배열 순서를 보장하지 않으므로 JSON에 `index_aligned_unverified`와 경고를 남김.
- 길이가 다른 노드는 핀 이름을 추측하지 않고 연결된 노드 쌍만 유지. 머티리얼 출력의 출발 노드와 출력 이름도 추가함.
- 스키마 버전 2로 갱신. 로컬 문법 검사 후 UE에서 다시 실행해 True/False 입력을 화면과 대조해야 함.

### 인덱스 대응 JSON 검토 및 상수값 보완

- UE 재실행 결과에 노드 24개, 연결 20개, 핀 미연결 14개, 읽지 못한 핀 0개가 기록됨. 입력이 있는 노드 17개 전부에서 핀 이름 배열과 연결 배열의 길이가 일치함.
- Static Switch True/False 연결이 Base Color 텍스처/색상, ORM 채널/비압축 경로, 텍스처/스칼라 대체, Emissive 경로와 이름상 일관됨. 인덱스 대응은 강하게 뒷받침되나, UE API 문서가 순서 보장을 하지 않아 시각 검증 전까지 미확정.
- 보고서에서 `MaterialExpressionConstant_1` 값이 빠진 점을 발견해 상수 노드 값과 텍스처 샘플 설정 기록을 리포터에 추가함. 로컬 문법 검사 후 다시 내보내기와 Static Switch 대조가 남음.

### JSON 결과 확인 및 Output Log 경고 조정

- 최신 schema 2 보고서 확인: 노드 24개, 연결 20개, 미연결 핀 14개, 미확인 핀 0개. 입력이 있는 17개 노드 모두 입력 이름/연결 배열 길이가 일치.
- Constant_1 값 0.0 및 Material Output 연결이 JSON에 기록됨. ORM의 R/G/B → AO/Roughness/Metallic, 개별 텍스처/스칼라 대체, Base Color와 Emissive의 텍스처/값 스위치 흐름이 기존 설계와 논리적으로 일치함.
- 사용자는 화면에서 인덱스 연결을 직접 대조할 예정이므로 Output Log 경고 출력은 제거. 검증 전제는 GPT가 결과를 과신하지 않도록 JSON의 `extraction.warnings`와 `index_alignment_status`에 유지.
- 최신 스크립트 로컬 문법 검사 후 UE에서 재실행 확인이 남음.

### MM_MasterSurface JSON과 그래프 화면 대조

- 사용자가 제공한 UE Material Editor 스크린샷과 schema 2 JSON을 대조함. Base Color, ORM R/G/B, UseUnpacked 텍스처/스칼라, Emissive 텍스처/색상·강도 분기, Normal 직접 연결이 모두 일치.
- Static Switch 핀 이름의 인덱스 대응은 이 MM_MasterSurface 그래프에서 화면과 일치함. JSON의 20개 연결과 14개 미연결 입력도 화면과 부합함.
- 스크린샷에서 `BaseColorTexture` 노드에 빨간 `ERROR!` 표시가 있지만 JSON에는 노드 오류 상태가 없어 기록되지 않음. 해당 노드는 기본 텍스처가 null이며 compile status는 `not_queried`; 원인은 아직 미확인.
- NormalTexture는 기본 텍스처 `/Fab/Textures/Standard/T_DefaultNormal`이 있으며 스크린샷에 오류 표시가 없음.

### 세션 마감

- 읽기 전용 머티리얼 그래프 리포터 구현 및 UE 5.8.3 사용자 실행 결과 확인 완료.
- 사용자가 제공한 Material Editor 화면과 JSON 연결을 대조해 MM_MasterSurface의 핀 대응이 일치함을 확인. Output Log 경고는 제거하고 JSON 메타데이터의 추출 전제는 유지.
- 남은 후속 항목은 화면에서 발견한 `BaseColorTexture`의 ERROR 표시 원인과 이를 읽기 전용 보고서에 포함할 방법 조사.
- 관련 파일만 변경됐음을 검토한 후 커밋하기로 함.

### BaseColorTexture 표시 원인 확인

- 사용자가 Material Editor의 `BaseColorTexture` 노드에 보인 `ERROR!` 표시는 텍스처를 아직 지정하지 않은 상태에서 발생한 것이라고 확인함. 연결 추출기 오류나 별도 원인 미확인 항목이 아님.
- HANDOFF의 후속 항목을 이에 맞게 정정함.

## 2026-10-02

### Blender 스켈레탈 명칭 정렬 및 다음 설계 인계

- 사용자가 SSS/Opacity는 우선 배제하고 Blender 스켈레탈 명칭을 임포터 계약에 맞추기로 결정함.
- 익스포터 메시 접두사를 `SK_`에서 `SKM_`으로, 스켈레탈 FBX/manifest 접미사를 `_SK`에서 `_SKM`으로 변경. 사용자가 미리보기에서 입력한 기존 `SK_` 이름도 접두사 중복 없이 정규화.
- Blender 안내서의 출력 규칙을 갱신하고 Unreal 임포터 안내서에서 이전 `_SK` 미지원 메모를 제거.
- HANDOFF를 현재 상태와 바로 다음 단계 중심으로 정리. 다음 세션은 SSS/Opacity 표면 방식, 텍스처/파라미터, 임포터 Material Instance 설정 범위를 설계한 뒤 머티리얼 제작으로 진행.
- SSS/Opacity 구현은 시작하지 않음. Python Blender 런타임 및 Unreal Editor에서의 실제 출력/임포트 검증은 사용자 환경에서 후속 확인 필요.

### Unreal 임포터 선택 흐름 및 최신 마스터 구조 반영

- 임포터는 실행할 때마다 Windows 폴더 선택 창을 열고, 선택한 폴더에서 `_SM.json` / `_SKM.json` manifest를 하나 이상 고르는 방식으로 정리. FBX는 선택한 JSON의 `fbx` 경로에서 읽고, 선택한 묶음별로 `/Game/Imports/<BundleName>/{Meshes,Materials,Textures}`에 저장.
- 이 세션 범위는 Unreal 임포터와 관련 안내/체크포인트만. Blender 익스포터의 `_SK` → `_SKM` 변경은 별도 세션에서 반영하기로 함. 임포터의 스켈레탈 에셋명 접두사도 `SKM_`로 지정.
- Substance 출력은 `<ExportFolder>/textures/Substance/`에서 찾고, `<Project>_<Material>_<Map>` 파일명에서 프로젝트 접두사를 무시해 manifest 머티리얼 이름과 맵 접미사를 매칭. 동일한 역할 후보가 여럿이면 모호성 경고 후 하위 우선순위 소스를 사용.
- 최신 마스터 그래프 파라미터명에 맞춰 Base Color, ORM, 개별 AO/Roughness/Metallic, Emissive texture/fallback Switch와 값을 설정. Metallic Switch는 사용자가 수정한 `UseUnpackedMetallic`으로 간주. 현재 그래프에 없는 Emissive Mask 파라미터 자동 할당은 제거.
- Unreal Editor 안에서 대화상자, UE Python의 Windows ctypes 호출, 머티리얼 파라미터와 FBX 임포트의 실제 실행 확인은 아직 안 함. 사용자의 UE 5.8 프로젝트에서 실행 확인이 다음 단계.

### Skeletal 파일 접미사 임시 조정

- 현재 테스트 에셋이 `_SK` 규칙이므로 임포터가 `_SK` manifest/FBX 쌍을 읽고 Unreal 메시 이름에 `SK_` 접두사를 쓰도록 변경. 향후 네이밍 확정에 따라 다시 조정 가능.
- Unreal의 **Execute Python Script** 파일 선택 창은 Unreal이 띄우며 임포터 내부 소스 폴더 선택과 별도임을 확인. 임포터는 그 다음 매번 소스 폴더 선택과 manifest 다중 선택 창을 띄움. 첫 스크립트 선택 단계까지 없애려면 별도 실행 진입점이 필요.

### 소스 경로와 manifest 선택 창 통합

- 기존 폴더 대화상자 후 파일 선택 대화상자를 여는 두 단계가 불필요하다는 사용자 피드백을 반영. Windows 파일 탐색기 스타일 다중 선택 창 하나에서 소스 폴더로 이동하고 `_SM` / `_SK` manifest를 고르도록 통합.
- Unreal **Execute Python Script**가 여는 임포터 스크립트 선택 창은 그대로 유지되며, 위 통합은 임포터가 여는 선택 창에 적용.

### Unreal Editor 첫 스켈레탈 임포트 로그 검토

- 사용자가 제공한 UE 로그에서 `Inna_SK.fbx` 번역/임포트 완료와 `/Game/Imports/Inna/Meshes/SK_Inna`, `SK_Inna_Skeleton` 저장을 확인. 30개 텍스처와 9개 Material Instance도 저장됐고 총 41개 에셋 검증이 완료됨. Python traceback이나 임포터 중단은 없음.
- Material Instance마다 기존 경로 `load_asset` 실패가 `LogEditorAssetSubsystem: Error`로 9회 출력된 뒤 생성·저장됨. 결과는 성공했지만 없는 에셋을 조회하는 정상 흐름이 Error 레벨로 보여 로그를 불필요하게 길게 함. 존재 여부 확인 후 로드하도록 개선 필요.
- Skeletal FBX는 약 44초 만에 임포트됐으나 `Root_Skeleton` bind pose가 유효하지 않아 UE가 time-zero pose로 skinning을 재결합했다는 경고가 있음. 메시 포즈/변형과 머티리얼 슬롯은 에디터에서 시각 확인 필요.
- 콘텐츠 검증은 41개를 처리하고 표시된 9개 validator에서 실패 수 0. 295개 shader compile job도 모두 완료. 로그만으로 최종 외관/변형 품질까지 확인한 것은 아님.

### Skeletal 네이밍 복귀 및 다음 설계 범위

- 테스트 파일이 `_SK`였던 임포트 프로토타입 실행 결과를 확인한 뒤, 다음 공유 규칙을 위해 임포터 계약을 `_SKM` manifest/FBX와 `SKM_` 에셋 접두사로 다시 맞춤. Blender 익스포터는 이번 세션 범위가 아니므로 현재 `_SK` 상태이며 후속 세션에서 임포터에 맞춰 변경.
- 사용자는 프로토타입을 만족스럽게 평가. Material Instance에서 Static Switch를 끄면 비활성 경로의 하위 파라미터가 숨고 조작되지 않는 동작을 의도한 작업자 UI로 받아들임.
- Blender 애드온은 단순 접미사 변경을 넘어 임포터의 입력/폴더/파일 계약에 맞춰 개편 필요. Opacity 및 SSS 머티리얼을 지금 지원할지 이후 단계로 미룰지는 설계 논의가 남음. 다음 세션은 범위 설계부터 시작.

### 마스터 머티리얼 설계 확정 및 임포터 단계 전환

- 사용자가 최종 MM_MasterSurface 화면을 검토하고, 작업자/임포터가 조작할 슬롯과 파라미터 구성을 정리한 뒤 임포터 개발로 넘어가기로 함.
- Scalar 값은 텍스처와 혼합하는 보정값이 아니라 해당 텍스처가 없을 때만 사용하는 대체값으로 확정. 작업자 UI에서는 `Scalar`보다 대체값임을 드러내는 이름이 적절함.
- 작업자는 가급적 DCC에서 보정하고, 임포트 뒤 텍스처 변경과 Static Switch 변경을 묶는 별도 후처리 도구는 개발하지 않기로 함.
- 임포터가 Material Instance에 텍스처/값을 설정할 때 대응하는 Static Switch도 함께 설정하는 방향으로 진행. 기본 Material Instance 패널의 텍스처 직접 변경은 스위치와 자동 연동되지 않으므로, 일반 작업 흐름으로 삼지 않음.
- 다음 세션에서는 최종 MM_MasterSurface를 저장한 뒤 읽기 전용 그래프 리포터를 다시 실행해 최신 JSON을 확보하고, 기존 임포터와 대조해 필요한 구현 범위를 확인함. 이전 JSON은 최신 그래프와 차이가 있을 수 있음.
