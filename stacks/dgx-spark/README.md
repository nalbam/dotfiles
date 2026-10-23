# DGX Spark stack

DGX Spark에서 모델 서빙(vLLM·TensorFold), ComfyUI, 모니터링(Grafana Alloy·DCGM Exporter)을
Docker Compose와 user systemd로 운영한다. 운영 명령은 `dot` CLI가 제공한다.

- 처음 설치: [모듈 설치](#모듈-설치)
- 모드 전환·서비스 조작: [운영 명령](#운영-명령)
- API 공개: [Tailnet 통합 API](#tailnet-통합-api), [인터넷 API](#인터넷-api)
- 모델 추가: [모델 서비스 추가](#모델-서비스-추가)

## 구조와 실행 위치

저장소의 `stacks/dgx-spark/`는 원본이다. `dot`은 원본을 런타임 디렉터리로 복사한 뒤
그 디렉터리에서 `scripts/*.sh`를 실행한다.

| 항목 | 값 |
| --- | --- |
| 런타임 디렉터리 | `~/.config/dgx-spark` (`DOT_SPARK_DIR`로 변경) |
| Compose 프로젝트 이름 | `dgx-spark` (`docker-compose.yml`의 `name`으로 고정) |
| 원본에서 복사하지 않는 파일 | `.env`, `.env.grafana`, `backups/`, `grafana/model-targets.json`, `api/model-targets.json`, `*.md`, `__pycache__/`, `*.pyc`, `*.pyo`, `.DS_Store`, `bench/` |

복사는 원본에 있는 파일만 덮어쓰며 런타임 디렉터리의 다른 파일은 지우지 않는다.
`.env`와 `.env.grafana`는 이 머신의 설정과 credential이며 저장소에 넣지 않는다.

컨테이너 image(`dockpad-*`), Compose label(`io.dockpad.*`), systemd unit(`dockpad-*.service`)의
`dockpad` 이름은 기존 설치와 호환하려고 유지한다. 이름을 바꾸면 컨테이너와 서비스가 다시 만들어진다.

배포는 `aarch64`, NVIDIA GPU, Docker 접근 권한, Docker Compose plugin, Tailscale, Python 3을 확인한다.
서비스 포트는 loopback과 Tailscale IPv4에만 bind한다.

## 모듈 설치

| 명령 | 동작 |
| --- | --- |
| `dot add llm` | 원본을 런타임 디렉터리로 복사하고 `scripts/deploy.sh`와 `scripts/health-check.sh`를 실행한다. |
| `dot add monitoring` | 모니터링 파일을 복사하고 `scripts/setup-grafana.sh`를 실행한다. 없는 Grafana Cloud 값을 묻고 `dcgm-exporter`와 `alloy`를 기동한다. `llm` 스택이 먼저 배포되어 있어야 한다. |

`dot up`은 운영 중인 스택을 다시 배포하지 않는다. 저장소가 스택 파일을 바꾸면 경고로 알리고,
배포는 서빙이 끊겨도 되는 때에 `dot llm deploy`로 실행한다. `monitoring`은 자기 파일이
바뀌면 `dot up`에서 다시 설정한다. 이때 Alloy·DCGM Exporter만 재시작하고 모델 서빙은
재시작하지 않는다.

모델·image 버전은 런타임 `.env`의 pin을 유지한다. 저장소의 기본값을 바꿔도 기존 `.env` 값은
바뀌지 않는다. 버전을 올리려면 `.env`의 해당 값을 수정한 뒤 `dot llm deploy`를 실행한다.
다운로드가 필요 없는 `.env` 변경(예: 컨텍스트 길이)은 `dot llm recreate`로 반영한다.

## 운영 명령

```bash
dot llm deploy                     # 복사, image·모델 준비, 배포, health check
dot llm recreate                   # .env 변경 반영(다운로드 없음)
dot llm mode flash                 # flash | models | comfyui
dot llm status
dot llm logs -f llm embedding
dot llm health
dot llm config                     # 활성 Compose 설정 출력
dot llm restart llm                # start | stop | restart <service>
dot llm public-api                 # 인증 프록시와 Tailscale Funnel 설정
```

다른 머신에서는 host를 지정한다. Host 정보는 `~/.config/dotfiles/hosts/<host>.env`에 둔다.

```bash
dot @<host> llm status
dot @<host> llm mode models
```

## 모드

기본 모드는 vLLM 모델 서빙인 `models`다. 처음 배포하거나 `.env`에 모드가 없으면 `models`를
선택한다. 선택한 모드는 `.env`의 `SPARK_MODE`에 보존한다.

| 모드 | 서비스 | 포트 |
| --- | --- | --- |
| `models` | `llm` (`nvidia/Qwen3.6-35B-A3B-NVFP4`), `embedding` (`Qwen/Qwen3-Embedding-4B`), `reranker` (`Qwen/Qwen3-Reranker-0.6B`) | `8000`, `8001`, `8002` |
| `flash` | `flash` (`TensorFold/Qwen3.8-Flash-Next-MLX-4bit-MTP`) | `8000` |
| `comfyui` | `comfyui` | `8188` |

`models`의 세 서비스는 `vllm/vllm-openai:v0.30.0`을 사용한다. 최초 배포는 image를 받고
Hugging Face snapshot을 준비한 뒤 offline 모드로 모델을 실행한다. 선택 배포는 대상과
`depends_on` 의존 서비스의 snapshot만 준비한다.

모드 전환은 다음 순서로 진행한다.

1. 대상 모드의 image와 모델을 준비한다. 실패하면 현재 모드를 유지한다.
2. 다른 모드의 서비스를 모두 중지하고 대상 모드를 기동한다.
3. 기동이나 health check가 실패하면 이전 모드로 복구한다.

같은 모드를 다시 선택하면 현재 모드를 중지하지 않고 다시 배포한다. 진행 중인 요청은 전환 중에
중단될 수 있으므로 전환 전에 확인한다. `dot llm mode`는 저장소의 스택 파일을 먼저 복사한다.
저장소 변경은 적용 전에 [검증](#검증)의 테스트로 확인한다.

### Qwen3.8-Flash-Next (`flash`)

`dockpad-tensorfold-flash:v0.6.1-ko2`에서 TensorFold CUDA backend가 MLX 4-bit 가중치를 GB10에서
직접 읽는다. 요청 모델 ID는 `qwen3.8-flash-next`, API는 `http://<tailscale-ip>:8000/v1`이다.
모니터링과 인증 프록시는 유지한다.

`Dockerfile.flash`는 NVIDIA PyTorch 26.07 ARM64 image digest, TensorFold v0.6.1 소스 commit,
[MiaAI-Lab 레시피](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark-TensorFold)
commit `4c0dea8ebe93a1d445d6a716b5a38995ff6e9362`을 고정한다. 원본 소스와 라이선스는
`/opt/tensorfold-source`, `/opt/miaai`에 보존한다. Image build 중 `tests/`의 scheduler 테스트를
실행한다. 모델 revision은 `FLASH_REVISION`의 전체 Hugging Face commit SHA로 고정하며 다른
revision을 자동 선택하지 않는다.

| 설정 | 기본값 | 범위·설명 |
| --- | --- | --- |
| `FLASH_MAX_MODEL_LEN` | 262,144 | 1,024~262,144 토큰 |
| `FLASH_MAX_NUM_SEQS` | 4 | 동시 요청 1~4 |
| `FLASH_HOST_RESERVE_GIB` | 8 | 8~32. 가용 메모리에서 제외하고 컨텍스트·캐시가 맞는지 검사 |
| `FLASH_THINKING_BUDGET` | 512 | 1~8,192. 출력 한도가 작으면 절반까지 줄임 |
| `FLASH_DRAFT_VOCAB` | `multilingual` | `english_code`는 원본 초안 어휘. 최종 토큰은 항상 전체 어휘로 검증 |

- KV는 int8, MTP는 최대 6토큰·confidence 0.60이다. 출력 기본 한도는 32,768토큰이다.
- Thinking은 기본 비활성화다. 요청의 `chat_template_kwargs.enable_thinking=true` 또는
  `reasoning_effort`로 켠다. 요청에 명시한 `thinking_budget`은 그대로 적용하므로
  `max_tokens`에 추론과 답변을 모두 담을 여유를 둔다.
- 이미지·비디오 입력은 inline data URL만 받는다. 원격 이미지 URL은 다운로드하지 않는다.
- 모델 다운로드는 약 106GiB다. 약 30GiB의 PLE 조회 테이블은 SSD에서 읽는다.
- 어휘·입력 checksum, CUDA/Triton cache는 `~/.cache/tensorfold-qwen38`에 보존한다.
- 첫 실행은 CUDA kernel 컴파일 때문에 오래 걸린다. Health 대기는 최대 30분이며 짧은
  chat completion으로 실제 생성을 검사한다.

GB10은 CPU와 GPU가 메모리를 공유한다. 컨테이너 RAM과 RAM+swap 한도는 112GiB다.
`dockpad-flash-memory-watch.service`는 다음 조건에서 Flash 컨테이너를 정상 중지한다.

- MemAvailable이 6GiB 미만인 상태가 5회 연속 발생한다.
- MemAvailable이 10GiB 미만이면서 MemFree가 2GiB 미만인 상태가 5회 연속 발생한다.

이 중지는 자동으로 재시작하지 않는다. 원인을 확인한 뒤 `dot llm deploy`를 실행한다.
같은 머신에서 메모리를 많이 쓰는 작업(예: Homebrew 소스 빌드)을 실행하면 이 조건에 도달할 수 있다.
재부팅 후 로그인 없이 감시하려면 계정의 systemd linger를 활성화한다.

컨테이너는 `flash_request_started`와 `flash_request` JSON 로그를 남긴다. 요청 ID, 입력·생성·추론
토큰, 최초 본문 시간(`first_content_s`), 캐시 적중, 종료·취소 사유를 기록한다. 프롬프트·답변·헤더는
저장하지 않는다.

성능 측정 도구는 `bench/`에 있다. 런타임 디렉터리로 복사하지 않으며 저장소에서 실행한다.

```bash
python3 stacks/dgx-spark/bench/benchmark-flash.py --base-url http://<tailscale-ip>:8000/v1 --output /tmp/flash-benchmark.json
python3 stacks/dgx-spark/bench/benchmark-flash-cache.py --base-url http://<tailscale-ip>:8000/v1 --output /tmp/flash-cache.json
```

`benchmark-flash.py`는 API의 completion-token usage로 요청별 decode 속도와 TTFT, 동시 요청의
합산 처리량을 측정한다. 기본값은 최대 출력 512토큰, temperature 0, thinking off, 동시 요청
1·2·4개, 조건별 3회다. `benchmark-flash-cache.py`는 약 2만 토큰의 공통 입력을 1~4개 동시 요청으로
재사용해 캐시 동작을 검사한다. 워밍업 후 같은 조건으로 반복 측정한다.

### ComfyUI (`comfyui`)

기본 버전은 `v0.34.5`, base image는 `nvcr.io/nvidia/pytorch:25.11-py3`다.
UI는 `http://<tailscale-ip>:8188`이다. `models`, `input`, `output`, `user`, `custom_nodes`는
`COMFYUI_DATA_PATH`(기본 `$HOME/.local/share/comfyui`)에 보존한다. ComfyUI용 모델은 자동으로
다운로드하지 않는다.

## Tailnet 통합 API

Tailscale 서비스 `llm`은 `https://llm.<tailnet>.ts.net/v1`에서 LLM·embedding·reranker를 제공한다.
요청에는 `Authorization: Bearer <key>`가 필요하다. Key는 Spark의 `~/.config/spark-secret-key`다.

| API 경로 | 대상 |
| --- | --- |
| `/v1/models` | 활성 모드의 통합 모델 카탈로그 |
| `/v1/chat/completions`, 기타 LLM API | `llm:8000` |
| `/v1/embeddings` | `embedding:8001` |
| `/v1/rerank`, `/v1/score` | `reranker:8002` |

`GET /v1/models`는 활성 모드의 모델 서버에서 목록을 읽어 합친다. OpenAI 목록 형식에 `service`,
`capabilities`, `endpoints`를 추가한다. 모델 서버에 연결할 수 없으면 `503`, 잘못된 목록을 받으면
`502`를 반환하며 일부 목록만 성공으로 반환하지 않는다. Key가 없거나 틀리면 `401`을 반환한다.

설정 절차:

1. Tailscale 관리자 화면에서 `llm` 서비스를 `tcp:443`으로 정의한다.
2. Spark에서 다음 명령을 실행한다. `flash` 모드에서는 `write-targets`의 인수를 `flash`로 지정한다.

   ```bash
   cd ~/.config/dgx-spark
   python3 -B scripts/services.py write-targets models
   docker compose --profile public up -d --force-recreate api-gateway
   tailscale serve --service=svc:llm --https=443 http://127.0.0.1:18001
   tailscale serve status
   ```

3. 처음 광고한 host를 관리자 화면에서 승인한다.

Caddy는 loopback `18001`에서 경로별로 요청을 전달한다. `api-catalog`는 vLLM image의 Python 표준
라이브러리로 실행하며 API key를 받거나 모델 서버에 전달하지 않는다.

## 인터넷 API

1. Spark의 `~/.config/spark-secret-key`에 32~128자의 base64/hex key를 저장하고 권한을 `0600`으로 설정한다.
2. `dot llm public-api`를 실행한다. Caddy 인증 프록시를 배포하고 Tailscale Funnel의 HTTPS `8443`을
   공개한다. 기존 tailnet 전용 `443` 설정은 유지한다.
3. 처음 실행하면 Tailscale 관리자 화면에서 이 host의 Funnel 사용을 승인해야 할 수 있다.

`serve config denied`가 나오면 Spark에서 `sudo tailscale set --operator="$USER"`를 한 번 실행한 뒤
다시 실행한다. Key를 교체한 뒤 같은 명령을 다시 실행하면 프록시가 새 key를 읽는다.

외부 주소는 `https://<host>.<tailnet>.ts.net:8443/v1`이다. 통합 API와 같은 경로와 인증을 사용한다.
Funnel은 loopback `18000`에 연결한다. ComfyUI와 모델의 개별 포트는 공개하지 않는다.
Tailscale IP의 `8000` 포트는 tailnet 안에서 key 없이 접근할 수 있다. 이 경로에도 key를 강제하려면
모델 서비스의 Tailscale IP 포트 바인딩을 제거한다.

```bash
curl -fsS https://<host>.<tailnet>.ts.net:8443/v1/models \
  -H "Authorization: Bearer $MODEL_API_KEY"
```

## 모델 서비스 추가

`docker-compose.yml`의 `models`·`flash` profile이 각 모드의 모델 목록이다. 서비스 이름·포트를
배포 스크립트에 따로 등록하지 않는다. 다른 런타임도 같은 profile에 독립 서비스로 추가할 수 있다.
각 서비스에는 실제 준비 상태를 검사하는 Compose `healthcheck`가 있어야 한다. 전체 모델의 GPU
메모리 사용량과 포트 충돌을 확인한다.

| Label | 용도 |
| --- | --- |
| `io.dockpad.hf-model` | 미리 다운로드할 Hugging Face `owner/model`. 생략하면 런타임이 직접 준비 |
| `io.dockpad.hf-revision` | 고정할 Hugging Face commit SHA. 생략하면 최신 snapshot |
| `io.dockpad.metrics-port` | 컨테이너 내부 Prometheus 포트. loopback에도 publish해야 함 |
| `io.dockpad.metrics-job` | Prometheus job 이름. 기본 `vllm` |
| `io.dockpad.metrics-path` | Prometheus 경로. 기본 `/metrics` |
| `io.dockpad.api-kind` | 통합 카탈로그 용도: `chat`, `embedding`, `reranker` |

- `hf-model`을 지정한 image에는 Python 3와 `huggingface_hub`가 있어야 하고, 서비스 volume에 모델
  cache를 보존해야 한다. 다운로드는 해당 서비스의 image와 volume을 사용한다.
- `api-kind`를 지정한 서비스는 `metrics-port`와 같은 포트에서 `/v1/models`를 제공해야 한다.
- 추가 모델은 배포·모드 중지·복구·health check에 자동으로 포함된다.
- 배포와 모드 전환은 활성 모드의 `grafana/model-targets.json`과 `api/model-targets.json`을 생성한다.
  두 파일은 생성물이며 Git과 복사 대상에서 제외한다.
- vLLM 외의 job은 해당 metric에 맞는 대시보드 panel을 별도로 구성한다.

## 모니터링

`dot add monitoring`은 Grafana Cloud 값을 입력받아 런타임 `.env.grafana`에 mode `0600`으로 저장한다.
Token은 숨김 입력으로 받는다. 값은 저장소에 넣지 않는다.

| 키 | 내용 |
| --- | --- |
| `GCLOUD_FM_URL` | Fleet Management URL (`https://fleet-management-<cluster>.grafana.net`) |
| `GCLOUD_FM_USERNAME` | Fleet Management user ID (숫자) |
| `GCLOUD_PROM_URL` | Prometheus remote-write URL (`https://prometheus-<region>.grafana.net/api/prom/push`) |
| `GCLOUD_PROM_USERNAME` | Prometheus user ID (숫자) |
| `GCLOUD_FM_COLLECTOR_ID` | Collector ID. 기본값은 `hostname -s` |
| `GCLOUD_RW_API_KEY` | Access policy token |

`.env.grafana`가 있는데 키가 하나라도 없으면 배포는 Compose를 실행하기 전에 중단한다.
터미널에서 `dot add monitoring`을 실행하면 기존 값을 유지하고 없는 값만 입력받는다. `dot up`은
값이 빠진 상태에서 새 `config.alloy`를 복사하지 않는다(Alloy가 재시작할 때 빈 값을 읽지 않도록).

이전 dockpad 설치는 `GCLOUD_RW_API_KEY`와 `GCLOUD_FM_COLLECTOR_ID`만 저장했다. 처음 `dot up` 전에
터미널에서 `dot add monitoring`을 실행해 나머지 네 값을 추가한다.

`.env.grafana`가 있으면 `dcgm-exporter`와 `alloy`가 배포·상태·health 대상에 포함된다.
Alloy의 내장 Node Exporter는 GB10 sysfs에서 응답하지 않는 `cpufreq` collector를 비활성화한다.
cAdvisor는 실행하지 않는다. 대시보드는 [Grafana 대시보드](../grafana/README.md)로 업로드한다.

## VibeMon 수집기

VibeMon 수집기는 이 스택과 `dot`이 설치하거나 관리하지 않는다. Spark에서 VibeMon 설치기로 설치한다:
`curl -fsSL https://vibemon.io/install/install.py | python3 - --collector`.

## 백업

ComfyUI 데이터는 `COMFYUI_DATA_PATH`에, 모델 cache는 `~/.cache/huggingface`에 저장한다.
자동 백업은 없다. 필요한 데이터와 `.env`·`.env.grafana`는 별도 도구로 보관한다.
Grafana token은 별도 secret 저장소에서 복구한다.

## 검증

저장소 루트에서 실행한다. 테스트는 임시 디렉터리와 가짜 Docker·HTTP·systemd 명령을 사용하며
실제 서버를 배포하지 않는다.

```bash
python3 -m unittest discover -s tests -p 'test_stack_*.py'
```
