#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""扫描 output/ 中的补丁，找出超出规则范围或无法命中规则档位的物品。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, cast

from ammo_rule_ranges import (
    AMMO_PENETRATION_MODIFIERS,
    AMMO_PENETRATION_TIERS,
    AMMO_PROFILE_RANGES,
    AMMO_SPECIAL_MODIFIERS,
)
from attachment_rule_ranges import MOD_PROFILE_RANGES
from gear_rule_ranges import GEAR_PROFILE_RANGES
from generate_realism_patch import (
    GEAR_CLAMP_RULES,
    GUN_CLAMP_RULES,
    MOD_CLAMP_RULES,
    RealismPatchGenerator,
)
from weapon_refinement_rules import (
    WEAPON_CALIBER_RULE_MODIFIERS,
    WEAPON_STOCK_RULE_MODIFIERS,
)
from weapon_rule_ranges import WEAPON_PROFILE_RANGES
from generate_realism_patch import ItemInfo

NumberRange = Tuple[float, float]
WarningDetail = Dict[str, str]
ID_LIKE_NAME_REGEX = re.compile(r"^[0-9a-f]{16,}$", re.IGNORECASE)
ARMBAND_PARENT_ID = "5b3f15d486f77432d0509248"
RANGE_COMPARISON_EPSILON = 1e-9


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def make_warning_detail(group: str, category: str, message: str) -> WarningDetail:
    return {
        "group": group,
        "category": category,
        "message": message,
    }


def build_warning_breakdown(warning_details: List[Mapping[str, str]]) -> Dict[str, Dict[str, int]]:
    by_group: Dict[str, int] = {}
    by_category: Dict[str, int] = {}
    for detail in warning_details:
        group = str(detail.get("group", "未分类警告"))
        category = str(detail.get("category", "unknown_warning"))
        by_group[group] = by_group.get(group, 0) + 1
        by_category[category] = by_category.get(category, 0) + 1
    return {
        "by_group": dict(sorted(by_group.items(), key=lambda item: (-item[1], item[0]))),
        "by_category": dict(sorted(by_category.items(), key=lambda item: (-item[1], item[0]))),
    }


class OutputRuleAuditor:
    def __init__(
        self,
        base_path: Path,
        output_dir: Optional[Path] = None,
        include_ok: bool = False,
        include_template_exports: bool = False,
    ):
        self.base_path = base_path
        self.output_dir = output_dir or (base_path / "output")
        self.include_ok = include_ok
        self.include_template_exports = include_template_exports
        self.generator = RealismPatchGenerator(str(base_path))
        self._source_file_cache: Dict[str, Optional[Dict[str, Any]]] = {}

    def _should_audit_file(self, path: Path) -> bool:
        if not path.is_file() or path.suffix.lower() != ".json":
            return False
        if self.include_template_exports:
            return True
        return path.stem.endswith("_realism_patch")

    def audit(self) -> Dict[str, Any]:
        json_files = sorted(
            path for path in self.output_dir.rglob("*.json") if self._should_audit_file(path)
        )
        report_files: List[Dict[str, Any]] = []
        total_items = 0
        total_violations = 0
        total_warnings = 0
        all_warning_details: List[Mapping[str, str]] = []

        for json_file in json_files:
            file_report = self._audit_file(json_file)
            if file_report["item_count"] == 0:
                continue
            all_warning_details.extend(file_report.pop("_warning_details", []))
            report_files.append(file_report)
            total_items += file_report["item_count"]
            total_violations += file_report["violation_count"]
            total_warnings += file_report["warning_count"]

        return {
            "output_dir": str(self.output_dir),
            "scan_mode": "all_json" if self.include_template_exports else "realism_patch_only",
            "file_count": len(report_files),
            "item_count": total_items,
            "violation_count": total_violations,
            "warning_count": total_warnings,
            "warning_breakdown": build_warning_breakdown(all_warning_details),
            "files": report_files,
        }

    def _audit_file(self, json_file: Path) -> Dict[str, Any]:
        with open(json_file, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        if not isinstance(data, dict):
            return {
                "file": str(json_file.relative_to(self.base_path)),
                "item_count": 0,
                "violation_count": 0,
                "warning_count": 1,
                "items": [],
                "warnings": ["文件根对象不是字典，已跳过"],
            }

        items: List[Dict[str, Any]] = []
        flagged_item_count = 0
        violation_count = 0
        warning_count = 0
        file_warning_details: List[Mapping[str, str]] = []
        source_file = self._derive_source_file(json_file)

        for item_id, patch in data.items():
            if not isinstance(patch, dict):
                warning_count += 1
                items.append(
                    {
                        "item_id": item_id,
                        "name": "",
                        "type": "",
                        "status": "warning",
                        "warnings": ["物品数据不是对象，无法审计"],
                        "warning_details": [
                            make_warning_detail("数据异常", "invalid_item_payload", "物品数据不是对象，无法审计")
                        ],
                        "violations": [],
                        "context": {"source_file": source_file},
                    }
                )
                file_warning_details.append(
                    make_warning_detail("数据异常", "invalid_item_payload", "物品数据不是对象，无法审计")
                )
                flagged_item_count += 1
                continue

            item_report = self._audit_item(item_id, patch, source_file)
            if self.include_ok or item_report["status"] != "ok":
                items.append(item_report)
            if item_report["status"] != "ok":
                flagged_item_count += 1
            violation_count += len(item_report["violations"])
            warning_count += len(item_report["warnings"])
            file_warning_details.extend(item_report.get("warning_details", []))

        return {
            "file": str(json_file.relative_to(self.base_path)).replace("\\", "/"),
            "source_file": source_file,
            "item_count": len(data),
            "flagged_item_count": flagged_item_count,
            "violation_count": violation_count,
            "warning_count": warning_count,
            "warning_breakdown": build_warning_breakdown(file_warning_details),
            "_warning_details": file_warning_details,
            "items": items,
        }

    def _derive_source_file(self, json_file: Path) -> str:
        relative = json_file.relative_to(self.output_dir)
        if relative.stem.endswith("_realism_patch"):
            source_name = relative.stem[: -len("_realism_patch")] + relative.suffix
            relative = relative.with_name(source_name)
        return relative.as_posix()

    def _load_source_items(self, source_file: str) -> Optional[Dict[str, Any]]:
        if source_file in self._source_file_cache:
            return self._source_file_cache[source_file]

        source_path = self.base_path / "input" / Path(source_file)
        if not source_path.exists():
            self._source_file_cache[source_file] = None
            return None

        try:
            with open(source_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
        except (OSError, json.JSONDecodeError):
            loaded = None

        self._source_file_cache[source_file] = loaded if isinstance(loaded, dict) else None
        return self._source_file_cache[source_file]

    def _build_item_info(self, item_id: str, patch: Mapping[str, Any], source_file: str) -> ItemInfo:
        item_info: ItemInfo = {
            "item_id": item_id,
            "parent_id": None,
            "clone_id": None,
            "template_id": None,
            "template_file": None,
            "name": patch.get("Name", ""),
            "is_weapon": False,
            "is_gear": False,
            "is_consumable": False,
            "item_type": patch.get("$type", ""),
            "properties": dict(patch),
            "source_file": source_file,
            "format_type": None,
        }

        source_items = self._load_source_items(source_file)
        if source_items and item_id in source_items and isinstance(source_items[item_id], dict):
            source_item = source_items[item_id]
            format_type = self.generator.detect_item_format(source_item)
            source_info = self.generator.extract_item_info(item_id, source_item, format_type, source_file)
            if format_type == "ITEMTOCLONE" and source_info.get("clone_id"):
                clone_id = str(source_info["clone_id"])
                parent_id = self.generator._resolve_itemtoclone_parent_id(source_item, clone_id)
                if parent_id:
                    source_info["parent_id"] = parent_id
                    source_info["template_file"] = self.generator.get_template_for_parent_id(parent_id)
                    source_info["is_weapon"] = self.generator.is_weapon(parent_id)
                    source_info["is_gear"] = self.generator.is_gear_simple(parent_id)
                    source_info["is_consumable"] = self.generator.is_consumable(parent_id)
            source_properties = dict(source_info.get("properties") or {})
            cast(Dict[str, Any], source_info)["source_properties"] = dict(source_properties)
            source_properties.update(dict(patch))
            source_info["properties"] = source_properties
            patch_name = patch.get("Name")
            if isinstance(patch_name, str) and patch_name.strip():
                source_info["name"] = patch_name
            source_info["item_type"] = patch.get("$type", source_info.get("item_type", ""))
            return source_info

        self.generator._enrich_item_info_with_source_context(
            item_info,
            dict(patch),
            "CURRENT_PATCH",
            source_file,
        )
        cast(Dict[str, Any], item_info)["source_properties"] = dict(item_info.get("properties") or {})
        return item_info

    def _is_cosmetic_item(self, item_info: Mapping[str, Any], patch: Mapping[str, Any]) -> bool:
        template_file = str(item_info.get("template_file") or "").lower()
        parent_id = self.generator.normalize_parent_id(item_info.get("parent_id"))
        item_name = str(patch.get("Name", "")).strip().lower()

        if "cosmeticstemplates.json" in template_file:
            return True
        if parent_id == ARMBAND_PARENT_ID:
            return True
        return any(keyword in item_name for keyword in ["patch", "补丁", "贴章", "臂章"])

    def _get_audit_exemption(self, item_info: Mapping[str, Any], patch: Mapping[str, Any]) -> Optional[str]:
        if item_info.get("is_consumable"):
            return "consumable"
        if self._is_cosmetic_item(item_info, patch):
            return "cosmetic"
        return None

    def _audit_item(self, item_id: str, patch: Mapping[str, Any], source_file: str) -> Dict[str, Any]:
        item_info = self._build_item_info(item_id, patch, source_file)
        item_type = str(patch.get("$type", ""))
        violations: List[Dict[str, Any]] = []
        warnings: List[str] = []
        warning_details: List[WarningDetail] = []
        context: Dict[str, Any] = {"source_file": source_file}
        audit_exemption = self._get_audit_exemption(item_info, patch)

        if audit_exemption:
            context["audit_exemption"] = audit_exemption
            return {
                "item_id": item_id,
                "name": patch.get("Name", ""),
                "type": item_type,
                "status": "ok",
                "warnings": warnings,
                "warning_details": warning_details,
                "violations": violations,
                "context": context,
            }

        if "RealismMod.Gun" in item_type:
            self._collect_range_violations(violations, patch, GUN_CLAMP_RULES, "global_clamp")
            weapon_profile = self.generator._infer_weapon_profile(dict(patch), item_info)
            context["weapon_profile"] = weapon_profile
            if weapon_profile:
                expected_ranges, extra_context = self._build_weapon_expected_ranges(dict(patch), item_info, weapon_profile)
                context.update(extra_context)
                self._collect_range_violations(violations, patch, expected_ranges, "weapon_rule")
            else:
                detail = self._build_profile_gap_warning_detail(
                    patch,
                    "weapon",
                    "weapon_profile_unresolved",
                    "无法推断武器规则档位，未能校验武器范围",
                )
                warnings.append(detail["message"])
                warning_details.append(detail)

            recoil_angle = patch.get("RecoilAngle")
            if is_number(recoil_angle):
                recoil_angle_value = float(cast(float, recoil_angle))
                if not 30 <= recoil_angle_value <= 150:
                    violations.append(
                        self._build_violation("RecoilAngle", recoil_angle, 30, 150, "weapon_special")
                    )

            if weapon_profile == "pistol" and patch.get("HasShoulderContact") is not False:
                violations.append(
                    {
                        "field": "HasShoulderContact",
                        "value": patch.get("HasShoulderContact"),
                        "expected": False,
                        "rule": "weapon_special",
                        "message": "手枪规则要求 HasShoulderContact=False",
                    }
                )

        elif "RealismMod.WeaponMod" in item_type:
            self._collect_range_violations(violations, patch, MOD_CLAMP_RULES, "global_clamp")
            mod_profile = self.generator._infer_mod_profile(dict(patch), item_info)
            context["mod_profile"] = mod_profile
            context["template_file"] = item_info.get("template_file")
            if mod_profile and mod_profile in MOD_PROFILE_RANGES:
                self._collect_range_violations(violations, patch, MOD_PROFILE_RANGES[mod_profile], "mod_rule")
            else:
                detail = self._build_mod_warning_detail(item_info, patch, mod_profile)
                if detail["category"] == "mod_profile_unresolved":
                    context["audit_exemption"] = "mod_profile_unresolved"
                    return {
                        "item_id": item_id,
                        "name": patch.get("Name", ""),
                        "type": item_type,
                        "status": "ok",
                        "warnings": warnings,
                        "warning_details": warning_details,
                        "violations": violations,
                        "context": context,
                    }
                warnings.append(detail["message"])
                warning_details.append(detail)

            velocity = patch.get("Velocity")
            item_name = str(patch.get("Name", "")).lower()
            max_velocity = 15.0 if "barrel" in item_name else 5.0
            if is_number(velocity):
                velocity_value = float(cast(float, velocity))
                if not -max_velocity <= velocity_value <= max_velocity:
                    violations.append(
                        self._build_violation("Velocity", velocity, -max_velocity, max_velocity, "mod_special")
                    )

            if context.get("mod_profile") == "muzzle_suppressor" and "CanCycleSubs" in patch and patch.get("CanCycleSubs") is not True:
                violations.append(
                    {
                        "field": "CanCycleSubs",
                        "value": patch.get("CanCycleSubs"),
                        "expected": True,
                        "rule": "mod_special",
                        "message": "消音器规则要求 CanCycleSubs=True",
                    }
                )

        elif "RealismMod.Ammo" in item_type:
            ammo_profile = self.generator._infer_ammo_profile(dict(patch), item_info)
            source_properties = item_info.get("source_properties")
            penetration_probe = dict(patch)
            if isinstance(source_properties, dict):
                for key in ["PenetrationPower", "Penetration", "penPower"]:
                    if key in source_properties:
                        penetration_probe[key] = source_properties[key]
                        break
            pen_tier = self.generator._infer_ammo_penetration_tier(penetration_probe, item_info)
            special_profile = self.generator._infer_ammo_special_profile(dict(patch), item_info)
            context.update(
                {
                    "ammo_profile": ammo_profile,
                    "penetration_tier": pen_tier,
                    "special_profile": special_profile,
                }
            )
            if ammo_profile in AMMO_PROFILE_RANGES:
                expected_ranges = self._build_ammo_expected_ranges(ammo_profile, pen_tier, special_profile)
                self._collect_range_violations(violations, patch, expected_ranges, "ammo_rule")
            else:
                detail = self._build_profile_gap_warning_detail(
                    patch,
                    "ammo",
                    "ammo_profile_unresolved",
                    "无法推断弹药规则档位，未能校验弹药范围",
                )
                warnings.append(detail["message"])
                warning_details.append(detail)

        elif "RealismMod.Gear" in item_type:
            self._collect_range_violations(violations, patch, GEAR_CLAMP_RULES, "gear_clamp")
            gear_profile = self.generator._infer_gear_profile(dict(patch), item_info)
            context["gear_profile"] = gear_profile
            if gear_profile and gear_profile in GEAR_PROFILE_RANGES:
                self._collect_range_violations(violations, patch, GEAR_PROFILE_RANGES[gear_profile], "gear_rule")
            else:
                detail = self._build_profile_gap_warning_detail(
                    patch,
                    "gear",
                    "gear_profile_unresolved",
                    "无法推断装备规则档位，未能校验装备范围",
                )
                warnings.append(detail["message"])
                warning_details.append(detail)
        else:
            detail = make_warning_detail(
                "未配置专项审计",
                "unsupported_item_type",
                "当前类型未配置专项审计，仅保留基础信息",
            )
            warnings.append(detail["message"])
            warning_details.append(detail)

        return {
            "item_id": item_id,
            "name": patch.get("Name", ""),
            "type": item_type,
            "status": "violation" if violations else ("warning" if warnings else "ok"),
            "warnings": warnings,
            "warning_details": warning_details,
            "violations": violations,
            "context": context,
        }

    def _build_profile_gap_warning_detail(
        self,
        patch: Mapping[str, Any],
        profile_kind: str,
        category: str,
        default_message: str,
    ) -> WarningDetail:
        item_name = str(patch.get("Name", "")).strip()
        if not item_name:
            return make_warning_detail("信息不足", f"{profile_kind}_empty_name", f"名称为空，{default_message}")
        if self._looks_like_item_id(item_name):
            return make_warning_detail("信息不足", f"{profile_kind}_id_like_name", f"名称疑似物品ID，{default_message}")
        return make_warning_detail("未识别规则档位", category, default_message)

    def _build_mod_warning_detail(
        self,
        item_info: Mapping[str, Any],
        patch: Mapping[str, Any],
        mod_profile: Optional[str],
    ) -> WarningDetail:
        template_file = str(item_info.get("template_file") or "")
        item_name = str(patch.get("Name", "")).strip()
        mod_type = str(patch.get("ModType", "")).strip()
        parent_id = str(item_info.get("parent_id") or "")

        if not item_name:
            return make_warning_detail("信息不足", "mod_empty_name", "名称为空，无法推断附件规则档位")
        if self._looks_like_item_id(item_name):
            return make_warning_detail("信息不足", "mod_id_like_name", "名称疑似物品ID，无法推断附件规则档位")

        unsupported_templates = {
            "ChargingHandleTemplates.json": ("无规则类别", "unsupported_charging_handle", "当前物品属于拉机柄类，尚未配置附件规则范围"),
            "AuxiliaryModTemplates.json": ("无规则类别", "unsupported_auxiliary_mod", "当前物品属于辅助小件类，尚未配置附件规则范围"),
            "UBGLTempaltes.json": ("无规则类别", "unsupported_ubgl", "当前物品属于下挂榴弹发射器类，尚未配置附件规则范围"),
        }
        if template_file in unsupported_templates:
            group, category, message = unsupported_templates[template_file]
            return make_warning_detail(group, category, message)

        if any(keyword in item_name.lower() for keyword in ["patch", "补丁", "贴章", "臂章"]):
            return make_warning_detail("无规则类别", "unsupported_cosmetic_patch", "当前物品更像装饰类部件，尚未配置附件规则范围")

        unsupported_name_patterns = {
            "charging handle": ("无规则类别", "unsupported_charging_handle", "当前物品属于拉机柄类，尚未配置附件规则范围"),
            "拉机柄": ("无规则类别", "unsupported_charging_handle", "当前物品属于拉机柄类，尚未配置附件规则范围"),
            "рукоятка взведения": ("无规则类别", "unsupported_charging_handle", "当前物品属于拉机柄类，尚未配置附件规则范围"),
            "bipod": ("无规则类别", "unsupported_bipod", "当前物品属于二脚架类，尚未配置附件规则范围"),
            "二脚架": ("无规则类别", "unsupported_bipod", "当前物品属于二脚架类，尚未配置附件规则范围"),
            "trigger": ("无规则类别", "unsupported_trigger_group", "当前物品属于扳机/击发组件类，尚未配置附件规则范围"),
            "hammer": ("无规则类别", "unsupported_trigger_group", "当前物品属于扳机/击发组件类，尚未配置附件规则范围"),
            "slide stop": ("无规则类别", "unsupported_pistol_internal", "当前物品属于手枪机件类，尚未配置附件规则范围"),
            "lens cap": ("无规则类别", "unsupported_optic_accessory", "当前物品属于瞄具附件小件类，尚未配置附件规则范围"),
        }
        lowered_name = item_name.lower()
        for pattern, detail in unsupported_name_patterns.items():
            if pattern in lowered_name or pattern in item_name:
                group, category, message = detail
                return make_warning_detail(group, category, message)

        if not template_file and not mod_type and not parent_id:
            return make_warning_detail("信息不足", "mod_missing_name_metadata_signals", "名称缺少有效类别关键词，且缺少模板/父类/ModType 信息，无法推断附件规则档位")

        if mod_profile and mod_profile not in MOD_PROFILE_RANGES:
            return make_warning_detail("无规则类别", "recognized_mod_profile_without_rule", f"已识别附件档位 {mod_profile}，但当前没有对应规则范围")

        return make_warning_detail("未识别规则档位", "mod_profile_unresolved", "无法推断附件规则档位，未能校验附件范围")

    def _looks_like_item_id(self, item_name: str) -> bool:
        return bool(ID_LIKE_NAME_REGEX.fullmatch(item_name.strip()))

    def _build_weapon_expected_ranges(
        self,
        patch: Mapping[str, Any],
        item_info: Mapping[str, Any],
        weapon_profile: str,
    ) -> Tuple[Dict[str, NumberRange], Dict[str, Any]]:
        ranges: Dict[str, NumberRange] = {
            key: (float(bounds[0]), float(bounds[1]))
            for key, bounds in WEAPON_PROFILE_RANGES[weapon_profile].items()
        }

        caliber_profile = self.generator._infer_weapon_caliber_profile(dict(patch), item_info)
        stock_profile = self.generator._infer_weapon_stock_profile(dict(patch))
        caliber_mods = WEAPON_CALIBER_RULE_MODIFIERS.get(caliber_profile, {}) if caliber_profile else {}
        stock_mods = WEAPON_STOCK_RULE_MODIFIERS.get(stock_profile, {}) if stock_profile else {}

        for key, base_range in WEAPON_PROFILE_RANGES[weapon_profile].items():
            delta_min = 0.0
            delta_max = 0.0
            if key in caliber_mods:
                delta_min += float(caliber_mods[key][0])
                delta_max += float(caliber_mods[key][1])
            if key in stock_mods:
                delta_min += float(stock_mods[key][0])
                delta_max += float(stock_mods[key][1])
            min_v = float(base_range[0]) + delta_min
            max_v = float(base_range[1]) + delta_max
            if min_v > max_v:
                min_v, max_v = max_v, min_v
            ranges[key] = (min_v, max_v)

        supplemental_keys = (set(caliber_mods.keys()) | set(stock_mods.keys())) - set(ranges.keys())
        for key in supplemental_keys:
            min_v = 0.0
            max_v = 0.0
            if key in caliber_mods:
                min_v += float(caliber_mods[key][0])
                max_v += float(caliber_mods[key][1])
            if key in stock_mods:
                min_v += float(stock_mods[key][0])
                max_v += float(stock_mods[key][1])
            if min_v > max_v:
                min_v, max_v = max_v, min_v
            ranges[key] = (min_v, max_v)

        return ranges, {
            "caliber_profile": caliber_profile,
            "stock_profile": stock_profile,
        }

    def _build_ammo_expected_ranges(
        self,
        ammo_profile: str,
        penetration_tier: str,
        special_profile: Optional[str],
    ) -> Dict[str, NumberRange]:
        expected_ranges: Dict[str, NumberRange] = {}
        base_ranges = AMMO_PROFILE_RANGES[ammo_profile]
        penetration_mods = AMMO_PENETRATION_MODIFIERS.get(penetration_tier, {})
        special_mods = AMMO_SPECIAL_MODIFIERS.get(special_profile, {}) if special_profile else {}
        malfunction_keys = {"MalfMisfireChance", "MisfireChance", "MalfFeedChance"}

        for key, base_range in base_ranges.items():
            tier_pair = penetration_mods.get(key, (0.0, 0.0))
            special_pair = special_mods.get(key, (0.0, 0.0))
            min_v = float(base_range[0]) + float(tier_pair[0]) + float(special_pair[0])
            max_v = float(base_range[1]) + float(tier_pair[1]) + float(special_pair[1])

            if key in malfunction_keys:
                min_v = max(0.001, min(0.015, min_v))
                max_v = max(0.001, min(0.015, max_v))
            if key == "ArmorDamage":
                min_v = max(1.0, min(1.2, min_v))
                max_v = max(1.0, min(1.2, max_v))
            if min_v > max_v:
                min_v, max_v = max_v, min_v
            expected_ranges[key] = (min_v, max_v)

        return expected_ranges

    def _collect_range_violations(
        self,
        violations: List[Dict[str, Any]],
        patch: Mapping[str, Any],
        expected_ranges: Mapping[str, Tuple[float, float]],
        rule_name: str,
    ) -> None:
        for field, bounds in expected_ranges.items():
            if field not in patch:
                continue
            value = patch.get(field)
            if not is_number(value):
                continue

            min_v = float(bounds[0])
            max_v = float(bounds[1])
            current = float(cast(float, value))
            if current < (min_v - RANGE_COMPARISON_EPSILON) or current > (max_v + RANGE_COMPARISON_EPSILON):
                violations.append(self._build_violation(field, value, min_v, max_v, rule_name))

    def _build_violation(
        self,
        field: str,
        value: Any,
        min_v: float,
        max_v: float,
        rule_name: str,
    ) -> Dict[str, Any]:
        return {
            "field": field,
            "value": value,
            "expected_min": min_v,
            "expected_max": max_v,
            "rule": rule_name,
            "message": f"{field}={value} 超出允许范围 [{min_v}, {max_v}]",
        }


def build_console_summary(report: Mapping[str, Any], summary_limit: int) -> str:
    lines = [
        "=" * 72,
        "输出结果规则审计",
        "=" * 72,
        f"扫描目录: {report['output_dir']}",
        f"扫描文件: {report['file_count']} 个",
        f"扫描物品: {report['item_count']} 个",
        f"违规字段: {report['violation_count']} 处",
        f"警告条目: {report['warning_count']} 条",
    ]

    warning_breakdown = report.get("warning_breakdown", {}).get("by_group", {})
    if warning_breakdown:
        lines.append("警告分组:")
        for group, count in warning_breakdown.items():
            lines.append(f"  - {group}: {count} 条")

    findings: List[str] = []
    for file_report in report["files"]:
        for item in file_report["items"]:
            if item["violations"]:
                first = item["violations"][0]
                findings.append(
                    f"[违规] {file_report['file']} | {item['item_id']} | {item['name'] or '<unnamed>'} | {first['message']}"
                )
            elif item["warnings"]:
                findings.append(
                    f"[警告] {file_report['file']} | {item['item_id']} | {item['name'] or '<unnamed>'} | {item['warnings'][0]}"
                )

    if findings:
        lines.append("-")
        lines.append(f"前 {min(summary_limit, len(findings))} 条结果:")
        lines.extend(findings[:summary_limit])
    else:
        lines.append("-")
        lines.append("未发现超出规则范围的物品。")

    return "\n".join(lines)


def build_warning_group_report(report: Mapping[str, Any], target_group: str) -> Dict[str, Any]:
    grouped_items: Dict[str, List[Dict[str, Any]]] = {}

    for file_report in report["files"]:
        file_path = str(file_report.get("file", ""))
        source_file = str(file_report.get("source_file", ""))
        for item in file_report.get("items", []):
            for detail in item.get("warning_details", []):
                if detail.get("group") != target_group:
                    continue

                category = str(detail.get("category", "unknown_warning"))
                grouped_items.setdefault(category, []).append(
                    {
                        "file": file_path,
                        "source_file": source_file,
                        "item_id": item.get("item_id", ""),
                        "name": item.get("name", ""),
                        "type": item.get("type", ""),
                        "message": detail.get("message", ""),
                        "context": item.get("context", {}),
                    }
                )

    categories: List[Dict[str, Any]] = []
    total_items = 0
    for category, items in sorted(grouped_items.items(), key=lambda entry: (-len(entry[1]), entry[0])):
        total_items += len(items)
        categories.append(
            {
                "category": category,
                "count": len(items),
                "items": items,
            }
        )

    return {
        "group": target_group,
        "count": total_items,
        "category_count": len(categories),
        "categories": categories,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="扫描 output 中不符合规则的物品")
    parser.add_argument(
        "--output-dir",
        default="output",
        help="待审计输出目录，默认 output",
    )
    parser.add_argument(
        "--report-file",
        default="audit_reports/output_rule_audit.json",
        help="审计报告输出路径，默认 audit_reports/output_rule_audit.json",
    )
    parser.add_argument(
        "--summary-limit",
        type=int,
        default=30,
        help="终端最多显示多少条结果，默认 30",
    )
    parser.add_argument(
        "--fail-on-violations",
        action="store_true",
        help="存在违规字段时返回非 0 退出码",
    )
    parser.add_argument(
        "--include-ok",
        action="store_true",
        help="将正常项也写入报告，默认仅保留违规/警告项",
    )
    parser.add_argument(
        "--include-template-exports",
        action="store_true",
        help="连同 output 下的模板导出 JSON 一起审计；默认仅扫描 *_realism_patch.json",
    )
    parser.add_argument(
        "--warning-group-report-file",
        default="",
        help="按警告分组导出清单，例如导出无规则类别清单到单独 JSON 文件",
    )
    parser.add_argument(
        "--warning-group",
        default="无规则类别",
        help="与 --warning-group-report-file 配套使用，要导出的警告分组名称，默认 无规则类别",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_path = Path(__file__).resolve().parent
    output_dir = (base_path / args.output_dir).resolve()
    report_file = (base_path / args.report_file).resolve()
    warning_group_report_file = (
        (base_path / args.warning_group_report_file).resolve()
        if args.warning_group_report_file
        else None
    )

    if not output_dir.exists():
        print(f"输出目录不存在: {output_dir}")
        return 1

    auditor = OutputRuleAuditor(
        base_path=base_path,
        output_dir=output_dir,
        include_ok=args.include_ok,
        include_template_exports=args.include_template_exports,
    )
    report = auditor.audit()

    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=4)

    if warning_group_report_file is not None:
        warning_group_report = build_warning_group_report(report, args.warning_group)
        warning_group_report_file.parent.mkdir(parents=True, exist_ok=True)
        with open(warning_group_report_file, "w", encoding="utf-8") as handle:
            json.dump(warning_group_report, handle, ensure_ascii=False, indent=4)

    print(build_console_summary(report, args.summary_limit))
    print(f"\n完整报告已写入: {report_file}")
    if warning_group_report_file is not None:
        print(
            f"警告分组清单已写入: {warning_group_report_file} "
            f"(分组: {args.warning_group}, 条目: {warning_group_report['count']})"
        )

    if args.fail_on_violations and report["violation_count"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())