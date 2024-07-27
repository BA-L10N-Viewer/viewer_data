import requests
import json

from tool.tool import get_path_based_on_repopath, repeat_until_its_ok
from tool.nexon_db import NexonDatabase

urls = {
    "jp": "https://raw.githubusercontent.com/electricgoat/ba-data/jp/DB/LocalizeExcelTable.json"
}
DATA = {"jp": []}

# download
for (lang, url) in urls.items():
    r = repeat_until_its_ok(requests.get, url).json()["DataList"]
    DATA[lang].extend(r)
    DATA[lang] = NexonDatabase(DATA[lang], "Key")


def find_and_fill(path: str):
    # load local data
    with open(get_path_based_on_repopath(path), "r", encoding="utf-8") as f:
        EXISTING_DATA = json.load(f)

    # process
    last_value = -1
    for (key, value) in EXISTING_DATA.items():
        if value != -1:
            last_value = value
        else:
            pos_jp = DATA["jp"].query_pos(last_value)
            i18n_entry = DATA["jp"].db[pos_jp + 1]

            EXISTING_DATA[key] = i18n_entry["Key"]
            last_value = i18n_entry["Key"]

    # export
    with open(get_path_based_on_repopath(path), "w", encoding="utf-8") as f:
        json.dump(EXISTING_DATA, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    find_and_fill("data/story/i18n/i18n_event_index.json")
    find_and_fill("data/story/i18n/i18n_main_index.json")
