# Grafana 대시보드

대시보드는 수집 스택과 독립적으로 관리하며 Grafana UI import, file provisioning,
HTTP API 업로드에 같은 JSON을 사용한다. 업로드에는 `bash`, `jq`, `curl`이 필요하다.
메트릭 수집 설정은 각 실행 환경이 소유하며 DGX Spark의 Alloy 설정은
[`stacks/dgx-spark/grafana/config.alloy`](../dgx-spark/grafana/config.alloy)에 둔다. 모델 메트릭 target은 Compose label에서
런타임 디렉터리의 `grafana/model-targets.json`으로 생성한다.

Spark의 `Service Health`는 현재 `service` label이 있는 모델 target을 instant query로 조회해
모델당 한 항목을 표시한다. `flash` 모드에서는 1개, 기본 `models` 모드에서는 3개가 표시되며,
모델을 추가하면 항목도 자동으로 늘어난다. 과거 조회 구간에만 존재하는 모델은 남겨 두지 않는다.
15초 수집 주기를 기준으로 최근 45초 내 sample만 사용해, Alloy 재시작 후 Prometheus의
lookback 구간에 남은 이전 모드의 target도 제외한다. 현재 target의 `up=0`은 Down으로 표시한다.
`Active Services`와 `Workload`도 현재 target을 기준으로 집계한다.

| 파일 | 내용 | UID |
| --- | --- | --- |
| `dashboards/agent-platform.json` | Host, Agent Studio·Memory, Node.js runtime, container resource | `agent-studio-idc` |
| `dashboards/dgx-spark.json` | Host, GB10 GPU, ComfyUI, vLLM, network·disk I/O | `dgx-spark` |

Agent Platform의 UID는 기존 대시보드 링크와 업데이트 호환성을 위해 유지한다.
두 대시보드는 특정 Grafana datasource나 hostname을 기본값으로 저장하지 않는다.
Import 후 `datasource`와 `instance`를 선택한다. 업로드 시 `GRAFANA_DATASOURCE_UID`로
기본 Prometheus datasource를 지정할 수도 있다.

## 업로드

저장소 루트에서 payload를 먼저 확인한다. `--dry-run`은 네트워크에 연결하지 않는다.

```bash
stacks/grafana/upload-dashboard.sh --dry-run agent-platform
stacks/grafana/upload-dashboard.sh --dry-run dgx-spark
```

실제 업로드는 대상 URL을 명시하며 dashboard 읽기·쓰기 권한이 있는 service account token을
숨김 입력으로 받는다. 자동화에서는 `GRAFANA_SERVICE_ACCOUNT_TOKEN`을 환경변수로 전달한다.
Alloy의 metrics write token과는 별도로 관리한다.

```bash
GRAFANA_URL=https://grafana.example.com \
  stacks/grafana/upload-dashboard.sh agent-platform

GRAFANA_URL=https://grafana.example.com \
  GRAFANA_FOLDER_UID=operations \
  GRAFANA_DATASOURCE_UID=prometheus \
  stacks/grafana/upload-dashboard.sh dgx-spark
```

이름 대신 JSON 파일 경로도 받는다. Script는 호출 디렉터리에 의존하지 않는다.
`GRAFANA_FOLDER_UID`를 생략하면 기존 대시보드의 폴더를 유지하고 신규 대시보드는 루트에 생성한다.
빈 값으로 명시하면 루트로 옮긴다. 같은 UID는 덮어쓰며 환경별 사본이 필요하면 JSON의 UID를 변경하라.
업로드 payload의 numeric `id`와 `version`은 다른 Grafana에서도 사용할 수 있도록 초기화한다.
현재 업로드 경로는 Grafana의 [호환 Dashboard HTTP API](https://github.com/grafana/grafana/blob/v11.6.0/docs/sources/developers/http_api/dashboard.md)
(`/api/dashboards/db`)를 사용한다.

## 메트릭 계약

공용 JSON으로 분리해도 수집 환경의 label이 자동 변환되지는 않는다. 다음 job과 label을 사용한다.

| 대상 | `job` | 추가 label·metric |
| --- | --- | --- |
| Host | `integrations/node_exporter` | `instance`, `node_*`; instance 목록은 `node_uname_info`에서 조회 |
| Agent Studio | `agent-studio` | `instance`, `agent_studio_*`, `process_*`, `nodejs_*` |
| Agent Memory | `agent-memory` | `instance`, `agent_memory_*`, `process_*`, `nodejs_*` |
| Container | `integrations/cadvisor` | `instance`, `service`, `container_*` |
| GPU | `dcgm-exporter` | `instance`, `DCGM_FI_DEV_*` |
| ComfyUI | `comfyui` | `instance`, `probe_success` |
| vLLM | `vllm` | `instance`, `service`, `vllm:*` |
| SGLang | `sglang` | `instance`, `service`, `sglang:*` |

Host와 workload는 같은 `instance` 값을 사용한다. k3s에서 재사용하려면 수집 설정에서
job·instance·service label을 맞추거나 해당 환경의 recording rule/query로 변환하라.
TensorFold의 원본 `/metrics`는 `tensorfold:*`를 제공한다. Spark Alloy는 모델 scrape 뒤
`prometheus.relabel.model_metrics`에서 `vllm:*`로 변환하고 `runtime="tensorfold"`를 추가한다.
기존 대시보드를 그대로 사용하며 원본·변환본을 중복 전송하지 않는다.
`request_success_total`은 엔진이 반환한 응답이며 출력 한도 종료도 포함한다.
`request_outcomes_total`로 정상 완료·출력 한도·취소·오류를 구분한다.
Prefix cache hit 비율은 반환된 응답의 전체 입력 토큰 대비 재사용 토큰 비율이다.
`first_content_seconds`는 추론을 제외한 최초 답변 지연을 측정한다.

기본 kubelet cAdvisor의 `namespace`·`pod`·`container` label만으로는 기존 container panel과
직접 호환되지 않는다. 수집하지 않는 metric의 panel은 비어 있으며, 이 디렉터리는 수집기를 설치하지 않는다.
