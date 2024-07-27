# Script for Manually used

## 自动填充区间内的i18n key编码
- 文件 `i18n_auto_find_and_fill.py`
- 使用方法
  - 部分填充一个JSON，如 `data/story/i18n/i18n_event_index.json` 这个
  - 修改Python脚本，更改或新增函数调用中的文件路径/文件名

## 基于i18n key自动提取需要的对应数据
- 文件 `generate_story_i18n.py`

## 对主要故事的数据i18n index填充
- 文件 `generate_i18n_index_story_main.py`
- 使用方法
  - 更新 `data/common/index_scenario_manifest_main.py`
  - 自动生成 `index_scenario_i18n_main.py` 与 `i18n_main_index.json` 两个文件