# Realism Patch Generator 架构

## 概览
`generate_realism_patch.py` 会处理 `input/` 中的 JSON 物品定义，并将规范化后的 Realism 补丁写入 `output/`，同时保留源目录结构。

处理流水线：
1. 从 `现实主义物品模板/` 加载模板。
2. 构建内存模板索引（`template_by_id`），以支持 O(1) 查询。
3. 将每个输入物品解析为规范化的 `ItemInfo`。
4. 在适用时分派格式专用处理器（`TEMPLATE_ID`、`CURRENT_PATCH`、`CLONE`）。
5. 对其他格式执行通用的构建/收尾/存储流程。
6. 按源文件分组导出补丁。

## 核心数据类型
- `ItemInfo`：在解析器与补丁流水线中使用的规范化物品元数据。
- `PatchData`：可变补丁对象（`Dict[str, Any]`）。
- `JsonObject`：原始 JSON 对象（`Dict[str, Any]`）。

## 主要组件
- 格式检测与解析：
  - `detect_item_format`
  - `extract_item_info`
  - `_extract_*_info` 辅助函数
- 补丁生成：
  - `_build_patch_for_parent_type`
  - `create_default_*_patch`
- 规则应用与合理性检查：
  - `apply_realism_sanity_check`
  - `_infer_weapon_profile`、`_infer_mod_profile`
- 处理编排：
  - `process_single_item`
  - `_dispatch_format_specific_item`
  - `_resolve_parent_id_for_processing`
  - `_build_finalize_and_store_primary_patch`
- 导出：
  - `_save_source_grouped_patches`
  - `save_patches`

## 设计说明
- 行为策略以兼容性优先：支持多种历史输入模式。
- 规则推断会优先使用显式标识符（`parent_id`、`ModType`），再回退到名称匹配。
- 热路径中使用的正则表达式会在模块级预编译。

## 安全扩展点
- 新增输入模式：
  - 扩展 `detect_item_format`。
  - 添加专用的 `_extract_*_info` 解析器。
  - 可选接入专门的分派处理器。
- 新增 Realism 规则集：
  - 在 `weapon_rule_ranges.py` 或 `attachment_rule_ranges.py` 中扩展范围表。
  - 在 `apply_realism_sanity_check` 中保留最终防护边界。

## 非目标
- 此脚本不会在补丁级合理性约束之外，尝试完整验证外部模组的正确性。
- 此脚本不会保留历史聚合输出；输出按源文件路径组织。
