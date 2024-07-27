import json
import logging

import requests
import opencc

from typing import Dict, List

from pydantic import BaseModel
from tool.tool import get_path_based_on_repopath, repeat_until_its_ok


class NexonMomotalkEntry(BaseModel):
    # metadata
    GroupId: int  # 多项选择/语句的组ID
    Id: int  # 实际语句的ID（绝对ID）
    CharacterId: int  # 人物ID（见SchaleDB）

    # condition
    MessageCondition: str
    MessageType: str
    PreConditionGroupId: int
    PreConditionFavorScheduleId: int
    FavorScheduleId: int
    NextGroupId: int

    # others
    FeedbackTimeMillisec: int

    # message
    Message: Dict


TW_TO_CN = opencc.OpenCC('tw2sp.json')
logging.basicConfig(level=logging.DEBUG)

filelist = ["AcademyMessanger1ExcelTable.json", "AcademyMessanger2ExcelTable.json",
            "AcademyMessanger3ExcelTable.json"]

lang_map = {"jp": "j", "global": "g"}
data = {i: [] for i in lang_map.keys()}

# get data
for lang in data.keys():
    url = f"https://raw.githubusercontent.com/electricgoat/ba-data/{lang}/Excel/[FILENAME]"
    for file in filelist:
        url_ = url.replace("[FILENAME]", file)

        r = repeat_until_its_ok(requests.get, url_)
        data[lang].extend(r.json()["DataList"])

# data mapping
result = []
result_mapping = {}  # GroupId_Id mapping
result_mapping_id = lambda a: f'{a["MessageGroupId"]}_{a["Id"]}'

# first mapping jp
for entry in data["jp"]:
    image_path_text = f"[img: {entry['ImagePath']}][\\n]" if entry["ImagePath"] else ""

    entry_ = NexonMomotalkEntry(**{
        # metadata
        "GroupId": entry["MessageGroupId"],  # 多项选择/语句的组ID
        "Id": entry["Id"],  # 实际语句的ID（绝对ID）
        "CharacterId": entry["CharacterId"],  # 人物ID（见SchaleDB）

        # condition, can be used to separate conversations
        "MessageCondition": entry["MessageCondition"],  # Feedback
        "MessageType": entry["MessageType"],
        "PreConditionGroupId": entry["PreConditionGroupId"],
        "PreConditionFavorScheduleId": entry["PreConditionFavorScheduleId"],
        "FavorScheduleId": entry["FavorScheduleId"],
        "NextGroupId": entry["NextGroupId"],

        # others
        "FeedbackTimeMillisec": entry["FeedbackTimeMillisec"],

        # message
        "Message": {
            "j_ko": image_path_text + entry["MessageKR"],
            "j_ja": image_path_text + entry["MessageJP"],
        }
    })

    result.append(entry_)
    result_mapping[result_mapping_id(entry)] = len(result) - 1

# then global
for entry in data["global"]:
    image_path_text = f"[img: {entry['ImagePath']}][\\n]" if entry["ImagePath"] else ""

    entry_ = result[result_mapping[result_mapping_id(entry)]].Message
    entry_["g_en"] = image_path_text + entry["MessageEN"]
    entry_["g_tw"] = image_path_text + entry["MessageTW"]
    entry_["g_tw_cn"] = TW_TO_CN.convert(entry_["g_tw"])
    entry_["g_ja"] = image_path_text + entry["MessageJP"]
    entry_["g_ko"] = image_path_text + entry["MessageKR"]
    result[result_mapping[result_mapping_id(entry)]].Message = entry_

# export
with open(get_path_based_on_repopath("data/_temp/mmt.json"), "w", encoding="utf-8") as f:
    json.dump([i.model_dump() for i in result], f, ensure_ascii=False)
