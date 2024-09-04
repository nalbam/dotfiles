import json
import os

# VS Code settings.json 파일 경로
settings_path = os.path.expanduser(
    "~/Library/Application Support/Code/User/settings.json"
)

# settings.json 파일 읽기
with open(settings_path, "r", encoding="utf-8") as file:
    settings = json.load(file)

# JSON 객체를 키를 기준으로 정렬
sorted_settings = {key: settings[key] for key in sorted(settings)}

# 정렬된 JSON 객체를 settings.json 파일에 다시 저장
with open(settings_path, "w", encoding="utf-8") as file:
    json.dump(sorted_settings, file, ensure_ascii=False, indent=4)

print("settings.json 파일이 성공적으로 정렬되었습니다.")
