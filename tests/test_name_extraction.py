import json
import unittest
from pathlib import Path

from audit_output_rule_violations import OutputRuleAuditor
from generate_realism_patch import RealismPatchGenerator


BASE_DIR = Path(__file__).resolve().parents[1]


class NameExtractionRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = RealismPatchGenerator(str(BASE_DIR))
        cls.auditor = OutputRuleAuditor(BASE_DIR)

    def _load_input_item(self, relative_path: str, item_id: str):
        data = json.loads((BASE_DIR / relative_path).read_text(encoding="utf-8"))
        return data[item_id]

    def test_clone_uses_locales_name_fallback(self) -> None:
        relative_path = "input/[2]新装备、衣服-TacticalGearComponent.json"
        item_id = "672e2e754f01ef56b4aa66a3"
        item = self._load_input_item(relative_path, item_id)

        expected_name = item["locales"]["en"]["name"]
        format_type = self.generator.detect_item_format(item)
        info = self.generator.extract_item_info(item_id, item, format_type, Path(relative_path).name)

        self.assertEqual("CLONE", format_type)
        self.assertEqual(expected_name, info["name"])

    def test_standard_uses_locales_name(self) -> None:
        relative_path = "input/[2]新物品-竞技场赛季奖励-SPT Battlepass.json"
        item_id = "67fd89d05567aff486d5083a"
        item = self._load_input_item(relative_path, item_id)

        expected_name = item["locales"]["en"]["name"]
        format_type = self.generator.detect_item_format(item)
        info = self.generator.extract_item_info(item_id, item, format_type, Path(relative_path).name)

        self.assertEqual("STANDARD", format_type)
        self.assertEqual(expected_name, info["name"])

    def test_vir_keeps_item_name_before_locales_fallback(self) -> None:
        relative_path = "input/[3]新武器-SIG_MCX_VIRTUS_items.json"
        item_id = "f546b7974a7dd485d05db42e"
        item = self._load_input_item(relative_path, item_id)

        expected_name = item["item"]["_name"]
        format_type = self.generator.detect_item_format(item)
        info = self.generator.extract_item_info(item_id, item, format_type, Path(relative_path).name)

        self.assertEqual("VIR", format_type)
        self.assertEqual(expected_name, info["name"])

    def test_itemtoclone_uses_localepush_name(self) -> None:
        relative_path = "input/[5]战局大修-RaidOverhaul_ConstItems/SecConts.json"
        item_id = "6621b12c9f46c3eb4a0c8f40"
        item = self._load_input_item(relative_path, item_id)

        expected_name = item["LocalePush"]["name"]
        format_type = self.generator.detect_item_format(item)
        info = self.generator.extract_item_info(item_id, item, format_type, Path(relative_path).name)

        self.assertEqual("ITEMTOCLONE", format_type)
        self.assertEqual(expected_name, info["name"])

    def test_current_patch_falls_back_to_localized_name_only_when_name_missing(self) -> None:
        item_id = "synthetic-current-patch"
        item = {
            "$type": "RealismMod.WeaponMod, RealismMod",
            "ItemID": item_id,
            "Name": "",
            "locales": {
                "en": {
                    "name": "Synthetic Localized Name",
                    "shortName": "Synthetic",
                    "description": "synthetic description",
                }
            },
        }

        format_type = self.generator.detect_item_format(item)
        info = self.generator.extract_item_info(item_id, item, format_type, "synthetic.json")

        self.assertEqual("CURRENT_PATCH", format_type)
        self.assertEqual("Synthetic Localized Name", info["name"])

    def test_current_patch_keeps_explicit_name_over_localized_fallback(self) -> None:
        item_id = "synthetic-current-patch-explicit"
        item = {
            "$type": "RealismMod.WeaponMod, RealismMod",
            "ItemID": item_id,
            "Name": "Explicit Current Patch Name",
            "locales": {
                "en": {
                    "name": "Synthetic Localized Name",
                }
            },
        }

        format_type = self.generator.detect_item_format(item)
        info = self.generator.extract_item_info(item_id, item, format_type, "synthetic.json")

        self.assertEqual("CURRENT_PATCH", format_type)
        self.assertEqual("Explicit Current Patch Name", info["name"])

    def test_audit_preserves_source_name_when_output_name_is_empty(self) -> None:
        source_file = "[2]新装备、衣服-TacticalGearComponent.json"
        item_id = "672e2e754f01ef56b4aa66a3"
        source_item = self._load_input_item(f"input/{source_file}", item_id)
        expected_name = source_item["locales"]["en"]["name"]

        item_info = self.auditor._build_item_info(
            item_id,
            {
                "$type": "RealismMod.WeaponMod, RealismMod",
                "Name": "",
                "ItemID": item_id,
            },
            source_file,
        )

        self.assertEqual(expected_name, item_info["name"])


if __name__ == "__main__":
    unittest.main()