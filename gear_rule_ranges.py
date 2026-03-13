"""Gear rule ranges used by the realism patch generator.

The gear pipeline intentionally stays shallower than gun/ammo rules:
we use template-file-aligned primary profiles, plus a small amount of
secondary refinement for soft armor plates and gas-protection cosmetics.
"""

GEAR_PROFILE_RANGES = {
    "armor_vest_light": {
        "SpallReduction": (0.15, 0.55),
        "ReloadSpeedMulti": (1.0, 1.06),
        "Comfort": (0.9, 1.08),
        "speedPenaltyPercent": (-4.5, 0.0),
        "weaponErgonomicPenalty": (-5.5, 0.0),
    },
    "armor_vest_heavy": {
        "SpallReduction": (0.55, 0.92),
        "ReloadSpeedMulti": (0.97, 1.03),
        "Comfort": (1.0, 1.14),
        "speedPenaltyPercent": (-8.0, -0.8),
        "weaponErgonomicPenalty": (-10.0, -1.0),
    },
    "armor_chest_rig_light": {
        "SpallReduction": (0.22, 0.55),
        "ReloadSpeedMulti": (0.95, 1.16),
        "Comfort": (0.76, 1.12),
        "speedPenaltyPercent": (-4.5, 0.0),
        "weaponErgonomicPenalty": (-4.0, 0.0),
    },
    "armor_chest_rig_heavy": {
        "SpallReduction": (0.55, 0.9),
        "ReloadSpeedMulti": (0.89, 1.08),
        "Comfort": (0.72, 1.1),
        "speedPenaltyPercent": (-6.5, -0.2),
        "weaponErgonomicPenalty": (-6.5, -0.5),
    },
    "chest_rig_light": {
        "SpallReduction": (1.0, 1.0),
        "ReloadSpeedMulti": (0.98, 1.17),
        "Comfort": (0.76, 1.18),
        "speedPenaltyPercent": (-0.4, 0.0),
    },
    "chest_rig_heavy": {
        "SpallReduction": (1.0, 1.0),
        "ReloadSpeedMulti": (0.86, 1.08),
        "Comfort": (0.7, 1.1),
        "speedPenaltyPercent": (-1.0, -0.2),
    },
    "helmet_light": {
        "SpallReduction": (1.0, 1.0),
        "ReloadSpeedMulti": (1.0, 1.0),
        "Comfort": (0.82, 1.06),
    },
    "helmet_heavy": {
        "SpallReduction": (1.0, 1.0),
        "ReloadSpeedMulti": (1.0, 1.0),
        "Comfort": (0.95, 1.16),
    },
    "armor_component_accessory": {
        "SpallReduction": (0.45, 0.85),
        "ReloadSpeedMulti": (1.0, 1.0),
    },
    "armor_component_faceshield": {
        "SpallReduction": (0.75, 1.0),
        "ReloadSpeedMulti": (1.0, 1.0),
    },
    "armor_mask_decorative": {
        "SpallReduction": (1.0, 1.0),
        "ReloadSpeedMulti": (1.0, 1.0),
    },
    "armor_mask_ballistic": {
        "SpallReduction": (0.7, 1.0),
        "ReloadSpeedMulti": (1.0, 1.0),
    },
    "armor_plate_hard": {
        "SpallReduction": (0.18, 0.85),
        "ReloadSpeedMulti": (1.0, 1.0),
    },
    "armor_plate_helmet": {
        "SpallReduction": (0.55, 1.0),
        "ReloadSpeedMulti": (1.0, 1.0),
    },
    "armor_plate_soft": {
        "SpallReduction": (0.1, 0.45),
        "ReloadSpeedMulti": (1.0, 1.0),
    },
    "backpack_compact": {
        "ReloadSpeedMulti": (1.0, 1.0),
        "Comfort": (0.9, 1.18),
        "speedPenaltyPercent": (-2.8, -0.6),
    },
    "backpack_full": {
        "ReloadSpeedMulti": (1.0, 1.0),
        "Comfort": (0.74, 0.96),
        "speedPenaltyPercent": (-4.8, -2.0),
    },
    "back_panel": {
        "ReloadSpeedMulti": (0.97, 1.02),
        "Comfort": (0.9, 1.0),
        "speedPenaltyPercent": (-0.65, -0.15),
        "weaponErgonomicPenalty": (0.0, 0.0),
    },
    "belt_harness": {
        "ReloadSpeedMulti": (1.0, 1.1),
        "Comfort": (1.0, 1.12),
        "speedPenaltyPercent": (-0.55, 0.0),
        "weaponErgonomicPenalty": (0.0, 0.0),
    },
    "headset": {
        "dB": (19, 26),
    },
    "cosmetic_headwear": {
        "ReloadSpeedMulti": (1.0, 1.0),
        "speedPenaltyPercent": (0.0, 0.0),
        "weaponErgonomicPenalty": (0.0, 0.0),
    },
    "protective_eyewear_standard": {
        "SpallReduction": (0.35, 0.62),
        "ReloadSpeedMulti": (1.0, 1.0),
    },
    "protective_eyewear_ballistic": {
        "SpallReduction": (0.62, 0.9),
        "ReloadSpeedMulti": (1.0, 1.0),
    },
    "cosmetic_gasmask": {
        "GasProtection": (0.82, 0.90),
        "RadProtection": (0.75, 0.82),
        "ReloadSpeedMulti": (1.0, 1.0),
        "speedPenaltyPercent": (-10.0, 0.0),
        "weaponErgonomicPenalty": (-24.0, 0.0),
    },
}