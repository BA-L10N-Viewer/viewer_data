import json
import requests
import opencc

from tool.nexon_db import NexonDatabase
from tool.tool import get_path_based_on_repopath, repeat_until_its_ok

from pydantic import BaseModel


class NexonMomotalkData(BaseModel):
    GroupId: int
    Id: int
    CharacterId: int

    MessageCondition: str
    FavorScheduleId: int
    NextGroupId: int

    Message: dict
    MessageBgColor: str = "white"

    RelatedEntry: list["NexonMomotalkData"] = []


TW_TO_CN = opencc.OpenCC('tw2sp.json')

# bond info
r = repeat_until_its_ok(requests.get,
                        "https://raw.githubusercontent.com/electricgoat/ba-data/jp/Excel/AcademyFavorScheduleExcelTable.json")
r = r.json()["DataList"]

# get all scenario l10n id
bond_scenario = {}
stu_to_bond = {}
for entry in r:
    bond_scenario[entry["ScenarioSriptGroupId"]] = entry["LocalizeScenarioId"]

    char_id = str(entry["CharacterId"])
    if char_id not in stu_to_bond:
        stu_to_bond[char_id] = []
    stu_to_bond[char_id].append(entry["ScenarioSriptGroupId"])
    stu_to_bond[str(entry["ScenarioSriptGroupId"])] = char_id

# mapping l10n content
global_l10n = repeat_until_its_ok(requests.get,
                                  "https://github.com/electricgoat/ba-data/raw/global/DB/LocalizeExcelTable.json")
global_l10n = NexonDatabase(global_l10n.json()["DataList"], "Key")
jp_l10n = repeat_until_its_ok(requests.get, "https://github.com/electricgoat/ba-data/raw/jp/DB/LocalizeExcelTable.json")
jp_l10n = NexonDatabase(jp_l10n.json()["DataList"], "Key")

for (key, s_id) in bond_scenario.items():
    jp_entry_pos = jp_l10n.query_pos(s_id)
    gl_entry_pos = global_l10n.query_pos(s_id)
    pos = [[jp_entry_pos, gl_entry_pos], [jp_entry_pos + 1, gl_entry_pos + 1]]

    temp = [
        {
            "j_ja": jp_l10n.db[pos1]["Jp"],
            "j_ko": jp_l10n.db[pos1]["Kr"],
        } for [pos1, pos2] in pos
    ]
    if gl_entry_pos >= 0:
        for (i, [pos1, pos2]) in enumerate(pos):
            temp[i].update({
                "g_en": global_l10n.db[pos2]["En"],
                "g_tw": global_l10n.db[pos2]["Tw"],
                "g_tw_cn": TW_TO_CN.convert(global_l10n.db[pos2]["Tw"]),
                "g_ja": global_l10n.db[pos2]["Jp"],
                "g_ko": global_l10n.db[pos2]["Kr"],
                "g_th": global_l10n.db[pos2]["Th"]
            })

    bond_scenario[key] = temp

# writing l10n content
with open(get_path_based_on_repopath("data/story/i18n/i18n_bond.json"), "w", encoding="UTF") as f:
    json.dump(bond_scenario, f, ensure_ascii=False, indent=2)
with open(get_path_based_on_repopath("data/common/index_momo.json"), "w", encoding="UTF") as f:
    json.dump(stu_to_bond, f, ensure_ascii=False, indent=2)

# slicing the mmt
with open(get_path_based_on_repopath("data/_temp/mmt.json"), "r", encoding="UTF") as f:
    mmt_data = json.load(f)
mmt_result = {}

for entry in mmt_data:
    if str(entry["CharacterId"]) not in stu_to_bond:
        continue

    group_id = entry["GroupId"]
    char_id = str(entry["CharacterId"])
    role_sensei, role_feedback = False, False

    target_entry = NexonMomotalkData(**entry)

    if char_id not in mmt_result:
        mmt_result[char_id] = []
    if entry["MessageCondition"] == "FavorRankUp":
        mmt_result[char_id].append([])
    elif entry["MessageCondition"] == "Answer":
        role_sensei = True
    elif entry["MessageCondition"] == "Feedback":
        role_feedback = True

    curr_mmt = mmt_result[char_id][-1]

    if role_feedback:
        # 指的是强问答绑定
        curr_entry = curr_mmt[-1]
        if group_id != curr_entry.NextGroupId:
            curr_entry = curr_mmt[-2]
            if group_id != curr_entry.NextGroupId:
                curr_mmt.append(target_entry)
            else:
                curr_entry.RelatedEntry.append(target_entry)
        else:
            curr_entry.RelatedEntry.append(target_entry)
    else:
        curr_mmt.append(target_entry)

# 强故事ID绑定
for (char_id, char_data) in mmt_result.items():
    for (curr_mmt_pos, curr_mmt) in enumerate(char_data):
        temp = []

        # 当前处理到哪个entry了
        entry_cursor = 0
        while True:
            if entry_cursor >= len(curr_mmt):
                break

            entry = curr_mmt[entry_cursor]
            entry1_id, entry2_id = -1, -1
            feedback = []
            if entry.MessageCondition == "Answer":
                # 如果是回答

                # 保存指向的下一个groupid
                entry1_id = entry.NextGroupId
                # 加入既有的related entry
                feedback.append(entry.RelatedEntry)

                # 试图查询有没有第二个
                try:
                    # 获取第二个
                    entry2 = curr_mmt[entry_cursor + 1]

                    # 为什么还要判断groupid呢
                    # 这是因为美咲第三话羁绊故事里有个很抽象的对话
                    # 老师只说了一句，美咲只说了一句，然后老师又只说了一句
                    # 导致两个不同的回答被合并到一个回答的两个不同选项里了
                    if entry.GroupId == entry2.GroupId and entry2.MessageCondition == "Answer":
                        # 如果也是回答，保存id
                        entry2_id = entry2.NextGroupId
                        feedback.append(entry2.RelatedEntry)
                except IndexError:
                    # 如果是最后一句的话
                    entry2 = None
            else:
                # 不是特殊情况
                temp.append(entry)
                temp.extend(entry.RelatedEntry)
                entry_cursor += 1
                continue

            # cursor移动
            if entry2_id != -1:
                # 如果entry2_id不为0，说明肯定有两个对话entry
                entry_cursor += 2
            else:
                entry_cursor += 1

            # 加入既有answer entry
            # 假如存在第二个
            if entry2_id != -1:
                # 共同操作
                temp.append(entry)
                entry.RelatedEntry = []
                temp.append(entry2)
                entry2.RelatedEntry = []

                # 假如两个ID都一样
                if entry1_id == entry2_id:
                    entry.MessageBgColor = "white"
                    entry2.MessageBgColor = "white"
                # 假如不一样
                else:
                    entry.MessageBgColor = "green"
                    entry2.MessageBgColor = "blue"
            # 假如只有一个
            else:
                temp.append(entry)
                entry.MessageBgColor = "white"
                entry.RelatedEntry = []

            # 加入既有feedback entry
            for (i, data) in enumerate(feedback):
                for j in data:
                    if i == 0:
                        if len(feedback) > 1 and len(feedback[1]) != 0:
                            j.MessageBgColor = "green"
                        else:
                            j.MessageBgColor = "white"
                    else:
                        # 这里要判断是不是只有一个feedback，因为两个都可能指向同一个
                        # 如果是，那么全变成绿的
                        if entry1_id == entry2_id:
                            j.MessageBgColor = "white"
                        else:
                            j.MessageBgColor = "blue"
                    temp.append(j)

        char_data[curr_mmt_pos] = temp

# 映射到具体bond scenario
for (char_id, char_data) in mmt_result.items():
    # TODO: WTF is this shit
    if str(char_id) not in stu_to_bond.keys():
        continue
    if isinstance(char_id, int):
        continue

    temp = []
    for (curr_mmt_pos, curr_mmt) in enumerate(char_data):
        temp.append({
            "BondScenarioId": stu_to_bond[str(char_id)][curr_mmt_pos],
            "Data": curr_mmt
        })

    mmt_result[str(char_id)] = temp

# 转换为JSON
temp_result = {}
for (char_id, char_data) in mmt_result.items():
    for entry in char_data:
        temp = []

        for i in entry["Data"]:
            temp.append(i.model_dump())

        entry["Data"] = temp
for (char_id, char_data) in mmt_result.items():
    # TODO: WTF is this shit
    if str(char_id) not in stu_to_bond.keys():
        continue

    with open(get_path_based_on_repopath(f"data/story/momotalk/{char_id}.json"), "w", encoding="UTF") as f:
        json.dump(char_data, f, ensure_ascii=False, indent=2)
