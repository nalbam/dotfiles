---
name: laya-integration
description: Integrate or evaluate Laya when the user selects Laya, or maintain an existing Laya integration. Laya 도입·평가·기존 통합 수정.
metadata:
  source: https://github.com/NandhaKishorM/laya
---

# Laya Integration

일반적인 분류·라우팅 요청만으로 Laya를 도입하지 않는다. 사용자가 선택한 모델과 아키텍처를 유지한다. API·체크포인트·지원 언어는 설치 버전과 [공식 저장소](https://github.com/NandhaKishorM/laya)에서 확인한다.

## 통합

1. 질문 유형, 대상 언어, 오분류 비용, 지연·메모리 목표를 확인한다. 산술·비교는 코드로 처리하고 Laya에는 텍스트 판단을 맡긴다.
2. 프로젝트의 패키지 관리 방식으로 설치한다. 모델 가중치의 최초 다운로드·캐시·오프라인 실행 조건을 구분한다.
3. 필요한 체크포인트를 시작 시 한 번 로드해 재사용한다. 대표 입력으로 워밍업하고 동시 호출의 자원 사용을 측정한다.
4. 질문은 입력이 무엇을 말하는지 묻고 선택지별 의미를 설명한다. 입력·선택지 길이가 해당 체크포인트에서 잘리지 않는지 확인한다.
5. 언어를 알면 지원되는 명시적 언어 설정을 사용한다. 자동 감지를 쓰면 대상 언어별 라우팅을 검증한다.
6. 모델 확률을 실제 정답률로 간주하지 않는다. 평가 데이터로 임계값을 정하고 낮은 신뢰도·추론 실패의 처리 경로를 구현한다.

## 최소 호출 예시

설치 버전의 API에 맞게 조정한다.

```python
import laya

agent = laya.load("convaiinnovations/laya")
result = agent.predict(
    "The customer asks for an invoice.",
    {
        "department": {
            "type": "choice",
            "instructions": "Which team handles this request?",
            "criteria": {
                "billing": "invoices and payments",
                "support": "technical problems",
            },
        },
    },
)
answer = result["answers"]["department"]
```

| 유형 | 입력·결과 |
|------|-----------|
| `choice` | 선택지 설명 → 선택값과 선택지별 확률 |
| `score` | 순서가 있는 수준 설명 → 점수와 수준별 확률 |
| `noul` | 참/거짓 질문 → 참일 확률 |

## 검증

- 실제 사용 언어·입력 길이·경계 사례를 포함한 라벨 데이터로 정확도와 오탐·미탐을 측정한다.
- 질문·모델·임계값을 고르는 데이터와 최종 평가 데이터를 나눠 과적합을 피한다.
- 콜드 스타트·워밍업 후 지연·메모리·사람이나 다른 모델로 넘기는 비율을 측정한다. 다른 환경의 벤치마크 수치를 보장하지 않는다.
- 통합 테스트에서는 반환 계약·실패·낮은 신뢰도를 검증한다. 보안 판정은 모델 출력 하나에 의존하지 않는다.

기존 스킬 원저자: [brain function collapse](https://brainfunctioncollapse.com/laya). Laya: Nandakishor M / Convai Innovations.
