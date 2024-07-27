import json
import copy

from tool.tool import get_path_based_on_repopath


# index_scenario_i18n_main.json
STORY_I18N_INDEX = {}
# i18n_main_index.json
I18N_KEY = {}

def walk_tree(tree, tree_id: list, story_typename: str):
    for entry in tree:
        tree_id_copy = copy.deepcopy(tree_id)
        tree_id_copy.append(entry["id"])

        I18N_KEY[entry["name"]] = -1
        I18N_KEY[entry["desc"]] = -1

        if entry["type"] == "parent":
            walk_tree(entry["data"], tree_id_copy, story_typename)
        elif entry["type"] == "child":
            story_ids = entry["data"]
            for (idx, story_id) in enumerate(story_ids, 1):
                key_name = f'[STORY_{story_typename.upper()}_{"_".join(tree_id_copy)}_{idx}_NAME]'
                key_desc = f'[STORY_{story_typename.upper()}_{"_".join(tree_id_copy)}_{idx}_DESC]'

                I18N_KEY[key_name] = -1
                I18N_KEY[key_desc] = -1
                STORY_I18N_INDEX[str(story_id)] = [key_name, key_desc]
        else:
            raise ValueError(entry["type"])


if __name__ == '__main__':
    with open(get_path_based_on_repopath("data/common/index_scenario_manifest_main.json"), "r", encoding="utf") as f:
        CONTENT = json.load(f)
    walk_tree(CONTENT["main"], [], "main")
    walk_tree(CONTENT["side"], [], "side")
    walk_tree(CONTENT["short"], [], "short")

    with open(get_path_based_on_repopath("data/common/index_scenario_i18n_main.json"), "w", encoding="utf") as f:
        json.dump(STORY_I18N_INDEX, f, ensure_ascii=False, indent=2)

    with open(get_path_based_on_repopath("data/story/i18n/i18n_main_index.json"), "r", encoding="utf") as f:
        temp = json.load(f)
    I18N_KEY.update(temp)
    with open(get_path_based_on_repopath("data/story/i18n/i18n_main_index.json"), "w", encoding="utf") as f:
        json.dump(I18N_KEY, f, ensure_ascii=False, indent=2)

