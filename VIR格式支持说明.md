# VIR格式支持说明 (v1.2更新)

## 更新概述
现实主义MOD兼容补丁生成器 v1.2 现已支持VIR (Virtual Item Resource) 格式的物品数据文件。

## 新增功能

### 1. 多格式自动识别
脚本现在能自动检测并处理两种数据格式：

#### STANDARD格式 (原有格式)
```json
{
  "65e83a7e9d55c7e8d19844e9": {
    "parentId": "5447b5cf4bdc2d65278b4567",
    "overrideProperties": {
      "Ergonomics": 48,
      "Velocity": 0
    },
    "itemTplToClone": "5fbcc1d9016cce60e8341ab3"
  }
}
```

#### VIR格式 (新支持)
```json
{
  "f546b7974a7dd485d05db42e": {
    "item": {
      "_id": "f546b7974a7dd485d05db42e",
      "_name": "virtus",
      "_parent": "5447b5f14bdc2d61278b4567",
      "_props": {
        "Weight": 0.4,
        "Ergonomics": 48,
        "Velocity": 0,
        ...
      }
    },
    "isweapon": true,
    "enable": true,
    "handbook": {...},
    "locales": {...}
  }
}
```

### 2. 智能格式检测逻辑

脚本通过以下特征识别格式：

**VIR格式识别条件**:
- 包含 `item` 字段
- `item` 对象包含 `_id`、`_parent`、`_props` 等EFT原生结构

**STANDARD格式识别条件**:
- 包含 `parentId` 字段或 `itemTplToClone` 字段

### 3. 兼容处理

#### 武器识别
- VIR格式: 优先使用 `isweapon` 字段，如无则通过 `_parent` 判断
- STANDARD格式: 通过 `parentId` 判断

#### 属性提取
- VIR格式: 从 `item._props` 提取属性
- STANDARD格式: 从 `overrideProperties` 提取属性

#### 名称处理
- VIR格式: 使用 `item._name` 作为Name
- STANDARD格式: 使用ItemID或从模板获取

## 处理示例

### 输入 (VIR格式)
```json
{
  "0cbf94f7ef447bf2813a89ab": {
    "enable": true,
    "item": {
      "_id": "0cbf94f7ef447bf2813a89ab",
      "_name": "mcx_virtus_upper_556",
      "_parent": "55818a304bdc2db5418b457d",
      "_props": {
        "Weight": 0.246,
        "Ergonomics": 10,
        ...
      }
    }
  }
}
```

### 输出 (Realism补丁)
```json
{
  "0cbf94f7ef447bf2813a89ab": {
    "$type": "RealismMod.WeaponMod, RealismMod",
    "ItemID": "0cbf94f7ef447bf2813a89ab",
    "Name": "mcx_virtus_upper_556",
    "ModType": "mount",
    "ModMalfunctionChance": -5,
    "Accuracy": 0,
    "HeatFactor": 1,
    "CoolFactor": 1,
    "Ergonomics": 0,
    "Weight": 0.088,
    ...
  }
}
```

## 新增ParentID映射

为了支持VIR格式中常见的物品类别，v1.2添加了以下映射：

| ParentID | 物品类型 | 模板文件 |
|----------|---------|---------|
| 55818a304bdc2db5418b457d | 机匣 | ReceiverTemplates.json |
| 56ea9461d2720b67698b456f | 护木 | HandguardTemplates.json |

## 使用方法

### 1. 准备VIR格式文件
将VIR格式的物品数据文件（如 `VIR_items.json`）放入 `Items/` 文件夹：

```
现实主义补丁生成用/
├── Items/
│   ├── VIR_items.json        ← VIR格式文件
│   ├── WeaponXXX.json        ← STANDARD格式文件
│   └── ...
```

### 2. 运行脚本
无需任何改动，直接运行：
```bash
python generate_realism_patch.py
```

### 3. 查看结果
脚本会自动识别所有格式的文件并生成统一的补丁输出。

## 处理结果示例

```
============================================================
EFT 现实主义MOD兼容补丁生成器 v1.2
============================================================
正在加载模板文件...
  已加载: 26 个模板文件 (1,884 个模板)

开始生成现实主义MOD兼容补丁...

处理文件: VIR_items.json
  处理完成: 49 个物品

处理文件: WeaponAK5C.json
  处理完成: 1 个物品

生成统计:
  武器补丁: 2 个
  配件补丁: 48 个
  总计: 50 个

补丁生成完成！
```

## 混合格式处理

脚本可以在同一次运行中处理多种格式的文件：

```
Items/
├── VIR_items.json           ← VIR格式 (49个物品)
├── WeaponAK5C.json          ← STANDARD格式 (1个物品)
├── Attachment_Scopes.json   ← STANDARD格式 (15个物品)
└── CustomMod.json           ← VIR格式 (8个物品)
```

所有物品会被正确识别并生成统一的补丁文件。

## 注意事项

### 1. 可选字段
VIR格式中的以下字段是可选的：
- `isweapon`: 如果缺失，脚本会通过 `_parent` 自动判断
- `enable`: 不影响补丁生成
- `clone`: 不影响补丁生成
- `handbook`: 不影响补丁生成
- `locales`: 不影响补丁生成

### 2. 必需字段
VIR格式中必须包含：
- `item` 对象
- `item._id` (物品ID)
- `item._parent` (物品类别ID)

### 3. 兼容性
- ✅ 完全向后兼容STANDARD格式
- ✅ 自动检测，无需手动指定格式
- ✅ 混合格式文件夹支持

## 技术细节

### 格式检测代码
```python
def detect_item_format(self, item_data: Dict) -> str:
    """检测物品数据格式类型"""
    # VIR格式：有 "item" 字段，且item是dict且包含_id, _parent, _props
    if "item" in item_data and isinstance(item_data["item"], dict):
        item_obj = item_data["item"]
        if "_id" in item_obj and "_parent" in item_obj:
            return "VIR"
    # 标准格式：有 "parentId" 或 "itemTplToClone"
    if "parentId" in item_data or "itemTplToClone" in item_data:
        return "STANDARD"
    return "UNKNOWN"
```

### 数据提取逻辑
```python
def extract_item_info(self, item_id: str, item_data: Dict, format_type: str) -> Dict:
    if format_type == "VIR":
        item_obj = item_data["item"]
        return {
            "item_id": item_id,
            "parent_id": item_obj.get("_parent"),
            "name": item_obj.get("_name"),
            "is_weapon": item_data.get("isweapon") or self.is_weapon(parent_id),
            "properties": item_obj.get("_props", {})
        }
    elif format_type == "STANDARD":
        return {
            "item_id": item_id,
            "parent_id": item_data.get("parentId"),
            "properties": item_data.get("overrideProperties", {}),
            "is_weapon": self.is_weapon(parent_id)
        }
```

## 更新总结

| 功能 | v1.1 | v1.2 |
|------|------|------|
| STANDARD格式支持 | ✅ | ✅ |
| VIR格式支持 | ❌ | ✅ |
| 自动格式检测 | ❌ | ✅ |
| 混合格式处理 | ❌ | ✅ |
| 完整配件属性 | ✅ | ✅ |
| Name字段生成 | ✅ | ✅ |

---

**更新日期**: 2026年2月20日  
**版本**: 1.2  
**作者**: GitHub Copilot
