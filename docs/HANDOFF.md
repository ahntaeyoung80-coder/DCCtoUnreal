# Handoff

## Current status

읽기 전용 Material JSON 리포터 구현과 UE 5.8.3 실행, MM_MasterSurface 그래프와 결과 대조를 완료했다. Base Color, ORM R/G/B, 텍스처/스칼라 스위치, Emissive, Normal 연결이 JSON과 화면에서 일치했다. 화면의 `BaseColorTexture` `ERROR!` 표시는 텍스처를 아직 넣지 않은 상태라 발생한다고 사용자가 확인했다.

## Decisions

- 리포터는 선택한 Material 하나를 JSON으로 내보내며 에셋을 저장·수정·재컴파일하지 않는다.
- 핀 인덱스 대응 주의사항은 JSON에 두고 Unreal Output Log 경고로 출력하지 않는다.

## Next

Unreal 마스터 머티리얼 설계를 이어간다. BaseColorTexture에 텍스처를 지정한 뒤 필요하면 리포트로 상태를 재확인한다.
