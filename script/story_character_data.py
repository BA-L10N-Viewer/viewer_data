import requests
import json
import opencc

from tool.tool import get_path_based_on_repopath, repeat_until_its_ok
from tool.nexon_db import NexonDatabase

urls = {"jp": ["https://raw.githubusercontent.com/electricgoat/ba-data/jp/DB/ScenarioCharacterNameExcelTable.json"],
        "global": [
            "https://raw.githubusercontent.com/electricgoat/ba-data/global/DB/ScenarioCharacterNameExcelTable.json"]
        }
DATA = {"jp": [], "global": []}
PROCESSED = {}

TW_TO_CN = opencc.OpenCC("tw2sp.json")


def convert_to_nx_lang(jp, gl):
    def convert(data_name: str):
        for (suffix, mapped_name) in data_mapping[data_name].items():
            for prefix in temp.keys():
                temp[prefix][mapped_name] = input_data[data_name][f"{prefix}{suffix}"]

    input_data = {"jp": jp, "global": gl}
    data_mapping = {
        "jp": {"JP": "j_ja", "KR": "j_ko"},
        "global": {"JP": "g_ja", "KR": "g_ko", "TH": "g_th", "TW": "g_tw", "EN": "g_en"}
    }
    temp = {"Name": {}, "Nickname": {}}

    convert("jp")
    if gl is not None and len(list(gl.keys())) != 0:
        convert("global")
        temp["Name"]["g_tw_cn"] = TW_TO_CN.convert(temp["Name"]["g_tw"])
        temp["Nickname"]["g_tw_cn"] = TW_TO_CN.convert(temp["Nickname"]["g_tw"])

    return temp


# download
for (lang, data) in urls.items():
    for url in data:
        r = repeat_until_its_ok(requests.get, url).json()["DataList"]
        DATA[lang].extend(r)
for (lang, data) in DATA.items():
    DATA[lang] = NexonDatabase(data, "CharacterName")

# l10n
for entry in DATA["jp"].db:
    char_id = entry["CharacterName"]

    jp_data = DATA["jp"].query(char_id)
    global_data = DATA["global"].query(char_id)

    PROCESSED[str(char_id)] = {
        "CharacterName": char_id,
        "SmallPortrait": entry["SmallPortrait"],
        **convert_to_nx_lang(jp_data, global_data)
    }
PROCESSED["-1"] = {
    "CharacterName": -1,
    "SmallPortrait": "null",
    "Name": {},
    "Nickname": {}
}

# export
with open(get_path_based_on_repopath("data/common/index_scenario_char.json"), "w", encoding="utf") as f:
    json.dump(PROCESSED, f, ensure_ascii=False, indent=2)
