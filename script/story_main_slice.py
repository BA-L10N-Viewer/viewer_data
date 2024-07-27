import json
import os
import re
import shutil
import traceback
from collections import OrderedDict

import opencc
import xxhash

from pydantic import BaseModel
from tool.tool import get_path_based_on_repopath

TW_TO_CN = opencc.OpenCC("tw2sp.json")

YOLO_THE_SHITTY_OPTION = True


# ----------------------------------------------------
# Nexon Story Data Model
class NexonStoryI18nData(BaseModel):
    j_ja: str
    j_ko: str
    g_ja: str
    g_ko: str
    g_en: str
    g_th: str
    g_tw: str
    g_tw_cn: str
    c_cn: str = "[cn not found]"
    c_cn_tw: str = "[cn not found]"


class NexonStoryData(BaseModel):
    SelectionGroup: int
    SelectionToGroup: int = -1
    PopupFileName: str

    Message: NexonStoryI18nData
    CharacterId: int = -1
    DataType: str
    Script: str

    BGMId: int
    Sound: str
    BGName: int


# ----------------------------------------------------


# ----------------------------------------------------
# Nexon Story Script Tool
class ScriptKrRegex:
    # 标题名（标题/小标题）
    # group(1) - Title
    # group(2) - Subtitle
    title = re.compile(r"#title;([^;\n]+);?([^;\n]+)?;?", re.I)
    # 场景名
    # group(1) - Text
    place = re.compile(r"#place;([^;\n]+);?", re.I)
    # 旁白
    # group(1) - Character  |  Text
    # group(2) - Text
    na = re.compile(r"#na;([^;\n]+);?([^;\n]+)?;?", re.I)
    # 说话
    # group(2) - Character
    # group(4) - text
    speaker = re.compile(r"^(?!#)([1-5]);([^;\n]+);([^;\n]+);?([^;\n]+)?", re.I)
    # st
    # group(4) - Text
    st = re.compile(r"#st;(\[-?\d+,-?\d+]);(serial|instant|smooth);(\d+);?(.+)?", re.I)
    # stm
    # group(3) - Text
    stm = re.compile(r"#stm;(\[0,-?\d+]);(serial|instant|smooth);(\d+);([^;\n]+);?", re.I)
    # option
    # group(1) - SelectionGroupId
    # group(2) - Text
    option = re.compile(r"\[n?s(\d{0,2})?]([^;\n]+)")
    # nextepisode
    # group(1) - Title
    # group(2) - Subtitle
    nextEpisode = re.compile(r"#nextepisode;([^;\n]+);([^;\n]+);?", re.I)


class ScriptKrBbcodeRegex:
    # log
    # group(1) - character
    # group(2) - text
    log = re.compile(r'\[log=?(.*?)?](.*?)\[\/log]', re.I)

    @staticmethod
    def func_log(match):
        character_id = match.group(1) if match.group(1) else ''
        text = match.group(2) if match.group(2) else ''
        return f"<cmd-char>{character_id}</cmd-char>{text}"

    # ruby
    # group(1) - ruby target
    # group(2) - raw text
    # HTML code: `<ruby>{group(2)}<rp>(</rp><rt>{group(1)}</rt><rp>)</rp> </ruby>`
    ruby = re.compile(r'\[ruby=(.*?)](.*?)\[\/ruby]', re.I)

    @staticmethod
    def func_ruby(match):
        ruby_target = match.group(1) if match.group(1) else ''
        raw_text = match.group(2) if match.group(2) else ''
        return f'<ruby>{raw_text}<rp>(</rp><rt>{ruby_target}</rt><rp>)</rp></ruby>'

    # b (bold)
    # group(1) - text
    b = re.compile(r'\[b](.*?)\[\/b]', re.I)

    @staticmethod
    def func_b(match):
        text = match.group(1) if match.group(1) else ''
        return f'<b>{text}</b>'

    # i (斜体)
    # group(1) - text
    i = re.compile(r'\[i](.*?)\[\/i]', re.I)

    @staticmethod
    def func_i(match):
        text = match.group(1) if match.group(1) else ''
        return f'<i>{text}</i>'

    # color
    # group(1) - color (#ffffff)
    # group(2) - text
    color = re.compile(r'\[([a-fA-F0-9]{6})](.*?)\[-]')

    @staticmethod
    def func_color(match):
        color = match.group(1) if match.group(1) else ''
        text = match.group(2) if match.group(2) else ''
        return f'<font color="{color}">{text}</font>'


class ScriptKrTool:
    @staticmethod
    def convert_to_json(text: str):
        regex = ScriptKrBbcodeRegex

        result = regex.log.sub(regex.func_log, text)
        result = regex.ruby.sub(regex.func_ruby, result)
        result = regex.b.sub(regex.func_b, result)
        result = regex.i.sub(regex.func_i, result)
        result = regex.color.sub(regex.func_color, result)

        return result

    @staticmethod
    def extract_text(text: str):
        regex = ScriptKrRegex

        result = regex.title.search(text)
        if result:
            temp = f'<span class="scenario-cmd-title">{result.group(1)}</span>'
            if result.group(2):
                temp += f'<br/><span class="scenario-cmd-title">{result.group(2)}</span>'

            return ["title", [temp.replace("#n", "<br/>")]]

        result = regex.place.search(text)
        if result:
            temp = [str(result.group(1)).replace("#n", "<br/>")]

            return ["place", temp]

        result = regex.na.search(text)
        if result:
            if result.group(2):
                temp = [result.group(1), str(result.group(2)).replace("#n", "<br/>")]
            else:
                temp = ["-1", str(result.group(1)).replace("#n", "<br/>")]

            return ["na", temp]

        result = regex.speaker.search(text)
        if result:
            if not result.group(4):
                raise ValueError

            temp = [result.group(2) if result.group(2) else -1,
                    str(result.group(4)).replace("#n", "<br/>")]

            return ["speaker", temp]

        result = regex.st.search(text)
        if result:
            temp = [str(result.group(3)).replace("#n", "<br/>")]
            return ["st", temp]

        result = regex.stm.search(text)
        if result:
            temp = [str(result.group(4)).replace("#n", "<br/>")]
            return ["stm", temp]

        result = regex.option.search(text)
        if result:
            temp = [result.group(1) if result.group(1) else "-1",
                    str(result.group(2)).replace("#n", "<br/>")]
            return ["option", temp]

        result = regex.nextEpisode.search(text)
        if result:
            temp = f'<span class="scenario-cmd-next-episode">{result.group(1)}</span>'
            if result.group(2):
                temp += f'<br/><span class="scenario-cmd-next-episode">{result.group(2)}</span>'

            return ["nextEpisode", [temp.replace("#n", "<br/>")]]

        raise ValueError(text)

    @staticmethod
    def split_script(script: str):
        temp = script.split("\n")
        result = []
        for i in temp:
            try:
                result.append(ScriptKrTool.extract_text(i))
            except ValueError:
                pass
        return result


def convert_to_lang(entry: dict, script_kr: str, data_type: str):
    def convert2(text):
        temp = text.split(";")
        if data_type == "title":
            result = f'<span class="scenario-cmd-title">{temp[0]}</span>'
            if len(temp) == 2:
                result += f'<br/><span class="scenario-cmd-title">{temp[1]}</span>'
            return result
        elif data_type == "nextEpisode":
            result = f'<span class="scenario-cmd-next-episode">{temp[0]}</span>'
            if len(temp) == 2:
                result += f'<br/><span class="scenario-cmd-next-episode">{temp[1]}</span>'
            return result
        else:
            result = text

        return result.replace("#n", "<br/>")

    convert = lambda i: convert2(ScriptKrTool.convert_to_json(i))
    return NexonStoryI18nData(
        **{"j_ja": convert(entry.get("TextJp")), "j_ko": convert(script_kr),
           "g_ja": convert(entry.get("TextJpG", "")), "g_ko": convert(script_kr),
           "g_en": convert(entry.get("TextEn", "")), "g_th": convert(entry.get("TextTh", "")),
           "g_tw": convert(entry.get("TextTw", "")), "g_tw_cn": TW_TO_CN.convert(convert(entry.get("TextTw", "")))}
    )


def get_option(text):
    text = re.sub(r'(\[.*?\])', lambda match: match.group(1).replace(" ", ""), text)

    temp = ScriptKrTool.split_script(text)
    result = OrderedDict()
    for i in temp:
        if i[0] == "option":
            # 只处理存在选择的（[s数字]）
            # 只处理例如 [s]xxxx 这种
            # 必须要有前置数据
            if "[s" in text and i[1][0] == "-1" and len(result.keys()) != 0:
                result[str(int(list(result.keys())[0]) + 1)] = i[1][-1]
            elif i[1][0] not in result:
                result[i[1][0]] = i[1][-1]
            else:
                result[str(int(i[1][0])+1)] = i[1][-1]

    # print(result)
    return result


# ----------------------------------------------------

# ----------------------------------------------------
# Main Script
# ----------------------------------------------------
with open(get_path_based_on_repopath("data/_temp/story.json"), "r", encoding="utf-8") as f:
    STORY_RAW = json.load(f)
STORY_PROCESSED = {}

for (story_id, data) in STORY_RAW.items():
    if story_id not in STORY_PROCESSED:
        STORY_PROCESSED[story_id] = []
    curr_story = STORY_PROCESSED[story_id]

    for entry in data:
        temp = ScriptKrTool.split_script(entry["ScriptKr"])
        for (index, entry_part) in enumerate(temp):
            entry_obj = NexonStoryData(
                SelectionGroup=entry["SelectionGroup"],
                PopupFileName=entry["PopupFileName"],

                Message=convert_to_lang(entry, entry_part[1][-1], entry_part[0]),
                DataType=entry_part[0],
                Script=entry["ScriptKr"].replace("\n", "\\n"),

                BGMId=entry["BGMId"],
                Sound=entry["Sound"],
                BGName=entry["BGName"],
            )

            # 将speaker和na的CharacterId更改
            if entry_part[0] == "speaker" or entry_part[0] == "na":
                entry_obj.CharacterId = "-1" if not entry_part[1][0] else xxhash.xxh32_intdigest(entry_part[1][0])
            # 将带人名的na转为speaker
            if entry_part[0] == "na" and (entry_part[1][0] != "" or entry_part[1][0] != -1):
                entry_obj.DataType = "speaker"
            # 对option的特殊处理
            if entry_part[0] == "option":
                entry_obj.SelectionToGroup = int(entry_part[1][0])
                # print(entry["ScriptKr"])

                # 自己查 `너희는 그때의……?` 关键词
                temp114514 = {}
                for (key, value) in entry.items():
                    if "Text" in key:
                        if value == '':
                            print("Exception: value is null but is still being processed", story_id)
                            continue

                        temp114515 = get_option(value)
                        if entry_part[1][0] not in temp114515.keys():
                            if YOLO_THE_SHITTY_OPTION:
                                temp114514[key] = temp114515[list(temp114515.keys())[index]]
                            else:
                                raise KeyError(temp114514, entry_part[1][0])
                        else:
                            temp114514[key] = temp114515[entry_part[1][0]]

                entry_obj.Message = convert_to_lang(temp114514, entry_part[1][-1], entry_part[0])

            # 转换为NexonStoryI18nData
            curr_story.append(entry_obj)

# export
os.makedirs(get_path_based_on_repopath("data/_temp/story/normal"), exist_ok=True)
shutil.rmtree(get_path_based_on_repopath("data/_temp/story/normal"))
os.makedirs(get_path_based_on_repopath("data/_temp/story/normal"), exist_ok=True)
for (story_id, data) in STORY_PROCESSED.items():
    with open(get_path_based_on_repopath(f"data/_temp/story/normal/{story_id}.json"), mode="w", encoding="utf-8") as f:
        json.dump([i.model_dump() for i in data],
                  f, ensure_ascii=False, indent=2)
