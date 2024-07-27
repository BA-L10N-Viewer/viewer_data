import json
import os
import shutil
from collections import OrderedDict

from functools import partial

from tool.tool import get_path_based_on_repopath
from pydantic import BaseModel

OPTION_TEXT_COLOR = ["#4EA24E", "#59ADF8", "#FF3333",
                     "#FF7800", "#800000"]


class NexonStoryData(BaseModel):
    SelectionGroup: int
    SelectionToGroup: int = -1
    PopupFileName: str

    Message: dict
    CharacterId: int = -1
    DataType: str
    Script: str

    BGMId: int
    Sound: str
    BGName: int

    ShowTextColor: str = "black"
    RelatedEntry: list = list()


BASE_DATA_DIR = get_path_based_on_repopath("data/_temp/story/normal")
get_story_path = partial(os.path.join, BASE_DATA_DIR)

os.makedirs(get_path_based_on_repopath(f"data/story/normal"), exist_ok=True)
shutil.rmtree(get_path_based_on_repopath(f"data/story/normal"))
os.makedirs(get_path_based_on_repopath(f"data/story/normal"), exist_ok=True)
for filename in os.listdir(BASE_DATA_DIR):
    filepath = get_story_path(filename)

    with open(filepath, "r", encoding="utf") as f:
        DATA = json.load(f)
    PROCESSED = []

    '''
    def fuck_nested_option(pos_, option_dict=None, depth=0):
        """
        cnm 嵌套对话选项及回答是吧，我neng死你
        :param option_list: 相当于 curr_option
        :param pos_: 相当于 pos
        :param depth: 主要是用来控制
        :return: 返回需要加进去的entry
        """
        # 选项检测
        pos2 = pos_
        curr_option = OrderedDict() if not option_dict else option_dict

        # 存储所有option（最多三个还是多少来着）
        for i in range(5):
            if pos2 >= len(DATA):
                raise IndexError("wtf is this shit")

            entry2 = NexonStoryData(**DATA[pos2])
            if entry2.DataType != "option":
                break
            curr_option[str(entry2.SelectionToGroup)] = entry2
            curr_option[str(entry2.SelectionToGroup)].RelatedEntry = []

            pos2 += 1

            # print("save option", pos2, i, entry2)
        # 存储所有option对应的回答
        while True:
            if pos2 >= len(DATA):
                break

            entry2 = NexonStoryData(**DATA[pos2])
            if entry2.SelectionGroup == 0:
                break
            elif entry2.SelectionToGroup != -1:
                # 嵌套问题
                print(entry2)
                pos2, _ = fuck_nested_option(pos2, curr_option, depth=depth + len(list(curr_option.keys())))
                print(_)
                curr_option[str(entry2.SelectionGroup)].RelatedEntry.extend(_.values())
            else:
                curr_option[str(entry2.SelectionGroup)].RelatedEntry.append(entry2.RelatedEntry)

            pos2 += 1

            # print("link option")
        # 设定对话颜色
        check_result = []
        for i in curr_option.values():
            if len(i.RelatedEntry) == 0:
                check_result.append(True)
        # 只有一个回答？那就全部黑字
        if len(curr_option.keys()) == 1:
            check_result = [True]
            # 强制向前再进一个，抵消下面的减去
            # 主要是因为有的是一个问句，而问句下面没有回答
            pos2 += 1
        if all(check_result):
            # 默认黑字
            pass
        else:
            for (idx, option) in enumerate(curr_option.values()):
                color = OPTION_TEXT_COLOR[(depth + idx) % len(OPTION_TEXT_COLOR)]
                option.ShowTextColor = color
                for _ in option.RelatedEntry:
                    _.ShowTextColor = color

        return pos2, curr_option
    '''


    def fuck_nested_option(pos_, existed_option=None, parent_option=None, depth=0):
        # 记录当前pos
        pos2 = pos_
        existed_option = existed_option if existed_option is not None else OrderedDict()
        parent_option = parent_option

        curr_option = OrderedDict()

        # 向下检索相关option
        for i in range(5):
            if pos2 >= len(DATA):
                break

            entry2 = NexonStoryData(**DATA[pos2])
            if entry2.DataType != "option":
                break
            curr_option[str(entry2.SelectionToGroup)] = entry2
            curr_option[str(entry2.SelectionToGroup)].RelatedEntry = []

            # print("fdsjifjds", entry2.Message["g_tw"])

            pos2 += 1

        # 检索option的相关回答
        while True:
            if pos2 >= len(DATA):
                break

            entry2 = NexonStoryData(**DATA[pos2])
            if entry2.SelectionGroup == 0:
                # 说明这个时候分支结束
                break
            elif entry2.SelectionToGroup != -1:
                if str(entry2.SelectionGroup) not in curr_option:
                    break

                pos2 = fuck_nested_option(pos2, curr_option, curr_option[str(entry2.SelectionGroup)],
                                          depth=depth + len(list(curr_option.keys())))
            else:
                if str(entry2.SelectionGroup) in curr_option:
                    curr_option[str(entry2.SelectionGroup)].RelatedEntry.append(entry2)
                else:
                    # 说明拐到前一个option的回答了
                    break

            pos2 += 1

        # 将子option加到父option上
        if parent_option is None:
            #TODO
            pass
        else:
            if len(list(curr_option.values())) != 0:
                for i in list(curr_option.values()):
                    parent_option.RelatedEntry.append(i)
                    # print("pppppp", i.Message["g_tw"])
                    # print("pppppppppppp", parent_option.RelatedEntry[-1])

        # 设定对话颜色
        # print(depth)
        check_result = []
        for i in curr_option.values():
            if len(i.RelatedEntry) == 0:
                check_result.append(True)
            else:
                check_result.append(False)
        # 只有一个回答？那就全部黑字
        if len(curr_option.keys()) == 1:
            check_result = [True]
            # 强制向前再进一个，抵消下面的减去
            # 主要是因为有的是一个问句，而问句下面没有回答
            pos2 += 1
        if all(check_result):
            # print(check_result)
            # 默认黑字
            pass
        else:
            for (idx, option) in enumerate(curr_option.values()):
                color = OPTION_TEXT_COLOR[(depth + idx) % len(OPTION_TEXT_COLOR)]
                # print(color)
                option.ShowTextColor = color
                for _ in option.RelatedEntry:
                    _.ShowTextColor = color

        if depth != 0:
            return pos2
        else:
            return pos2, curr_option


    pos = 0
    while pos < len(DATA):
        entry = DATA[pos]
        temp = NexonStoryData(**entry)
        if temp.DataType != "option" or temp.SelectionToGroup == -1:
            pos += 1

            PROCESSED.append(temp)
        else:
            pos2, curr_option = fuck_nested_option(pos)


            def insert_option(curr_option):
                # 广度优先
                if isinstance(curr_option, dict):
                    items = curr_option.values()
                elif isinstance(curr_option, list):
                    items = curr_option
                else:
                    raise TypeError(curr_option)

                PROCESSED.extend(items)
                for option in items:
                    option_related = option.RelatedEntry
                    PROCESSED.extend(option_related)
                    for related_entry in option_related:
                        if len(related_entry.RelatedEntry) != 0:
                            insert_option(related_entry.RelatedEntry)


            # 插入回答
            insert_option(curr_option)

            pos = pos2 - 1

    # 写入回去
    with open(get_path_based_on_repopath(f"data/story/normal/{filename}"), "w", encoding="utf") as f:
        print(filename)
        json.dump([i.model_dump(exclude={"RelatedEntry"}) for i in PROCESSED if not isinstance(i, list)],
                  f, ensure_ascii=False, indent=2)
