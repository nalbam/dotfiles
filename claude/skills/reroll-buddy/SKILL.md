---
name: reroll-buddy
description: Use when the user wants to reroll their Claude Code /buddy companion pet. Triggers on "/reroll-buddy", "buddy 다시 뽑기", "펫 초기화", "companion 리셋", "buddy 리롤", "다른 펫 뽑고 싶어".
allowed-tools: Read, Edit, Bash
---

# Reroll Buddy

Claude Code `/buddy` 펫(companion)을 초기화하여 다시 뽑을 수 있게 하는 스킬.

## Overview

`/buddy`로 뽑은 펫 정보는 `~/.claude.json` 파일의 `companion` 키에 저장된다. 이 키를 제거하면 `/buddy`를 다시 실행하여 새 펫을 뽑을 수 있다.

## Workflow

### 1. 현재 펫 정보 확인

```bash
python3 -c "
import json, os
path = os.path.expanduser('~/.claude.json')
with open(path, 'r') as f:
    data = json.load(f)
if 'companion' not in data:
    print('NO_COMPANION')
else:
    print(json.dumps(data['companion'], indent=2, ensure_ascii=False))
"
```

- `companion` 키가 없으면 "이미 초기화된 상태입니다. `/buddy`를 실행하여 새 펫을 뽑으세요." 안내 후 종료
- `companion` 키가 있으면 현재 펫 이름과 성격을 사용자에게 보여준다

### 2. 사용자 확인

**반드시** 사용자에게 확인을 받는다:
- 현재 펫 이름을 표시
- "이 펫을 초기화하고 새로 뽑으시겠습니까?" 질문

### 3. companion 키 제거

사용자가 확인하면 `companion` 키만 정확히 제거:

```bash
python3 -c "
import json, os
path = os.path.expanduser('~/.claude.json')
with open(path, 'r') as f:
    data = json.load(f)
del data['companion']
with open(path, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write('\n')
print('Done')
"
```

### 4. 안내

초기화 완료 후 `/buddy`를 다시 실행하라고 안내한다.

## Important

- `~/.claude.json`은 Claude Code 핵심 설정 파일이므로 `companion` 키만 제거할 것
- 제거 전 반드시 사용자 확인 필수
- `/buddy`는 이벤트 기능이므로 시기에 따라 다시 뽑기가 불가능할 수 있음
