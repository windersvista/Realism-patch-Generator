#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EFT 现实主义MOD兼容补丁生成器 v2.0
用于根据Items文件夹中的物品数据，使用模板生成Realism MOD兼容配置文件

版本历史:
- v2.0 (2026-02-20): ItemToClone 格式支持（本次更新）
- v1.9 (2026-02-20): 支持递归读取 Items 文件夹下的所有子文件夹中的 JSON 文件
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
    "5448e54d4bdc2dcc718b4568": "armor/ArmorTemplates.json",
    # 装甲板 (ARMORPLATE)
    "644120aa86ffbe10ee032b6f": "armor/ArmorPlateTemplates.json",
    # 装甲插板 (Armor_Plate)
    "5b5f704686f77447ec5d76d7": "armor/ArmorPlateTemplates.json",
    # 背包 (BACKPACK)
    "5448e53e4bdc2d60728b4567": "armor/BackpackTemplates.json",
    # 胸挂 (CHEST_RIG)
    "5448e5284bdc2dcb718b4567": "armor/ChestRigTemplates.json",
    # 护甲装备 (ARMORED_EQUIPMENT)
    "57bef4c42459772e8d35a53b": "armor/ArmoredEquipmentTemplates.json",
    # 头盔 (HEADWEAR)
    "5a341c4086f77401f2541505": "armor/HelmetTemplates.json",
    # 面罩 (FACECOVER)
    "5a341c4686f77469e155819e": "armor/FaceCoverTemplates.json",
    # 耳机 (HEADPHONES)
    "5645bcb74bdc2ded0b8b4578": "armor/HeadphonesTemplates.json",
    # 臂章 (ARMBAND)
    "5b3f15d486f77432d0509248": "armor/ArmbandTemplates.json",
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
        self.items_path = self.base_path / "Items"
        self.templates_base_path = self.base_path / "现实主义物品模板"
        
        # 加载所有模板
        self.templates = {}
        self.load_all_templates()
        
        # 存储生成的补丁
        self.weapon_patches = {}
        self.attachment_patches = {}
        self.ammo_patches = {}
        self.gear_patches = {}
        self.consumables_patches = {}
        
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
            info["properties"] = item_data.get("overrideProperties", {})
            # 通过parentId判断是否为武器
            if info["parent_id"]:
                info["is_weapon"] = self.is_weapon(info["parent_id"])
        
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
            # 从locales提取名称
            if "locales" in item_data and "Name" in item_data["locales"]:
                info["name"] = item_data["locales"]["Name"]
            # 从items._props提取属性
            if "items" in item_data and "_props" in item_data["items"]:
                info["properties"] = item_data["items"]["_props"]
            # clone格式需要通过clone ID查找parent_id和类型
            # 这将在后续处理中通过find_template_by_id完成
        
        return info
    
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
        
        # 首先尝试精确匹配ItemID
        if item_id in template_data:
            result = copy.deepcopy(template_data[item_id])
            # 确保ItemID正确
            result["ItemID"] = item_id
            return result
        
        # 如果没有精确匹配，随机选择一个模板作为基础
        if template_data:
            random_template = random.choice(list(template_data.values()))
            result = copy.deepcopy(random_template)
            result["ItemID"] = item_id
            # 保留Name属性，或者生成一个基于ItemID的Name
            if "Name" in result:
                # 保留模板的Name作为参考
                pass
            else:
                # 如果模板没有Name，生成一个
                result["Name"] = f"item_{item_id}"
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
    
    def process_single_item(self, item_id: str, item_data: Dict, items_data: Dict, processed_items: set) -> bool:
        """
        处理单个物品，支持递归处理 clone 引用
        
        Args:
            item_id: 物品ID
            item_data: 物品数据
            items_data: 当前文件的所有物品数据
            processed_items: 已处理的物品ID集合
            
        Returns:
            bool: 是否成功处理
        """
        # 如果已经处理过，直接返回
        if item_id in processed_items:
            return True
        
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
                if item_info.get("name") and "Name" in template_data:
                    template_data["Name"] = item_info["name"]
                
                # 根据类型分类存储
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
                if self.process_single_item(clone_id, items_data[clone_id], items_data, processed_items):
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
                # 如果有name信息，更新Name字段
                if item_info.get("name") and "Name" in template_data:
                    template_data["Name"] = item_info["name"]
                
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
                    if item_info.get("name") and "Name" in patch:
                        patch["Name"] = item_info["name"]
                else:
                    patch = self.create_default_consumable_patch(item_id, item_info)
            else:
                patch = self.create_default_consumable_patch(item_id, item_info)
            
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
            if item_info.get("name") and "Name" in patch:
                patch["Name"] = item_info["name"]
        else:
            # 使用默认模板
            if is_weapon_item:
                patch = self.create_default_weapon_patch(item_id, item_info)
            else:
                patch = self.create_default_mod_patch(item_id, item_info, template_file)
        
        # 存储补丁
        if is_weapon_item:
            self.weapon_patches[item_id] = patch
        else:
            self.attachment_patches[item_id] = patch
        
        processed_items.add(item_id)
        return True
    
    def process_item_file(self, item_file: Path):
        """处理单个物品文件"""
        # 显示相对于Items文件夹的路径
        try:
            relative_path = item_file.relative_to(self.items_path)
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
            # 使用新的递归处理方法
            if self.process_single_item(item_id, item_data, items_data, processed_items):
                processed_count += 1
        
        print(f"  处理完成: {processed_count} 个物品")
    
    def generate_patches(self):
        """生成所有补丁"""
        print("\n开始生成现实主义MOD兼容补丁...")
        print(f"物品文件夹: {self.items_path}")
        
        # 递归处理所有JSON文件（包括子文件夹）
        json_files = list(self.items_path.rglob("*.json"))
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
        
        # 保存武器补丁
        if self.weapon_patches:
            weapon_output = output_dir / "weapons_realism_patch.json"
            with open(weapon_output, 'w', encoding='utf-8') as f:
                json.dump(self.weapon_patches, f, ensure_ascii=False, indent=4)
            print(f"\n武器补丁已保存到: {weapon_output}")
        
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
    print("EFT 现实主义MOD兼容补丁生成器 v2.0")
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
