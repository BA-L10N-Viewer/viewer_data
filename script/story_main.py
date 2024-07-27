import functools
import os
import shutil
import json
import requests
import jellyfish

from tool.tool import get_path_based_on_repopath, repeat_until_its_ok

from collections import OrderedDict

from colorama import init as colorama_init
from colorama import Fore
from colorama import Style

colorama_init()

UPDATE_FILE = True
FILE_DIRECTORY = get_path_based_on_repopath("data/_temp/raw")
get_filepath = functools.partial(os.path.join, FILE_DIRECTORY)

urls = {
    "jp": ["https://raw.githubusercontent.com/electricgoat/ba-data/jp/DB/ScenarioScriptExcelTable.json"],
    "global": [
        # "https://raw.githubusercontent.com/electricgoat/ba-data/global/DB/ScenarioScriptExcelTable.json",
        "https://raw.githubusercontent.com/electricgoat/ba-data/global/DB/ScenarioScriptExcelTable1.json",
        "https://raw.githubusercontent.com/electricgoat/ba-data/global/DB/ScenarioScriptExcelTable2.json"
    ]
}

# data update
if UPDATE_FILE:
    os.makedirs(FILE_DIRECTORY, exist_ok=True)
    shutil.rmtree(FILE_DIRECTORY)
    os.makedirs(FILE_DIRECTORY)

    for (lang, urls) in urls.items():
        temp = []
        for url in urls:
            temp.extend(repeat_until_its_ok(requests.get, url, timeout=15).json()["DataList"])
        with open(get_filepath(f"{lang}_story.json"), "w", encoding="UTF-8") as f:
            json.dump(temp, f, ensure_ascii=False, indent=2)

# data load
EXISTING_DATA = {"global": [], "jp": []}
for lang in EXISTING_DATA.keys():
    with open(get_filepath(f"{lang}_story.json"), "r", encoding="UTF-8") as f:
        EXISTING_DATA[lang] = json.load(f)

# data slice (jp)
DATA_SLICE = {"jp": OrderedDict()}
for entry in EXISTING_DATA["jp"]:
    group_id = str(entry["GroupId"])
    if group_id not in DATA_SLICE["jp"]:
        DATA_SLICE["jp"][group_id] = []

    if entry["TextJp"] != "":
        DATA_SLICE["jp"][group_id].append(entry)

# data mapping (global -> jp)
for entry in EXISTING_DATA["global"]:
    group_id = str(entry["GroupId"])
    if group_id not in DATA_SLICE["jp"]:
        continue

    target_data_key = ["TextTh", "TextTw", "TextEn"]
    text_jp = entry["TextJp"]
    for entry2 in DATA_SLICE["jp"][group_id]:
        if jellyfish.jaro_similarity(entry2["TextJp"], text_jp) > 0.93:
            for _ in target_data_key:
                entry2[_] = entry[_]
            entry2["TextJpG"] = entry["TextJp"]
            entry2["ScriptKrG"] = entry["ScriptKr"]

# export
with open(get_path_based_on_repopath("data/_temp/story.json"), "w", encoding="UTF-8") as f:
    json.dump(DATA_SLICE["jp"], f, ensure_ascii=False, indent=2)


'''
# data export
for (lang, data) in DATA_SLICE.items():
    ids = [2000109, 2000706]
    os.makedirs(get_path_based_on_repopath("data/_temp/raw/story"), exist_ok=True)
    for id in ids:
        with open(get_path_based_on_repopath(f"data/_temp/raw/story/test_{id}_{lang}.json"), "w", encoding="UTF") as f:
            json.dump(DATA_SLICE[lang][str(id)], f, ensure_ascii=False, indent=2)

# data check
for group_id in DATA_SLICE["global"].keys():
    try:
        if len(DATA_SLICE["global"][group_id]) != len(DATA_SLICE["jp"][group_id]):
            print(f"INCONSISTENT DATA: {Fore.GREEN}{group_id}{Style.RESET_ALL} "
                  f'({Fore.BLUE}{len(DATA_SLICE["global"][group_id])}/'
                  f'{Fore.RED}{len(DATA_SLICE["jp"][group_id])}{Style.RESET_ALL})')
    except Exception as e:
        print(f'{Fore.RED}ERROR: {e}{Style.RESET_ALL} ({Fore.GREEN}{group_id}{Style.RESET_ALL})')
'''