import requests
import json
import opencc

from tool.tool import get_path_based_on_repopath, repeat_until_its_ok
from tool.nexon_db import NexonDatabase

TW_TO_CN = opencc.OpenCC("tw2sp.json")
FILELIST = ["data/story/i18n/i18n_event_index.json", "data/story/i18n/i18n_main_index.json"]

urls = {
    "jp": "https://raw.githubusercontent.com/electricgoat/ba-data/jp/DB/LocalizeExcelTable.json",
    "global": "https://raw.githubusercontent.com/electricgoat/ba-data/global/DB/LocalizeExcelTable.json",
}
DATA = {"jp": [], "global": [], "custom": []}

# download
for (lang, url) in urls.items():
    r = repeat_until_its_ok(requests.get, url).json()["DataList"]
    DATA[lang].extend(r)
    DATA[lang] = NexonDatabase(DATA[lang], "Key")
with open(get_path_based_on_repopath("data/story/i18n/_i18n_main.json"), "r", encoding="utf-8") as f:
    r = json.load(f)
    DATA["custom"].extend(r)
    DATA["custom"] = NexonDatabase(DATA["custom"], "Key")

# what are the i18n IDs?
I18N_KEY = set()
for path in FILELIST:
    with open(get_path_based_on_repopath(path), "r", encoding="utf") as f:
        temp = json.load(f)
    temp = list(temp.values())
    I18N_KEY.update(temp)

# find the IDs and export
I18N_DATA = {}
for key in I18N_KEY:
    entry_jp, entry_global = DATA["jp"].query(key), DATA["global"].query(key)
    if (not entry_jp) and (not entry_global):
        entry_jp = entry_global = DATA["custom"].query(key)

    temp = {}

    temp["j_ja"] = entry_jp["Jp"]
    temp["j_ko"] = entry_jp["Kr"]
    if entry_global is not None:
        temp["g_ja"] = entry_global["Jp"]
        temp["g_ko"] = entry_global["Kr"]
        temp["g_th"] = entry_global["Th"]
        temp["g_en"] = entry_global["En"]
        temp["g_tw"] = entry_global["Tw"]
        temp["g_tw_cn"] = TW_TO_CN.convert(entry_global["Tw"])

    I18N_DATA[str(key)] = temp

# export
with open(get_path_based_on_repopath("data/story/i18n/i18n_story.json"), "w", encoding="utf") as f:
    json.dump(I18N_DATA, f, ensure_ascii=False, indent=2)
