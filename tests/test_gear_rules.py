import unittest
from pathlib import Path

from generate_realism_patch import RealismPatchGenerator


BASE_DIR = Path(__file__).resolve().parents[1]


class GearRuleRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = RealismPatchGenerator(str(BASE_DIR))

    def _gear_info(self, parent_id: str, template_file: str, properties=None):
        return {
            "item_id": "synthetic-gear",
            "parent_id": parent_id,
            "clone_id": None,
            "template_id": None,
            "template_file": template_file,
            "name": None,
            "is_weapon": False,
            "is_gear": True,
            "is_consumable": False,
            "item_type": "RealismMod.Gear, RealismMod",
            "properties": properties or {},
            "source_file": "synthetic.json",
            "format_type": "CURRENT_PATCH",
        }

    def test_infer_soft_armor_plate_profile_from_name(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "level3_soft_armor_front",
        }
        item_info = self._gear_info("644120aa86ffbe10ee032b6f", "armorPlateTemplates.json")

        self.assertEqual("armor_plate_soft", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_helmet_plate_profile_from_name(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "ulach_level4_helmet_armor_top",
        }
        item_info = self._gear_info("644120aa86ffbe10ee032b6f", "armorPlateTemplates.json")

        self.assertEqual("armor_plate_helmet", self.generator._infer_gear_profile(patch, item_info))

    def test_full_backpack_rules_apply_expected_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "item_equipment_backpack_blackjack",
            "Comfort": 0.1,
            "speedPenaltyPercent": 8,
        }
        item_info = self._gear_info("5448e53e4bdc2d60728b4567", "bagTemplates.json")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["Comfort"]), 0.74)
        self.assertLessEqual(float(patch["Comfort"]), 0.96)
        self.assertGreaterEqual(float(patch["speedPenaltyPercent"]), -4.8)
        self.assertLessEqual(float(patch["speedPenaltyPercent"]), -2.0)
        self.assertEqual(1.0, float(patch["ReloadSpeedMulti"]))

    def test_gasmask_cosmetic_rules_apply_protection_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "synthetic_gas_mask",
            "IsGasMask": True,
            "GasProtection": 0.0,
            "RadProtection": 2.0,
        }
        item_info = self._gear_info("5b3f15d486f77432d0509248", "cosmeticsTemplates.json")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["GasProtection"]), 0.01346)
        self.assertLessEqual(float(patch["GasProtection"]), 0.86)
        self.assertGreaterEqual(float(patch["RadProtection"]), 0.0)
        self.assertLessEqual(float(patch["RadProtection"]), 0.82)

    def test_infer_unknown_plate_carrier_name_as_armor_chest_rig(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "PARACLETE APC先进防弹板携行背心",
            "ArmorClass": "MK4A Plates",
        }
        item_info = self._gear_info("", "")

        self.assertEqual("armor_chest_rig_heavy", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_light_chest_rig_from_name(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "item_equipment_rig_bankrobber",
        }
        item_info = self._gear_info("", "chestrigTemplates.json")

        self.assertEqual("chest_rig_light", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_heavy_chest_rig_from_name(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "item_equipment_rig_beltab",
        }
        item_info = self._gear_info("", "chestrigTemplates.json")

        self.assertEqual("chest_rig_heavy", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_light_armor_vest_from_armor_class(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "PACA soft armor vest",
            "ArmorClass": "NIJ II",
        }
        item_info = self._gear_info("", "armorVestsTemplates.json")

        self.assertEqual("armor_vest_light", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_heavy_armor_vest_from_armor_class(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "6B13 assault armor",
            "ArmorClass": "GOST 6A",
        }
        item_info = self._gear_info("", "armorVestsTemplates.json")

        self.assertEqual("armor_vest_heavy", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_light_armor_chest_rig_from_armor_class(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "6B3 armored rig",
            "ArmorClass": "GOST 2A",
        }
        item_info = self._gear_info("", "armorChestrigTemplates.json")

        self.assertEqual("armor_chest_rig_light", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_light_helmet_name_from_keyword(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "Ops-Core FAST MT MODXII（黑色）",
            "ArmorClass": "NIJ II",
        }
        item_info = self._gear_info("", "")

        self.assertEqual("helmet_light", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_heavy_helmet_name_from_keyword(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "Altyn assault helmet",
            "ArmorClass": "GOST 2",
        }
        item_info = self._gear_info("", "")

        self.assertEqual("helmet_heavy", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_back_panel_profile(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "背部面板 v1",
        }
        item_info = self._gear_info("", "")

        self.assertEqual("back_panel", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_bearing_system_as_full_backpack(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "Mystery Ranch NICE COMM 3 BVS 背负系统（黑色）",
        }
        item_info = self._gear_info("", "")

        self.assertEqual("backpack_full", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_sling_bag_as_compact_backpack(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "item_equipment_backpack_takedown_sling",
        }
        item_info = self._gear_info("", "bagTemplates.json")

        self.assertEqual("backpack_compact", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_beret_as_cosmetic_headwear(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "BOPE 贝雷帽",
        }
        item_info = self._gear_info("", "cosmeticsTemplates.json")

        self.assertEqual("cosmetic_headwear", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_ballistic_glasses_as_protective_eyewear(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "NPP KlASS Condor 渐变射击眼镜",
            "ArmorClass": "Anti-Shatter Resistance V50 ≥ 230 m/s",
        }
        item_info = self._gear_info("", "armorMasksTemplates.json")

        self.assertEqual("protective_eyewear_ballistic", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_standard_glasses_as_standard_eyewear(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "item_equipment_glasses_6B34",
            "ArmorClass": "Unclassified",
        }
        item_info = self._gear_info("", "armorMasksTemplates.json")

        self.assertEqual("protective_eyewear_standard", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_faceshield_as_component_faceshield(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "helmet_altyn_face_shield",
            "ArmorClass": "GOST 2",
        }
        item_info = self._gear_info("", "armorComponentsTemplates.json")

        self.assertEqual("armor_component_faceshield", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_mandible_as_component_accessory(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "item_equipment_helmet_galvion_mandible",
            "ArmorClass": "16gr V50 >= 905 m/s",
        }
        item_info = self._gear_info("", "armorComponentsTemplates.json")

        self.assertEqual("armor_component_accessory", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_ballistic_mask_as_ballistic_profile(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "item_equipment_atomic",
            "ArmorClass": "NIJ IIIA",
        }
        item_info = self._gear_info("", "armorMasksTemplates.json")

        self.assertEqual("armor_mask_ballistic", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_decorative_mask_as_decorative_profile(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "item_equipment_death_mask",
            "ArmorClass": "Unclassified",
        }
        item_info = self._gear_info("", "armorMasksTemplates.json")

        self.assertEqual("armor_mask_decorative", self.generator._infer_gear_profile(patch, item_info))

    def test_infer_belt_as_belt_harness(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "TGC MULE 战术腰带",
        }
        item_info = self._gear_info("", "")

        self.assertEqual("belt_harness", self.generator._infer_gear_profile(patch, item_info))

    def test_back_panel_rules_apply_expected_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "背部面板 v2",
            "ReloadSpeedMulti": 0.5,
            "Comfort": 1.5,
            "speedPenaltyPercent": -5,
        }
        item_info = self._gear_info("", "")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["ReloadSpeedMulti"]), 0.97)
        self.assertLessEqual(float(patch["ReloadSpeedMulti"]), 1.02)
        self.assertGreaterEqual(float(patch["Comfort"]), 0.9)
        self.assertLessEqual(float(patch["Comfort"]), 1.0)
        self.assertGreaterEqual(float(patch["speedPenaltyPercent"]), -0.65)
        self.assertLessEqual(float(patch["speedPenaltyPercent"]), -0.15)

    def test_belt_rules_apply_expected_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "TGC 警用腰带",
            "ReloadSpeedMulti": 0.5,
            "Comfort": 0.5,
            "speedPenaltyPercent": -4,
        }
        item_info = self._gear_info("", "")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["ReloadSpeedMulti"]), 1.0)
        self.assertLessEqual(float(patch["ReloadSpeedMulti"]), 1.1)
        self.assertGreaterEqual(float(patch["Comfort"]), 1.0)
        self.assertLessEqual(float(patch["Comfort"]), 1.12)
        self.assertGreaterEqual(float(patch["speedPenaltyPercent"]), -0.55)
        self.assertLessEqual(float(patch["speedPenaltyPercent"]), 0.0)

    def test_compact_backpack_rules_apply_expected_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "item_equipment_backpack_takedown_sling",
            "Comfort": 0.2,
            "speedPenaltyPercent": -5,
        }
        item_info = self._gear_info("", "bagTemplates.json")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["Comfort"]), 0.9)
        self.assertLessEqual(float(patch["Comfort"]), 1.18)
        self.assertGreaterEqual(float(patch["speedPenaltyPercent"]), -2.8)
        self.assertLessEqual(float(patch["speedPenaltyPercent"]), -0.6)
        self.assertEqual(1.0, float(patch["ReloadSpeedMulti"]))

    def test_light_chest_rig_rules_apply_expected_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "item_equipment_rig_bankrobber",
            "ReloadSpeedMulti": 0.5,
            "Comfort": 0.1,
            "speedPenaltyPercent": -2,
        }
        item_info = self._gear_info("", "chestrigTemplates.json")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["ReloadSpeedMulti"]), 0.98)
        self.assertLessEqual(float(patch["ReloadSpeedMulti"]), 1.17)
        self.assertGreaterEqual(float(patch["Comfort"]), 0.76)
        self.assertLessEqual(float(patch["Comfort"]), 1.18)
        self.assertGreaterEqual(float(patch["speedPenaltyPercent"]), -0.4)
        self.assertLessEqual(float(patch["speedPenaltyPercent"]), 0.0)

    def test_heavy_chest_rig_rules_apply_expected_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "item_equipment_rig_beltab",
            "ReloadSpeedMulti": 1.3,
            "Comfort": 1.2,
            "speedPenaltyPercent": 0.0,
        }
        item_info = self._gear_info("", "chestrigTemplates.json")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["ReloadSpeedMulti"]), 0.86)
        self.assertLessEqual(float(patch["ReloadSpeedMulti"]), 1.08)
        self.assertGreaterEqual(float(patch["Comfort"]), 0.7)
        self.assertLessEqual(float(patch["Comfort"]), 1.1)
        self.assertGreaterEqual(float(patch["speedPenaltyPercent"]), -1.0)
        self.assertLessEqual(float(patch["speedPenaltyPercent"]), -0.2)

    def test_helmet_plate_rules_apply_expected_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "ulach_level4_helmet_armor_top",
            "SpallReduction": 0.0,
        }
        item_info = self._gear_info("", "armorPlateTemplates.json")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["SpallReduction"]), 0.55)
        self.assertLessEqual(float(patch["SpallReduction"]), 1.0)
        self.assertEqual(1.0, float(patch["ReloadSpeedMulti"]))

    def test_light_armor_vest_rules_apply_expected_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "PACA soft armor vest",
            "ArmorClass": "NIJ II",
            "SpallReduction": 1.0,
            "Comfort": 0.1,
            "speedPenaltyPercent": -9,
        }
        item_info = self._gear_info("", "armorVestsTemplates.json")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["SpallReduction"]), 0.15)
        self.assertLessEqual(float(patch["SpallReduction"]), 0.55)
        self.assertGreaterEqual(float(patch["Comfort"]), 0.9)
        self.assertLessEqual(float(patch["Comfort"]), 1.08)
        self.assertGreaterEqual(float(patch["speedPenaltyPercent"]), -4.5)
        self.assertLessEqual(float(patch["speedPenaltyPercent"]), 0.0)

    def test_heavy_armor_vest_rules_apply_expected_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "6B13 assault armor",
            "ArmorClass": "GOST 6A",
            "SpallReduction": 0.0,
            "Comfort": 0.1,
            "speedPenaltyPercent": 0.0,
        }
        item_info = self._gear_info("", "armorVestsTemplates.json")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["SpallReduction"]), 0.55)
        self.assertLessEqual(float(patch["SpallReduction"]), 0.92)
        self.assertGreaterEqual(float(patch["Comfort"]), 1.0)
        self.assertLessEqual(float(patch["Comfort"]), 1.14)
        self.assertGreaterEqual(float(patch["speedPenaltyPercent"]), -8.0)
        self.assertLessEqual(float(patch["speedPenaltyPercent"]), -0.8)

    def test_heavy_armor_chest_rig_rules_apply_expected_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "Tactec plate carrier",
            "ArmorClass": "NIJ IV",
            "SpallReduction": 0.0,
            "ReloadSpeedMulti": 1.3,
            "Comfort": 1.2,
        }
        item_info = self._gear_info("", "armorChestrigTemplates.json")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["SpallReduction"]), 0.55)
        self.assertLessEqual(float(patch["SpallReduction"]), 0.9)
        self.assertGreaterEqual(float(patch["ReloadSpeedMulti"]), 0.89)
        self.assertLessEqual(float(patch["ReloadSpeedMulti"]), 1.08)
        self.assertGreaterEqual(float(patch["Comfort"]), 0.72)
        self.assertLessEqual(float(patch["Comfort"]), 1.1)

    def test_faceshield_rules_apply_expected_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "helmet_altyn_face_shield",
            "SpallReduction": 0.0,
            "ReloadSpeedMulti": 1.2,
        }
        item_info = self._gear_info("", "armorComponentsTemplates.json")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["SpallReduction"]), 0.75)
        self.assertLessEqual(float(patch["SpallReduction"]), 1.0)
        self.assertEqual(1.0, float(patch["ReloadSpeedMulti"]))

    def test_ballistic_mask_rules_apply_expected_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "item_equipment_atomic",
            "ArmorClass": "NIJ IIIA",
            "SpallReduction": 0.0,
        }
        item_info = self._gear_info("", "armorMasksTemplates.json")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["SpallReduction"]), 0.7)
        self.assertLessEqual(float(patch["SpallReduction"]), 1.0)
        self.assertEqual(1.0, float(patch["ReloadSpeedMulti"]))

    def test_standard_eyewear_rules_apply_expected_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "item_equipment_glasses_6B34",
            "ArmorClass": "Unclassified",
            "SpallReduction": 0.0,
        }
        item_info = self._gear_info("", "armorMasksTemplates.json")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["SpallReduction"]), 0.35)
        self.assertLessEqual(float(patch["SpallReduction"]), 0.62)
        self.assertEqual(1.0, float(patch["ReloadSpeedMulti"]))

    def test_ballistic_eyewear_rules_apply_expected_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "NPP KlASS Condor 渐变射击眼镜",
            "ArmorClass": "Anti-Shatter Resistance V50 ≥ 230 m/s",
            "SpallReduction": 0.0,
        }
        item_info = self._gear_info("", "armorMasksTemplates.json")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["SpallReduction"]), 0.62)
        self.assertLessEqual(float(patch["SpallReduction"]), 0.9)
        self.assertEqual(1.0, float(patch["ReloadSpeedMulti"]))

    def test_light_helmet_rules_apply_expected_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "Ops-Core FAST MT",
            "Comfort": 0.3,
        }
        item_info = self._gear_info("", "helmetTemplates.json")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["Comfort"]), 0.82)
        self.assertLessEqual(float(patch["Comfort"]), 1.06)
        self.assertEqual(1.0, float(patch["ReloadSpeedMulti"]))

    def test_heavy_helmet_rules_apply_expected_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Gear, RealismMod",
            "Name": "Altyn assault helmet",
            "Comfort": 0.3,
        }
        item_info = self._gear_info("", "helmetTemplates.json")

        self.generator.apply_realism_sanity_check(patch, item_info)

        self.assertGreaterEqual(float(patch["Comfort"]), 0.95)
        self.assertLessEqual(float(patch["Comfort"]), 1.16)
        self.assertEqual(1.0, float(patch["ReloadSpeedMulti"]))


if __name__ == "__main__":
    unittest.main()