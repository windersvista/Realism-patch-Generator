# EFT 现实主义MOD兼容补丁生成器

## 📋 项目概述

**EFT 现实主义MOD兼容补丁生成器 v2.0** 是一个功能强大的Python脚本，用于为《逃离塔科夫》(Escape from Tarkov) 现实主义MOD (Realism Mod) 自动生成兼容补丁。它可以根据Items文件夹中的物品数据，使用预定义的模板快速生成规范化的配置文件。

## 🎯 核心特性

- ✅ **多格式支持**: 同时支持 `TEMPLATE_ID`、`VIR`、`CLONE`、`STANDARD`、`ItemToClone` 5种数据格式
- ✅ **智能格式检测**: 自动识别输入数据格式，无需手动指定
- ✅ **递归文件扫描**: 自动处理Items文件夹及其所有子文件夹中的JSON文件
- ✅ **完整属性支持**: 为各类物品保留并生成完整的现实主义MOD属性
- ✅ **模板库管理**: 内置丰富的物品模板库，涵盖武器、配件、装备等多种类型
- ✅ **灵活组合输出**: 支持按物品类型分类输出或合并输出单一文件

## 📊 版本历史

| 版本 | 日期 | 主要更新 |
|------|------|---------|
| **v2.0** | 2026-02-20 | 📌 **ItemToClone格式支持** - 支持新的物品引用格式，HandbookParent智能映射，常量前缀识别 |
| v1.9 | 2026-02-20 | 递归文件夹扫描 |
| v1.8 | 2026-02-20 | Clone链递归处理、enable字段检查 |
| v1.7 | 2026-02-20 | 消耗品模板支持、TacticalCombo类型识别 |
| v1.6 | 2026-02-20 | 模板路径迁移、ammo和gear模板、TemplateID格式 |
| v1.5-v1.0 | 2026-02-20 | 基础功能开发 |

## 📁 项目结构

```
Realism-patch-Generator/
├── generate_realism_patch.py              # 🚀 主程序脚本
├── 运行补丁生成器.bat                      # 快速启动脚本（Windows）
├── Items/                                  # 📥 输入目录 - 待处理的物品数据
│   ├── weapon_data_1.json
│   ├── attachments_data_1.json
│   └── ...（支持子文件夹）
├── 现实主义物品模板/                       # 📘 模板库
│   ├── weapons/
│   │   ├── AssaultRifleTemplates.json
│   │   ├── PistolTemplates.json
│   │   └── ...
│   ├── attachments/
│   │   ├── ScopeTemplates.json
│   │   ├── MagazineTemplates.json
│   │   └── ...
│   ├── ammo/
│   ├── gear/
│   └── consumables/
├── output/                                 # 📤 输出目录（自动创建）
│   ├── all_items_realism_patch.json       # ⭐ 完整补丁（推荐使用）
│   ├── weapons_realism_patch.json          # 武器补丁
│   ├── attachments_realism_patch.json      # 配件补丁
│   ├── ammo_realism_patch.json             # 弹药补丁
│   └── consumables_realism_patch.json      # 消耗品补丁（可选）
└── 📚 文档
    ├── README.md                          # 本文件
    ├── 快速入门.md
    ├── 高级配置指南.md
    └── v2.0更新说明.md
```

## 🚀 快速开始

### 步骤 1️⃣：安装环境要求
- **Python 3.6 或更高版本** 已安装
- 无需额外的依赖包（仅使用Python标准库）

### 步骤 2️⃣：准备物品数据
将待生成补丁的物品JSON文件放入 `Items/` 文件夹：
- 可以直接放在 `Items/` 目录根部
- 也可以放在 `Items/` 的子目录中（会自动递归扫描）
- 支持多个文件和任意目录层级

### 步骤 3️⃣：运行生成器
选择以下任一方式运行：

**方式A - Windows批处理（推荐）**
```bash
双击 运行补丁生成器.bat
```

**方式B - 命令行**
```bash
python generate_realism_patch.py
```

**方式C - Python IDE**
- 在VS Code、PyCharm等IDE中直接运行脚本

### 步骤 4️⃣：获取生成的补丁
运行完成后，在 `output/` 文件夹中查看结果：
- 📌 **all_items_realism_patch.json** - 包含所有物品的完整补丁（推荐选择此文件使用）
- weapons_realism_patch.json - 仅包含武器补丁
- attachments_realism_patch.json - 仅包含配件补丁
- ammo_realism_patch.json - 仅包含弹药补丁

## 📋 使用方法详解

### 输入数据格式

脚本支持5种物品数据格式，会自动识别：

#### 1️⃣ **ITEMTOCLONE 格式** （v2.0新增）
```json
{
  "item_id": {
    "ItemToClone": "ASSAULTRIFLE_AK74",
    "OverrideProperties": {
      "Accuracy": 0.5
    },
    "Handbook": {
      "HandbookParent": "AssaultRifles",
      "Price": 50000
    }
  }
}
```

#### 2️⃣ **STANDARD 格式**（推荐）
```json
{
  "item_id": {
    "parentId": "5447b5cf4bdc2d65278b4567",
    "overrideProperties": {
      "Accuracy": 0.5
    }
  }
}
```

#### 3️⃣ **VIR 格式**
```json
{
  "item_id": {
    "item": {
      "_id": "item_id",
      "_parent": "5447b5cf4bdc2d65278b4567",
      "_props": {...}
    }
  }
}
```

#### 4️⃣ **CLONE 格式**
```json
{
  "item_id": {
    "clone": "template_id",
    "overrideProperties": {...}
  }
}
```

#### 5️⃣ **TEMPLATE_ID 格式**
```json
{
  "item_id": "template_id"
}
```

### 智能特性

#### ✨ ItemToClone 常量前缀识别 （v2.0新增）
脚本可以通过常量名称前缀自动推断物品类型：

- **武器前缀**: `ASSAULTRIFLE_`、`RIFLE_`、`SNIPER`、`SHOTGUN_`、`SMG_`、`PISTOL_`、`MACHINEGUN_`、`GRENADELAUNCHER_`
- **配件前缀**: `MAGAZINE_`、`RECEIVER_`、`BARREL_`、`STOCK_`、`HANDGUARD_`、`GRIP_`、`SIGHT_`、`SCOPE_`、`SUPPRESSOR_`、`MOUNT_`...
- **装备前缀**: `ARMOR_`、`HELMET_`、`HEADPHONES_`、`FACECOVER_`...
- **其他前缀**: `AMMO_`、`CONTAINER_`、`KEY_`、`INFO_`...

#### 🔍 HandbookParent 映射 （v2.0新增）
支持通过 `Handbook.HandbookParent` 字段推断物品类型：

**武器类型**: AssaultRifles, Handguns, MachineGuns, SniperRifles, Shotguns, SMGs 等  
**配件类型**: Magazines, Sights, Scopes, Stocks, Barrels, Suppressors, Grips 等  
**装备类型**: Armor, Backpacks, ChestRigs, Headwear, FaceCover 等

#### 🔄 Clone 链递归处理 （v1.8支持）
支持链式Clone引用，脚本会自动递归解析并继承属性。

#### 📂 递归文件夹扫描 （v1.9支持）
Items文件夹中的所有JSON文件都会被自动发现和处理，包括：
- 直接放在Items/目录的文件
- 任意深度的子文件夹中的文件
    "enable": true,     // 可选字段
    "clone": "..."      // 可选字段
  }
}
```

脚本会自动检测数据格式并正确处理。

### 2. 模板匹配
脚本通过物品的 `parentId` 字段来识别物品类型，并匹配相应的模板文件：

#### 武器类型映射
- 突击步枪 → `weapons/AssaultRifleTemplates.json`
- 手枪 → `weapons/PistolTemplates.json`
- 狙击步枪 → `weapons/SniperRifleTemplates.json`
- 等等...

#### 配件类型映射
- 瞄准镜 → `attatchments/ScopeTemplates.json`
- 弹匣 → `attatchments/MagazineTemplates.json`
- 枪口装置 → `attatchments/MuzzleDeviceTemplates.json`
- 等等...

### 2. 数据生成策略

#### 武器和配件
- **精确匹配**: 如果模板中存在相同ItemID的配置，直接使用该配置
- **模板随机选择**: 如果没有精确匹配，从相同类型的模板中随机选择一个作为基础
- **默认配置**: 如果找不到合适的模板，使用预设的默认配置

#### 子弹（新增）
- 子弹无需模板文件，直接从原始数据提取属性
- 自动提取：Damage、PenetrationPower、InitialSpeed、BulletMassGram、BallisticCoeficient
- 所有子弹默认LoyaltyLevel为1，BasePriceModifier为1

### 3. 输出格式
生成的补丁文件为标准JSON格式，可以直接用于现实主义MOD。

## 生成统计示例
```
生成统计:
  武器补丁: 55 个
  配件补丁: 492 个
  子弹补丁: 3 个
  总计: 550 个
```

## 跳过的物品
以下情况的物品会被跳过：
1. 没有 `parentId` 字段的物品
2. `parentId` 未在映射表中定义的物品（如任务物品、容器等）
3. 使用自定义 `parentId` 的物品

这些被跳过的物品会在控制台输出中显示，格式如：
```
跳过 <ItemID>: 未找到匹配的模板 (parentId: <ParentID>)
```

## ParentID 映射表

### 武器类型
| ParentID | 武器类型 | 模板文件 |
|----------|---------|---------|
| 5447b5cf4bdc2d65278b4567 | 突击步枪 | AssaultRifleTemplates.json |
| 5447b5fc4bdc2d87278b4567 | 卡宾枪 | AssaultCarbineTemplates.json |
| 5447bed64bdc2d97278b4568 | 机枪 | MachinegunTemplates.json |
| 5447b6094bdc2dc3278b4567 | 精确射手步枪 | MarksmanRifleTemplates.json |
| 5447b6254bdc2dc3278b4568 | 狙击步枪 | SniperRifleTemplates.json |
| 5447b5e04bdc2d62278b4567 | 冲锋枪 | SMGTemplates.json |
| 5447b5c44bdc2d87278b4567 | 霰弹枪 | ShotgunTemplates.json |
| 5447b5e04bdc2d62278b4566 | 手枪 | PistolTemplates.json |
| 5447bedf4bdc2d87278b4568 | 榴弹发射器 | GrenadeLauncherTemplates.json |

### 配件类型
| ParentID | 配件类型 | 模板文件 |
|----------|---------|---------|
| 55818ad54bdc2ddc698b4569 | 瞄准镜 | ScopeTemplates.json |
| 55818acf4bdc2dde698b456b | 机械瞄具 | IronSightTemplates.json |
| 5448bc234bdc2d3c308b4569 | 弹匣 | MagazineTemplates.json |
| 550aa4cd4bdc2dd8348b456c | 枪口装置 | MuzzleDeviceTemplates.json |
| 55818b084bdc2d5b648b4571 | 前握把 | ForegripTemplates.json |
| 55818a684bdc2ddd698b456d | 枪托 | StockTemplates.json |
| 55818b164bdc2ddc698b456c | 手枪握把 | PistolGripTemplates.json |
| 55818a6f4bdc2db9688b456b | 护木 | HandguardTemplates.json |
| 555ef6e44bdc2de9068b457e | 枪管 | BarrelTemplates.json |
| 55818b224bdc2dde698b456f | 导轨 | MountTemplates.json |

### 子弹类型
| ParentID | 物品类型 | 处理方式 |
|----------|---------|---------|
| 5485a8684bdc2da71d8b4567 | 子弹 | 直接生成（无需模板） |

## 子弹补丁格式

子弹补丁使用简化的格式，不需要模板文件。生成的子弹补丁包含以下字段：

### 必需字段
- `$type`: "RealismMod.Ammo, RealismMod"
- `ItemID`: 子弹的唯一ID
- `Name`: 子弹名称
- `Damage`: 伤害值
- `PenetrationPower`: 穿透力
- `LoyaltyLevel`: 忠诚度等级（默认1）
- `BasePriceModifier`: 基础价格修正（默认1）

### 可选字段
- `InitialSpeed`: 初始速度（米/秒）
- `BulletMassGram`: 子弹质量（克）
- `BallisticCoeficient`: 弹道系数

### 示例
```json
{
    "6bf1974e43598ca9672d9380": {
        "$type": "RealismMod.Ammo, RealismMod",
        "ItemID": "6bf1974e43598ca9672d9380",
        "Name": "dbp191",
        "Damage": 48,
        "PenetrationPower": 48,
        "LoyaltyLevel": 1,
        "BasePriceModifier": 1,
        "InitialSpeed": 940,
        "BulletMassGram": 4,
        "BallisticCoeficient": 0.275
    }
}
```

## 自定义修改

### 添加新的ParentID映射
如果需要支持新的物品类型，可以在脚本中的 `PARENT_ID_TO_TEMPLATE` 字典中添加映射：

```python
PARENT_ID_TO_TEMPLATE = {
    # 添加新的映射
    "新的ParentID": "path/to/TemplateFile.json",
    # ...
}
```

### 修改默认模板
可以修改脚本中的 `DEFAULT_WEAPON_TEMPLATE` 和 `DEFAULT_MOD_TEMPLATE` 来调整默认配置的属性值。

## 注意事项

1. **备份数据**: 运行脚本前建议备份重要数据
2. **检查输出**: 生成补丁后，建议检查output文件夹中的JSON文件，确保格式正确
3. **模板完整性**: 确保weapons和attatchments文件夹中的模板文件完整且格式正确
4. **编码问题**: 所有JSON文件应使用UTF-8编码

## 问题排查

### 问题1: 脚本无法运行
- 检查Python版本是否为3.6+
- 确保所有必需的文件夹存在（Items, weapons, attatchments）

### 问题2: 生成的物品数量少于预期
- 检查控制台输出中的"跳过"信息
- 确认被跳过的物品的parentId是否在映射表中
- 可能需要添加新的parentId映射

### 问题3: 生成的JSON格式错误
- 检查模板文件是否为有效的JSON格式
- 确保模板文件编码为UTF-8

## 版本信息
- 版本: 1.0
- 创建日期: 2026年2月20日
- 作者: GitHub Copilot

## 许可
本脚本仅供学习和研究使用。
