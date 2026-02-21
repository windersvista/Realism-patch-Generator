# Realism Patch Generator (C# Version)
# EFT 现实主义MOD兼容性补丁生成器 (C#版)

这是一个专门为 **SPT-EFT (Single Player Tarkov)** 设计的补丁自动生成工具。它能快速解析原有 MOD 的物品 JSON 文件，并生成符合 **Realism Mod** 要求的补丁（Patch）。

## 🚀 核心功能
*   **多格式兼容**：自动兼容 `VIR`, `Standard`, `Clone`, `ItemToClone` 等多种 MOD 设计格式。
*   **智能属性提取**：自动读取枪械重量、人体工程学、后坐力等基础数值并转换。
*   **模板系统**：提供预设的现实主义武器（Rifles/Pistols/Shotguns）、弹药、医疗品、装备等模版。
*   **分类输出**：补丁文件会按物品类型自动整理到输出文件夹。

## 📁 目录说明
*   `input/`：【输入】将需要生成补丁的原始 MOD JSON 放置此处。
*   `output/`：【输出】生成后的 `Realism` 兼容补丁将存放在这里。
*   `现实主义物品模板/`：【配置】存放不同类别的属性底图（JSON），可自由调整：
    *   `weapons/`
    *   `ammo/`
    *   `gear/`
    *   `consumables/`
    *   `attatchments/`

## 🛠️ 使用步骤
1.  **准备文件**：在 `input` 文件夹内放入 MOD 的物品 JSON 数据。
2.  **启动程序**：运行 `RealismPatchGenerator.exe`。
    *   *命令行可选参数：`[input_dir] [output_dir]`*
3.  **应用补丁**：将 `output` 目录下生成的 JSON 文件，按需整合到你的 Realism Mod 配置中。

## ⚠️ 注意事项
*   生成的数值是基于模板生成的预设值（如 `VerticalRecoil`, `VisualMulti` 等），建议生成后针对个别特殊 MOD 武器进行手动微调以达到最佳平衡。
*   程序会自动过滤空 ID 物品，并尽可能识别出武器的父类 ID 进行标准化处理。

---
*Created by [GitHub Copilot]*
