# Handoff

## Current status

마스터 머티리얼의 입력 슬롯, 대체값, 작업자 발광 토글, 임포터 관리 Static Switch 구성을 설계했다. Scalar 값은 해당 텍스처가 없을 때만 쓰는 대체값이다. 작업자 보정은 가능한 한 DCC에서 하고, 임포트 후 텍스처와 스위치를 연동하는 별도 도구는 만들지 않는다.

## Decisions

- 임포터는 텍스처/값을 Material Instance에 채우고, 해당 입력 경로의 Static Switch도 함께 설정한다.
- 일반 Material Instance 패널에서 텍스처를 바꿔도 Static Switch가 자동 연동되지는 않는다. 후처리 도구는 범위에서 제외한다.
- 머티리얼 그래프 리포터는 선택한 Material 하나를 JSON으로 읽기 전용 내보내며 에셋을 저장·수정·재컴파일하지 않는다.

## Next

최종 MM_MasterSurface를 저장한 뒤 그래프 리포터를 다시 실행해 최신 JSON을 확보한다. 기존 임포터와 JSON을 대조하고 합의된 입력 우선순위에 따라 Material Instance 파라미터와 Static Switch 설정을 구현·검증한다.
