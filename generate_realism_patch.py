#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EFT 现实主义MOD兼容补丁生成器 v2.4
用于根据input文件夹中的物品数据，使用模板生成Realism MOD兼容配置文件

版本历史:
- v2.4 (2026-02-21): 
    - 引入“现实主义最高优先级规则校验”系统，强制规避数值夸大；
    - 实现基于物理规律的自动化属性推断：材质感应、尺寸性能缩放、枪管长度转换初速等逻辑；
    - 完善属性合并保护机制，防止非现实主义 MOD 数据破坏 Realism 核心数值体系；
    - 修正装备类（Armor/Vests/ChestRig）的所有映射路径与类型识别逻辑；
    - 优化模板选择，优先根据 `itemTplToClone` 或 `clone` ID 寻找精确匹配，极大幅度提升数值合理性。
- v2.3.1 (2026-02-21): 修复 __init__ 中缺失分类字典导致的 AttributeError
- v2.3 (2026-02-21): 实现按源文件名输出补丁的功能，支持输出文件名与输入文件名对应
- v2.2 (2026-02-21): 输入文件属性优先逻辑，支持从 locales 提取 Name，完善 CLONE 格式兼容性
- v2.1 (2026-02-21): 将输入文件夹从 Items 改为 input
- v2.0 (2026-02-20): ItemToClone 格式支持（本次更新）
- v1.9 (2026-02-20): 支持递归读取 input 文件夹下的所有子文件夹中的 JSON 文件
- v1.8 (2026-02-20): 支持文件内 clone 引用链（递归处理同一文件中的 clone 引用），支持 enable 字段检查
- v1.7 (2026-02-20): 加载 consumables/ 文件夹下的消耗品模板（food.json、meds.json），识别 RealismMod.Consumable 类型物品，生成独立的 consumables_realism_patch.json 文件，支持 TacticalCombo 类型（战术组合装置）
- v1.6 (2026-02-20): 重大更新 - 模板路径迁移至"现实主义物品模板"文件夹，新增ammo和gear模板支持，新增TemplateID格式识别（支持旧补丁MoxoPixel-BlackCore格式）
- v1.5.1 (2026-02-20): 新增 Armor_Plate (5b5f704686f77447ec5d76d7) 装甲插板类型识别支持
- v1.5 (2026-02-20): CLONE格式支持，可从clone ID在模板中查找并继承数值（适用于BlackCore等MOD）
- v1.4 (2026-02-20): 扩展物品类型映射，支持parentId字符串名称格式（如"GAS_BLOCK"）自动转换为ID
- v1.3 (2026-02-20): 子弹数据支持，自动识别parentId为5485a8684bdc2da71d8b4567的子弹
- v1.2 (2026-02-20): VIR格式支持，智能格式检测，扩展parentId映射
- v1.1 (2026-02-20): 完整配件数据结构支持，智能类型识别
- v1.0 (2026-02-20): 初始版本
"""

import json
import os
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
import copy

# 定义parentId到模板文件的映射 (基于 itemBaseClasses.md 完整映射)
PARENT_ID_TO_TEMPLATE = {
    # ===== 武器类型映射 =====
    # 突击步枪 (ASSAULT_RIFLE)
    "5447b5f14bdc2d61278b4567": "weapons/AssaultRifleTemplates.json",
    # 突击卡宾枪 (ASSAULT_CARBINE)
    "5447b5fc4bdc2d87278b4567": "weapons/AssaultCarbineTemplates.json",
    # 手枪 (HANDGUN)
    "5447b5cf4bdc2d65278b4567": "weapons/PistolTemplates.json",
    # 机枪 (MACHINEGUN)
    "5447bed64bdc2d97278b4568": "weapons/MachinegunTemplates.json",
    # 精确射手步枪 (MARKSMAN_RIFLE)
    "5447b6194bdc2d67278b4567": "weapons/MarksmanRifleTemplates.json",
    # 狙击步枪 (SNIPER_RIFLE)
    "5447b6254bdc2dc3278b4568": "weapons/SniperRifleTemplates.json",
    # 霰弹枪 (SHOTGUN)
    "5447b6094bdc2dc3278b4567": "weapons/ShotgunTemplates.json",
    # 冲锋枪 (SMG) - 注: itemBaseClasses 中没有SMG，这是原有映射
    "5447b5e04bdc2d62278b4567": "weapons/SMGTemplates.json",
    # 榴弹发射器 (GRENADE_LAUNCHER)
    "5447bedf4bdc2d87278b4568": "weapons/GrenadeLauncherTemplates.json",
    # 特殊武器 - 其他武器相关ID
    "617f1ef5e8b54b0998387732": "weapons/SpecialWeaponTemplates.json",
    "617f1ef5e8b54b0998387733": "weapons/GrenadeLauncherTemplates.json",
    # 投掷武器 (THROWABLE_WEAPON)
    "543be6564bdc2df4348b4568": "weapons/ThrowableTemplates.json",
    # 近战武器 (KNIFE)
    "5447e1d04bdc2dff2f8b4567": "weapons/MeleeTemplates.json",
    
    # ===== 配件类型映射 =====
    # 枪管 (BARREL)
    "555ef6e44bdc2de9068b457e": "attatchments/BarrelTemplates.json",
    # 双脚架 (BIPOD)
    "55818afb4bdc2dde698b456d": "attatchments/ForegripTemplates.json",
    # 拉机柄 (CHARGING_HANDLE)
    "55818a6f4bdc2db9688b456b": "attatchments/ChargingHandleTemplates.json",
    # 紧凑型反射瞄具 (COMPACT_REFLEX_SIGHT)
    "55818acf4bdc2dde698b456b": "attatchments/ScopeTemplates.json",
    # 消焰器 (FLASHHIDER)
    "550aa4bf4bdc2dd6348b456b": "attatchments/MuzzleDeviceTemplates.json",
    # 手电筒 (FLASHLIGHT)
    "55818b084bdc2d5b648b4571": "attatchments/FlashlightLaserTemplates.json",
    # 战术组合装置 (TacticalCombo)
    "55818b164bdc2ddc698b456c": "attatchments/FlashlightLaserTemplates.json",
    # 前握把 (FOREGRIP)
    "55818af64bdc2d5b648b4570": "attatchments/ForegripTemplates.json",
    # 导气箍 (GAS_BLOCK)
    "56ea9461d2720b67698b456f": "attatchments/GasblockTemplates.json",
    # 护木 (HANDGUARD)
    "55818a104bdc2db9688b4569": "attatchments/HandguardTemplates.json",
    # 机械瞄具 (IRON_SIGHT)
    "55818ac54bdc2d5b648b456e": "attatchments/IronSightTemplates.json",
    # 弹匣 (MAGAZINE)
    "5448bc234bdc2d3c308b4569": "attatchments/MagazineTemplates.json",
    # 导轨/基座 (MOUNT)
    "55818b224bdc2dde698b456f": "attatchments/MountTemplates.json",
    # 枪口组合装置 (MUZZLECOMBO)
    "550aa4dd4bdc2dc9348b4569": "attatchments/MuzzleDeviceTemplates.json",
    # 手枪握把 (PISTOLGRIP)
    "55818a684bdc2ddd698b456d": "attatchments/PistolGripTemplates.json",
    # 机匣 (RECEIVER)
    "55818a304bdc2db5418b457d": "attatchments/ReceiverTemplates.json",
    # 反射瞄具 (REFLEX_SIGHT)
    "55818ad54bdc2ddc698b4569": "attatchments/ScopeTemplates.json",
    # 瞄准镜 (SCOPE)
    "55818ae44bdc2dde698b456c": "attatchments/ScopeTemplates.json",
    # 消音器 (SILENCER)
    "550aa4cd4bdc2dd8348b456c": "attatchments/MuzzleDeviceTemplates.json",
    # 枪托 (STOCK)
    "55818a594bdc2db9688b456a": "attatchments/StockTemplates.json",
    # 下挂榴弹发射器 (UBGL)
    "55818b014bdc2ddc698b456b": "attatchments/UBGLTempaltes.json",
    # 突击型瞄准镜 (ASSAULT_SCOPE)
    "55818add4bdc2d5b648b456f": "attatchments/ScopeTemplates.json",
    # 战术装置/激光
    "5a74651486f7744e73386dd1": "attatchments/FlashlightLaserTemplates.json",
    "5448fe124bdc2da5018b4567": "attatchments/FlashlightLaserTemplates.json",
    # 辅助配件
    "5448fe394bdc2d0d028b456c": "attatchments/AuxiliaryModTemplates.json",
    # 其他机匣相关
    "55818b0f4bdc2db9688b4569": "attatchments/ReceiverTemplates.json",
    # 拉机柄 (充电手柄)
    "55818b1d4bdc2d5b648b4572": "attatchments/ChargingHandleTemplates.json",
    # 下挂榴弹发射器 (备用ID)
    "617f1ef5e8b54b0998387734": "attatchments/UBGLTempaltes.json",
    
    # ===== 护甲和装备类型映射 =====
    # 护甲 (ARMOR)
    "5448e54d4bdc2dcc718b4568": "gear/armorVestsTemplates.json",
    # 装甲板 (ARMORPLATE)
    "644120aa86ffbe10ee032b6f": "gear/armorPlateTemplates.json",
    # 装甲插板 (Armor_Plate)
    "5b5f704686f77447ec5d76d7": "gear/armorPlateTemplates.json",
    # 背包 (BACKPACK)
    "5448e53e4bdc2d60728b4567": "gear/bagTemplates.json",
    # 胸挂 (CHEST_RIG)
    "5448e5284bdc2dcb718b4567": "gear/chestrigTemplates.json",
    # 护甲装备 (ARMORED_EQUIPMENT)
    "57bef4c42459772e8d35a53b": "gear/armorChestrigTemplates.json",
    # 头盔 (HEADWEAR)
    "5a341c4086f77401f2541505": "gear/helmetTemplates.json",
    # 面罩 (FACECOVER)
    "5a341c4686f77469e155819e": "gear/armorMasksTemplates.json",
    # 耳机 (HEADPHONES)
    "5645bcb74bdc2ded0b8b4578": "gear/headsetTemplates.json",
    # 臂章 (ARMBAND)
    "5b3f15d486f77432d0509248": "gear/cosmeticsTemplates.json",
    # 物品组件/模组 (Armor components)
    "55d7217a4bdc2d86028b456d": "gear/armorComponentsTemplates.json",
    # 夜视仪 (NIGHTVISION)
    "5a2c3a9486f774688b05e574": "equipment/NightVisionTemplates.json",
    # 热成像 (THERMALVISION)
    "5d21f59b6dbe99052b54ef83": "equipment/ThermalVisionTemplates.json",
    # 便携式测距仪 (PORTABLE_RANGEFINDER)
    "61605ddea09d851a0a0c1bbc": "equipment/RangefinderTemplates.json",
    # 指南针 (COMPASS)
    "5f4fbaaca5573a5ac31db429": "equipment/CompassTemplates.json",
    
    # ===== 消耗品类型映射 =====
    # 子弹 (AMMO) - 特殊标识
    "5485a8684bdc2da71d8b4567": "AMMO",
    # 医疗用品 (MEDICAL_ITEM)
    "5448f3ac4bdc2dce718b4569": "consumables/meds.json",
    # 医疗包 (MEDITKIT)
    "5448f39d4bdc2d0a728b4568": "consumables/meds.json",
    # 药品 (DRUG)
    "5448f3a14bdc2d27728b4569": "consumables/meds.json",
    # 兴奋剂 (STIMULANT)
    "5448f3a64bdc2d60728b456a": "consumables/meds.json",
    # 食物 (FOOD)
    "5448e8d04bdc2ddf718b4569": "consumables/food.json",
    # 饮料 (DRINK)
    "5448e8d64bdc2dce718b4568": "consumables/food.json",
    
    # ===== 其他物品类型 =====
    # 弹药盒 (AMMO_CONTAINER)
    "543be5cb4bdc2deb348b4568": "containers/AmmoContainerTemplates.json",
    # 通用容器 (COMMON_CONTAINER)
    "5795f317245977243854e041": "containers/CommonContainerTemplates.json",
    # 上锁容器 (LOCKING_CONTAINER)
    "5671435f4bdc2d96058b4569": "containers/LockingContainerTemplates.json",
    # 钥匙卡 (KEYCARD)
    "5c164d2286f774194c5e69fa": "items/KeycardTemplates.json",
    # 机械钥匙 (KEYMECHANICAL)
    "5c99f98d86f7745c314214b3": "items/KeyMechanicalTemplates.json",
    # 金钱 (MONEY)
    "543be5dd4bdc2deb348b4569": "items/MoneyTemplates.json",
    # 修理工具 (REPAIRKITS)
    "616eb7aea207f41933308f46": "items/RepairKitTemplates.json",
    # 工具 (TOOL)
    "57864bb7245977548b3b66c2": "items/ToolTemplates.json",
    # 地图 (MAP)
    "567849dd4bdc2d150f8b456e": "items/MapTemplates.json",
    # 燃料 (FUEL)
    "5d650c3e815116009f6201d2": "items/FuelTemplates.json",
    # 润滑剂 (LUBRICANT)
    "57864e4c24597754843f8723": "items/LubricantTemplates.json",
    # 电池 (BATTERY)
    "57864ee62459775490116fc1": "items/BatteryTemplates.json",
    # 电子设备 (ELECTRONICS)
    "57864a66245977548f04a81f": "items/ElectronicsTemplates.json",
    # 建筑材料 (BUILDING_MATERIAL)
    "57864ada245977548638de91": "items/BuildingMaterialTemplates.json",
    # 医疗用品 (MEDICAL_SUPPLIES)
    "57864c8c245977548867e7f1": "items/MedicalSuppliesTemplates.json",
    # 信息 (INFO)
    "5448ecbe4bdc2d60728b4568": "items/InfoTemplates.json",
    # 特殊物品 (SPECIAL_ITEM)
    "5447e0e74bdc2d3c308b4567": "items/SpecialItemTemplates.json",
}

# 定义物品类型名称到ID的映射 (用于处理parentId为字符串名称的情况，如 "GAS_BLOCK" -> "56ea9461d2720b67698b456f")
ITEM_TYPE_NAME_TO_ID = {
    # 武器类型
    "ASSAULT_RIFLE": "5447b5f14bdc2d61278b4567",
    "ASSAULT_CARBINE": "5447b5fc4bdc2d87278b4567",
    "HANDGUN": "5447b5cf4bdc2d65278b4567",
    "MACHINEGUN": "5447bed64bdc2d97278b4568",
    "MARKSMAN_RIFLE": "5447b6194bdc2d67278b4567",
    "SNIPER_RIFLE": "5447b6254bdc2dc3278b4568",
    "SHOTGUN": "5447b6094bdc2dc3278b4567",
    "SMG": "5447b5e04bdc2d62278b4567",
    "GRENADE_LAUNCHER": "5447bedf4bdc2d87278b4568",
    "THROWABLE_WEAPON": "543be6564bdc2df4348b4568",
    "KNIFE": "5447e1d04bdc2dff2f8b4567",
    
    # 配件类型
    "BARREL": "555ef6e44bdc2de9068b457e",
    "BIPOD": "55818afb4bdc2dde698b456d",
    "CHARGING_HANDLE": "55818a6f4bdc2db9688b456b",
    "COMPACT_REFLEX_SIGHT": "55818acf4bdc2dde698b456b",
    "FLASHHIDER": "550aa4bf4bdc2dd6348b456b",
    "FLASHLIGHT": "55818b084bdc2d5b648b4571",
    "TacticalCombo": "55818b164bdc2ddc698b456c",
    "FOREGRIP": "55818af64bdc2d5b648b4570",
    "GAS_BLOCK": "56ea9461d2720b67698b456f",
    "HANDGUARD": "55818a104bdc2db9688b4569",
    "IRON_SIGHT": "55818ac54bdc2d5b648b456e",
    "MAGAZINE": "5448bc234bdc2d3c308b4569",
    "MOUNT": "55818b224bdc2dde698b456f",
    "MUZZLECOMBO": "550aa4dd4bdc2dc9348b4569",
    "PISTOLGRIP": "55818a684bdc2ddd698b456d",
    "RECEIVER": "55818a304bdc2db5418b457d",
    "REFLEX_SIGHT": "55818ad54bdc2ddc698b4569",
    "SCOPE": "55818ae44bdc2dde698b456c",
    "SILENCER": "550aa4cd4bdc2dd8348b456c",
    "STOCK": "55818a594bdc2db9688b456a",
    "UBGL": "55818b014bdc2ddc698b456b",
    "ASSAULT_SCOPE": "55818add4bdc2d5b648b456f",
    
    # 护甲和装备
    "ARMOR": "5448e54d4bdc2dcc718b4568",
    "ARMORPLATE": "644120aa86ffbe10ee032b6f",
    "Armor_Plate": "5b5f704686f77447ec5d76d7",
    "BACKPACK": "5448e53e4bdc2d60728b4567",
    "CHEST_RIG": "5448e5284bdc2dcb718b4567",
    "ARMORED_EQUIPMENT": "57bef4c42459772e8d35a53b",
    "HEADWEAR": "5a341c4086f77401f2541505",
    "FACECOVER": "5a341c4686f77469e155819e",
    "HEADPHONES": "5645bcb74bdc2ded0b8b4578",
    "ARMBAND": "5b3f15d486f77432d0509248",
    "NIGHTVISION": "5a2c3a9486f774688b05e574",
    "THERMALVISION": "5d21f59b6dbe99052b54ef83",
    "PORTABLE_RANGEFINDER": "61605ddea09d851a0a0c1bbc",
    "COMPASS": "5f4fbaaca5573a5ac31db429",
    
    # 消耗品
    "AMMO": "5485a8684bdc2da71d8b4567",
    "MEDICAL_ITEM": "5448f3ac4bdc2dce718b4569",
    "MEDITKIT": "5448f39d4bdc2d0a728b4568",
    "DRUG": "5448f3a14bdc2d27728b4569",
    "STIMULANT": "5448f3a64bdc2d60728b456a",
    "FOOD": "5448e8d04bdc2ddf718b4569",
    "DRINK": "5448e8d64bdc2dce718b4568",
    
    # 其他物品
    "AMMO_CONTAINER": "543be5cb4bdc2deb348b4568",
    "COMMON_CONTAINER": "5795f317245977243854e041",
    "LOCKING_CONTAINER": "5671435f4bdc2d96058b4569",
    "KEYCARD": "5c164d2286f774194c5e69fa",
    "KEY_CARD": "5c164d2286f774194c5e69fa",
    "KEYMECHANICAL": "5c99f98d86f7745c314214b3",
    "MONEY": "543be5dd4bdc2deb348b4569",
    "REPAIRKITS": "616eb7aea207f41933308f46",
    "TOOL": "57864bb7245977548b3b66c2",
    "MAP": "567849dd4bdc2d150f8b456e",
    "FUEL": "5d650c3e815116009f6201d2",
    "LUBRICANT": "57864e4c24597754843f8723",
    "BATTERY": "57864ee62459775490116fc1",
    "ELECTRONICS": "57864a66245977548f04a81f",
    "BUILDING_MATERIAL": "57864ada245977548638de91",
    "MEDICAL_SUPPLIES": "57864c8c245977548867e7f1",
    "INFO": "5448ecbe4bdc2d60728b4568",
    "SPECIAL_ITEM": "5447e0e74bdc2d3c308b4567",
    "VIS_OBSERV_DEVICE": "5448e5724bdc2ddf718b4568",
    "LOOT_CONTAINER": "566965d44bdc2d814c8b4571",
    "STATIONARY_CONT.": "567583764bdc2d98058b456e",
    "STASH": "566abbb64bdc2d144c8b457d",
    "INVENTORY": "55d720f24bdc2d88028b456d",
    "POCKETS": "557596e64bdc2dc2118b4571",
    "RANDOMLOOTCONTAINER": "62f109593b54472778797866",
    "OTHER": "590c745b86f7743cc433c5f2",
}

# 定义 HandbookParent 到 parent_id 的映射 (用于处理ItemToClone格式)
HANDBOOK_PARENT_TO_ID = {
    # 武器
    "AssaultRifles": "5447b5f14bdc2d61278b4567",
    "AssaultCarbines": "5447b5fc4bdc2d87278b4567",
    "Handguns": "5447b5cf4bdc2d65278b4567",
    "MachineGuns": "5447bed64bdc2d97278b4568",
    "MarksmanRifles": "5447b6194bdc2d67278b4567",
    "SniperRifles": "5447b6254bdc2dc3278b4568",
    "Shotguns": "5447b6094bdc2dc3278b4567",
    "SMGs": "5447b5e04bdc2d62278b4567",
    "GrenadeLaunchers": "5447bedf4bdc2d87278b4568",
    
    # 配件
    "Mods": "5448fe124bdc2da5018b4567",  # 默认配件
    "Magazines": "5448bc234bdc2d3c308b4569",  # 弹匣
    "Sights": "55818ad54bdc2ddc698b4569",  # 瞄具
    "Scopes": "55818ae44bdc2dde698b456c",  # 高倍瞄具
    "IronSights": "55818ac54bdc2d5b648b456e",  # 机械瞄具
    "Stocks": "55818a594bdc2db9688b456a",  # 枪托
    "Handguards": "55818a104bdc2db9688b4569",  # 护木
    "Barrels": "555ef6e44bdc2de9068b457e",  # 枪管
    "Suppressors": "550aa4cd4bdc2dd8348b456c",  # 消音器
    "Flashhiders": "550aa4bf4bdc2dd6348b456b",  # 制退器
    "Grips": "55818af64bdc2d5b648b4570",  # 前握把
    "PistolGrips": "55818a684bdc2ddd698b456d",  # 手枪握把
    "Mounts": "55818b224bdc2dde698b456f",  # 导轨
    "Receivers": "55818a304bdc2db5418b457d",  # 机匣
    "ChargingHandles": "55818a6f4bdc2db9688b456b",  # 拉机柄
    "GasBlocks": "56ea9461d2720b67698b456f",  # 导气箍
    
    # 弹药
    "Ammo": "5485a8684bdc2da71d8b4567",  # 默认弹药父类
    
    # 护甲和装备
    "Armor": "5448e54d4bdc2dcc718b4568",
    "Backpacks": "5448e53e4bdc2d60728b4567",
    "ChestRigs": "5448e5284bdc2dcb718b4567",
    "Headwear": "5a341c4086f77401f2541505",
    "FaceCover": "5a341c4686f77469e155819e",
    "Headphones": "5645bcb74bdc2ded0b8b4578",
    
    # 容器
    "Containers": "5795f317245977243854e041",  # 通用容器
    
    # 钥匙
    "MechanicalKeys": "5c99f98d86f7745c314214b3",  # 机械钥匙
    "Keycards": "5c164d2286f774194c5e69fa",  # 钥匙卡
    
    # 其他
    "Info": "5448ecbe4bdc2d60728b4568",  # 信息
}

# 定义默认的武器模板（如果没有找到匹配的模板，使用这个）
DEFAULT_WEAPON_TEMPLATE = {
    "$type": "RealismMod.Gun, RealismMod",
    "WeapType": "rifle",
    "OperationType": "",
    "WeapAccuracy": 0,
    "BaseTorque": 4.5,
    "HasShoulderContact": True,
    "Ergonomics": 85,
    "VerticalRecoil": 65,
    "HorizontalRecoil": 160,
    "Dispersion": 6,
    "CameraRecoil": 0.037,
    "VisualMulti": 1.1,
    "Convergence": 13.5,
    "RecoilAngle": 80,
    "BaseMalfunctionChance": 0.0012,
    "HeatFactorGun": 0.22,
    "HeatFactorByShot": 1,
    "CoolFactorGun": 0.1,
    "CoolFactorGunMods": 1,
    "AllowOverheat": True,
    "CenterOfImpact": 0,
    "HipAccuracyRestorationDelay": 0.2,
    "HipAccuracyRestorationSpeed": 7,
    "HipInnaccuracyGain": 0.16,
    "ShotgunDispersion": 0,
    "Velocity": 0,
    "RecoilDamping": 0.82,
    "RecoilHandDamping": 0.6,
    "WeaponAllowADS": False,
    "Weight": 1.5,
    "DurabilityBurnRatio": 0.28,
    "AutoROF": 600,
    "SemiROF": 340,
    "LoyaltyLevel": 2,
    "BaseReloadSpeedMulti": 1.0,
    "BaseChamberSpeedMulti": 1,
    "MinChamberSpeed": 0.7,
    "MaxChamberSpeed": 1.5,
    "IsManuallyOperated": False,
    "BaseChamberCheckSpeed": 1,
    "BaseFixSpeed": 1,
    "OffsetRotation": 0.011,
    "RecoilIntensity": 0.19,
    "RecoilCenter": {"x": 0, "y": -0.35, "z": 0}
}

# 定义默认的子弹模板
DEFAULT_AMMO_TEMPLATE = {
    "$type": "RealismMod.Ammo, RealismMod",
    "Name": "",
    "Damage": 50,
    "PenetrationPower": 20,
    "LoyaltyLevel": 1,
    "BasePriceModifier": 1
}

# 定义默认的消耗品模板
DEFAULT_CONSUMABLE_TEMPLATE = {
    "$type": "RealismMod.Consumable, RealismMod",
    "Name": "",
    "TemplateType": "consumable",
    "LoyaltyLevel": 1,
    "BasePriceModifier": 1,
    "ConsumableType": "other",
    "Duration": 0,
    "Delay": 0,
    "EffectPeriod": 0,
    "WaitPeriod": 0,
    "Strength": 0,
    "TunnelVisionStrength": 0,
    "CanBeUsedInRaid": True
}

# 定义默认的配件模板（精简版，只包含基础必需属性）
DEFAULT_MOD_TEMPLATE = {
    "$type": "RealismMod.WeaponMod, RealismMod",
    "ModType": "",
    "Ergonomics": 0,
    "Weight": 0.1,
    "ConflictingItems": [],
    "LoyaltyLevel": 1,
    "VerticalRecoil": 0,
    "HorizontalRecoil": 0,
    "AimSpeed": 0,
    "Accuracy": 0
}

# 配件类型特定属性映射（当使用默认模板时，根据配件类型添加额外属性）
MOD_TYPE_SPECIFIC_ATTRS = {
    # 枪托相关
    "Stock": {
        "Dispersion": 0,
        "CameraRecoil": 0,
        "HasShoulderContact": False,
        "BlocksFolding": False,
        "StockAllowADS": False,
        "Handling": 0,
        "AutoROF": 0,
        "SemiROF": 0,
        "ModMalfunctionChance": 0,
    },
    # 握把相关
    "grip": {
        "Dispersion": 0,
        "Handling": 0,
        "AimStability": 0,
    },
    # 护木相关
    "handguard": {
        "Dispersion": 0,
        "HeatFactor": 1,
        "CoolFactor": 1,
        "Handling": 0,
    },
    # 枪管相关
    "barrel": {
        "Dispersion": 0,
        "Convergence": 0,
        "CenterOfImpact": 0,
        "HeatFactor": 1,
        "CoolFactor": 1,
        "DurabilityBurnModificator": 1,
        "Velocity": 0,
        "ShotgunDispersion": 1,
        "Loudness": 0,
        "Flash": 0,
        "AutoROF": 0,
        "SemiROF": 0,
        "ModMalfunctionChance": 0,
    },
    # 枪口装置（含消音器、补偿器等）
    "muzzle": {
        "Dispersion": 0,
        "CameraRecoil": 0,
        "Convergence": 0,
        "HeatFactor": 1,
        "CoolFactor": 1,
        "DurabilityBurnModificator": 1,
        "Velocity": 0,
        "Loudness": 0,
        "CanCycleSubs": False,
        "RecoilAngle": 0,
        "AutoROF": 0,
        "SemiROF": 0,
        "ModMalfunctionChance": 0,
    },
    # 弹匣相关
    "magazine": {
        "ReloadSpeed": 0,
        "MalfunctionChance": 0,
        "LoadUnloadModifier": 0,
        "CheckTimeModifier": 0,
    },
    # 瞄准镜相关
    "sight": {
        # 瞄准镜通常只需要基础属性
    },
    # 刺刀
    "bayonet": {
        "Dispersion": 0,
        "CameraRecoil": 0,
        "MeleeDamage": 0,
        "MeleePen": 0,
        "HeatFactor": 1,
        "CoolFactor": 1,
        "DurabilityBurnModificator": 1,
        "Velocity": 0,
        "Loudness": 0,
        "Convergence": 0,
        "RecoilAngle": 0,
        "AutoROF": 0,
        "SemiROF": 0,
        "ModMalfunctionChance": 0,
        "CanCycleSubs": False,
    }
}


class RealismPatchGenerator:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.input_path = self.base_path / "input"
        self.templates_base_path = self.base_path / "现实主义物品模板"
        
        # 加载所有模板
        self.templates = {}
        self.load_all_templates()
        
        # 存储生成的补丁（按类型分类）
        self.weapon_patches = {}
        self.attachment_patches = {}
        self.ammo_patches = {}
        self.gear_patches = {}
        self.consumables_patches = {}
        
        # 按源文件名分组存储生成的补丁
        # 格式: { "filename": { "item_id": patch_data, ... }, ... }
        self.file_based_patches = {}

    def apply_realism_sanity_check(self, patch: Dict):
        """
        根据“现实主义“Realism”装备补丁属性规则说明”对补丁数值进行最终校验和纠正。
        实现“最优先生成规则”：规避数值夸大，并根据物品名称推断现实世界属性。
        """
        item_id = patch.get("ItemID", "Unknown")
        item_name = patch.get("Name", "").lower()
        item_type = patch.get("$type", "")

        # 1. 基础限制：规避夸大数值 (Clamping)
        if "RealismMod.Gun" in item_type:
            # 武器限制
            if "Ergonomics" in patch:
                patch["Ergonomics"] = max(10, min(100, patch["Ergonomics"])) 
            if "VerticalRecoil" in patch:
                patch["VerticalRecoil"] = max(10, min(1800, patch["VerticalRecoil"]))
            if "Convergence" in patch:
                patch["Convergence"] = max(1, min(40, patch["Convergence"]))
            if "RecoilAngle" in patch:
                # 引导后坐力角度到合理范围 (通常 80-95 是垂直向上系列)
                if patch["RecoilAngle"] < 30 or patch["RecoilAngle"] > 150:
                    patch["RecoilAngle"] = 90
                
        elif "RealismMod.WeaponMod" in item_type:
            # 配件限制
            if "VerticalRecoil" in patch:
                # 即使是最好的消音器，也极难超过 -35% 减震
                patch["VerticalRecoil"] = max(-35.0, min(35.0, patch["VerticalRecoil"]))
            if "HorizontalRecoil" in patch:
                patch["HorizontalRecoil"] = max(-35.0, min(35.0, patch["HorizontalRecoil"]))
            if "Dispersion" in patch:
                patch["Dispersion"] = max(-55.0, min(55.0, patch["Dispersion"]))
            if "Velocity" in patch:
                # 初速修正：枪管常用范围 -15% 到 +15%
                max_v = 15.0 if "barrel" in item_name else 5.0
                patch["Velocity"] = max(-max_v, min(max_v, patch["Velocity"]))
            if "Loudness" in patch:
                # 消音器效果限制：-45 是顶级消音器的限度
                patch["Loudness"] = max(-45, min(50, patch["Loudness"]))
            if "Accuracy" in patch:
                # 精度修正通常在 -10 到 +10 之间
                patch["Accuracy"] = max(-15, min(15, patch["Accuracy"]))

        elif "RealismMod.Gear" in item_type:
            # 装备限制
            if "ReloadSpeedMulti" in patch:
                # 装填倍率极其敏感，通常在 0.9 到 1.2 之间
                patch["ReloadSpeedMulti"] = max(0.85, min(1.25, patch["ReloadSpeedMulti"]))
            if "Comfort" in patch:
                # 舒适度（重量惩罚系数）
                patch["Comfort"] = max(0.6, min(1.4, patch["Comfort"]))
            if "speedPenaltyPercent" in patch:
                # 移速惩罚通常是负数且不应低于 -30%
                patch["speedPenaltyPercent"] = max(-40, min(10, patch["speedPenaltyPercent"]))
                
        # 2. 自动化现实数据推断 (Automated Reality-based Lookup)
        # 模拟“查询现实效果”：基于关键词和物理常识自动调整数值
        
        # A. 材质影响
        if any(kw in item_name for kw in ["titanium", "ti-", "carbon"]):
            # 钛合金/碳纤维：更轻 (通常轻 15-20%)，散热更好
            if "Weight" in patch: patch["Weight"] = round(patch["Weight"] * 0.8, 3)
            if "CoolFactor" in patch: patch["CoolFactor"] = round(patch["CoolFactor"] * 1.15, 2)
            if "Ergonomics" in patch: patch["Ergonomics"] = round(patch["Ergonomics"] * 1.05, 1)
        elif "steel" in item_name:
            # 钢制：更重，但更耐用
            if "Weight" in patch: patch["Weight"] = round(patch["Weight"] * 1.25, 3)
            if "DurabilityBurnModificator" in patch: patch["DurabilityBurnModificator"] = round(patch["DurabilityBurnModificator"] * 0.9, 2)
            
        # B. 紧凑型/超大型设备推断
        if any(kw in item_name for kw in ["compact", "mini", "short", "k-", "kurz"]):
            if "Weight" in patch: patch["Weight"] = round(patch["Weight"] * 0.75, 3)
            if "Loudness" in patch and patch["Loudness"] < 0: patch["Loudness"] = round(patch["Loudness"] * 0.7, 1) # 消音效果较差
            if "VerticalRecoil" in patch and patch["VerticalRecoil"] < 0: patch["VerticalRecoil"] = round(patch["VerticalRecoil"] * 0.7, 2) # 减震效果较差
        elif any(kw in item_name for kw in ["long", "extended", "heavy", "full"]):
            if "Weight" in patch: patch["Weight"] = round(patch["Weight"] * 1.3, 3)
            if "Accuracy" in patch: patch["Accuracy"] = round(patch["Accuracy"] * 1.1 + 1, 1)
            
        # C. 枪管长度推断初速 (毫米/英寸转换)
        import re
        length_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:mm|inch|in|")', item_name)
        if length_match and "barrel" in item_name:
            try:
                val = float(length_match.group(1))
                # 转换为毫米进行评估
                mm_val = val * 25.4 if any(u in item_name for u in ["inch", "in", '"']) else val
                
                # 现实物理规律：长枪管提升初速，短枪管降低初速。
                # 现代步枪标准枪管约为 14.5-16.5 英寸 (370-420mm)
                # 每增加或减少 1 英寸 (25.4mm)，初速变化约 1.5%
                inferred_velocity = (mm_val - 370) / 25.4 * 1.5
                
                # 直接应用到 Velocity 字段
                if patch.get("Velocity", 0) == 0:
                    patch["Velocity"] = round(max(-18, min(18, inferred_velocity)), 2)
            except: pass

        # D. 安全性兜底：防止任何属性出现天文数字
        for key, value in patch.items():
            if isinstance(value, (int, float)):
                if "Recoil" in key: patch[key] = max(-2000, min(2000, value))
                elif "Ergonomics" in key: patch[key] = max(-50, min(100, value))
                elif "Weight" in key: patch[key] = max(0, min(50, value))
                elif "Multi" in key or "Factor" in key: patch[key] = max(0.01, min(10.0, value))

    def load_all_templates(self):
        """加载所有模板文件"""
        print("正在加载模板文件...")
        
        # 加载武器模板
        weapons_path = self.templates_base_path / "weapons"
        if weapons_path.exists():
            for template_file in weapons_path.glob("*.json"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                        self.templates[template_file.name] = template_data
                        print(f"  已加载: {template_file.name} ({len(template_data)} 个模板)")
                except Exception as e:
                    print(f"  警告: 无法加载 {template_file.name}: {e}")
        
        # 加载配件模板
        attachments_path = self.templates_base_path / "attatchments"
        if attachments_path.exists():
            for template_file in attachments_path.glob("*.json"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                        self.templates[template_file.name] = template_data
                        print(f"  已加载: {template_file.name} ({len(template_data)} 个模板)")
                except Exception as e:
                    print(f"  警告: 无法加载 {template_file.name}: {e}")
        
        # 加载子弹模板
        ammo_path = self.templates_base_path / "ammo"
        if ammo_path.exists():
            for template_file in ammo_path.glob("*.json"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                        self.templates[template_file.name] = template_data
                        print(f"  已加载: {template_file.name} ({len(template_data)} 个模板)")
                except Exception as e:
                    print(f"  警告: 无法加载 {template_file.name}: {e}")
        
        # 加载护甲/装备模板
        gear_path = self.templates_base_path / "gear"
        if gear_path.exists():
            for template_file in gear_path.glob("*.json"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                        self.templates[template_file.name] = template_data
                        print(f"  已加载: {template_file.name} ({len(template_data)} 个模板)")
                except Exception as e:
                    print(f"  警告: 无法加载 {template_file.name}: {e}")
        
        # 加载消耗品模板
        consumables_path = self.templates_base_path / "consumables"
        if consumables_path.exists():
            for template_file in consumables_path.glob("*.json"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                        self.templates[template_file.name] = template_data
                        print(f"  已加载: {template_file.name} ({len(template_data)} 个模板)")
                except Exception as e:
                    print(f"  警告: 无法加载 {template_file.name}: {e}")
    
    def normalize_parent_id(self, parent_id: Optional[str]) -> Optional[str]:
        """标准化parentId，将字符串名称（如'GAS_BLOCK'）转换为ID"""
        if not parent_id:
            return parent_id
        
        # 如果是字符串名称格式（全大写且包含下划线），尝试转换为ID
        if parent_id.isupper() or "_" in parent_id:
            normalized_id = ITEM_TYPE_NAME_TO_ID.get(parent_id)
            if normalized_id:
                return normalized_id
        
        # 否则返回原值（已经是ID或未知格式）
        return parent_id
    
    def get_template_for_parent_id(self, parent_id: str) -> str:
        """根据parentId获取模板文件名"""
        # 标准化 parentId
        parent_id = self.normalize_parent_id(parent_id)
        template_path = PARENT_ID_TO_TEMPLATE.get(parent_id)
        if template_path:
            return os.path.basename(template_path)
        return None
    
    def detect_item_format(self, item_data: Dict) -> str:
        """检测物品数据格式类型"""
        # TEMPLATE_ID格式：有 "TemplateID" 字段（旧补丁中MoxoPixel-BlackCore的格式）
        if "TemplateID" in item_data and "$type" in item_data:
            return "TEMPLATE_ID"
        # VIR格式：有 "item" 字段，且item是dict且包含_id, _parent, _props
        if "item" in item_data and isinstance(item_data["item"], dict):
            item_obj = item_data["item"]
            if "_id" in item_obj and "_parent" in item_obj:
                return "VIR"
        # ITEMTOCLONE格式：有 "ItemToClone" 字段（新格式）
        if "ItemToClone" in item_data:
            return "ITEMTOCLONE"
        # CLONE格式：有 "clone" 字段（BlackCore等）
        if "clone" in item_data:
            return "CLONE"
        # 标准格式：有 "parentId" 或 "itemTplToClone"
        if "parentId" in item_data or "itemTplToClone" in item_data:
            return "STANDARD"
        return "UNKNOWN"
    
    def extract_item_info(self, item_id: str, item_data: Dict, format_type: str) -> Dict:
        """根据格式提取物品信息"""
        info = {
            "item_id": item_id,
            "parent_id": None,
            "clone_id": None,
            "template_id": None,
            "name": None,
            "is_weapon": False,
            "is_gear": False,
            "is_consumable": False,
            "item_type": None,
            "properties": {}
        }
        
        if format_type == "TEMPLATE_ID":
            # TEMPLATE_ID格式（旧补丁MoxoPixel-BlackCore）
            info["template_id"] = item_data.get("TemplateID")
            info["name"] = item_data.get("Name")
            info["item_type"] = item_data.get("$type")
            # 根据$type判断类型
            if "RealismMod.Gun" in info["item_type"]:
                info["is_weapon"] = True
            elif "RealismMod.Gear" in info["item_type"]:
                info["is_gear"] = True
            elif "RealismMod.Consumable" in info["item_type"]:
                info["is_consumable"] = True
        
        elif format_type == "VIR":
            # VIR格式
            if "item" in item_data:
                item_obj = item_data["item"]
                info["parent_id"] = self.normalize_parent_id(item_obj.get("_parent"))
                info["name"] = item_obj.get("_name")
                info["properties"] = item_obj.get("_props", {})
                # 如果有isweapon字段则使用，否则通过parent_id判断
                if "isweapon" in item_data:
                    info["is_weapon"] = item_data["isweapon"]
                elif info["parent_id"]:
                    info["is_weapon"] = self.is_weapon(info["parent_id"])
        
        elif format_type == "STANDARD":
            # 标准格式
            info["parent_id"] = self.normalize_parent_id(item_data.get("parentId"))
            info["clone_id"] = item_data.get("itemTplToClone")
            info["properties"] = item_data.get("overrideProperties", {})
            if "locales" in item_data:
                locales = item_data["locales"]
                for lang in ["en", "ch", "zh", "ru"]:
                    if isinstance(locales, dict) and lang in locales and isinstance(locales[lang], dict) and "name" in locales[lang]:
                        info["name"] = locales[lang]["name"]
                        break
            # 详细判断类型
            if info["parent_id"]:
                info["is_weapon"] = self.is_weapon(info["parent_id"])
                info["is_gear"] = self.is_gear_simple(info["parent_id"])
                info["is_consumable"] = self.is_consumable(info["parent_id"])
            elif info["clone_id"]:
                info["is_weapon"] = self.is_weapon_by_clone_id(info["clone_id"])
        
        elif format_type == "ITEMTOCLONE":
            # ITEMTOCLONE格式（新格式）
            info["clone_id"] = item_data.get("ItemToClone")
            # 从LocalePush提取名称
            if "LocalePush" in item_data:
                locale_data = item_data["LocalePush"]
                if "name" in locale_data:
                    info["name"] = locale_data["name"]
            # 从OverrideProperties提取属性
            if "OverrideProperties" in item_data:
                info["properties"] = item_data["OverrideProperties"]
            # 需要通过clone ID查找parent_id和类型
        
        elif format_type == "CLONE":
            # CLONE格式（BlackCore等）
            info["clone_id"] = item_data.get("clone")
            # 从locales提取名称，支持层级路径（如 locales.en.Name）或扁平路径
            if "locales" in item_data:
                locales = item_data["locales"]
                # 尝试常见语言层级
                for lang in ["en", "ch", "zh", "ru"]:
                    if isinstance(locales, dict) and lang in locales and isinstance(locales[lang], dict) and "Name" in locales[lang]:
                        info["name"] = locales[lang]["Name"]
                        break
                # 如果还没找到且locales直接含有Name
                if not info["name"] and isinstance(locales, dict) and "Name" in locales:
                    info["name"] = locales["Name"]
            
            # 尝试从 handbook 提取 parent_id
            if "handbook" in item_data:
                handbook = item_data["handbook"]
                h_parent = handbook.get("ParentId") or handbook.get("parentId")
                if h_parent:
                    info["parent_id"] = self.normalize_parent_id(h_parent)
            
            # 从 items._props 或 item._props 提取属性
            # 兼容 "items" 和 "item" 两种拼写（用户输入文件中使用的是 "item"）
            item_obj_key = "items" if "items" in item_data else ("item" if "item" in item_data else None)
            if item_obj_key and "_props" in item_data[item_obj_key]:
                info["properties"] = item_data[item_obj_key]["_props"]
                # 如果没从handbook拿到parent_id，尝试从_props拿到_parent
                if not info["parent_id"] and "_parent" in item_data[item_obj_key]:
                    info["parent_id"] = self.normalize_parent_id(item_data[item_obj_key]["_parent"])
            # clone格式需要通过clone ID查找parent_id和类型
            # 这将在后续处理中通过find_template_by_id完成
        
        return info
    
    def merge_input_properties(self, patch: Dict, item_info: Dict):
        """将输入文件中的属性合并到生成的补丁中（输入文件优先覆盖模板）"""
        # 1. 首先合并显式的 Name
        input_name = item_info.get("name")
        if input_name:
            # 如果模板已经有名字且输入的名字看起来是自动生成的(如"ammo_..."), 则不覆盖
            if "Name" in patch and input_name.startswith("ammo_") and not patch["Name"].startswith("ammo_"):
                pass
            else:
                patch["Name"] = input_name
            
        # 2. 遍历输入文件中的 _props/properties 字典
        input_props = item_info.get("properties", {})
        if not input_props:
            return
            
        # 这些是现实主义补丁的核心字段
        # 我们需要小心覆盖这些字段，因为模板中的值通常更符合现实主义的需求
        is_weapon = patch.get("$type") == "RealismMod.Gun, RealismMod"
        
        # 对于武器，绝不从 mods 的原始数据中覆盖这些核心现实主义字段
        sensitive_fields = {
            "Ergonomics", "VerticalRecoil", "HorizontalRecoil", 
            "Dispersion", "Convergence", "RecoilDamping", "RecoilHandDamping",
            "HipAccuracyRestorationDelay", "HipAccuracyRestorationSpeed", "HipInnaccuracyGain",
            "CameraRecoil", "VisualMulti", "RecoilAngle", "RecoilIntensity"
        }
        
        realism_fields = {
            "Ergonomics", "Weight", "VerticalRecoil", "HorizontalRecoil", 
            "Velocity", "Loudness", "Accuracy", "Name", "ModType",
            "ConflictingItems", "LoyaltyLevel", "DurabilityBurnModificator",
            "AutoROF", "SemiROF", "ModMalfunctionChance",
            "PenetrationPower", "Damage", "InitialSpeed", "BulletMassGram", "BallisticCoeficient"
        }
        
        for key, value in input_props.items():
            # 特殊处理：如果输入文件中有这些字段，无论模板有没有，都考虑覆盖或添加
            # 情况A：字段名完全匹配（例如 Ergonomics, Name 等）
            if key in realism_fields or key in patch:
                # 过滤掉一些可能引起问题的空值
                if value is not None:
                    # 如果是武器/配件的敏感字段，且模板中已经有了（且不为0），则跳过覆盖
                    # 除非这个值看起来特别"现实主义"（比如很大或很小）
                    if key in sensitive_fields and key in patch and patch[key] != 0:
                        continue
                        
                    if key == "Name" and not value and input_name:
                        continue
                    patch[key] = value
                    
            # 情况B：处理一些可能的大小写差异或 Tarkov 原始字段名到 Realism 字段名的映射
            elif key == "Recoil" and "VerticalRecoil" in patch:
                if patch["VerticalRecoil"] == 0:
                    patch["VerticalRecoil"] = value
            elif key == "Weight" and "Weight" in patch:
                patch["Weight"] = value

    def is_gear_simple(self, parent_id: str) -> bool:
        """判断是否为装备类型(护甲、背包、挂钩、头盔等)"""
        parent_id = self.normalize_parent_id(parent_id)
        # 装备相关的 parent_id 列表
        gear_ids = [
            "5448e54d4bdc2dcc718b4568",  # ARMOR
            "644120aa86ffbe10ee032b6f",  # ARMORPLATE
            "5b5f704686f77447ec5d76d7",  # Armor_Plate
            "5448e53e4bdc2d60728b4567",  # BACKPACK
            "5448e5284bdc2dcb718b4567",  # CHEST_RIG
            "57bef4c42459772e8d35a53b",  # ARMORED_EQUIPMENT
            "5a341c4086f77401f2541505",  # HEADWEAR
            "5a341c4686f77469e155819e",  # FACECOVER
            "5645bcb74bdc2ded0b8b4578",  # HEADPHONES
            "5b3f15d486f77432d0509248",  # ARMBAND
        ]
        return parent_id in gear_ids

    def is_weapon_by_clone_id(self, clone_id: str) -> bool:
        """通过 clone_id 推断是否为武器"""
        template = self.find_template_by_id(clone_id)
        if template and "$type" in template:
            return "RealismMod.Gun" in template["$type"]
        return False

    def is_weapon(self, parent_id: str) -> bool:
        """判断是否为武器"""
        template_file = self.get_template_for_parent_id(parent_id)
        if template_file and template_file in self.templates:
            # 检查模板中的$type字段
            for item in self.templates[template_file].values():
                if "$type" in item:
                    return "RealismMod.Gun" in item["$type"]
        return False
    
    def is_ammo(self, parent_id: str) -> bool:
        """判断是否为子弹"""
        parent_id = self.normalize_parent_id(parent_id)
        return parent_id == "5485a8684bdc2da71d8b4567"
    
    def is_consumable(self, parent_id: str) -> bool:
        """判断是否为消耗品类型"""
        parent_id = self.normalize_parent_id(parent_id)
        # 消耗品相关的 parent_id 列表
        consumable_ids = [
            "5448e8d04bdc2ddf718b4569",  # FOOD
            "5448e8d64bdc2dce718b4568",  # DRINK
            "5448f3ac4bdc2dce718b4569",  # MEDICAL_ITEM
            "5448f39d4bdc2d0a728b4568",  # MEDITKIT
            "5448f3a14bdc2d27728b4569",  # DRUG
            "5448f3a64bdc2d60728b456a",  # STIMULANT
        ]
        return parent_id in consumable_ids
    
    def find_template_by_id(self, clone_id: str) -> Optional[Dict]:
        """在所有已加载的模板中搜索指定ID的模板数据"""
        if not clone_id:
            return None
        
        # 遍历所有模板文件
        for template_file, template_data in self.templates.items():
            if clone_id in template_data:
                # 找到了，返回深拷贝
                result = copy.deepcopy(template_data[clone_id])
                return result
        
        return None
    
    def find_template_by_template_id(self, template_id: str) -> Optional[Dict]:
        """通过TemplateID在所有已加载的模板中搜索指定ID的模板数据"""
        if not template_id:
            return None
        
        # 遍历所有模板文件
        for template_file, template_data in self.templates.items():
            if template_id in template_data:
                # 找到了，返回深拷贝
                result = copy.deepcopy(template_data[template_id])
                return result
        
        return None
    
    def select_template_data(self, template_file: str, item_id: str, clone_id: Optional[str] = None) -> Dict:
        """从模板文件中选择合适的数据"""
        if template_file not in self.templates:
            return None
        
        template_data = self.templates[template_file]
        
        # 1. 尝试精确匹配 ItemID
        if item_id in template_data:
            result = copy.deepcopy(template_data[item_id])
            result["ItemID"] = item_id
            return result
        
        # 2. 尝试匹配 clone_id
        if clone_id and clone_id in template_data:
            result = copy.deepcopy(template_data[clone_id])
            result["ItemID"] = item_id
            return result
        
        # 3. 尝试在所有模板中跨文件搜索 clone_id
        if clone_id:
            found_template = self.find_template_by_id(clone_id)
            if found_template:
                found_template["ItemID"] = item_id
                return found_template

        # 4. 如果没有匹配，寻找一个该类别中最通用的模板，而不是完全随机
        if template_data:
            # 尝试找一个名字里带 "std" 或 "standard" 的
            for tid, tval in template_data.items():
                name = tval.get("Name", "").lower()
                if "std" in name or "standard" in name:
                    result = copy.deepcopy(tval)
                    result["ItemID"] = item_id
                    return result
            
            # 如果还是没找到，随机选择一个模板作为基础 (最后手段)
            random_template = random.choice(list(template_data.values()))
            result = copy.deepcopy(random_template)
            result["ItemID"] = item_id
            return result
        
        return None
    
    def clean_mod_data(self, mod_data: Dict) -> Dict:
        """清理配件数据，移除不必要的零值属性（可选）"""
        # 必须保留的属性
        required_fields = {
            "$type", "ItemID", "ModType", "Ergonomics", "Weight", 
            "ConflictingItems", "LoyaltyLevel", "VerticalRecoil", "HorizontalRecoil"
        }
        
        # 这个函数目前只是返回原数据，保留所有属性
        # 如果需要精简，可以启用下面的清理逻辑
        return mod_data
        
        # 清理逻辑（注释掉以保留所有属性）
        # cleaned = {}
        # for key, value in mod_data.items():
        #     # 保留必需字段
        #     if key in required_fields:
        #         cleaned[key] = value
        #     # 保留非零值
        #     elif value != 0 and value != False and value != 1:
        #         cleaned[key] = value
        #     # 保留特殊的默认值
        #     elif key in ["ShotgunDispersion", "HeatFactor", "CoolFactor", "DurabilityBurnModificator"]:
        #         cleaned[key] = value
        # return cleaned
    
    def create_default_weapon_patch(self, item_id: str, item_info: Dict) -> Dict:
        """创建默认的武器补丁"""
        patch = copy.deepcopy(DEFAULT_WEAPON_TEMPLATE)
        patch["ItemID"] = item_id
        
        # 添加Name属性
        if item_info.get("name"):
            patch["Name"] = item_info["name"]
        else:
            patch["Name"] = f"weapon_{item_id}"
        
        # 尝试从属性中提取一些信息
        props = item_info.get("properties", {})
        if "Weight" in props:
            patch["Weight"] = props["Weight"]
        if "Ergonomics" in props:
            patch["Ergonomics"] = props["Ergonomics"]
        if "bFirerate" in props:
            patch["AutoROF"] = props["bFirerate"]
        
        return patch
    
    def get_mod_type_from_template(self, template_file: str) -> str:
        """根据模板文件名推断配件类型"""
        template_to_modtype = {
            "StockTemplates.json": "Stock",
            "ForegripTemplates.json": "grip",
            "HandguardTemplates.json": "handguard",
            "BarrelTemplates.json": "barrel",
            "MuzzleDeviceTemplates.json": "muzzle",
            "MagazineTemplates.json": "magazine",
            "ScopeTemplates.json": "sight",
            "IronSightTemplates.json": "sight",
        }
        return template_to_modtype.get(template_file, "")
    
    def create_default_mod_patch(self, item_id: str, item_info: Dict, template_file: str = None) -> Dict:
        """创建默认的配件补丁，根据类型添加相应属性"""
        patch = copy.deepcopy(DEFAULT_MOD_TEMPLATE)
        patch["ItemID"] = item_id
        
        # 推断ModType
        mod_type = ""
        if template_file:
            mod_type = self.get_mod_type_from_template(template_file)
            patch["ModType"] = mod_type
        
        # 添加Name属性
        if item_info.get("name"):
            patch["Name"] = item_info["name"]
        else:
            patch["Name"] = f"mod_{item_id}"
        
        # 根据ModType添加特定属性
        if mod_type in MOD_TYPE_SPECIFIC_ATTRS:
            patch.update(MOD_TYPE_SPECIFIC_ATTRS[mod_type])
        
        # 尝试从属性中提取一些信息
        props = item_info.get("properties", {})
        if "Weight" in props:
            patch["Weight"] = props["Weight"]
        if "Ergonomics" in props:
            patch["Ergonomics"] = props["Ergonomics"]
        
        return patch
    
    def create_default_ammo_patch(self, item_id: str, item_info: Dict) -> Dict:
        """创建默认的子弹补丁"""
        patch = copy.deepcopy(DEFAULT_AMMO_TEMPLATE)
        patch["ItemID"] = item_id
        
        # 添加Name属性
        if item_info.get("name"):
            patch["Name"] = item_info["name"]
        else:
            patch["Name"] = f"ammo_{item_id}"
        
        # 尝试从属性中提取子弹数据
        props = item_info.get("properties", {})
        if "Damage" in props:
            patch["Damage"] = props["Damage"]
        if "PenetrationPower" in props:
            patch["PenetrationPower"] = props["PenetrationPower"]
        if "InitialSpeed" in props:
            patch["InitialSpeed"] = props["InitialSpeed"]
        if "BulletMassGram" in props:
            patch["BulletMassGram"] = props["BulletMassGram"]
        if "BallisticCoeficient" in props:
            patch["BallisticCoeficient"] = props["BallisticCoeficient"]
        
        return patch
    
    def create_default_consumable_patch(self, item_id: str, item_info: Dict) -> Dict:
        """创建默认的消耗品补丁"""
        patch = copy.deepcopy(DEFAULT_CONSUMABLE_TEMPLATE)
        patch["ItemID"] = item_id
        
        # 添加Name属性
        if item_info.get("name"):
            patch["Name"] = item_info["name"]
        else:
            patch["Name"] = f"consumable_{item_id}"
        
        return patch
    
    def process_single_item(self, item_id: str, item_data: Dict, items_data: Dict, processed_items: set, source_file: str = None) -> bool:
        """
        处理单个物品，支持递归处理 clone 引用
        
        Args:
            item_id: 物品ID
            item_data: 物品数据
            items_data: 当前文件的所有物品数据
            processed_items: 已处理的物品ID集合
            source_file: 数据来源文件名
            
        Returns:
            bool: 是否成功处理
        """
        # 如果已经处理过，直接返回
        if item_id in processed_items:
            return True
        
        # 助手方法：存储到基于文件的补丁中
        def add_to_file_patches(patch):
            if source_file:
                if source_file not in self.file_based_patches:
                    self.file_based_patches[source_file] = {}
                self.file_based_patches[source_file][item_id] = patch

        # 检查 enable 字段，如果为 False 则跳过
        if "enable" in item_data and not item_data["enable"]:
            return False
        
        # 检测文件格式
        format_type = self.detect_item_format(item_data)
        
        if format_type == "UNKNOWN":
            return False
        
        # 提取物品信息
        item_info = self.extract_item_info(item_id, item_data, format_type)
        
        clone_id = item_info.get("clone_id")
        template_id = item_info.get("template_id")
        parent_id = item_info.get("parent_id")
        
        # 对于TEMPLATE_ID格式
        if format_type == "TEMPLATE_ID" and template_id:
            template_data = self.find_template_by_template_id(template_id)
            
            if template_data:
                template_data["ItemID"] = item_id
                
                # 合并输入属性 (输入文件优先)
                self.merge_input_properties(template_data, item_info)
                
                # 应用最优先现实主义数值规则校验
                self.apply_realism_sanity_check(template_data)
                
                # 按文件存储
                add_to_file_patches(template_data)
                
                # 根据类型分类存储 (保留旧的存储方式以防万一)
                if item_info.get("is_weapon"):
                    self.weapon_patches[item_id] = template_data
                elif item_info.get("is_gear"):
                    self.gear_patches[item_id] = template_data
                elif item_info.get("is_consumable"):
                    self.consumables_patches[item_id] = template_data
                else:
                    self.attachment_patches[item_id] = template_data
                
                processed_items.add(item_id)
                return True
            else:
                print(f"  跳过 {item_id}: 未找到TemplateID {template_id} 对应的模板")
                return False
        
        # 对于CLONE格式
        if format_type == "CLONE" and clone_id:
            # 首先在模板中查找
            template_data = self.find_template_by_id(clone_id)
            
            # 如果模板中没找到，尝试在当前文件中查找
            if not template_data and clone_id in items_data:
                # 递归处理 clone 源物品
                if self.process_single_item(clone_id, items_data[clone_id], items_data, processed_items, source_file):
                    # 从已生成的补丁中获取 clone 源的数据
                    if clone_id in self.weapon_patches:
                        template_data = copy.deepcopy(self.weapon_patches[clone_id])
                    elif clone_id in self.attachment_patches:
                        template_data = copy.deepcopy(self.attachment_patches[clone_id])
                    elif clone_id in self.gear_patches:
                        template_data = copy.deepcopy(self.gear_patches[clone_id])
                    elif clone_id in self.consumables_patches:
                        template_data = copy.deepcopy(self.consumables_patches[clone_id])
            
            if template_data:
                # 更新ItemID
                template_data["ItemID"] = item_id
                
                # 合并输入属性 (输入文件优先)
                self.merge_input_properties(template_data, item_info)
                
                # 应用最优先现实主义数值规则校验
                self.apply_realism_sanity_check(template_data)
                
                # 按文件存储
                add_to_file_patches(template_data)
                
                # 根据模板中的$type判断类型
                if "$type" in template_data:
                    if "RealismMod.Gun" in template_data["$type"]:
                        self.weapon_patches[item_id] = template_data
                    elif "RealismMod.Gear" in template_data["$type"]:
                        self.gear_patches[item_id] = template_data
                    elif "RealismMod.Consumable" in template_data["$type"]:
                        self.consumables_patches[item_id] = template_data
                    elif "RealismMod.Ammo" in template_data["$type"]:
                        self.ammo_patches[item_id] = template_data
                    else:
                        self.attachment_patches[item_id] = template_data
                else:
                    self.attachment_patches[item_id] = template_data
                
                processed_items.add(item_id)
                return True
            else:
                print(f"  跳过 {item_id}: 未找到clone ID {clone_id} 对应的模板")
                return False
        
        # 对于ITEMTOCLONE格式
        if format_type == "ITEMTOCLONE" and clone_id:
            # 从Handbook字段获取parent_id
            handbook_parent = item_data.get("HandbookParent")
            
            # 如果HandbookParent是24字符的ID，直接使用
            if handbook_parent and len(handbook_parent) == 24:
                parent_id = handbook_parent
            # 否则从映射表中查找
            elif handbook_parent and handbook_parent in HANDBOOK_PARENT_TO_ID:
                parent_id = HANDBOOK_PARENT_TO_ID[handbook_parent]
            
            # 如果没有parent_id，尝试从ItemToClone常量名称推断
            if not parent_id and clone_id:
                # 从ItemToClone常量名称推断类型
                if "AMMO_" in clone_id:
                    parent_id = "5485a8684bdc2da71d8b4567"  # 弹药
                elif any(weapon_type in clone_id for weapon_type in ["ASSAULTRIFLE_", "RIFLE_", "SHOTGUN_", "SMG_", "PISTOL_", "HANDGUN_", "MACHINEGUN_", "GRENADELAUNCHER_"]):
                    # 根据常量名称推断武器类型
                    if "ASSAULTRIFLE_" in clone_id:
                        parent_id = "5447b5f14bdc2d61278b4567"  # 突击步枪
                    elif "RIFLE_" in clone_id or "MARKSMANRIFLE_" in clone_id:
                        parent_id = "5447b6194bdc2d67278b4567"  # 精确射手步枪
                    elif "SNIPER" in clone_id or "SNIPERRIFLE_" in clone_id:
                        parent_id = "5447b6254bdc2dc3278b4568"  # 狙击步枪
                    elif "SHOTGUN_" in clone_id:
                        parent_id = "5447b6094bdc2dc3278b4567"  # 霰弹枪
                    elif "SMG_" in clone_id:
                        parent_id = "5447b5e04bdc2d62278b4567"  # 冲锋枪
                    elif "PISTOL_" in clone_id or "HANDGUN_" in clone_id:
                        parent_id = "5447b5cf4bdc2d65278b4567"  # 手枪
                    elif "MACHINEGUN_" in clone_id:
                        parent_id = "5447bed64bdc2d97278b4568"  # 机枪
                    elif "GRENADELAUNCHER_" in clone_id:
                        parent_id = "5447bedf4bdc2d87278b4568"  # 榴弹发射器
                elif "MAGAZINE_" in clone_id or "MAG_" in clone_id:
                    parent_id = "5448bc234bdc2d3c308b4569"  # 弹匣
                elif "ARMOR_" in clone_id or "VEST_" in clone_id:
                    parent_id = "5448e54d4bdc2dcc718b4568"  # 护甲
                elif "CONTAINER_" in clone_id or "SECURE_" in clone_id:
                    parent_id = "5795f317245977243854e041"  # 容器
                elif "KEY_" in clone_id or "KEYCARD_" in clone_id:
                    if "KEYCARD_" in clone_id:
                        parent_id = "5c164d2286f774194c5e69fa"  # 钥匙卡
                    else:
                        parent_id = "5c99f98d86f7745c314214b3"  # 机械钥匙
                elif "INFO_" in clone_id or "DIARY_" in clone_id:
                    parent_id = "5448ecbe4bdc2d60728b4568"  # 信息
                elif "HEADWEAR_" in clone_id or "HELMET_" in clone_id:
                    parent_id = "5a341c4086f77401f2541505"  # 头盔
                elif "HEADPHONES_" in clone_id:
                    parent_id = "5645bcb74bdc2ded0b8b4578"  # 耳机
                elif "FACECOVER_" in clone_id:
                    parent_id = "5a341c4686f77469e155819e"  # 面罩
                # 配件类型
                elif "RECEIVER_" in clone_id:
                    parent_id = "55818a304bdc2db5418b457d"  # 机匣
                elif "BARREL_" in clone_id:
                    parent_id = "555ef6e44bdc2de9068b457e"  # 枪管
                elif "STOCK_" in clone_id:
                    parent_id = "55818a594bdc2db9688b456a"  # 枪托
                elif "HANDGUARD_" in clone_id:
                    parent_id = "55818a104bdc2db9688b4569"  # 护木
                elif "GRIP_" in clone_id or "FOREGRIP_" in clone_id:
                    parent_id = "55818af64bdc2d5b648b4570"  # 前握把
                elif "PISTOLGRIP_" in clone_id:
                    parent_id = "55818a684bdc2ddd698b456d"  # 手枪握把
                elif "SIGHT_" in clone_id or "SCOPE_" in clone_id:
                    if "SCOPE_" in clone_id:
                        parent_id = "55818ae44bdc2dde698b456c"  # 高倍瞄具
                    else:
                        parent_id = "55818ad54bdc2ddc698b4569"  # 瞄具
                elif "SILENCER_" in clone_id or "SUPPRESSOR_" in clone_id:
                    parent_id = "550aa4cd4bdc2dd8348b456c"  # 消音器
                elif "FLASHHIDER_" in clone_id or "MUZZLE_" in clone_id:
                    parent_id = "550aa4bf4bdc2dd6348b456b"  # 制退器/枪口
                elif "MOUNT_" in clone_id:
                    parent_id = "55818b224bdc2dde698b456f"  # 导轨

            
            # 如果找到了parent_id，继续处理
            if parent_id:
                item_info["parent_id"] = parent_id
                # 继续使用标准流程处理
            else:
                print(f"  跳过 {item_id}: 无法确定ItemToClone格式的parent_id (ItemToClone={clone_id})")
                return False
        
        # 对于非CLONE/ITEMTOCLONE格式，需要parent_id
        if not parent_id:
            return False
        
        # 检查是否为子弹
        is_ammo_item = self.is_ammo(parent_id)
        
        if is_ammo_item:
            patch = self.create_default_ammo_patch(item_id, item_info)
            # 合并输入属性 (输入文件优先)
            self.merge_input_properties(patch, item_info)
            
            # 应用最优先现实主义数值规则校验（根据核心规则进行校验和推断）
            self.apply_realism_sanity_check(patch)
            
            # 按文件存储
            add_to_file_patches(patch)
            
            self.ammo_patches[item_id] = patch
            processed_items.add(item_id)
            return True
        
        # 检查是否为消耗品
        is_consumable_item = self.is_consumable(parent_id)
        
        if is_consumable_item:
            template_file = self.get_template_for_parent_id(parent_id)
            
            if template_file and template_file in self.templates:
                template_data = self.select_template_data(template_file, item_id, clone_id)
                
                if template_data:
                    patch = template_data
                else:
                    patch = self.create_default_consumable_patch(item_id, item_info)
            else:
                patch = self.create_default_consumable_patch(item_id, item_info)
            
            # 合并输入属性 (输入文件优先)
            self.merge_input_properties(patch, item_info)
            
            # 应用最优先现实主义数值规则校验（根据核心规则进行校验和推断）
            self.apply_realism_sanity_check(patch)
            
            # 按文件存储
            add_to_file_patches(patch)
            
            self.consumables_patches[item_id] = patch
            processed_items.add(item_id)
            return True
        
        # 其他类型（武器/配件）
        template_file = self.get_template_for_parent_id(parent_id)
        
        if not template_file:
            return False
        
        # 获取模板数据
        template_data = self.select_template_data(template_file, item_id, clone_id)
        
        is_weapon_item = item_info["is_weapon"]
        
        if template_data:
            patch = template_data
        else:
            # 使用默认模板
            if is_weapon_item:
                patch = self.create_default_weapon_patch(item_id, item_info)
            else:
                patch = self.create_default_mod_patch(item_id, item_info, template_file)
        
        # 合并输入属性 (输入文件优先)
        self.merge_input_properties(patch, item_info)
        
        # 应用最优先现实主义数值规则校验（根据核心规则进行校验和推断）
        self.apply_realism_sanity_check(patch)
        
        # 按文件存储
        add_to_file_patches(patch)
        
        # 存储补丁
        if is_weapon_item:
            self.weapon_patches[item_id] = patch
        else:
            self.attachment_patches[item_id] = patch
        
        processed_items.add(item_id)
        return True
    
    def process_item_file(self, item_file: Path):
        """处理单个物品文件"""
        # 显示相对于input文件夹的路径
        try:
            relative_path = item_file.relative_to(self.input_path)
            print(f"\n处理文件: {relative_path}")
        except ValueError:
            print(f"\n处理文件: {item_file.name}")
        
        try:
            with open(item_file, 'r', encoding='utf-8') as f:
                items_data = json.load(f)
        except Exception as e:
            print(f"  错误: 无法读取文件: {e}")
            return
        
        # 创建已处理物品集合
        processed_items = set()
        processed_count = 0
        
        # 遍历所有物品
        for item_id, item_data in items_data.items():
            # 使用新的递归处理方法，传入源文件名以实现按文件保存
            if self.process_single_item(item_id, item_data, items_data, processed_items, item_file.stem):
                processed_count += 1
        
        print(f"  处理完成: {processed_count} 个物品")
    
    def generate_patches(self):
        """生成所有补丁"""
        print("\n开始生成现实主义MOD兼容补丁...")
        print(f"物品文件夹: {self.input_path}")
        
        # 递归处理所有JSON文件（包括子文件夹）
        json_files = list(self.input_path.rglob("*.json"))
        print(f"找到 {len(json_files)} 个JSON文件")
        
        for item_file in json_files:
            self.process_item_file(item_file)
        
        print(f"\n生成统计:")
        print(f"  武器补丁: {len(self.weapon_patches)} 个")
        print(f"  配件补丁: {len(self.attachment_patches)} 个")
        print(f"  子弹补丁: {len(self.ammo_patches)} 个")
        print(f"  装备补丁: {len(self.gear_patches)} 个")
        print(f"  消耗品补丁: {len(self.consumables_patches)} 个")
        total = len(self.weapon_patches) + len(self.attachment_patches) + len(self.ammo_patches) + len(self.gear_patches) + len(self.consumables_patches)
        print(f"  总计: {total} 个")
    
    def save_patches(self, output_dir: str = None):
        """保存生成的补丁文件"""
        if output_dir is None:
            output_dir = self.base_path / "output"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        
        print("\n正在导出补丁文件...")
        
        # 1. 按源文件名保存（用户要求的新功能）
        for source_name, patches in self.file_based_patches.items():
            if patches:
                file_output = output_dir / f"{source_name}_realism_patch.json"
                with open(file_output, 'w', encoding='utf-8') as f:
                    json.dump(patches, f, ensure_ascii=False, indent=4)
                print(f"  [源文件分类] 补丁已保存到: {file_output.name}")

        # 2. 同时保留原有的分类保存逻辑（可选，如果您只需要按文件名保存，可以删除以下部分）
        # 保存武器补丁
        if self.weapon_patches:
            weapon_output = output_dir / "weapons_realism_patch.json"
            with open(weapon_output, 'w', encoding='utf-8') as f:
                json.dump(self.weapon_patches, f, ensure_ascii=False, indent=4)
            print(f"  [类型分类] 武器补丁: {weapon_output.name}")
        
        # 保存配件补丁
        if self.attachment_patches:
            attachment_output = output_dir / "attachments_realism_patch.json"
            with open(attachment_output, 'w', encoding='utf-8') as f:
                json.dump(self.attachment_patches, f, ensure_ascii=False, indent=4)
            print(f"配件补丁已保存到: {attachment_output}")
        
        # 保存子弹补丁
        if self.ammo_patches:
            ammo_output = output_dir / "ammo_realism_patch.json"
            with open(ammo_output, 'w', encoding='utf-8') as f:
                json.dump(self.ammo_patches, f, ensure_ascii=False, indent=4)
            print(f"子弹补丁已保存到: {ammo_output}")
        
        # 保存装备补丁
        if self.gear_patches:
            gear_output = output_dir / "gear_realism_patch.json"
            with open(gear_output, 'w', encoding='utf-8') as f:
                json.dump(self.gear_patches, f, ensure_ascii=False, indent=4)
            print(f"装备补丁已保存到: {gear_output}")
        
        # 保存消耗品补丁
        if self.consumables_patches:
            consumables_output = output_dir / "consumables_realism_patch.json"
            with open(consumables_output, 'w', encoding='utf-8') as f:
                json.dump(self.consumables_patches, f, ensure_ascii=False, indent=4)
            print(f"消耗品补丁已保存到: {consumables_output}")
        
        # 保存合并的补丁
        all_patches = {**self.weapon_patches, **self.attachment_patches, **self.ammo_patches, **self.gear_patches, **self.consumables_patches}
        if all_patches:
            combined_output = output_dir / "all_items_realism_patch.json"
            with open(combined_output, 'w', encoding='utf-8') as f:
                json.dump(all_patches, f, ensure_ascii=False, indent=4)
            print(f"合并补丁已保存到: {combined_output}")


def main():
    """主函数"""
    print("=" * 60)
    print("EFT 现实主义MOD兼容补丁生成器 v2.4")
    print("=" * 60)
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建生成器
    generator = RealismPatchGenerator(script_dir)
    
    # 生成补丁
    generator.generate_patches()
    
    # 保存补丁
    generator.save_patches()
    
    print("\n" + "=" * 60)
    print("补丁生成完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
