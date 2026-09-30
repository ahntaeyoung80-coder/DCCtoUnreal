# DCC to Unreal

Blender에서 메시와 재질 정보를 내보내고 Unreal Editor에서 가져오는 도구 모음입니다.

## 폴더 안내

- `docs/`: 간결한 세션 인수인계와 누적 작업 로그
- `blender/`: Blender 애드온과 사용 안내
- `unreal/`: Unreal Editor Python 스크립트와 사용 안내

내보낸 FBX/JSON과 텍스처는 프로젝트 코드 폴더와 섞지 말고 별도의 작업 출력 폴더에 저장하세요. 아직 예제 입력 파일은 없으므로 `examples/` 폴더는 만들지 않았습니다.

## 빠른 시작

1. [Blender Exporter 안내](blender/README_dcc_batch_exporter.md)를 따라 `blender/dcc_batch_exporter.py`를 설치합니다.
2. Blender에서 FBX/JSON을 내보냅니다.
3. [Unreal 도구 안내](unreal/README_unreal_dcc_importer.md)를 읽고 Unreal Editor에서 기본 템플릿 생성기를 실행한 뒤 임포터를 실행합니다.

기본 템플릿 생성기는 기존 Unreal 프로젝트에 `/Game/Imports` 폴더와 `/Game/Materials/Master/MM_MasterSurface`를 만듭니다. 이미 있는 마스터 머티리얼 그래프는 그대로 둡니다. `.upack` 패키징은 이 스크립트의 범위가 아닙니다.

이 도구는 현재 초기 프로토타입입니다. 실제 Blender/Unreal 프로젝트에서 실행 결과를 확인한 뒤 프로덕션 파일에 적용하세요.

## 새 세션에서 작업 이어가기

같은 프로젝트 폴더를 계속 사용하고, 새 대화에서는 `docs/HANDOFF.md`를 먼저 읽도록 요청하세요. Codex는 루트 `AGENTS.md`의 지침에 따라 작업 시작 전에 확인합니다. 현재 체크포인트는 `HANDOFF.md`, 누적 결정과 변경 기록은 `docs/WORK_LOG.md`에 둡니다. 세션별 폴더나 코드 복사본은 만들지 않습니다.
