#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import random
import shutil
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Mapping, TypedDict
import copy
from generator_static_data import (
    DEFAULT_AMMO_TEMPLATE,
    DEFAULT_CONSUMABLE_TEMPLATE,
    DEFAULT_MOD_TEMPLATE,
    DEFAULT_WEAPON_TEMPLATE,
    HANDBOOK_PARENT_TO_ID,
    ITEM_TYPE_NAME_TO_ID,
    MOD_TYPE_SPECIFIC_ATTRS,
    PARENT_ID_TO_TEMPLATE,
)
from weapon_rule_ranges import WEAPON_PROFILE_RANGES
from attachment_rule_ranges import MOD_PROFILE_RANGES
from ammo_rule_ranges import (
    AMMO_PROFILE_KEYWORDS,
    AMMO_PROFILE_RANGES,
    AMMO_SPECIAL_KEYWORDS,
    AMMO_SPECIAL_MODIFIERS,
    AMMO_PENETRATION_TIERS,
    AMMO_PENETRATION_MODIFIERS,
)
from gear_rule_ranges import GEAR_PROFILE_RANGES
from weapon_refinement_rules import (
    CALIBER_PROFILE_KEYWORDS,
    WEAPON_CALIBER_RULE_MODIFIERS,
    WEAPON_STOCK_RULE_MODIFIERS,
)

# 武器类型 parent_id 分组（用于应用武器规则指南中的典型范围）
WEAPON_PARENT_GROUPS = {
    "assault": {
        "5447b5f14bdc2d61278b4567",  # ASSAULT_RIFLE
        "5447b5fc4bdc2d87278b4567",  # ASSAULT_CARBINE
    },
    "pistol": {
        "5447b5cf4bdc2d65278b4567",  # HANDGUN
    },
    "smg": {
        "5447b5e04bdc2d62278b4567",  # SMG
    },
    "sniper": {
        "5447b6194bdc2d67278b4567",  # MARKSMAN_RIFLE
        "5447b6254bdc2dc3278b4568",  # SNIPER_RIFLE
    },
    "shotgun": {
        "5447b6094bdc2dc3278b4567",  # SHOTGUN
    },
    "machinegun": {
        "5447bed64bdc2d97278b4568",  # MACHINEGUN
    },
    "launcher": {
        "5447bedf4bdc2d87278b4568",  # GRENADE_LAUNCHER
    },
}

# 武器规则范围已拆分到 weapon_rule_ranges.py，便于独立维护与调参。
# 附件规则范围已拆分到 attachment_rule_ranges.py，便于独立维护与调参。
# Gear 规则范围已拆分到 gear_rule_ranges.py，便于独立维护与调参。

GUN_CLAMP_RULES = {
    "Ergonomics": (10, 100),
    "VerticalRecoil": (10, 700),
    "HorizontalRecoil": (20, 700),
    "Convergence": (1, 40),
    "LoyaltyLevel": (1, 5),
}

MOD_CLAMP_RULES = {
    "VerticalRecoil": (-35.0, 35.0),
    "HorizontalRecoil": (-35.0, 35.0),
    "Dispersion": (-55.0, 55.0),
    "Loudness": (-45, 50),
    "Accuracy": (-15, 15),
    "LoyaltyLevel": (1, 4),
}

GEAR_CLAMP_RULES = {
    "ReloadSpeedMulti": (0.85, 1.25),
    "Comfort": (0.6, 1.4),
    "speedPenaltyPercent": (-40, 10),
}

MAG_CAPACITY_NAME_REGEX = re.compile(r"\b(\d{1,3})(?:\s*|-)?(?:round|rnd|rds)\b", re.IGNORECASE)
MAG_CAPACITY_CN_REGEX = re.compile(r"(?<!\d)(\d{1,3})\s*发")
MAG_CAPACITY_RU_REGEX = re.compile(r"(?<![\d.])(\d{1,3})\s*патрон", re.IGNORECASE)
BARREL_LENGTH_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*(mm|inch|in|\")")


class ItemInfo(TypedDict):
    item_id: str
    parent_id: Optional[str]
    clone_id: Optional[str]
    template_id: Optional[str]
    template_file: Optional[str]
    name: Optional[str]
    is_weapon: bool
    is_gear: bool
    is_consumable: bool
    item_type: Optional[str]
    properties: Dict[str, Any]
    source_file: Optional[str]
    format_type: Optional[str]


PatchData = Dict[str, Any]
JsonObject = Dict[str, Any]


class RealismPatchGenerator:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.input_path = self.base_path / "input"
        self.templates_base_path = self.base_path / "现实主义物品模板"
        self.random_seed = 20260313
        self.random = random.Random(self.random_seed)
        
        # 加载所有模板
        self.templates = {}
        self.template_by_id = {}
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
        # 记录每个源文件的导出命名策略：plain(原文件名) / suffix(_realism_patch)
        self.file_output_mode = {}
        # 当文件内 CURRENT_PATCH 占比“超过该阈值”时，导出保持原文件名。
        # 0.5 表示“多数（>50%）即按原名输出”。
        self.current_patch_plain_ratio_threshold = 0.5
        self._template_parent_index = self._build_template_parent_index()

    def _load_templates_from_dir(self, relative_dir: str):
        """按稳定顺序加载指定目录下的所有模板文件。"""
        template_dir = self.templates_base_path / relative_dir
        if not template_dir.exists():
            return

        for template_file in sorted(template_dir.glob("*.json"), key=lambda path: path.name.lower()):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                    self.templates[template_file.name] = template_data
                    print(f"  已加载: {template_file.name} ({len(template_data)} 个模板)")
            except Exception as e:
                print(f"  警告: 无法加载 {template_file.name}: {e}")

    def _build_template_parent_index(self) -> Dict[str, List[str]]:
        """构建 template_file -> parent_id 列表索引（按 PARENT_ID_TO_TEMPLATE 反向生成）。"""
        index: Dict[str, List[str]] = {}
        for parent_id, template_path in PARENT_ID_TO_TEMPLATE.items():
            # AMMO 是特殊标记，不是模板文件。
            if template_path == "AMMO":
                continue
            template_name = os.path.basename(template_path)
            index.setdefault(template_name, []).append(parent_id)
        return index

    def _apply_field_clamps(self, patch: PatchData, clamp_rules: Mapping[str, Tuple[float | int, float | int]]):
        """按字段-区间规则批量夹紧。"""
        for field, (min_v, max_v) in clamp_rules.items():
            if field in patch:
                patch[field] = self._clamp(patch[field], min_v, max_v)

    def _infer_template_file_from_source_file(self, source_file: Optional[str]) -> Optional[str]:
        """根据输入源相对路径推断模板文件名（优先服务 CURRENT_PATCH）。"""
        if not source_file:
            return None

        source_path = Path(source_file)
        if source_path.suffix:
            template_name = source_path.name
        else:
            template_name = f"{source_path.name}.json"

        # 只对规范目录启用，避免误将任意文件名当作模板。
        top_level = source_path.parts[0].lower() if source_path.parts else ""
        if top_level in {"weapons", "attatchments", "gear", "ammo", "consumables"}:
            return template_name
        return None

    def _infer_parent_id_from_template_file(self, template_file: Optional[str]) -> Optional[str]:
        """根据模板文件名反推 parent_id（CURRENT_PATCH 缺 parentId 时使用）。"""
        if not template_file:
            return None

        parent_ids = self._template_parent_index.get(template_file, [])
        if len(parent_ids) == 1:
            return parent_ids[0]

        # 多 parent 共享同模板时，给出稳定优先 parent（避免随机漂移）。
        preferred_parent_by_template = {
            "ScopeTemplates.json": "55818ae44bdc2dde698b456c",
            "MuzzleDeviceTemplates.json": "550aa4bf4bdc2dd6348b456b",
            "FlashlightLaserTemplates.json": "55818b084bdc2d5b648b4571",
            "ReceiverTemplates.json": "55818a304bdc2db5418b457d",
            "UBGLTempaltes.json": "55818b014bdc2ddc698b456b",
            "armorPlateTemplates.json": "644120aa86ffbe10ee032b6f",
            "meds.json": "5448f3ac4bdc2dce718b4569",
            "food.json": "5448e8d04bdc2ddf718b4569",
        }
        preferred = preferred_parent_by_template.get(template_file)
        if preferred:
            return preferred

        return None

    def _enrich_item_info_with_source_context(
        self,
        info: ItemInfo,
        item_data: JsonObject,
        format_type: str,
        source_file: Optional[str],
    ):
        """统一补全 item_info 上下文，让 CURRENT_PATCH 成为一等输入格式。"""
        info["format_type"] = format_type
        info["source_file"] = source_file

        # 1) 先从 source_file 推模板文件，供 CURRENT_PATCH 直接使用。
        if not info.get("template_file"):
            source_template = self._infer_template_file_from_source_file(source_file)
            if source_template:
                info["template_file"] = source_template

        # 2) parent_id 缺失时，按模板文件反推（武器/核心配件）。
        if not info.get("parent_id") and info.get("template_file"):
            inferred_parent = self._infer_parent_id_from_template_file(info.get("template_file"))
            if inferred_parent:
                info["parent_id"] = inferred_parent

        # 3) 当前 patch 的 item_type 通常可信，用于稳定分类。
        item_type = str(info.get("item_type") or item_data.get("$type") or "")
        if item_type:
            info["item_type"] = item_type
        if "RealismMod.Gun" in item_type:
            info["is_weapon"] = True
        elif "RealismMod.Gear" in item_type:
            info["is_gear"] = True
        elif "RealismMod.Consumable" in item_type:
            info["is_consumable"] = True

        # 4) source_file 目录兜底分类（用于 item_type 异常或缺失场景）。
        src = str(source_file or "").lower()
        if src.startswith("weapons/"):
            info["is_weapon"] = True
        elif src.startswith("gear/"):
            info["is_gear"] = True
        elif src.startswith("consumables/"):
            info["is_consumable"] = True

    def _rebuild_template_id_index(self):
        """构建模板ID索引，保持“先加载的模板优先”语义。"""
        self.template_by_id = {}
        for template_data in self.templates.values():
            if not isinstance(template_data, dict):
                continue
            for template_id, template_item in template_data.items():
                if template_id not in self.template_by_id:
                    self.template_by_id[template_id] = template_item

    def _clamp(self, value: Any, min_v: float, max_v: float) -> Any:
        """仅对数值执行夹紧，其余类型保持不变。"""
        if isinstance(value, (int, float)):
            return max(min_v, min(max_v, value))
        return value

    def _weighted_sample_in_range(self, original_value: Any, min_v: float, max_v: float, prefer_int: Optional[bool] = None) -> Any:
        """在规则区间内按权重重算数值。

        权重策略：以“原值(夹紧后)”与“区间中点”的加权结果作为三角分布 mode，
        既保留原始物品风格，又确保结果落在规则范围内并发生重算。
        """
        if min_v > max_v:
            min_v, max_v = max_v, min_v

        if prefer_int is None:
            prefer_int = False

        if min_v == max_v:
            return int(round(min_v)) if prefer_int else float(min_v)

        if isinstance(original_value, bool) or not isinstance(original_value, (int, float)):
            return original_value

        clamped_original = self._clamp(float(original_value), min_v, max_v)
        center = (float(min_v) + float(max_v)) / 2.0

        # 越偏向原值，越能保留物品个体差异；其余权重回归规则中位。
        preserve_ratio = 0.7
        mode = clamped_original * preserve_ratio + center * (1.0 - preserve_ratio)
        sampled = self.random.triangular(float(min_v), float(max_v), float(mode))

        if prefer_int:
            return int(round(sampled))

        precision = self._infer_float_precision(min_v, max_v)
        return round(self._clamp(round(sampled, precision), min_v, max_v), precision)

    def _infer_float_precision(self, *values: float) -> int:
        """根据范围值推断浮点保留位数，避免小概率字段被量化到范围外。"""
        precision = 2
        for value in values:
            normalized = f"{float(value):.6f}".rstrip("0").rstrip(".")
            if "." not in normalized:
                continue
            precision = max(precision, len(normalized.split(".", 1)[1]))
        return max(2, min(4, precision))

    def _get_range_seed_value(self, min_v: float, max_v: float, prefer_int: bool) -> float | int:
        """为缺失字段生成范围内的初始基准值。"""
        if min_v > max_v:
            min_v, max_v = max_v, min_v

        # 区间跨过 0 时，以 0 作为中性基准；否则取中点。
        seed = 0.0 if min_v <= 0 <= max_v else (min_v + max_v) / 2.0
        if prefer_int:
            return int(round(seed))
        return round(float(seed), self._infer_float_precision(min_v, max_v))

    def _apply_numeric_ranges(self, patch: PatchData, ranges: Dict[str, tuple], ensure_fields: bool = False):
        """按规则范围对补丁字段进行加权重算。"""
        for key, range_pair in ranges.items():
            if not (isinstance(range_pair, tuple) and len(range_pair) == 2):
                continue

            min_v = float(range_pair[0])
            max_v = float(range_pair[1])
            prefer_int = isinstance(range_pair[0], int) and isinstance(range_pair[1], int)

            if key not in patch:
                if not ensure_fields:
                    continue
                patch[key] = self._get_range_seed_value(min_v, max_v, prefer_int)

            patch[key] = self._weighted_sample_in_range(patch[key], min_v, max_v, prefer_int=prefer_int)

    def _infer_weapon_profile(self, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> Optional[str]:
        """推断武器规则档位。"""
        parent_id = self.normalize_parent_id((item_info or {}).get("parent_id")) if item_info else None
        if parent_id:
            for profile, parent_set in WEAPON_PARENT_GROUPS.items():
                if parent_id in parent_set:
                    return profile

        template_file = str((item_info or {}).get("template_file") or "") if item_info else ""
        template_profile_map = {
            "AssaultRifleTemplates.json": "assault",
            "AssaultCarbineTemplates.json": "assault",
            "PistolTemplates.json": "pistol",
            "SMGTemplates.json": "smg",
            "MarksmanRifleTemplates.json": "sniper",
            "SniperRifleTemplates.json": "sniper",
            "ShotgunTemplates.json": "shotgun",
            "MachinegunTemplates.json": "machinegun",
            "GrenadeLauncherTemplates.json": "launcher",
            "SpecialWeaponTemplates.json": "assault",
        }
        if template_file in template_profile_map:
            return template_profile_map[template_file]

        name = str(patch.get("Name", "")).lower()
        weap_type = str(patch.get("WeapType", "")).lower()
        name_tokens = set(re.findall(r"[a-z0-9]+", name))

        if any(k in name for k in ["pistol", "handgun"]) or "pistol" in weap_type:
            return "pistol"
        if "smg" in name or "smg" in weap_type:
            return "smg"
        if any(k in name for k in ["launcher", "grenade launcher", "m203", "gp25", "ubgl"]) or "launcher" in weap_type:
            return "launcher"
        if any(k in name for k in ["sniper", "marksman", "dmr", "anti-materiel", "anti materiel", "狙击"]):
            return "sniper"
        if "lmg" in name_tokens or "mg" in name_tokens or "machinegun" in name or "machinegun" in weap_type:
            return "machinegun"
        if "shotgun" in name or "shotgun" in weap_type:
            return "shotgun"
        if any(k in name for k in ["carbine", "assault", "rifle"]):
            return "assault"
        return None

    def _extract_gear_armor_class_text(self, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> str:
        """提取装备防护等级相关文本，用于轻量级 gear 细分。"""
        candidates = [patch.get("ArmorClass"), patch.get("Name")]

        if item_info and isinstance(item_info.get("properties"), dict):
            props = item_info["properties"]
            candidates.extend([
                props.get("ArmorClass"),
                props.get("armorClass"),
                props.get("Name"),
                props.get("name"),
            ])

        return " ".join(str(value) for value in candidates if value).lower()

    def _infer_armor_plate_profile(self, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> str:
        """根据名称与防护文本区分软插板和硬插板。"""
        armor_text = self._extract_gear_armor_class_text(patch, item_info)
        helmet_keywords = [
            "helmet_armor",
            "helmet armor",
            "helmet",
            "ears",
            "nape",
            "top",
            "jaw",
            "eyes",
        ]
        soft_keywords = [
            "soft armor",
            "soft",
            "backer",
            "iiia",
            "gost 2",
            "gost 2a",
            "2a",
            "3a",
            "soft_armor",
            "软甲",
            "软插板",
        ]
        if self._contains_any_keyword(armor_text, helmet_keywords):
            return "armor_plate_helmet"
        if self._contains_any_keyword(armor_text, soft_keywords):
            return "armor_plate_soft"
        return "armor_plate_hard"

    def _infer_body_armor_profile(self, base_profile: str, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> str:
        """按 ArmorClass 将护甲背心和护甲胸挂细分为轻型/重型。"""
        armor_text = self._extract_gear_armor_class_text(patch, item_info)

        heavy_keywords = [
            "gost 4",
            "gost 5",
            "gost 5a",
            "gost 6",
            "nij iii+",
            "nij iv",
            "rf3",
            "xsapi",
            "esapi",
            "mk4a",
            "rev. g",
            "rev. j",
            "pm 5",
            "pm 8",
            "pm 10",
            "plates",
        ]
        light_keywords = [
            "gost 2",
            "gost 2a",
            "gost 3",
            "gost 3a",
            "nij ii",
            "nij iia",
            "nij iii",
            "pm 2",
            "pm 3",
        ]

        if any(keyword in armor_text for keyword in heavy_keywords):
            return f"{base_profile}_heavy"
        if any(keyword in armor_text for keyword in light_keywords):
            return f"{base_profile}_light"
        return f"{base_profile}_heavy"

    def _infer_cosmetic_gear_profile(self, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> Optional[str]:
        """仅对带防毒/防辐射语义或明确头饰语义的 cosmetic 条目应用 gear 规则。"""
        name = str(patch.get("Name", "")).lower()
        props = (item_info or {}).get("properties") or {}

        if patch.get("IsGasMask"):
            return "cosmetic_gasmask"
        if any(key in patch for key in ["GasProtection", "RadProtection"]):
            return "cosmetic_gasmask"
        if any(key in props for key in ["GasProtection", "gasProtection", "RadProtection", "radProtection"]):
            return "cosmetic_gasmask"
        if self._contains_any_keyword(name, ["gas mask", "respirator", "防毒", "防毒面具", "gasmask", "maska"]):
            return "cosmetic_gasmask"
        if self._contains_any_keyword(name, ["beret", "贝雷帽", "cap", "帽", "boonie", "watch cap"]):
            return "cosmetic_headwear"
        return None

    def _infer_helmet_profile(self, patch: PatchData) -> str:
        """根据头盔平台语义细分轻型/重型头盔。"""
        name = str(patch.get("Name", "")).lower()

        if self._contains_any_keyword(
            name,
            [
                "altyn",
                "rys",
                "ronin",
                "maska",
                "vulkan",
                "tor",
                "zsh",
                "lshz",
                "kiver",
                "sphera",
                "devtac",
                "k1c",
                "shpm",
                "psh97",
                "ssh-68",
                "ssh68",
                "neosteel",
            ],
        ):
            return "helmet_heavy"

        return "helmet_light"

    def _infer_face_protection_profile(self, base_profile: str, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> str:
        """细分头盔附加护具与面罩类防护。"""
        name = str(patch.get("Name", "")).lower()
        armor_text = self._extract_gear_armor_class_text(patch, item_info)

        if base_profile == "armor_component":
            if self._contains_any_keyword(name, ["shield", "face shield", "faceshield", "visor", "面甲", "面罩"]):
                return "armor_component_faceshield"
            return "armor_component_accessory"

        ballistic_keywords = ["nij", "gost", "v50", "anti-shatter", "ansi", "mil-prf", "bs en", "ballistic"]
        if any(keyword in armor_text for keyword in ballistic_keywords):
            return "armor_mask_ballistic"
        return "armor_mask_decorative"

    def _infer_backpack_profile(self, patch: PatchData) -> str:
        """按体积语义将背包细分为 compact 与 full 两档。"""
        name = str(patch.get("Name", "")).lower()

        if self._contains_any_keyword(
            name,
            [
                "sling",
                "daypack",
                "day pack",
                "drawbridge",
                "switchblade",
                "medpack",
                "medbag",
                "redfox",
                "wild",
                "takedown",
                "t20",
                "vertx",
            ],
        ):
            return "backpack_compact"

        return "backpack_full"

    def _infer_eyewear_profile(self, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> str:
        """按防护文本细分普通防碎镜与弹道护目镜。"""
        armor_text = self._extract_gear_armor_class_text(patch, item_info)
        ballistic_keywords = ["v50", "anti-shatter", "ansi", "mil-prf", "ballistic", "z87", "31013"]

        if any(keyword in armor_text for keyword in ballistic_keywords):
            return "protective_eyewear_ballistic"
        return "protective_eyewear_standard"

    def _infer_chest_rig_profile(self, patch: PatchData) -> str:
        """按承载量语义区分轻载与重载胸挂。"""
        name = str(patch.get("Name", "")).lower()

        if self._contains_any_keyword(
            name,
            [
                "bankrobber",
                "micro",
                "d3crx",
                "cs_assault",
                "thunderbolt",
                "bssmk1",
                "recon",
                "zulu",
            ],
        ):
            return "chest_rig_light"

        return "chest_rig_heavy"

    def _infer_gear_profile(self, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> Optional[str]:
        """推断 Gear 规则档位。"""
        parent_id = self.normalize_parent_id((item_info or {}).get("parent_id")) if item_info else None
        template_file = str((item_info or {}).get("template_file") or "") if item_info else ""
        name = str(patch.get("Name", "")).lower()
        armor_class = str(patch.get("ArmorClass", "") or "").strip().lower()
        has_armor_class = bool(armor_class and armor_class not in {"unclassified", "none", "null"})

        if parent_id in {"644120aa86ffbe10ee032b6f", "5b5f704686f77447ec5d76d7"}:
            return self._infer_armor_plate_profile(patch, item_info)

        parent_profile_map = {
            "5448e54d4bdc2dcc718b4568": "armor_vest",
            "57bef4c42459772e8d35a53b": "armor_chest_rig",
            "5448e5284bdc2dcb718b4567": "chest_rig",
            "5a341c4086f77401f2541505": "helmet",
            "5a341c4686f77469e155819e": "armor_mask",
            "55d7217a4bdc2d86028b456d": "armor_component",
            "5448e53e4bdc2d60728b4567": "backpack",
            "5645bcb74bdc2ded0b8b4578": "headset",
            "5b3f15d486f77432d0509248": "cosmetic_gasmask",
        }
        if parent_id in parent_profile_map:
            profile = parent_profile_map[parent_id]
            if profile == "helmet":
                return self._infer_helmet_profile(patch)
            if profile in {"armor_vest", "armor_chest_rig"}:
                return self._infer_body_armor_profile(profile, patch, item_info)
            if profile == "chest_rig":
                return self._infer_chest_rig_profile(patch)
            if profile == "backpack":
                return self._infer_backpack_profile(patch)
            if profile in {"armor_component", "armor_mask"}:
                return self._infer_face_protection_profile(profile, patch, item_info)
            if profile == "cosmetic_gasmask":
                return self._infer_cosmetic_gear_profile(patch, item_info)
            return profile

        template_profile_map = {
            "armorVestsTemplates.json": "armor_vest",
            "armorChestrigTemplates.json": "armor_chest_rig",
            "chestrigTemplates.json": "chest_rig",
            "helmetTemplates.json": "helmet",
            "armorMasksTemplates.json": "armor_mask",
            "armorComponentsTemplates.json": "armor_component",
            "bagTemplates.json": "backpack",
            "headsetTemplates.json": "headset",
        }
        if template_file == "armorPlateTemplates.json":
            return self._infer_armor_plate_profile(patch, item_info)
        if template_file == "cosmeticsTemplates.json":
            return self._infer_cosmetic_gear_profile(patch, item_info)
        if template_file == "helmetTemplates.json":
            return self._infer_helmet_profile(patch)
        if template_file == "armorVestsTemplates.json":
            return self._infer_body_armor_profile("armor_vest", patch, item_info)
        if template_file == "armorChestrigTemplates.json":
            return self._infer_body_armor_profile("armor_chest_rig", patch, item_info)
        if template_file == "chestrigTemplates.json":
            return self._infer_chest_rig_profile(patch)
        if template_file == "bagTemplates.json":
            return self._infer_backpack_profile(patch)
        if template_file == "armorMasksTemplates.json" and self._contains_any_keyword(
            name, ["glasses", "goggles", "eyewear", "射击眼镜", "护目镜", "眼镜", "condor"]
        ):
            return self._infer_eyewear_profile(patch, item_info)
        if template_file == "armorMasksTemplates.json":
            return self._infer_face_protection_profile("armor_mask", patch, item_info)
        if template_file == "armorComponentsTemplates.json":
            return self._infer_face_protection_profile("armor_component", patch, item_info)
        if template_file in template_profile_map:
            return template_profile_map[template_file]

        if self._contains_any_keyword(name, ["headset", "headphones", "耳机", "耳麦"]):
            return "headset"
        if self._contains_any_keyword(name, ["beret", "贝雷帽", "boonie", "watch cap"]):
            return "cosmetic_headwear"
        if self._contains_any_keyword(name, ["back panel", "背部面板"]):
            return "back_panel"
        if self._contains_any_keyword(name, ["腰带", "belt", "warbelt", "battle belt", "警用腰带", "mule"]):
            return "belt_harness"
        if self._contains_any_keyword(name, ["backpack", "ruck", "pack", "bag", "背包", "背负系统", "bvs", "nice comm"]):
            return self._infer_backpack_profile(patch)
        if self._contains_any_keyword(name, ["soft armor", "armor plate", "plate", "插板", "软甲", "防弹插板"]):
            return self._infer_armor_plate_profile(patch, item_info)
        if self._contains_any_keyword(name, ["helmet", "头盔", "helm", "ops-core", "ops core", "fast mt", "tc2000", "mich", "ronin"]):
            return self._infer_helmet_profile(patch)
        if self._contains_any_keyword(name, ["glasses", "goggles", "eyewear", "射击眼镜", "护目镜", "眼镜", "condor"]):
            return self._infer_eyewear_profile(patch, item_info)
        if self._contains_any_keyword(name, ["visor", "face shield", "mandible", "aventail", "side armor", "applique", "护颈", "面甲"]):
            return self._infer_face_protection_profile("armor_component", patch, item_info)
        if self._contains_any_keyword(name, ["gas mask", "respirator", "mask", "面罩", "防毒"]):
            return self._infer_face_protection_profile("armor_mask", patch, item_info)
        if self._contains_any_keyword(
            name,
            [
                "plate carrier",
                "armor rig",
                "armored rig",
                "carrier",
                "jpc",
                "apc",
                "sohpc",
                "cgpc",
                "avs",
                "tqs",
                "战术背心",
                "携行背心",
                "板携行",
                "板携行背心",
                "护甲胸挂",
                "防弹胸挂",
            ],
        ):
            return self._infer_body_armor_profile("armor_chest_rig", patch, item_info)
        if has_armor_class and self._contains_any_keyword(name, ["rig", "胸挂", "背心", "vest"]):
            return self._infer_body_armor_profile("armor_chest_rig", patch, item_info)
        if self._contains_any_keyword(name, ["rig", "胸挂"]):
            return self._infer_chest_rig_profile(patch)
        if has_armor_class and self._contains_any_keyword(name, ["背心", "vest"]):
            return self._infer_body_armor_profile("armor_vest", patch, item_info)
        if self._contains_any_keyword(name, ["armor", "vest", "body armor", "护甲", "防弹衣"]):
            return self._infer_body_armor_profile("armor_vest", patch, item_info)

        return None

    def _extract_weapon_caliber_text(self, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> str:
        """提取口径相关文本，用于口径档位推断。"""
        candidates = [
            patch.get("Caliber"),
            patch.get("AmmoCaliber"),
            patch.get("caliber"),
            patch.get("ammoCaliber"),
        ]

        if item_info and isinstance(item_info.get("properties"), dict):
            props = item_info["properties"]
            candidates.extend([
                props.get("Caliber"),
                props.get("ammoCaliber"),
                props.get("AmmoCaliber"),
            ])

        candidates.append(patch.get("Name"))

        merged = " ".join(str(v) for v in candidates if v)
        return merged.lower()

    def _infer_weapon_caliber_profile(self, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> Optional[str]:
        """推断口径细分档位。"""
        caliber_text = self._extract_weapon_caliber_text(patch, item_info)
        weap_type = str(patch.get("WeapType", "")).lower()
        name = str(patch.get("Name", "")).lower()

        for profile, keywords in CALIBER_PROFILE_KEYWORDS:
            if any(k in caliber_text for k in keywords):
                return profile

        if "pistol" in weap_type or any(k in name for k in ["pistol", "handgun"]):
            return "pistol_caliber"

        return None

    def _infer_weapon_stock_profile(self, patch: PatchData) -> str:
        """推断枪托形态档位。"""
        name = str(patch.get("Name", "")).lower()
        weap_type = str(patch.get("WeapType", "")).lower()
        has_shoulder = patch.get("HasShoulderContact")

        if "bullpup" in name or "bullpup" in weap_type:
            return "bullpup"

        if "pistol" in weap_type or any(k in name for k in ["pistol", "machine pistol", "stockless"]):
            return "stockless"

        if any(k in name for k in ["folded", "stock folded", "no stock"]):
            return "folding_stock_collapsed"

        if any(k in name for k in ["fold", "folding"]):
            return "folding_stock_extended" if has_shoulder is not False else "folding_stock_collapsed"

        if has_shoulder is False:
            return "stockless"

        return "fixed_stock"

    def _extract_ammo_caliber_text(self, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> str:
        """提取弹药口径相关文本，用于口径分档推断。"""
        candidates = [
            patch.get("Caliber"),
            patch.get("AmmoCaliber"),
            patch.get("ammoCaliber"),
            patch.get("ammoType"),
            patch.get("Name"),
        ]

        if item_info and isinstance(item_info.get("properties"), dict):
            props = item_info["properties"]
            candidates.extend([
                props.get("Caliber"),
                props.get("AmmoCaliber"),
                props.get("ammoCaliber"),
                props.get("ammoType"),
            ])

        merged = " ".join(str(v) for v in candidates if v)
        return merged.lower()

    def _infer_ammo_profile(self, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> str:
        """根据口径关键词推断弹药分档。"""
        caliber_text = self._extract_ammo_caliber_text(patch, item_info)
        for profile, keywords in AMMO_PROFILE_KEYWORDS:
            if any(keyword in caliber_text for keyword in keywords):
                return profile

        # 未匹配到关键词时，使用中间威力步枪弹作为默认档位。
        return "intermediate_rifle"

    def _extract_ammo_variant_text(self, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> str:
        """提取弹种型号相关文本，用于第三层型号分档。"""
        candidates = [
            patch.get("Name"),
            patch.get("ShortName"),
            patch.get("Description"),
            patch.get("AmmoTooltipClass"),
        ]

        if item_info and isinstance(item_info.get("properties"), dict):
            props = item_info["properties"]
            candidates.extend([
                props.get("Name"),
                props.get("ShortName"),
                props.get("Description"),
                props.get("AmmoTooltipClass"),
                props.get("Caliber"),
            ])

        merged = " ".join(str(v) for v in candidates if v)
        return merged.lower()

    def _infer_ammo_special_profile(self, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> Optional[str]:
        """根据弹种型号关键词推断第三层细分档位。"""
        variant_text = self._extract_ammo_variant_text(patch, item_info)

        # 使用词元精确匹配，避免短关键词（如 ap/sp）造成子串误判。
        variant_tokens = set(re.findall(r"[a-z0-9]+", variant_text))

        for profile, keywords in AMMO_SPECIAL_KEYWORDS:
            for keyword in keywords:
                normalized = str(keyword).strip().lower().replace("-", " ").replace("_", " ")
                if not normalized:
                    continue

                if " " in normalized:
                    # 复合关键词（如 "soft point"）保留短语匹配能力。
                    if normalized in variant_text:
                        return profile
                    parts = [part for part in normalized.split(" ") if part]
                    if parts and all(part in variant_tokens for part in parts):
                        return profile
                elif normalized in variant_tokens:
                    return profile

        return None

    def _try_parse_number(self, value: Any) -> Optional[float]:
        """将输入值解析为数字。"""
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                return None
        return None

    def _extract_penetration_value(self, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> Optional[float]:
        """提取穿深数值（PenetrationPower）。"""
        pen_value = self._try_parse_number(patch.get("PenetrationPower"))
        if pen_value is not None:
            return pen_value

        if item_info and isinstance(item_info.get("properties"), dict):
            props = item_info["properties"]
            for key in ["PenetrationPower", "Penetration", "penPower"]:
                parsed = self._try_parse_number(props.get(key))
                if parsed is not None:
                    return parsed

        return None

    def _infer_ammo_penetration_tier(self, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> str:
        """根据穿深推断弹药穿深档位。"""
        penetration = self._extract_penetration_value(patch, item_info)
        if penetration is None:
            return "pen_lvl_5"

        for tier, pen_range in AMMO_PENETRATION_TIERS.items():
            if not (isinstance(pen_range, tuple) and len(pen_range) == 2):
                continue
            min_pen = float(pen_range[0])
            max_pen = float(pen_range[1])
            if min_pen <= penetration <= max_pen:
                return tier

        return "pen_lvl_11" if penetration > 130 else "pen_lvl_1"

    def _apply_ammo_profile_ranges(self, patch: PatchData, item_info: Optional[Mapping[str, Any]]):
        """应用弹药规则：口径基础范围 + 穿深分层增量修正。"""
        ammo_profile = self._infer_ammo_profile(patch, item_info)
        if ammo_profile not in AMMO_PROFILE_RANGES:
            return

        penetration_tier = self._infer_ammo_penetration_tier(patch, item_info)
        special_profile = self._infer_ammo_special_profile(patch, item_info)
        penetration_mods = AMMO_PENETRATION_MODIFIERS.get(penetration_tier, {})
        special_mods = AMMO_SPECIAL_MODIFIERS.get(special_profile, {}) if special_profile else {}
        base_ranges = AMMO_PROFILE_RANGES[ammo_profile]
        malfunction_keys = {"MalfMisfireChance", "MisfireChance", "MalfFeedChance"}

        for key, base_range in base_ranges.items():
            if not (isinstance(base_range, tuple) and len(base_range) == 2):
                continue

            tier_pair = penetration_mods.get(key, (0.0, 0.0))
            special_pair = special_mods.get(key, (0.0, 0.0))
            min_v = float(base_range[0]) + float(tier_pair[0]) + float(special_pair[0])
            max_v = float(base_range[1]) + float(tier_pair[1]) + float(special_pair[1])
            if min_v > max_v:
                min_v, max_v = max_v, min_v

            # 故障概率字段统一限制到规则约定区间。
            if key in malfunction_keys:
                min_v = self._clamp(min_v, 0.001, 0.015)
                max_v = self._clamp(max_v, 0.001, 0.015)
                if min_v > max_v:
                    min_v, max_v = max_v, min_v

            # ArmorDamage 采用护甲/插板耐久伤害倍率，统一限制在 1.00~1.20。
            if key == "ArmorDamage":
                min_v = self._clamp(min_v, 1.0, 1.2)
                max_v = self._clamp(max_v, 1.0, 1.2)
                if min_v > max_v:
                    min_v, max_v = max_v, min_v

            if key not in patch:
                prefer_int = isinstance(base_range[0], int) and isinstance(base_range[1], int)
                patch[key] = self._get_range_seed_value(min_v, max_v, prefer_int)
            else:
                prefer_int = isinstance(base_range[0], int) and isinstance(base_range[1], int)

            patch[key] = self._weighted_sample_in_range(patch[key], min_v, max_v, prefer_int=prefer_int)

    def _apply_weapon_refinement_ranges(self, patch: PatchData, weapon_profile: Optional[str], item_info: Optional[Mapping[str, Any]]):
        """应用武器二级细分规则：口径 + 枪托形态。"""
        if not weapon_profile or weapon_profile not in WEAPON_PROFILE_RANGES:
            return

        caliber_profile = self._infer_weapon_caliber_profile(patch, item_info)
        stock_profile = self._infer_weapon_stock_profile(patch)

        caliber_mods = WEAPON_CALIBER_RULE_MODIFIERS.get(caliber_profile, {}) if caliber_profile else {}
        stock_mods = WEAPON_STOCK_RULE_MODIFIERS.get(stock_profile, {}) if stock_profile else {}

        # 按基础范围 + 增量修正计算最终夹紧区间。
        for key, base_range in WEAPON_PROFILE_RANGES[weapon_profile].items():
            if not isinstance(base_range, tuple) or len(base_range) != 2:
                continue

            if key not in patch:
                prefer_int = isinstance(base_range[0], int) and isinstance(base_range[1], int)
                patch[key] = self._get_range_seed_value(float(base_range[0]), float(base_range[1]), prefer_int)
            else:
                prefer_int = isinstance(base_range[0], int) and isinstance(base_range[1], int)

            delta_min = 0.0
            delta_max = 0.0

            if key in caliber_mods:
                delta_min += float(caliber_mods[key][0])
                delta_max += float(caliber_mods[key][1])

            if key in stock_mods:
                delta_min += float(stock_mods[key][0])
                delta_max += float(stock_mods[key][1])

            if delta_min == 0.0 and delta_max == 0.0:
                continue

            min_v = float(base_range[0]) + delta_min
            max_v = float(base_range[1]) + delta_max
            if min_v > max_v:
                min_v, max_v = max_v, min_v

            patch[key] = self._weighted_sample_in_range(patch[key], min_v, max_v, prefer_int=prefer_int)

        # 对基础档位未覆盖但二级规则有明确约束的字段，做补充夹紧。
        supplemental_keys = set(caliber_mods.keys()) | set(stock_mods.keys())
        for key in supplemental_keys:
            if key in WEAPON_PROFILE_RANGES[weapon_profile]:
                continue

            ranges = []
            if key in caliber_mods:
                ranges.append(caliber_mods[key])
            if key in stock_mods:
                ranges.append(stock_mods[key])
            if not ranges:
                continue

            min_v = sum(float(r[0]) for r in ranges)
            max_v = sum(float(r[1]) for r in ranges)
            if min_v > max_v:
                min_v, max_v = max_v, min_v

            if key not in patch:
                prefer_int = all(isinstance(bound, int) for pair in ranges for bound in pair)
                patch[key] = self._get_range_seed_value(min_v, max_v, prefer_int)
            else:
                prefer_int = all(isinstance(bound, int) for pair in ranges for bound in pair)

            patch[key] = self._weighted_sample_in_range(patch[key], min_v, max_v, prefer_int=prefer_int)

    def _infer_magazine_profile(self, capacity: Optional[int], item_name: str) -> str:
        """根据容量与名称推断弹匣档位。"""
        if any(k in item_name for k in ["drum", "casket", "quad", "coupled", "twin", "beta", "helical", "snail"]):
            return "magazine_drum"
        if any(k in item_name for k in ["extended", "extend", "加长", "扩容"]):
            return "magazine_extended"
        if any(k in item_name for k in ["compact", "short", "stubby", "短弹匣", "短匣"]):
            return "magazine_compact"
        if capacity is None:
            return "magazine_standard"
        if capacity <= 20:
            return "magazine_compact"
        if capacity <= 40:
            return "magazine_standard"
        if capacity <= 60:
            return "magazine_extended"
        return "magazine_drum"

    def _extract_barrel_length_mm(self, item_name: str) -> Optional[float]:
        """从名称中提取枪管长度，统一换算为毫米。"""
        length_matches = BARREL_LENGTH_REGEX.findall(item_name)
        if not length_matches:
            return None
        try:
            value_text, unit = length_matches[-1]
            value = float(value_text)
        except (TypeError, ValueError):
            return None
        if unit in {"inch", "in", '"'}:
            return value * 25.4
        return value

    def _infer_barrel_profile_from_name(self, item_name: str) -> str:
        """根据名称和长度推断枪管档位。"""
        if self._contains_any_keyword(item_name, ["integral barrel-suppressor", "integral suppressor", "integrally suppressed", "barrel-suppressor", "一体消音枪管", "整体消音枪管"]):
            return "barrel_integral_suppressed"

        barrel_length_mm = self._extract_barrel_length_mm(item_name)
        if any(k in item_name for k in ["shortened", "short", "sbr", "kurz"]):
            return "barrel_short"
        if barrel_length_mm is not None and barrel_length_mm <= 330 and any(k in item_name for k in ["carbine", "smg", "pdw", "shotgun", "12ga", "762x51", "556x45", "545x39", "762x39"]):
            return "barrel_short"
        if any(k in item_name for k in ["extended", "long", "rifle length", "full length"]):
            return "barrel_long"
        return "barrel_medium"

    def _infer_suppressor_profile_from_name(self, item_name: str) -> str:
        """根据名称推断消音器细分档位。"""
        if any(k in item_name for k in ["mini", "mini2", "compact", "short", "45s", "rbs", "k-can", "mini monster"]):
            return "muzzle_suppressor_compact"
        return "muzzle_suppressor"

    def _is_handguard_like_name(self, item_name: str) -> bool:
        """判断名称是否明显指向护木/前端组件。"""
        return item_name.startswith("handguard_") or self._contains_any_keyword(
            item_name,
            ["护木", "forend", "handguard", "front-end assembly", "front end assembly", "цевье"],
        )

    def _infer_handguard_profile_from_name(self, item_name: str) -> str:
        """根据名称推断护木长度档位。"""
        if any(k in item_name for k in ["short", "carbine", "pdw", "compact"]):
            return "handguard_short"
        if any(k in item_name for k in ["long", "extended", "rifle length", "full length"]):
            return "handguard_long"
        return "handguard_medium"

    def _infer_sight_profile_from_name(self, item_name: str) -> Optional[str]:
        """根据名称关键词推断瞄具档位。"""
        normalized = item_name.lower().replace(",", ".")

        if any(k in normalized for k in [
            "sight_front", "sight_rear", "front sight", "rear sight", "sight post", "front post",
            "iron", "mbus", "flip", "backup", "drum rear sight", "tritium rear sight", "tritium front sight",
        ]):
            return "iron_sight"

        red_dot_keywords = [
            "red dot", "reddot", "reflex", "holo", "holographic", "rds",
            "eotech", "xps", "exps", "aimpoint", "micro", "t1", "t2",
            "pk06", "okp", "kobra", "romeo", "holosun", "delta point",
            "deltapoint", "rmr", "srs", "uh-1",
            "1p87", "comp_m4", "comp m4", "compm4", "aimpooint",
            "boss_xe", "boss xe",
        ]
        if any(k in normalized for k in red_dot_keywords):
            return "scope_red_dot"
        if re.search(r"(?:^|[^0-9])1(?:[.]0+)?x(?:[^0-9]|$)", normalized):
            return "scope_red_dot"

        magnified_keywords = [
            "acog", "prism", "specter", "hamr", "valday", "lpvo", "vudu", "razor",
            "march", "bravo4", "ta01", "ta11", "ps320", "hensoldt",
        ]
        if any(k in normalized for k in magnified_keywords):
            return "scope_magnified"
        if re.search(r"(?:^|[^0-9])(2|3|4|5|6|7|8|9|10|11|12)(?:[.]\d+)?x(?:[^0-9]|$)", normalized):
            return "scope_magnified"
        if re.search(r"(?:^|[^0-9])1(?:[.]\d+)?[-/](2|3|4|5|6|7|8|9|10|11|12)(?:[.]\d+)?(?:x)?(?:[^0-9]|$)", normalized):
            return "scope_magnified"

        return None

    def _to_optional_bool(self, value: Any) -> Optional[bool]:
        """将输入值转换为可空布尔。"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "y"}:
                return True
            if lowered in {"false", "0", "no", "n"}:
                return False
        return None

    def _infer_mod_stock_profile(self, item_name: str, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> str:
        """推断枪托附件细分。"""
        raw_props = (item_info or {}).get("properties")
        props: Dict[str, Any] = raw_props if isinstance(raw_props, dict) else {}

        if any(k in item_name for k in ["buttpad", "recoil pad", "butt pad", "shoulder pad", "托腮", "后托垫", "枪托垫", "缓冲垫"]):
            return "stock_buttpad"

        stock_allow_ads = self._to_optional_bool(props.get("StockAllowADS"))
        if stock_allow_ads is None:
            stock_allow_ads = self._to_optional_bool(patch.get("StockAllowADS"))

        has_shoulder = self._to_optional_bool(props.get("HasShoulderContact"))
        if has_shoulder is None:
            has_shoulder = self._to_optional_bool(patch.get("HasShoulderContact"))

        folding_keywords = [
            "fold", "folding", "collapsed", "retracted", "telescop", "wire", "pdw", "skeleton",
            "折叠", "伸缩", "收缩", "骨架", "折叠托", "伸缩托", "枪托",
        ]
        if stock_allow_ads is True:
            return "stock_ads_support"
        if has_shoulder is False or any(k in item_name for k in folding_keywords):
            return "stock_folding"
        return "stock_fixed"

    def _contains_any_keyword(self, text: str, keywords: List[str]) -> bool:
        """判断文本是否包含任一关键词。"""
        return any(keyword in text for keyword in keywords)

    def _get_mod_parent_base_profile(self, parent_id: Optional[str]) -> Optional[str]:
        """由 parent_id 推断附件基础档位。"""
        if parent_id is None:
            return None

        parent_profile_map = {
            "5448bc234bdc2d3c308b4569": "magazine",
            "56ea9461d2720b67698b456f": "gasblock",
            "55818a304bdc2db5418b457d": "receiver",
            "55818a684bdc2ddd698b456d": "pistol_grip",
            "55818af64bdc2d5b648b4570": "foregrip",
            "55818a594bdc2db9688b456a": "stock",
            "55818b224bdc2dde698b456f": "mount",
            "55818ac54bdc2d5b648b456e": "iron_sight",
            "55818ae44bdc2dde698b456c": "scope_magnified",
            "55818ad54bdc2ddc698b4569": "scope_red_dot",
            "55818add4bdc2d5b648b456f": "scope_magnified",
            "55818acf4bdc2dde698b456b": "scope_red_dot",
            "55818a104bdc2db9688b4569": "handguard_medium",
            "555ef6e44bdc2de9068b457e": "barrel_medium",
            "55818b084bdc2d5b648b4571": "flashlight_laser",
            "55818b164bdc2ddc698b456c": "flashlight_laser",
            "5448fe124bdc2da5018b4567": "flashlight_laser",
            "550aa4cd4bdc2dd8348b456c": "muzzle_suppressor",
            "550aa4bf4bdc2dd6348b456b": "muzzle_flashhider",
            "550aa4dd4bdc2dc9348b4569": "muzzle_brake",
        }
        return parent_profile_map.get(parent_id)

    def _infer_mod_profile_from_name_fallback(self, name: str, item_info: Optional[Mapping[str, Any]], patch: PatchData) -> Optional[str]:
        """缺失 parentId/ModType 时，按名称兜底推断附件档位。"""
        if name.startswith("catch_"):
            return "catch"
        if name.startswith("hammer_"):
            return "hammer"
        if name.startswith("trigger_"):
            return "trigger"
        if name.startswith("charge_") or "charging handle" in name or "charging_handle" in name or "拉机柄" in name:
            return "charging_handle"
        if name.startswith("bipod_") or "bipod" in name or "二脚架" in name:
            return "bipod"
        if "rear_hook" in name or "rear hook" in name:
            return "stock_rear_hook"
        if "eyecup" in name:
            return "optic_eyecup"
        if "killflash" in name:
            return "optic_killflash"
        if "panel" in name:
            return "rail_panel"
        if name.startswith("gas_block_") or name.startswith("gasblock_") or "gas block" in name or "导气箍" in name:
            return "gasblock"
        if name.startswith("foregrip_") or self._contains_any_keyword(name, ["前握把", "垂直前握把", "斜握把", "握把挡块", "前握挡块", "hand stop", "grip stop", "handstop", "vertical grip", "angled grip", "foregrip", "sturmgriff"]):
            return "foregrip"
        if name.startswith("pistolgrip_") or self._contains_any_keyword(name, ["pistol grip", "小角度握把", "后握把", "пистолетная рукоятка"]):
            return "pistol_grip"
        if "握把" in name and "前握把" not in name and "垂直" not in name and "斜握" not in name:
            return "pistol_grip"
        if name.startswith("stock_adapter_"):
            return "stock_adapter"
        if "buttpad" in name or "butt pad" in name or self._contains_any_keyword(name, ["托腮", "枪托垫", "后托垫"]):
            return "stock_buttpad"
        if name.startswith("buffer_") or name.startswith("buffertube_") or "buffer tube" in name or "缓冲管" in name:
            return "buffer_adapter"
        if name.startswith("stock_") or self._contains_any_keyword(name, ["枪托", "buttstock", "brace", "底盘枪托", "приклад", "托"]):
            return self._infer_mod_stock_profile(name, patch, item_info)
        if name.startswith("receiver_") or name.startswith("reciever_") or self._contains_any_keyword(name, ["机匣", "机匣盖", "防尘盖", "receiver", "reciever", "dust cover", "upper receiver", "upper reciever", "slide", "крышка ствольной коробки"]):
            return "receiver"
        if name.startswith("mag_") or name.startswith("magazine_") or self._contains_any_keyword(name, ["弹匣", "magazine", "drum", "casket", "магазин"]):
            mag_capacity = self._extract_mag_capacity(item_info, name)
            return self._infer_magazine_profile(mag_capacity, name)
        if self._is_handguard_like_name(name):
            return self._infer_handguard_profile_from_name(name)
        if name.startswith("silencer_") or "suppressor" in name or self._contains_any_keyword(name, ["消音器", "抑制器", "消声器", "глушитель"]):
            return self._infer_suppressor_profile_from_name(name)
        if name.startswith("railq"):
            return "handguard_medium"
        if self._contains_any_keyword(name, ["barrel and rail system", "rail system", "front-end assembly", "front end assembly"]) and self._contains_any_keyword(name, ["m-lok", "mlok", "keymod", "barrel", "forend", "handguard", "护木"]):
            return self._infer_handguard_profile_from_name(name)
        if name.startswith("mount_") or self._contains_any_keyword(name, ["导轨", "基座", "偏移座", "镜座", "mount", "rail segment", "rail", "offset mount"]):
            return "mount"
        if name.startswith("barrel_") or self._contains_any_keyword(name, ["枪管", "barrel", "ствол"]):
            return self._infer_barrel_profile_from_name(name)
        if name.startswith("sight_") or name.startswith("scope_") or self._contains_any_keyword(name, ["瞄具", "瞄准镜", "全息", "红点", "反射式"]):
            sight_profile = self._infer_sight_profile_from_name(name)
            if sight_profile:
                return sight_profile
            return "scope_red_dot"
        if "adapter" in name and any(k in name for k in ["muzzle", "suppressor", "silencer", "taper", "qd", "消音器", "抑制器"]):
            return "muzzle_adapter"
        if self._contains_any_keyword(name, ["thread protector", "螺纹保护", "protective cap"]):
            return "muzzle_thread"
        if self._contains_any_keyword(name, ["制退器", "compensator", "muzzle brake", "brake"]):
            return "muzzle_brake"
        if name.startswith("muzzle_") or "flashhider" in name or "compensator" in name or self._contains_any_keyword(name, ["消焰器", "消焰", "火帽", "flash hider"]):
            return "muzzle_flashhider"
        if self._contains_any_keyword(name, ["flashlight", "laser", "peq", "dbal", "x400", "xc1", "战术灯", "战术装置", "手电", "手电筒", "激光", "镭射", "照明", "wmx", "wmlx", "x300", "m300", "m600", "m640", "wmx200"]) and not self._contains_any_keyword(name, ["偏移座", "基座", "导轨", "mount", "rail"]):
            return "flashlight_laser"
        if self._contains_any_keyword(name, ["gas tube", "导气管"]):
            return "gasblock"
        if self._contains_any_keyword(name, ["front-end assembly", "front end assembly"]):
            return self._infer_handguard_profile_from_name(name)
        return None

    def _infer_mod_profile_from_template_file(self, template_file: str, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> Optional[str]:
        """根据模板文件名兜底推断附件档位，避免规则漏命中。"""
        template_name = os.path.basename(template_file)
        item_name = str(patch.get("Name", "")).lower()

        if template_name == "MagazineTemplates.json":
            mag_capacity = self._extract_mag_capacity(item_info, item_name)
            return self._infer_magazine_profile(mag_capacity, item_name)
        if template_name == "BarrelTemplates.json":
            return self._infer_barrel_profile_from_name(item_name)
        if template_name == "HandguardTemplates.json":
            return self._infer_handguard_profile_from_name(item_name)
        if template_name == "StockTemplates.json":
            return self._infer_mod_stock_profile(item_name, patch, item_info)
        if template_name == "ChargingHandleTemplates.json":
            return "charging_handle"

        template_profile_map = {
            "MuzzleDeviceTemplates.json": "muzzle_flashhider",
            "ForegripTemplates.json": "foregrip",
            "PistolGripTemplates.json": "pistol_grip",
            "ReceiverTemplates.json": "receiver",
            "GasblockTemplates.json": "gasblock",
            "MountTemplates.json": "mount",
            "FlashlightLaserTemplates.json": "flashlight_laser",
            "IronSightTemplates.json": "iron_sight",
        }

        if template_name == "ScopeTemplates.json":
            return self._infer_sight_profile_from_name(item_name) or "scope_red_dot"

        return template_profile_map.get(template_name)

    def _infer_mod_profile(self, patch: PatchData, item_info: Optional[Mapping[str, Any]]) -> Optional[str]:
        """推断附件细分规则档位。"""
        name = str(patch.get("Name", "")).lower()
        mod_type = str(patch.get("ModType", "")).lower()
        parent_id = self.normalize_parent_id((item_info or {}).get("parent_id")) if item_info else None
        base_profile = self._get_mod_parent_base_profile(parent_id)

        # 基于 ModType / 名称进一步细分
        if "muzzle" in mod_type or (base_profile and base_profile.startswith("muzzle")):
            if mod_type in ["muzzle_supp_adapter", "sig_taper_brake"]:
                return "muzzle_adapter"
            if "adapter" in mod_type:
                return "muzzle_adapter"
            if "adapter" in name and any(k in name for k in ["muzzle", "suppressor", "silencer", "taper", "qd"]):
                return "muzzle_adapter"
            if any(k in name for k in ["silencer", "suppressor", "qd", "pbs"]) or self._contains_any_keyword(name, ["消音器", "抑制器", "消声器", "глушитель"]):
                return self._infer_suppressor_profile_from_name(name)
            if any(k in name for k in ["brake", "comp", "compensator"]) or self._contains_any_keyword(name, ["制退器"]):
                return "muzzle_brake"
            if "thread" in name or "protector" in name or self._contains_any_keyword(name, ["螺纹保护", "保护帽"]):
                return "muzzle_thread"
            if self._contains_any_keyword(name, ["消焰器", "消焰", "火帽", "flash hider"]):
                return "muzzle_flashhider"
            return "muzzle_flashhider"

        if "barrel" in mod_type or "short_barrel" in mod_type or (base_profile and base_profile.startswith("barrel")):
            return self._infer_barrel_profile_from_name(name)

        if "handguard" in mod_type or (base_profile and base_profile.startswith("handguard")):
            return self._infer_handguard_profile_from_name(name)

        if self._is_handguard_like_name(name):
            return self._infer_handguard_profile_from_name(name)

        if mod_type in ["magazine"] or base_profile == "magazine":
            mag_capacity = self._extract_mag_capacity(item_info, name)
            return self._infer_magazine_profile(mag_capacity, name)

        if mod_type in ["grip", "foregrip"] or "foregrip" in mod_type or "verticalgrip" in mod_type or "handstop" in mod_type:
            return "foregrip"
        if mod_type in ["bipod"]:
            return "bipod"
        if "mag" in mod_type and "malf" not in mod_type:
            mag_capacity = self._extract_mag_capacity(item_info, name)
            return self._infer_magazine_profile(mag_capacity, name)
        if mod_type in ["gas", "gasblock", "gas_block"]:
            return "gasblock"
        if mod_type in ["stock_adapter"]:
            return "stock_adapter"
        if mod_type in ["buffer_adapter", "buffer_tube"] or mod_type.startswith("buffer"):
            return "buffer_adapter"
        if mod_type in ["grip_stock_adapter"]:
            return "stock_adapter"
        if "buttpad" in mod_type:
            return "stock_buttpad"
        if mod_type in ["stock"] or mod_type.startswith("stock") or mod_type.endswith("_stock"):
            return self._infer_mod_stock_profile(name, patch, item_info)
        if mod_type in ["pistolgrip", "pistol_grip"] or ("pistol" in mod_type and "grip" in mod_type):
            return "pistol_grip"
        if mod_type in ["receiver"] or "receiver" in mod_type or "reciever" in mod_type:
            return "receiver"
        if mod_type in ["mount"] or "mount" in mod_type or "rail" in mod_type:
            if name.startswith("silencer_") or "suppressor" in name or self._contains_any_keyword(name, ["消音器", "抑制器", "消声器", "глушитель"]):
                return self._infer_suppressor_profile_from_name(name)
            if self._contains_any_keyword(name, ["barrel and rail system", "rail system", "front-end assembly", "front end assembly"]) and self._contains_any_keyword(name, ["m-lok", "mlok", "handguard", "forend", "barrel"]):
                return self._infer_handguard_profile_from_name(name)
            return "mount"
        if mod_type in ["iron_sight"]:
            return "iron_sight"
        if mod_type in ["reflex_sight", "compact_reflex_sight"]:
            return "scope_red_dot"
        if mod_type in ["scope", "assault_scope"]:
            return "scope_magnified"
        if "laser" in mod_type or "flashlight" in mod_type or "tactical" in mod_type:
            return "flashlight_laser"
        if mod_type in ["sight"]:
            sight_profile = self._infer_sight_profile_from_name(name)
            if sight_profile:
                return sight_profile
            template_file = str((item_info or {}).get("template_file") or "")
            if template_file == "ScopeTemplates.json":
                # ScopeTemplates 在 CURRENT_PATCH 缺 parentId 时会回填到通用 parent，
                # 该 parent 倾向高倍；未命中关键词时优先给红点兜底，避免整批误判。
                return "scope_red_dot"
            if base_profile in {"iron_sight", "scope_red_dot", "scope_magnified"}:
                return base_profile
            return "scope_red_dot"

        fallback_profile = self._infer_mod_profile_from_name_fallback(name, item_info, patch)
        if fallback_profile:
            return fallback_profile

        template_file = str((item_info or {}).get("template_file") or "")
        if template_file:
            template_profile = self._infer_mod_profile_from_template_file(template_file, patch, item_info)
            if template_profile:
                return template_profile

        return base_profile

    def _extract_mag_capacity(self, item_info: Optional[Mapping[str, Any]], item_name: str = "") -> Optional[int]:
        """从输入属性中提取弹匣容量（发数）。"""
        info = item_info or {}
        props = info.get("properties") or {}

        for key in ["Capacity", "capacity", "MaxCount", "max_count", "CartridgeMaxCount", "cartridgeMaxCount"]:
            raw_value = props.get(key)
            if isinstance(raw_value, (int, float)):
                value = int(raw_value)
                if 1 <= value <= 200:
                    return value
            if isinstance(raw_value, str) and raw_value.strip().isdigit():
                value = int(raw_value.strip())
                if 1 <= value <= 200:
                    return value

        cartridges = props.get("Cartridges") or props.get("cartridges")
        if isinstance(cartridges, list):
            for slot in cartridges:
                if not isinstance(slot, dict):
                    continue
                raw_value = slot.get("_max_count")
                if isinstance(raw_value, (int, float)):
                    value = int(raw_value)
                    if 1 <= value <= 200:
                        return value
                if isinstance(raw_value, str) and raw_value.strip().isdigit():
                    value = int(raw_value.strip())
                    if 1 <= value <= 200:
                        return value

        # 名称兜底：匹配“30-round / 30 round / 30rnd / 30 rds”等常见容量标记。
        if item_name:
            match = MAG_CAPACITY_NAME_REGEX.search(item_name)
            if match:
                value = int(match.group(1))
                if 1 <= value <= 200:
                    return value
            match = MAG_CAPACITY_CN_REGEX.search(item_name)
            if match:
                value = int(match.group(1))
                if 1 <= value <= 200:
                    return value
            match = MAG_CAPACITY_RU_REGEX.search(item_name)
            if match:
                value = int(match.group(1))
                if 1 <= value <= 200:
                    return value

        return None

    def _ensure_required_fields(self, patch: PatchData, item_type: str, item_info: Optional[Mapping[str, Any]]):
        """根据新规则文档补全必填字段。"""
        if "RealismMod.Gun" in item_type:
            patch.setdefault("$type", "RealismMod.Gun, RealismMod")
            patch.setdefault("Name", (item_info or {}).get("name") or f"weapon_{patch.get('ItemID', 'unknown')}")
            patch.setdefault("Weight", 1.5)
            patch.setdefault("LoyaltyLevel", 1)
        elif "RealismMod.WeaponMod" in item_type:
            patch.setdefault("$type", "RealismMod.WeaponMod, RealismMod")
            patch.setdefault("Name", (item_info or {}).get("name") or f"mod_{patch.get('ItemID', 'unknown')}")
            patch.setdefault("Weight", 0.1)
            patch.setdefault("LoyaltyLevel", 1)
            patch.setdefault("ModType", "")
        elif "RealismMod.Ammo" in item_type:
            patch.setdefault("$type", "RealismMod.Ammo, RealismMod")
            patch.setdefault("Name", (item_info or {}).get("name") or f"ammo_{patch.get('ItemID', 'unknown')}")
            patch.setdefault("LoyaltyLevel", 1)
            patch.setdefault("BasePriceModifier", 1)

    def _apply_material_heuristics(self, patch: PatchData, item_name: str) -> None:
        """基于材质关键词预调整物品属性。"""
        if any(keyword in item_name for keyword in ["titanium", "ti-", "carbon"]):
            if "Weight" in patch:
                patch["Weight"] = round(patch["Weight"] * 0.8, 3)
            if "CoolFactor" in patch:
                patch["CoolFactor"] = round(patch["CoolFactor"] * 1.15, 2)
            if "Ergonomics" in patch:
                patch["Ergonomics"] = round(patch["Ergonomics"] * 1.05, 1)
        elif "steel" in item_name:
            if "Weight" in patch:
                patch["Weight"] = round(patch["Weight"] * 1.25, 3)
            if "DurabilityBurnModificator" in patch:
                patch["DurabilityBurnModificator"] = round(patch["DurabilityBurnModificator"] * 0.9, 2)

    def _apply_size_heuristics(self, patch: PatchData, item_name: str) -> None:
        """基于尺寸/形态关键词预调整物品属性。"""
        if any(keyword in item_name for keyword in ["compact", "mini", "short", "k-", "kurz"]):
            if "Weight" in patch:
                patch["Weight"] = round(patch["Weight"] * 0.75, 3)
            if "Loudness" in patch and patch["Loudness"] < 0:
                patch["Loudness"] = round(patch["Loudness"] * 0.7, 1)
            if "VerticalRecoil" in patch and patch["VerticalRecoil"] < 0:
                patch["VerticalRecoil"] = round(patch["VerticalRecoil"] * 0.7, 2)
        elif any(keyword in item_name for keyword in ["long", "extended", "heavy", "full"]):
            if "Weight" in patch:
                patch["Weight"] = round(patch["Weight"] * 1.3, 3)
            if "Accuracy" in patch:
                patch["Accuracy"] = round(patch["Accuracy"] * 1.1 + 1, 1)

    def _apply_barrel_velocity_heuristic(self, patch: PatchData, item_name: str) -> None:
        """基于枪管长度预估初速偏移。"""
        barrel_length_mm = self._extract_barrel_length_mm(item_name)
        if barrel_length_mm is None or "barrel" not in item_name:
            return

        inferred_velocity = (barrel_length_mm - 370) / 25.4 * 1.5
        current_velocity = patch.get("Velocity", 0)
        if current_velocity == 0:
            patch["Velocity"] = round(self._clamp(inferred_velocity, -18, 18), 2)

    def _apply_pre_rule_heuristics(self, patch: PatchData) -> None:
        """在规则区间采样前应用启发式，让最终写盘结果保持在规则口径内。"""
        item_name = str(patch.get("Name", "")).lower()
        self._apply_material_heuristics(patch, item_name)
        self._apply_size_heuristics(patch, item_name)
        self._apply_barrel_velocity_heuristic(patch, item_name)

    def apply_realism_sanity_check(self, patch: PatchData, item_info: Optional[Mapping[str, Any]] = None):
        """
        根据新旧规则文档对补丁进行最终校验：
        1) 保证必填字段；
        2) 按武器/附件细分规则夹紧数值；
        3) 保留原有现实主义推断与极值兜底。
        """
        item_type = str(patch.get("$type", ""))

        # 0. 必填字段兜底
        self._ensure_required_fields(patch, item_type, item_info)
        item_name = str(patch.get("Name", "")).lower()
        item_type = str(patch.get("$type", ""))

        # 0.5 先应用现实启发式，再进入规则区间采样。
        self._apply_pre_rule_heuristics(patch)

        # 1. 基础限制：规避夸大数值 (Clamping)
        if "RealismMod.Gun" in item_type:
            self._apply_field_clamps(patch, GUN_CLAMP_RULES)
            if "RecoilAngle" in patch and (patch["RecoilAngle"] < 30 or patch["RecoilAngle"] > 150):
                patch["RecoilAngle"] = 90

            # 应用武器新规则范围
            weapon_profile = self._infer_weapon_profile(patch, item_info)
            if weapon_profile and weapon_profile in WEAPON_PROFILE_RANGES:
                self._apply_numeric_ranges(patch, WEAPON_PROFILE_RANGES[weapon_profile], ensure_fields=True)
                self._apply_weapon_refinement_ranges(patch, weapon_profile, item_info)
                self._apply_field_clamps(patch, GUN_CLAMP_RULES)

            # 文档要求手枪默认无抵肩
            if weapon_profile == "pistol":
                patch["HasShoulderContact"] = False

        elif "RealismMod.WeaponMod" in item_type:
            self._apply_field_clamps(patch, MOD_CLAMP_RULES)
            if "Velocity" in patch:
                max_v = 15.0 if "barrel" in item_name else 5.0
                patch["Velocity"] = self._clamp(patch["Velocity"], -max_v, max_v)

            # 应用附件新规则范围
            mod_profile = self._infer_mod_profile(patch, item_info)
            if mod_profile and mod_profile in MOD_PROFILE_RANGES:
                self._apply_numeric_ranges(patch, MOD_PROFILE_RANGES[mod_profile], ensure_fields=True)
                self._apply_field_clamps(patch, MOD_CLAMP_RULES)

            # 文档要求消音器必须可循环亚音速弹
            if mod_profile == "muzzle_suppressor" and "CanCycleSubs" in patch:
                patch["CanCycleSubs"] = True

        elif "RealismMod.Ammo" in item_type:
            self._apply_ammo_profile_ranges(patch, item_info)

        elif "RealismMod.Gear" in item_type:
            self._apply_field_clamps(patch, GEAR_CLAMP_RULES)
            gear_profile = self._infer_gear_profile(patch, item_info)
            if gear_profile and gear_profile in GEAR_PROFILE_RANGES:
                self._apply_numeric_ranges(patch, GEAR_PROFILE_RANGES[gear_profile], ensure_fields=True)
                self._apply_field_clamps(patch, GEAR_CLAMP_RULES)

        # 2. 安全性兜底：防止任何属性出现天文数字
        for key, value in patch.items():
            if isinstance(value, (int, float)):
                if "Recoil" in key:
                    patch[key] = self._clamp(value, -2000, 2000)
                elif "Ergonomics" in key:
                    patch[key] = self._clamp(value, -50, 100)
                elif "Weight" in key:
                    patch[key] = self._clamp(value, 0, 50)
                elif "Multi" in key or "Factor" in key:
                    patch[key] = self._clamp(value, 0.01, 10.0)

    def load_all_templates(self):
        """加载所有模板文件"""
        print("正在加载模板文件...")

        for relative_dir in ["weapons", "attatchments", "ammo", "gear", "consumables"]:
            self._load_templates_from_dir(relative_dir)

        self._rebuild_template_id_index()
    
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
    
    def get_template_for_parent_id(self, parent_id: Optional[str]) -> Optional[str]:
        """根据parentId获取模板文件名"""
        # 标准化 parentId
        parent_id = self.normalize_parent_id(parent_id)
        if not parent_id:
            return None
        template_path = PARENT_ID_TO_TEMPLATE.get(parent_id)
        if template_path:
            return os.path.basename(template_path)
        return None
    
    def detect_item_format(self, item_data: JsonObject) -> str:
        """检测物品数据格式类型"""
        # CURRENT_PATCH格式：当前 input 中常见的 Realism 补丁对象（$type + ItemID）
        if "$type" in item_data and "ItemID" in item_data and "TemplateID" not in item_data:
            return "CURRENT_PATCH"
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

    def _create_empty_item_info(self, item_id: str) -> ItemInfo:
        """创建标准化的 item_info 结构。"""
        return {
            "item_id": item_id,
            "parent_id": None,
            "clone_id": None,
            "template_id": None,
            "template_file": None,
            "name": None,
            "is_weapon": False,
            "is_gear": False,
            "is_consumable": False,
            "item_type": None,
            "properties": {},
            "source_file": None,
            "format_type": None,
        }

    def _extract_localized_name(self, locale_blob: Any) -> Optional[str]:
        """从 locales / LocalePush 结构中提取显示名称。"""
        if not isinstance(locale_blob, dict):
            return None

        for lang in ["en", "ch", "zh", "ru"]:
            lang_locale = locale_blob.get(lang)
            if not isinstance(lang_locale, dict):
                continue
            localized_name = lang_locale.get("name") or lang_locale.get("Name")
            if isinstance(localized_name, str) and localized_name.strip():
                return localized_name

        localized_name = locale_blob.get("name") or locale_blob.get("Name")
        if isinstance(localized_name, str) and localized_name.strip():
            return localized_name

        return None

    def _extract_template_id_info(self, info: ItemInfo, item_data: JsonObject):
        info["template_id"] = item_data.get("TemplateID")
        info["name"] = item_data.get("Name")
        info["item_type"] = item_data.get("$type")
        template_id = info.get("template_id")
        if template_id:
            info["template_file"] = self._find_template_file_by_template_id(template_id)
        item_type = str(info.get("item_type") or "")
        if "RealismMod.Gun" in item_type:
            info["is_weapon"] = True
        elif "RealismMod.Gear" in item_type:
            info["is_gear"] = True
        elif "RealismMod.Consumable" in item_type:
            info["is_consumable"] = True

    def _extract_current_patch_info(self, info: ItemInfo, item_data: JsonObject):
        info["item_type"] = item_data.get("$type")
        info["name"] = item_data.get("Name")
        if not info["name"]:
            info["name"] = self._extract_localized_name(item_data.get("locales"))
        if not info["name"]:
            info["name"] = self._extract_localized_name(item_data.get("LocalePush"))

        ignored_keys = {
            "$type", "ItemID", "TemplateID", "parentId", "itemTplToClone",
            "clone", "ItemToClone", "enable", "locales", "LocalePush",
            "OverrideProperties", "overrideProperties", "item", "items", "handbook"
        }
        info["properties"] = {k: v for k, v in item_data.items() if k not in ignored_keys}

        if "parentId" in item_data:
            info["parent_id"] = self.normalize_parent_id(item_data.get("parentId"))
        if info["parent_id"]:
            info["template_file"] = self.get_template_for_parent_id(info["parent_id"])

        # CURRENT_PATCH 常见缺失 parentId/ModType，按名称和 ModType 兜底模板文件，
        # 避免 receiver/reciever 等规则因 profile 推断失败而漏命中。
        if not info["template_file"]:
            name_l = str(info.get("name") or "").lower()
            mod_type_l = str(item_data.get("ModType") or "").lower()
            if name_l.startswith("receiver_") or name_l.startswith("reciever_") or mod_type_l == "receiver":
                info["template_file"] = "ReceiverTemplates.json"
            elif name_l.startswith("gas_block_") or name_l.startswith("gasblock_") or mod_type_l in ["gas", "gasblock", "gas_block"]:
                info["template_file"] = "GasblockTemplates.json"

        item_type = str(info.get("item_type") or "")
        if "RealismMod.Gun" in item_type:
            info["is_weapon"] = True
        elif "RealismMod.Gear" in item_type:
            info["is_gear"] = True
        elif "RealismMod.Consumable" in item_type:
            info["is_consumable"] = True

    def _extract_vir_info(self, info: ItemInfo, item_data: JsonObject):
        item_obj = item_data.get("item")
        if not isinstance(item_obj, dict):
            return
        info["parent_id"] = self.normalize_parent_id(item_obj.get("_parent"))
        info["name"] = item_obj.get("_name")
        if not info["name"]:
            info["name"] = self._extract_localized_name(item_data.get("locales"))
        info["properties"] = item_obj.get("_props", {})
        if info["parent_id"]:
            info["template_file"] = self.get_template_for_parent_id(info["parent_id"])
        if "isweapon" in item_data:
            info["is_weapon"] = item_data["isweapon"]
        elif info["parent_id"]:
            info["is_weapon"] = self.is_weapon(info["parent_id"])

    def _extract_standard_info(self, info: ItemInfo, item_data: JsonObject):
        info["parent_id"] = self.normalize_parent_id(item_data.get("parentId"))
        info["clone_id"] = item_data.get("itemTplToClone")
        info["properties"] = item_data.get("overrideProperties", {})
        if info["parent_id"]:
            info["template_file"] = self.get_template_for_parent_id(info["parent_id"])

        info["name"] = self._extract_localized_name(item_data.get("locales"))

        if info["parent_id"]:
            info["is_weapon"] = self.is_weapon(info["parent_id"])
            info["is_gear"] = self.is_gear_simple(info["parent_id"])
            info["is_consumable"] = self.is_consumable(info["parent_id"])
        elif info["clone_id"]:
            info["is_weapon"] = self.is_weapon_by_clone_id(info["clone_id"])

    def _extract_itemtoclone_info(self, info: ItemInfo, item_data: JsonObject):
        info["clone_id"] = item_data.get("ItemToClone")
        info["name"] = self._extract_localized_name(item_data.get("LocalePush"))
        if not info["name"]:
            info["name"] = self._extract_localized_name(item_data.get("locales"))
        if "OverrideProperties" in item_data:
            info["properties"] = item_data["OverrideProperties"]

    def _extract_clone_info(self, info: ItemInfo, item_data: JsonObject):
        info["clone_id"] = item_data.get("clone")
        info["name"] = self._extract_localized_name(item_data.get("locales"))

        handbook = item_data.get("handbook")
        if isinstance(handbook, dict):
            h_parent = handbook.get("ParentId") or handbook.get("parentId")
            if h_parent:
                info["parent_id"] = self.normalize_parent_id(h_parent)

        item_obj_key = "items" if "items" in item_data else ("item" if "item" in item_data else None)
        if item_obj_key and "_props" in item_data[item_obj_key]:
            info["properties"] = item_data[item_obj_key]["_props"]
            if not info["parent_id"] and "_parent" in item_data[item_obj_key]:
                info["parent_id"] = self.normalize_parent_id(item_data[item_obj_key]["_parent"])
        if info["parent_id"]:
            info["template_file"] = self.get_template_for_parent_id(info["parent_id"])
    
    def extract_item_info(
        self,
        item_id: str,
        item_data: JsonObject,
        format_type: str,
        source_file: Optional[str] = None,
    ) -> ItemInfo:
        """根据格式提取物品信息"""
        info = self._create_empty_item_info(item_id)

        if format_type == "TEMPLATE_ID":
            self._extract_template_id_info(info, item_data)
        elif format_type == "CURRENT_PATCH":
            self._extract_current_patch_info(info, item_data)
        elif format_type == "VIR":
            self._extract_vir_info(info, item_data)
        elif format_type == "STANDARD":
            self._extract_standard_info(info, item_data)
        elif format_type == "ITEMTOCLONE":
            self._extract_itemtoclone_info(info, item_data)
        elif format_type == "CLONE":
            self._extract_clone_info(info, item_data)

        self._enrich_item_info_with_source_context(info, item_data, format_type, source_file)

        return info
    
    def merge_input_properties(self, patch: PatchData, item_info: ItemInfo):
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

    def is_gear_simple(self, parent_id: Optional[str]) -> bool:
        """判断是否为装备类型(护甲、背包、挂钩、头盔等)"""
        parent_id = self.normalize_parent_id(parent_id)
        if not parent_id:
            return False
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

    def is_weapon(self, parent_id: Optional[str]) -> bool:
        """判断是否为武器"""
        if not parent_id:
            return False
        template_file = self.get_template_for_parent_id(parent_id)
        if template_file and template_file in self.templates:
            # 检查模板中的$type字段
            for item in self.templates[template_file].values():
                if "$type" in item:
                    return "RealismMod.Gun" in item["$type"]
        return False
    
    def is_ammo(self, parent_id: Optional[str]) -> bool:
        """判断是否为子弹"""
        parent_id = self.normalize_parent_id(parent_id)
        if not parent_id:
            return False
        return parent_id == "5485a8684bdc2da71d8b4567"
    
    def is_consumable(self, parent_id: Optional[str]) -> bool:
        """判断是否为消耗品类型"""
        parent_id = self.normalize_parent_id(parent_id)
        if not parent_id:
            return False
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

        template_item = self.template_by_id.get(clone_id)
        if template_item is None:
            return None
        return copy.deepcopy(template_item)
    
    def find_template_by_template_id(self, template_id: str) -> Optional[Dict]:
        """通过TemplateID在所有已加载的模板中搜索指定ID的模板数据"""
        if not template_id:
            return None

        template_item = self.template_by_id.get(template_id)
        if template_item is None:
            return None
        return copy.deepcopy(template_item)

    def _find_template_file_by_template_id(self, template_id: str) -> Optional[str]:
        """返回模板ID所在的模板文件名。"""
        if not template_id:
            return None
        for template_file, template_data in self.templates.items():
            if isinstance(template_data, dict) and template_id in template_data:
                return template_file
        return None
    
    def select_template_data(self, template_file: str, item_id: str, clone_id: Optional[str] = None) -> Optional[Dict]:
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
            
            # 最后手段：按稳定顺序选取第一个模板，避免输出随运行漂移。
            first_template_key = sorted(template_data.keys())[0]
            result = copy.deepcopy(template_data[first_template_key])
            result["ItemID"] = item_id
            return result
        
        return None
    
    def create_default_weapon_patch(self, item_id: str, item_info: ItemInfo) -> PatchData:
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
            "ForegripTemplates.json": "foregrip",
            "HandguardTemplates.json": "handguard",
            "BarrelTemplates.json": "barrel",
            "MuzzleDeviceTemplates.json": "muzzle",
            "MagazineTemplates.json": "magazine",
            "ScopeTemplates.json": "sight",
            "IronSightTemplates.json": "sight",
            "MountTemplates.json": "mount",
            "PistolGripTemplates.json": "pistol_grip",
            "ReceiverTemplates.json": "receiver",
            "GasblockTemplates.json": "gasblock",
            "FlashlightLaserTemplates.json": "flashlight_laser",
            "AuxiliaryModTemplates.json": "auxiliary",
        }
        return template_to_modtype.get(template_file, "")
    
    def create_default_mod_patch(self, item_id: str, item_info: ItemInfo, template_file: Optional[str] = None) -> PatchData:
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
    
    def create_default_ammo_patch(self, item_id: str, item_info: ItemInfo) -> PatchData:
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
    
    def create_default_consumable_patch(self, item_id: str, item_info: ItemInfo) -> PatchData:
        """创建默认的消耗品补丁"""
        patch = copy.deepcopy(DEFAULT_CONSUMABLE_TEMPLATE)
        patch["ItemID"] = item_id
        
        # 添加Name属性
        if item_info.get("name"):
            patch["Name"] = item_info["name"]
        else:
            patch["Name"] = f"consumable_{item_id}"
        
        return patch

    def _add_to_file_patches(self, item_id: str, patch: PatchData, source_file: Optional[str]):
        """按源文件分组存储补丁。"""
        if not source_file:
            return
        if source_file not in self.file_based_patches:
            self.file_based_patches[source_file] = {}
        self.file_based_patches[source_file][item_id] = patch

    def _finalize_patch(self, item_id: str, patch: PatchData, item_info: ItemInfo, processed_items: set, source_file: Optional[str]):
        """统一执行属性合并、规则校验、按文件存储。"""
        self.merge_input_properties(patch, item_info)
        self.apply_realism_sanity_check(patch, item_info)
        self._add_to_file_patches(item_id, patch, source_file)
        processed_items.add(item_id)

    def _store_patch_by_item_info_flags(self, item_id: str, patch: PatchData, item_info: ItemInfo):
        """按 item_info 标记分类存储（用于 TEMPLATE_ID 分支）。"""
        if item_info.get("is_weapon"):
            self.weapon_patches[item_id] = patch
        elif item_info.get("is_gear"):
            self.gear_patches[item_id] = patch
        elif item_info.get("is_consumable"):
            self.consumables_patches[item_id] = patch
        else:
            self.attachment_patches[item_id] = patch

    def _store_patch_by_patch_type(self, item_id: str, patch: PatchData):
        """按补丁中的 $type 分类存储（用于 CLONE 分支）。"""
        patch_type = str(patch.get("$type", ""))
        if "RealismMod.Gun" in patch_type:
            self.weapon_patches[item_id] = patch
        elif "RealismMod.Gear" in patch_type:
            self.gear_patches[item_id] = patch
        elif "RealismMod.Consumable" in patch_type:
            self.consumables_patches[item_id] = patch
        elif "RealismMod.Ammo" in patch_type:
            self.ammo_patches[item_id] = patch
        else:
            self.attachment_patches[item_id] = patch

    def _resolve_clone_template(self, clone_id: str, items_data: JsonObject, processed_items: set, source_file: Optional[str]) -> Optional[PatchData]:
        """解析 CLONE 源模板：先查模板库，再查同文件递归来源。"""
        template_data = self.find_template_by_id(clone_id)

        if not template_data and clone_id in items_data:
            if self.process_single_item(clone_id, items_data[clone_id], items_data, processed_items, source_file):
                if clone_id in self.weapon_patches:
                    template_data = copy.deepcopy(self.weapon_patches[clone_id])
                elif clone_id in self.attachment_patches:
                    template_data = copy.deepcopy(self.attachment_patches[clone_id])
                elif clone_id in self.gear_patches:
                    template_data = copy.deepcopy(self.gear_patches[clone_id])
                elif clone_id in self.consumables_patches:
                    template_data = copy.deepcopy(self.consumables_patches[clone_id])

        return template_data

    def _infer_parent_id_from_item_to_clone(self, clone_id: str) -> Optional[str]:
        """根据 ItemToClone 常量名推断 parent_id。"""
        if not clone_id:
            return None

        if "AMMO_" in clone_id:
            return "5485a8684bdc2da71d8b4567"

        if any(weapon_type in clone_id for weapon_type in ["ASSAULTRIFLE_", "RIFLE_", "SHOTGUN_", "SMG_", "PISTOL_", "HANDGUN_", "MACHINEGUN_", "GRENADELAUNCHER_"]):
            if "ASSAULTRIFLE_" in clone_id:
                return "5447b5f14bdc2d61278b4567"
            if "RIFLE_" in clone_id or "MARKSMANRIFLE_" in clone_id:
                return "5447b6194bdc2d67278b4567"
            if "SNIPER" in clone_id or "SNIPERRIFLE_" in clone_id:
                return "5447b6254bdc2dc3278b4568"
            if "SHOTGUN_" in clone_id:
                return "5447b6094bdc2dc3278b4567"
            if "SMG_" in clone_id:
                return "5447b5e04bdc2d62278b4567"
            if "PISTOL_" in clone_id or "HANDGUN_" in clone_id:
                return "5447b5cf4bdc2d65278b4567"
            if "MACHINEGUN_" in clone_id:
                return "5447bed64bdc2d97278b4568"
            if "GRENADELAUNCHER_" in clone_id:
                return "5447bedf4bdc2d87278b4568"

        if "MAGAZINE_" in clone_id or "MAG_" in clone_id:
            return "5448bc234bdc2d3c308b4569"
        if "ARMOR_" in clone_id or "VEST_" in clone_id:
            return "5448e54d4bdc2dcc718b4568"
        if "CONTAINER_" in clone_id or "SECURE_" in clone_id:
            return "5795f317245977243854e041"
        if "KEY_" in clone_id or "KEYCARD_" in clone_id:
            if "KEYCARD_" in clone_id:
                return "5c164d2286f774194c5e69fa"
            return "5c99f98d86f7745c314214b3"
        if "INFO_" in clone_id or "DIARY_" in clone_id:
            return "5448ecbe4bdc2d60728b4568"
        if "HEADWEAR_" in clone_id or "HELMET_" in clone_id:
            return "5a341c4086f77401f2541505"
        if "HEADPHONES_" in clone_id:
            return "5645bcb74bdc2ded0b8b4578"
        if "FACECOVER_" in clone_id:
            return "5a341c4686f77469e155819e"
        if "RECEIVER_" in clone_id:
            return "55818a304bdc2db5418b457d"
        if "BARREL_" in clone_id:
            return "555ef6e44bdc2de9068b457e"
        if "STOCK_" in clone_id:
            return "55818a594bdc2db9688b456a"
        if "HANDGUARD_" in clone_id:
            return "55818a104bdc2db9688b4569"
        if "GRIP_" in clone_id or "FOREGRIP_" in clone_id:
            return "55818af64bdc2d5b648b4570"
        if "PISTOLGRIP_" in clone_id:
            return "55818a684bdc2ddd698b456d"
        if "SIGHT_" in clone_id or "SCOPE_" in clone_id:
            if "SCOPE_" in clone_id:
                return "55818ae44bdc2dde698b456c"
            return "55818ad54bdc2ddc698b4569"
        if "SILENCER_" in clone_id or "SUPPRESSOR_" in clone_id:
            return "550aa4cd4bdc2dd8348b456c"
        if "FLASHHIDER_" in clone_id or "MUZZLE_" in clone_id:
            return "550aa4bf4bdc2dd6348b456b"
        if "MOUNT_" in clone_id:
            return "55818b224bdc2dde698b456f"

        return None

    def _resolve_itemtoclone_parent_id(self, item_data: Dict, clone_id: str) -> Optional[str]:
        """解析 ITEMTOCLONE 的 parent_id。"""
        handbook_parent = item_data.get("HandbookParent")

        if handbook_parent and len(handbook_parent) == 24:
            return handbook_parent

        if handbook_parent and handbook_parent in HANDBOOK_PARENT_TO_ID:
            return HANDBOOK_PARENT_TO_ID[handbook_parent]

        return self._infer_parent_id_from_item_to_clone(clone_id)

    def _handle_template_id_item(self, item_id: str, item_info: ItemInfo, template_id: str, processed_items: set, source_file: Optional[str]) -> bool:
        """处理 TEMPLATE_ID 格式物品。"""
        template_data = self.find_template_by_template_id(template_id)
        if not template_data:
            print(f"  跳过 {item_id}: 未找到TemplateID {template_id} 对应的模板")
            return False

        template_data["ItemID"] = item_id
        self._finalize_patch(item_id, template_data, item_info, processed_items, source_file)
        self._store_patch_by_item_info_flags(item_id, template_data, item_info)
        return True

    def _handle_current_patch_item(self, item_id: str, item_data: Dict, item_info: ItemInfo, processed_items: set, source_file: Optional[str]) -> bool:
        """处理 CURRENT_PATCH 格式物品（直接重写当前 input 的补丁对象）。"""
        patch = copy.deepcopy(item_data)
        patch["ItemID"] = item_id

        # Name 兜底，避免空名称影响下游规则推断与输出可读性
        if not patch.get("Name") and item_info.get("name"):
            patch["Name"] = item_info["name"]

        self._finalize_patch(item_id, patch, item_info, processed_items, source_file)
        self._store_patch_by_patch_type(item_id, patch)
        return True

    def _handle_clone_item(self, item_id: str, item_info: ItemInfo, clone_id: str, items_data: JsonObject, processed_items: set, source_file: Optional[str]) -> bool:
        """处理 CLONE 格式物品。"""
        template_data = self._resolve_clone_template(clone_id, items_data, processed_items, source_file)
        if not template_data:
            print(f"  跳过 {item_id}: 未找到clone ID {clone_id} 对应的模板")
            return False

        template_data["ItemID"] = item_id
        self._finalize_patch(item_id, template_data, item_info, processed_items, source_file)
        self._store_patch_by_patch_type(item_id, template_data)
        return True

    def _handle_itemtoclone_parent_resolution(self, item_id: str, item_data: JsonObject, item_info: ItemInfo, clone_id: str) -> bool:
        """处理 ITEMTOCLONE 的 parent_id 解析及类型刷新。"""
        parent_id = self._resolve_itemtoclone_parent_id(item_data, clone_id)
        if not parent_id:
            print(f"  跳过 {item_id}: 无法确定ItemToClone格式的parent_id (ItemToClone={clone_id})")
            return False

        item_info["parent_id"] = parent_id
        item_info["template_file"] = self.get_template_for_parent_id(parent_id)
        item_info["is_weapon"] = self.is_weapon(parent_id)
        item_info["is_gear"] = self.is_gear_simple(parent_id)
        item_info["is_consumable"] = self.is_consumable(parent_id)
        return True

    def _build_patch_for_parent_type(self, item_id: str, item_info: ItemInfo, parent_id: str, clone_id: Optional[str]) -> Optional[PatchData]:
        """根据 parent 类型构建补丁（不包含最终合并/校验/存储）。"""
        if self.is_ammo(parent_id):
            return self.create_default_ammo_patch(item_id, item_info)

        if self.is_consumable(parent_id):
            template_file = self.get_template_for_parent_id(parent_id)
            if template_file and template_file in self.templates:
                template_data = self.select_template_data(template_file, item_id, clone_id)
                if template_data:
                    return template_data
            return self.create_default_consumable_patch(item_id, item_info)

        template_file = self.get_template_for_parent_id(parent_id)
        if not template_file:
            return None

        template_data = self.select_template_data(template_file, item_id, clone_id)
        if template_data:
            return template_data

        if item_info.get("is_weapon"):
            return self.create_default_weapon_patch(item_id, item_info)
        return self.create_default_mod_patch(item_id, item_info, template_file)

    def _store_primary_patch(self, item_id: str, patch: PatchData, parent_id: str, item_info: ItemInfo):
        """按主类别存储补丁（ammo/consumable/weapon/attachment）。"""
        if self.is_ammo(parent_id):
            self.ammo_patches[item_id] = patch
            return

        if self.is_consumable(parent_id):
            self.consumables_patches[item_id] = patch
            return

        if item_info.get("is_weapon"):
            self.weapon_patches[item_id] = patch
            return

        self.attachment_patches[item_id] = patch

    def _dispatch_template_id_format(
        self,
        item_id: str,
        item_info: ItemInfo,
        template_id: Optional[str],
        processed_items: set,
        source_file: Optional[str],
    ) -> Optional[bool]:
        """分发 TEMPLATE_ID 格式处理。"""
        if not template_id:
            return None
        return self._handle_template_id_item(item_id, item_info, template_id, processed_items, source_file)

    def _dispatch_current_patch_format(
        self,
        item_id: str,
        item_data: JsonObject,
        item_info: ItemInfo,
        processed_items: set,
        source_file: Optional[str],
    ) -> Optional[bool]:
        """分发 CURRENT_PATCH 格式处理。"""
        return self._handle_current_patch_item(item_id, item_data, item_info, processed_items, source_file)

    def _dispatch_clone_format(
        self,
        item_id: str,
        item_info: ItemInfo,
        clone_id: Optional[str],
        items_data: JsonObject,
        processed_items: set,
        source_file: Optional[str],
    ) -> Optional[bool]:
        """分发 CLONE 格式处理。"""
        if not clone_id:
            return None
        return self._handle_clone_item(item_id, item_info, clone_id, items_data, processed_items, source_file)

    def _dispatch_format_specific_item(
        self,
        format_type: str,
        item_id: str,
        item_data: JsonObject,
        item_info: ItemInfo,
        template_id: Optional[str],
        clone_id: Optional[str],
        items_data: JsonObject,
        processed_items: set,
        source_file: Optional[str],
    ) -> Optional[bool]:
        """根据格式分发到专用处理器，返回 None 表示交给通用流程。"""
        format_handlers = {
            "TEMPLATE_ID": lambda: self._dispatch_template_id_format(
                item_id, item_info, template_id, processed_items, source_file
            ),
            "CURRENT_PATCH": lambda: self._dispatch_current_patch_format(
                item_id, item_data, item_info, processed_items, source_file
            ),
            "CLONE": lambda: self._dispatch_clone_format(
                item_id, item_info, clone_id, items_data, processed_items, source_file
            ),
        }

        handler = format_handlers.get(format_type)
        if handler is None:
            return None
        return handler()

    def _resolve_parent_id_for_processing(
        self,
        item_id: str,
        item_data: JsonObject,
        item_info: ItemInfo,
        format_type: str,
        clone_id: Optional[str],
    ) -> Optional[str]:
        """解析进入通用补丁流程所需的 parent_id。"""
        if format_type == "ITEMTOCLONE" and clone_id:
            if not self._handle_itemtoclone_parent_resolution(item_id, item_data, item_info, clone_id):
                return None
        return item_info.get("parent_id")

    def _build_finalize_and_store_primary_patch(
        self,
        item_id: str,
        item_info: ItemInfo,
        parent_id: Optional[str],
        clone_id: Optional[str],
        processed_items: set,
        source_file: Optional[str],
    ) -> bool:
        """执行通用补丁构建、收尾处理与分类存储。"""
        if not parent_id:
            return False

        patch = self._build_patch_for_parent_type(item_id, item_info, parent_id, clone_id)
        if not patch:
            return False

        self._finalize_patch(item_id, patch, item_info, processed_items, source_file)
        self._store_primary_patch(item_id, patch, parent_id, item_info)
        return True
    
    def process_single_item(
        self,
        item_id: str,
        item_data: JsonObject,
        items_data: JsonObject,
        processed_items: set,
        source_file: Optional[str] = None,
        format_type: Optional[str] = None,
    ) -> bool:
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
        if item_id in processed_items:
            return True

        if "enable" in item_data and not item_data["enable"]:
            return False

        if format_type is None:
            format_type = self.detect_item_format(item_data)
        if format_type == "UNKNOWN":
            return False

        item_info = self.extract_item_info(item_id, item_data, format_type, source_file)
        clone_id = item_info.get("clone_id")
        template_id = item_info.get("template_id")

        handler_result = self._dispatch_format_specific_item(
            format_type,
            item_id,
            item_data,
            item_info,
            template_id,
            clone_id,
            items_data,
            processed_items,
            source_file,
        )
        if handler_result is not None:
            return handler_result

        parent_id = self._resolve_parent_id_for_processing(
            item_id,
            item_data,
            item_info,
            format_type,
            clone_id,
        )
        return self._build_finalize_and_store_primary_patch(
            item_id,
            item_info,
            parent_id,
            clone_id,
            processed_items,
            source_file,
        )

    def _print_processing_file(self, item_file: Path):
        """打印当前处理文件路径。"""
        try:
            relative_path = item_file.relative_to(self.input_path)
            print(f"\n处理文件: {relative_path}")
        except ValueError:
            print(f"\n处理文件: {item_file.name}")

    def _load_items_data(self, item_file: Path) -> Optional[JsonObject]:
        """读取单个输入 JSON 文件。"""
        try:
            with open(item_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"  错误: 无法读取文件: {e}")
            return None

    def _process_items_in_file(self, items_data: JsonObject, source_name: str) -> Tuple[int, int]:
        """处理文件内所有物品，返回(成功处理数量, CURRENT_PATCH处理数量)。"""
        processed_items = set()
        processed_count = 0
        current_patch_count = 0

        for item_id, item_data in items_data.items():
            format_type = self.detect_item_format(item_data)
            if self.process_single_item(
                item_id,
                item_data,
                items_data,
                processed_items,
                source_name,
                format_type,
            ):
                processed_count += 1
                if format_type == "CURRENT_PATCH":
                    current_patch_count += 1

        return processed_count, current_patch_count

    def _print_generation_summary(self):
        """打印生成统计信息。"""
        weapon_count = len(self.weapon_patches)
        attachment_count = len(self.attachment_patches)
        ammo_count = len(self.ammo_patches)
        gear_count = len(self.gear_patches)
        consumable_count = len(self.consumables_patches)
        total = weapon_count + attachment_count + ammo_count + gear_count + consumable_count

        print(f"\n生成统计:")
        print(f"  武器补丁: {weapon_count} 个")
        print(f"  配件补丁: {attachment_count} 个")
        print(f"  子弹补丁: {ammo_count} 个")
        print(f"  装备补丁: {gear_count} 个")
        print(f"  消耗品补丁: {consumable_count} 个")
        print(f"  总计: {total} 个")
    
    def process_item_file(self, item_file: Path):
        """处理单个物品文件"""
        self._print_processing_file(item_file)

        items_data = self._load_items_data(item_file)
        if items_data is None:
            return

        # 使用 input 下的相对路径作为分组键，避免同名文件冲突并可还原目录结构。
        try:
            source_key = str(item_file.relative_to(self.input_path).with_suffix(""))
        except ValueError:
            source_key = item_file.stem

        processed_count, current_patch_count = self._process_items_in_file(items_data, source_key)

        # 当文件中 CURRENT_PATCH 占多数（>50%）时，输出保持原文件名（不加后缀）。
        current_patch_ratio = (current_patch_count / processed_count) if processed_count > 0 else 0.0
        if processed_count > 0 and current_patch_ratio > self.current_patch_plain_ratio_threshold:
            self.file_output_mode[source_key] = "plain"
        else:
            self.file_output_mode[source_key] = "suffix"

        print(f"  处理完成: {processed_count} 个物品")
    
    def generate_patches(self):
        """生成所有补丁"""
        print("\n开始生成现实主义MOD兼容补丁...")
        print(f"物品文件夹: {self.input_path}")

        json_files = sorted(self.input_path.rglob("*.json"), key=lambda path: str(path.relative_to(self.input_path)).lower())
        print(f"找到 {len(json_files)} 个JSON文件")

        for item_file in json_files:
            self.process_item_file(item_file)

        self._print_generation_summary()

    def _save_source_grouped_patches(self, output_path: Path):
        """按源文件保存补丁，并保留 input 的原目录结构。"""
        for source_name, patches in self.file_based_patches.items():
            if not patches:
                continue

            source_rel = Path(source_name)
            output_mode = self.file_output_mode.get(source_name, "suffix")
            output_filename = f"{source_rel.name}.json" if output_mode == "plain" else f"{source_rel.name}_realism_patch.json"
            file_output = output_path / source_rel.parent / output_filename
            file_output.parent.mkdir(parents=True, exist_ok=True)

            with open(file_output, 'w', encoding='utf-8') as f:
                json.dump(patches, f, ensure_ascii=False, indent=4)

            try:
                display_rel = file_output.relative_to(output_path)
            except ValueError:
                display_rel = file_output
            print(f"  [源文件输出] 补丁已保存到: {display_rel}")

    def _clear_output_directory(self, output_path: Path):
        """清空输出目录中的旧结果（保留 output 根目录本身）。"""
        if not output_path.exists():
            return

        for child in output_path.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    
    def save_patches(self, output_dir: Optional[str] = None):
        """保存补丁文件（仅按源文件输出，并保留目录结构）。"""
        if output_dir is None:
            output_path = self.base_path / "output"
        else:
            output_path = Path(output_dir)

        output_path.mkdir(parents=True, exist_ok=True)
        
        print("\n正在导出补丁文件...")

        self._clear_output_directory(output_path)
        self._save_source_grouped_patches(output_path)


def main():
    """主函数"""
    print("=" * 60)
    print("EFT 现实主义数值生成器 v3.17")
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
