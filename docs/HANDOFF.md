# Handoff

## Current status

Blender 익스포터의 스켈레탈 이름을 임포터 계약에 맞춰 `SKM_` 접두사와 `_SKM` 묶음 접미사로 변경했다. 정적 메시 `SM_`/`_SM` 규칙, manifest schema version 2, 출력 폴더에서 manifest가 지정하는 FBX·텍스처를 찾는 흐름은 유지한다. SSS와 Opacity는 현재 익스포트/임포트하지 않으며 다음 설계 대상으로 남긴다.

마스터 머티리얼 `MM_MasterSurface`와 기본 임포터는 UE 5.8에서 프로토타입 검증을 진행했다. 임포터는 텍스처/값에 맞춰 Static Switch를 설정한다. Scalar는 텍스처가 없을 때만 쓰는 대체값이다. 임포트 후 텍스처와 스위치를 연동하는 별도 도구는 만들지 않는다.

## Decisions

- SSS와 Opacity 지원은 당분간 제외한다. 별도 설계 세션에서 마스터 머티리얼 구성을 먼저 논의한다.
- Blender 출력 디렉터리를 기준으로 임포터가 선택한 manifest와 그 manifest가 가리키는 FBX·텍스처를 읽는다.
- ORM은 Substance 텍스처 입력으로 다루며 Blender 익스포터 범위가 아니다. Emissive는 Blender 값/텍스처 또는 Substance 텍스처에서 받을 수 있다.
- Skeletal 명칭은 메시 `SKM_`, manifest/FBX 묶음 `_SKM`; Static은 `SM_`, `_SM`이다.

## Next

다음 세션은 SSS와 Opacity용 Unreal 마스터 머티리얼 설계·제작 논의부터 시작한다. 먼저 필요한 표면 방식(예: Opaque/Masked/Translucent), 지원할 텍스처와 파라미터, 임포터의 Material Instance 설정 범위를 차례로 확정한다. 설계가 확정되기 전에는 코드를 수정하지 않는다.

후속 검증 항목: Blender에서 실제 `_SKM` 파일 출력, UE의 Skeletal bind pose 경고 및 메시 변형 시각 확인, Material Instance lookup 로그 개선.
