import requests
import json

from collections import OrderedDict

from tool.tool import get_path_based_on_repopath, repeat_until_its_ok

urls = {"jp": "https://raw.githubusercontent.com/electricgoat/ba-data/jp/Excel/EventContentScenarioExcelTable.json"}
DATA = {"jp": []}

# download
for (lang, url) in urls.items():
    r = repeat_until_its_ok(requests.get, url).json()["DataList"]
    DATA[lang].extend(r)

PROCESSED = []
PROCESSED_DICT = OrderedDict()
STORY_I18N_TABLE = OrderedDict()
I18N_TABLE = OrderedDict()

# index data
for (pos, entry) in enumerate(DATA["jp"]):
    event_id = entry["EventContentId"]
    index_id = entry["Id"]
    scenario_id = entry["ScenarioGroupId"]

    # 810 情人节特殊处理
    if entry["IsMeetup"] and (event_id == 810 or event_id == 834):
        event_id = 999
        print(entry["Order"])

    if str(event_id) not in PROCESSED_DICT:
        PROCESSED_DICT[str(event_id)] = []

    PROCESSED_DICT[str(event_id)].extend(scenario_id)

# process
for (event_id, data) in PROCESSED_DICT.items():
    # 新增活动数据
    curr_event = None
    for entry in PROCESSED:
        if entry["id"] == event_id:
            curr_event = entry
    if curr_event is None:
        curr_event = {
            "type": "child",
            "id": str(event_id),
            "name": f"[STORY_EVENT_{event_id}_NAME]",
            "desc": f"[STORY_EVENT_{event_id}_DESC]",
            "data": []
        }
        PROCESSED.append(curr_event)
        I18N_TABLE[f'[STORY_EVENT_{event_id}_NAME]'] = -1
        I18N_TABLE[f'[STORY_EVENT_{event_id}_DESC]'] = -1

    for (idx, story_id) in enumerate(data, 1):
        i18n_id_name = f"[STORY_EVENT_{event_id}_{idx}_NAME]"
        i18n_id_desc = f"[STORY_EVENT_{event_id}_{idx}_DESC_1]"

        STORY_I18N_TABLE[str(story_id)] = [i18n_id_name, i18n_id_desc]
        curr_event["data"].append(story_id)

        I18N_TABLE[i18n_id_name] = -1
        I18N_TABLE[i18n_id_desc] = -1

# export
with open(get_path_based_on_repopath("data/common/index_scenario_manifest_event.json"), "w",
          encoding="utf-8") as f:
    json.dump(PROCESSED, f, ensure_ascii=False, indent=2)
with open(get_path_based_on_repopath("data/common/index_scenario_i18n_event.json"), "w", encoding="utf-8") as f:
    json.dump(STORY_I18N_TABLE, f, ensure_ascii=False, indent=2)
# append i18n_event.json
with open(get_path_based_on_repopath("data/story/i18n/i18n_event_index.json"), "r", encoding="utf-8") as f:
    temp = json.load(f)
I18N_TABLE.update(temp)
with open(get_path_based_on_repopath("data/story/i18n/i18n_event_index.json"), "w", encoding="utf-8") as f:
    json.dump(I18N_TABLE, f, ensure_ascii=False, indent=2)

