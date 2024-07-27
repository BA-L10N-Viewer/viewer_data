import logging
import os, shutil
import requests
import json
import opencc

from collections import OrderedDict

from tool.tool import repeat_until_its_ok, get_path_based_on_repopath
from tool.nexon_db import NexonDatabase

from pydantic import BaseModel

TW_TO_CN = opencc.OpenCC('tw2sp.json')
CN_TO_TW = opencc.OpenCC('s2twp.json')


def remove_newline(text):
    temp = text.replace('\n', '<br />')
    temp = temp.replace("<br /><br />", "[\\n]")
    temp = temp.replace('<br />', "[\\n]")
    return temp


def get_l10n_nx(data: dict, data_prefix: str):
    lang = ["Kr", "Jp", "Tw", "En", "Th"]
    result = {"Kr": "null", "Jp": "null", "Tw": "null", "En": "null", "Th": "null"}

    for i in lang:
        if f"{data_prefix}{i}" in data:
            result[i] = remove_newline(data.get(f"{data_prefix}{i}", "null data"))
        elif f"{data_prefix}{i.upper()}" in data:
            result[i] = remove_newline(data.get(f"{data_prefix}{i.upper()}", "null data"))

    return result


def nx_convert_to_nx_data(data: dict, lang_prefix: str = "j"):
    temp = {}
    for (lang, content) in data.items():
        if lang == "Jp":
            lang = "ja"
        elif lang == "Kr":
            lang = "ko"
        else:
            lang = lang.lower()
        lang = lang_prefix + "_" + lang

        if content != "null":
            temp[lang] = content
            if lang == "tw":
                temp[lang_prefix + "_" + "tw_cn"] = TW_TO_CN.convert(content)

    return temp


def nx_concat_data_to_nx_data(jp_data: dict, gl_data: dict):
    temp = {}
    temp.update(nx_convert_to_nx_data(jp_data, "j"))
    temp.update(nx_convert_to_nx_data(gl_data, "g"))
    return temp


# LocalizeCharProfileExcelTable
data_charprofile = {"global": [], "jp": []}
# CharacterVoiceExcelTable
data_voice = {"global": [], "jp": []}
# LocalizeEtcExcelTable
data_etc_l10n = {"global": [], "jp": []}
# CharacterDialogEventExcelTable
data_voice_event = {"global": [], "jp": []}
# CharacterExcelTable
data_charinfo = {"global": [], "jp": []}

# filelist
filelist = {
    "CharacterExcelTable.json": data_charinfo,
    "LocalizeCharProfileExcelTable.json": data_charprofile,
    "LocalizeEtcExcelTable.json": data_etc_l10n,
    "CharacterVoiceExcelTable.json": data_voice,
    "CharacterDialogEventExcelTable.json": data_voice_event,
}
file_index_key = {
    "CharacterExcelTable.json": "Id",
    "LocalizeCharProfileExcelTable.json": "CharacterId",
    "LocalizeEtcExcelTable.json": "Key",
    "CharacterVoiceExcelTable.json": "CharacterVoiceUniqueId",
    "CharacterDialogEventExcelTable.json": "CostumeUniqueId",
}

# download files
for (filename, _) in filelist.items():
    for lang in ["jp", "global"]:
        for directory in ["DB", "Excel"]:
            url = f"https://raw.githubusercontent.com/electricgoat/ba-data/{lang}/{directory}/{filename}"

            r = repeat_until_its_ok(requests.get, url)
            if r.status_code == 404:
                logging.warning(url)
                continue
            logging.info(url)

            _[lang] = r.json()["DataList"]

# NexonDatabase wrapper
for (filename, _) in filelist.items():
    for lang in ["jp", "global"]:
        _[lang] = NexonDatabase(_[lang], file_index_key[filename])

# character
result = {}

# getting all existing student
for i in data_charinfo["jp"].db:
    # basic info
    data = {
        "Id": i["Id"],
        "LocalizeEtcId": i["LocalizeEtcId"],
        "School": i["School"],
        "Club": i["Club"],
    }

    # ------------------------------------------------------
    # 人物档案（大部分）
    temp1, temp2 = data_charprofile["jp"].query(i["Id"]), data_charprofile["global"].query(i["Id"])
    # Momotalk状态
    data["StatusMessage"] = nx_concat_data_to_nx_data(get_l10n_nx(temp1, "StatusMessage"),
                                                      get_l10n_nx(temp2, "StatusMessage"))
    """
    # 姓
    data["FamilyName"] = nx_concat_data_to_nx_data(get_l10n_nx(temp1, "FamilyName"),
                                                   get_l10n_nx(temp2, "FamilyName"))
    """
    # 爱好
    data["Hobby"] = nx_concat_data_to_nx_data(get_l10n_nx(temp1, "Hobby"),
                                              get_l10n_nx(temp2, "Hobby"))
    # 武器 名称、描述
    data["WeaponName"] = nx_concat_data_to_nx_data(get_l10n_nx(temp1, "WeaponName"),
                                                   get_l10n_nx(temp2, "WeaponName"))
    data["WeaponDesc"] = nx_concat_data_to_nx_data(get_l10n_nx(temp1, "WeaponDesc"),
                                                   get_l10n_nx(temp2, "WeaponDesc"))
    # 个人档案
    data["Profile"] = nx_concat_data_to_nx_data(get_l10n_nx(temp1, "ProfileIntroduction"),
                                                get_l10n_nx(temp2, "ProfileIntroduction"))
    # 第一次抽出来的提示语
    data["CharacterSSRNew"] = nx_concat_data_to_nx_data(get_l10n_nx(temp1, "CharacterSSRNew"),
                                                        get_l10n_nx(temp2, "CharacterSSRNew"))
    # ------------------------------------------------------

    """
    # ------------------------------------------------------
    # LocalizeEtc
    temp1, temp2 = data_etc_l10n["jp"].query(i["LocalizeEtcId"]), data_etc_l10n["global"].query(i["LocalizeEtcId"])
    # 名
    data["Name"] = nx_concat_data_to_nx_data(get_l10n_nx(temp1, "Name"),
                                             get_l10n_nx(temp2, "Name"))
    # ------------------------------------------------------
    """

    result[str(i["Id"])] = data

# SchaleDB data
SCHALE_DB_LANG = OrderedDict({"en": "en", "th": "th", "cn": "cn", "jp": "ja", "kr": "ko", "tw": "tw", "zh": "zh"})
SCHALE_DB_VOICE_DATA = OrderedDict()
SCHALE_DB_STU_DATA = OrderedDict()
for (_, lang) in SCHALE_DB_LANG.items():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
    r = repeat_until_its_ok(requests.get, f"https://schale.gg/data/{_}/voice.min.json", headers=headers)
    SCHALE_DB_VOICE_DATA[lang] = r.json()

    r = repeat_until_its_ok(requests.get, f"https://schale.gg/data/{_}/students.min.json", headers=headers)
    SCHALE_DB_STU_DATA[lang] = r.json()

# process data
for (lang, data) in SCHALE_DB_VOICE_DATA.items():
    for (char_id, char_data) in data.items():
        # 检测result里头有没有voice
        if "Voicelines" not in result[str(char_id)].keys():
            result[str(char_id)]["Voicelines"] = {}

        for voice_type in ["Event", "Lobby", "Normal"]:
            # 检查result-voice里头有没有对应type
            if voice_type not in result[str(char_id)]["Voicelines"].keys():
                result[str(char_id)]["Voicelines"][voice_type] = []

            voice_data = char_data[voice_type]
            actual_voice_entry_idx = 0  # 实际存在的voiceline
            for (entry_idx, voice_entry) in enumerate(voice_data):
                if 'UITitleIdle1' in voice_entry["Group"]:
                    # 部分语言没有第一条的数据
                    voice_entry["Transcription"] = "[default] Blue Archive"
                if "Transcription" not in voice_entry.keys():
                    continue

                # 如果有文本
                # 先检查要不要添加entry
                curr_voiceslines = result[str(char_id)]["Voicelines"][voice_type]
                if len(curr_voiceslines) == actual_voice_entry_idx and lang == "en":
                    # 如果正好等于entry_idx，说明绝对没有
                    # 例如entry_idx=0, len=0时
                    curr_voiceslines.append({"Group": voice_entry["Group"],
                                             "Transcription": {}})
                    actual_voice_entry_idx += 1
                if lang != "en":
                    actual_voice_entry_idx += 1
                curr_voiceline = curr_voiceslines[actual_voice_entry_idx - 1]["Transcription"]

                transcription = remove_newline(voice_entry["Transcription"])
                # 添加文本
                if lang == "en":
                    curr_voiceline["g_en"] = transcription
                if lang == "ja":
                    curr_voiceline["j_ja"] = transcription
                    curr_voiceline["g_ja"] = transcription
                if lang == "ko":
                    curr_voiceline["j_ko"] = transcription
                    curr_voiceline["g_ko"] = transcription
                if lang == "cn":
                    curr_voiceline["c_cn"] = transcription
                    curr_voiceline["c_cn_tw"] = CN_TO_TW.convert(transcription)
                if lang == "tw":
                    curr_voiceline["g_tw"] = transcription
                    curr_voiceline["g_tw_cn"] = TW_TO_CN.convert(transcription)
                if lang == "th":
                    curr_voiceline["g_th"] = transcription
                curr_voiceslines[actual_voice_entry_idx - 1]["Transcription"] = curr_voiceline

# process data 2
for (lang, data) in SCHALE_DB_STU_DATA.items():
    for char_data in data:
        char_id = str(char_data["Id"])
        family_name = char_data["FamilyName"]
        name = char_data["Name"]

        curr_char = result[str(char_id)]
        if "FamilyName" not in curr_char.keys():
            curr_char["FamilyName"] = {}
        if "Name" not in curr_char.keys():
            curr_char["Name"] = {}

        curr_data_family = curr_char["FamilyName"]
        curr_data_name = curr_char["Name"]

        # 添加文本
        if lang == "en":
            curr_data_family["g_en"] = family_name
            curr_data_name["g_en"] = name
        if lang == "ja":
            curr_data_family["j_ja"] = family_name
            curr_data_name["j_ja"] = name
            curr_data_family["g_ja"] = family_name
            curr_data_name["g_ja"] = name
        if lang == "ko":
            curr_data_family["j_ko"] = family_name
            curr_data_name["j_ko"] = name
            curr_data_family["g_ko"] = family_name
            curr_data_name["g_ko"] = name
        if lang == "cn":
            curr_data_family["c_cn"] = family_name
            curr_data_name["c_cn"] = name
            curr_data_family["c_cn_tw"] = CN_TO_TW.convert(family_name)
            curr_data_name["c_cn_tw"] = CN_TO_TW.convert(name)
        if lang == "tw":
            curr_data_family["g_tw"] = family_name
            curr_data_name["g_tw"] = name
            curr_data_family["g_tw_cn"] = TW_TO_CN.convert(family_name)
            curr_data_name["g_tw_cn"] = TW_TO_CN.convert(name)
        if lang == "th":
            curr_data_family["g_th"] = family_name
            curr_data_name["g_th"] = name
        if lang == "zh":
            curr_data_family["c_zh"] = family_name
            curr_data_name["c_zh"] = name
            curr_data_family["c_zh_tw"] = CN_TO_TW.convert(family_name)
            curr_data_name["c_zh_tw"] = CN_TO_TW.convert(name)


result2 = OrderedDict()
# write
os.makedirs(get_path_based_on_repopath("data/common/schale_stu"), exist_ok=True)
shutil.rmtree(get_path_based_on_repopath("data/common/schale_stu"))
os.makedirs(get_path_based_on_repopath("data/common/schale_stu"), exist_ok=True)
for (i, j) in result.items():
    if len(list(j["Profile"].keys())) == 0:
        # 如果是空的
        continue
    try:
        temp = list(j["Name"].keys())
        if len(temp) != 0 and j["Name"][temp[0]] == "LocalizeError":
            continue
    except Exception:
        continue

    # 写入第二份文件
    result2[str(i)] = {
        "Id": j["Id"],
        "FamilyName": j["FamilyName"],
        "Name": j["Name"]
    }

    # 正式写入文件
    with open(get_path_based_on_repopath(f"data/common/schale_stu/{i}.json"), "w", encoding="UTF-8") as f:
        json.dump(result[i], f, ensure_ascii=False, indent=2)

with open(get_path_based_on_repopath("data/common/index_stu.json"), "w", encoding="UTF-8") as f:
    json.dump(result2, f, ensure_ascii=False, indent=2)
