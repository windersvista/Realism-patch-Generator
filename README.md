# EFT 现实主义MOD兼容补丁生成器 使用说明

## 版本信息
- **当前版本**: 1.3
- **更新日期**: 2026年2月20日
- **版本状态**: ✅ 稳定版

### 最新更新 (v1.3)
- ✅ **子弹数据支持**: 现在支持识别和生成子弹补丁（parentId: 5485a8684bdc2da71d8b4567）
- ✅ **子弹属性提取**: 自动提取Damage、PenetrationPower、InitialSpeed等属性
- ✅ **独立补丁文件**: 子弹补丁单独保存为ammo_realism_patch.json

### 历史更新 (v1.2)
- ✅ **VIR格式支持**: 现在支持VIR_items.json等使用 `{item: {...}, isweapon: bool}` 结构的文件
- ✅ **智能格式检测**: 自动识别STANDARD和VIR两种数据格式
- ✅ **扩展parentId映射**: 添加更多物品类别支持，减少处理失败

### 历史更新 (v1.1)
- ✅ **完整配件数据结构**: 现在生成的配件补丁包含所有类型特有属性
- ✅ **智能类型识别**: 根据配件类型自动添加相应的专有属性
- ✅ **完整属性保留**: 从模板复制时保留所有原始属性
- 📄 详细更新说明请查看 [配件数据结构更新说明.md](配件数据结构更新说明.md)

## 简介
这是一个用于生成《逃离塔科夫》(Escape from Tarkov) 现实主义MOD (Realism Mod) 兼容补丁的Python脚本。它可以根据Items文件夹中的武器、配件和子弹数据，自动生成相应的现实主义MOD配置文件。

## 文件结构
```
现实主义补丁生成用/
├── generate_realism_patch.py     # 主脚本
├── Items/                         # 待生成补丁的物品数据文件夹
│   ├── WeaponXXX.json            # 武器数据文件
│   ├── Attachment_XXX.json       # 配件数据文件
│   └── ...
├── weapons/                       # 武器模板文件夹
│   ├── AssaultRifleTemplates.json
│   ├── PistolTemplates.json
│   └── ...
├── attatchments/                  # 配件模板文件夹
│   ├── ScopeTemplates.json
│   ├── MagazineTemplates.json
│   └── ...
└── output/                        # 输出文件夹（自动创建）
    ├── weapons_realism_patch.json         # 武器补丁
    ├── attachments_realism_patch.json     # 配件补丁
    ├── ammo_realism_patch.json            # 子弹补丁
    └── all_items_realism_patch.json       # 合并的完整补丁
```

## 使用方法

### 1. 准备环境
确保已安装Python 3.6或更高版本。

### 2. 准备数据文件
将需要生成补丁的物品数据JSON文件放入 `Items/` 文件夹中。

### 3. 运行脚本
在命令行中执行：
```bash
python generate_realism_patch.py
```

或者直接双击 `generate_realism_patch.py` 文件运行。

### 4. 查看结果
脚本运行完成后，会在 `output/` 文件夹中生成四个JSON文件：
- **weapons_realism_patch.json**: 只包含武器的补丁
- **attachments_realism_patch.json**: 只包含配件的补丁
- **ammo_realism_patch.json**: 只包含子弹的补丁
- **all_items_realism_patch.json**: 包含所有物品的完整补丁

## 工作原理

### 1. 数据格式支持
脚本支持两种物品数据格式：

#### STANDARD格式 (标准格式)
```json
{
  "itemId": {
    "parentId": "5447b5cf4bdc2d65278b4567",
    "overrideProperties": {...},
    "itemTplToClone": "..."
  }
}
```

#### VIR格式 (虚拟物品格式)
```json
{
  "itemId": {
    "item": {
      "_id": "itemId",
      "_name": "item_name",
      "_parent": "5447b5cf4bdc2d65278b4567",
      "_props": {...}
    },
    "isweapon": true,  // 可选字段
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
