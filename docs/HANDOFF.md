# Handoff

## Current status

마스터 머티리얼의 입력 슬롯, 대체값, 작업자 발광 토글, 임포터 관리 Static Switch 구성을 설계했다. Scalar 값은 해당 텍스처가 없을 때만 쓰는 대체값이다. 작업자 보정은 가능한 한 DCC에서 하고, 임포트 후 텍스처와 스위치를 연동하는 별도 도구는 만들지 않는다.

Unreal 임포터 프로토타입을 UE 5.8에서 한 번 실행해 `Inna_SK.fbx`, 텍스처 30개, Material Instance 9개를 만들고 총 41개 에셋 검증을 마쳤다. 사용자는 Material Instance Static Switch가 꺼진 경로의 파라미터를 숨기고 조작을 막는 동작을 좋게 평가했다. 임포터는 다음 스켈레탈 계약인 `_SKM`/`SKM_`을 사용하지만 Blender 익스포터는 아직 `_SK`다. FBX의 bind pose 경고와 미존재 Material Instance 조회 Error 로그 9회는 기록해 둔다.

## Decisions

- 임포터는 텍스처/값을 Material Instance에 채우고, 해당 입력 경로의 Static Switch도 함께 설정한다.
- 일반 Material Instance 패널에서 텍스처를 바꿔도 Static Switch가 자동 연동되지는 않는다. 후처리 도구는 범위에서 제외한다.
- 머티리얼 그래프 리포터는 선택한 Material 하나를 JSON으로 읽기 전용 내보내며 에셋을 저장·수정·재컴파일하지 않는다.

## Next

다음 설계 세션에서 임포터 구조에 맞춘 Blender 애드온 이름/익스포트 폴더 및 파일 선택 규칙을 정하고, Opacity와 SSS를 현재 마스터/익스포터 범위에 포함할지 결정한다. 이후 별도 세션에서 Blender 애드온을 개편해 `_SKM` 출력과 맞춘다. Skeletal bind pose 경고와 Material Instance lookup 로그는 후속 검증/개선 항목이다.
