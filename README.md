# DCC to Unreal

Blender에서 메시와 재질 정보를 내보내고 Unreal Editor에서 가져오는 도구 모음입니다.

## 폴더 안내

- `docs/`: 프로젝트 개요, 설계 결정, 세션 인수인계 문서
- `blender/`: Blender 애드온과 사용 안내
- `unreal/`: Unreal Editor Python 스크립트와 사용 안내

내보낸 FBX/JSON과 텍스처는 프로젝트 코드 폴더와 섞지 말고 별도의 작업 출력 폴더에 저장하세요. 아직 예제 입력 파일은 없으므로 `examples/` 폴더는 만들지 않았습니다.

## 빠른 시작

1. [Blender Exporter 안내](blender/README_dcc_batch_exporter.md)를 따라 `blender/dcc_batch_exporter.py`를 설치합니다.
2. Blender에서 FBX/JSON을 내보냅니다.
3. [Unreal Importer 안내](unreal/README_unreal_dcc_importer.md)를 읽고 Unreal Editor에서 머티리얼 생성 스크립트를 먼저 실행한 뒤 임포터를 실행합니다.

이 도구는 현재 초기 프로토타입입니다. 실제 Blender/Unreal 프로젝트에서 실행 결과를 확인한 뒤 프로덕션 파일에 적용하세요.

## 새 세션에서 작업 이어가기

같은 프로젝트 폴더를 계속 사용하고, 새 대화에서는 먼저 `docs/다음_세션_인수인계.md`와 관련 README를 읽도록 요청하세요. 세션별 폴더나 코드 복사본을 만들지 말고, 작업이 끝날 때 인수인계 문서의 완료 내용과 다음 작업을 갱신합니다.
