# -*- coding: utf-8 -*-
"""武器二级细分规则（口径 + 枪托形态）。

这些规则用于在 WEAPON_PROFILE_RANGES 基础上做二次修正。
数值含义：每个字段是对基础范围的增量 (delta_min, delta_max)。
"""

# 口径细分修正（对基础武器范围做增量）
WEAPON_CALIBER_RULE_MODIFIERS = {
    # 9x19 / .45 ACP / 10mm
    "pistol_caliber": {
        "VerticalRecoil": (10, 30),
        "HorizontalRecoil": (8, 55),
        "Convergence": (1, 3),
        "Velocity": (-3, 2),
        "RecoilIntensity": (0.01, 0.06),
    },
    # 5.45x39 / 5.56x45
    "small_high_velocity": {
        "VerticalRecoil": (-5, 5),
        "HorizontalRecoil": (-5, 5),
        "Convergence": (0, 3),
        "Velocity": (0, 3),
        "RecoilIntensity": (-0.03, 0.02),
    },
    # 7.62x39（中间威力）
    "intermediate_rifle_762x39": {
        "VerticalRecoil": (8, 45),
        "HorizontalRecoil": (4, 32),
        "Convergence": (-1, 2),
        "Velocity": (2, 6),
        "RecoilIntensity": (0.01, 0.06),
    },
    # 7.62x51 / 6.8（全威力）
    "full_power_rifle": {
        "VerticalRecoil": (20, 90),
        "HorizontalRecoil": (14, 65),
        "Convergence": (-3, 1),
        "Velocity": (5, 15),
        "RecoilIntensity": (0.02, 0.1),
    },
    # 7.62x54R（全威力偏重后坐）
    "full_power_rifle_rimmed": {
        "VerticalRecoil": (30, 105),
        "HorizontalRecoil": (18, 75),
        "Convergence": (-4, 0),
        "Velocity": (7, 15),
        "RecoilIntensity": (0.03, 0.11),
    },
    # .300 WM / .338 LM / 12.7
    "magnum_heavy": {
        "VerticalRecoil": (80, 180),
        "HorizontalRecoil": (50, 130),
        "Convergence": (-5, -1),
        "Velocity": (10, 25),
        "RecoilIntensity": (0.08, 0.2),
    },
    # 12/20 Gauge
    "shotgun_shell": {
        "VerticalRecoil": (30, 120),
        "HorizontalRecoil": (20, 85),
        "ShotgunDispersion": (0, 1),
        "Convergence": (-2, 2),
        "RecoilIntensity": (0.06, 0.16),
    },
    # 4.6x30 / 5.7x28
    "pdw_high_pen_small": {
        "VerticalRecoil": (-15, 10),
        "HorizontalRecoil": (-20, 10),
        "Convergence": (2, 6),
        "Velocity": (5, 12),
        "RecoilIntensity": (-0.05, 0.02),
    },
}

# 枪托形态细分修正（对基础武器范围做增量）
WEAPON_STOCK_RULE_MODIFIERS = {
    "fixed_stock": {
        "VerticalRecoil": (-15, -5),
        "HorizontalRecoil": (-10, -3),
        "Convergence": (2, 6),
        "Ergonomics": (-4, 2),
        "BaseReloadSpeedMulti": (0.98, 1.05),
    },
    "folding_stock_extended": {
        "VerticalRecoil": (-8, 2),
        "HorizontalRecoil": (-5, 3),
        "Convergence": (0, 3),
        "Ergonomics": (0, 5),
        "BaseReloadSpeedMulti": (0.98, 1.03),
    },
    "folding_stock_collapsed": {
        "VerticalRecoil": (10, 55),
        "HorizontalRecoil": (8, 45),
        "Convergence": (-6, -2),
        "Ergonomics": (3, 12),
        "VisualMulti": (0.08, 0.25),
    },
    "bullpup": {
        "VerticalRecoil": (-5, 10),
        "HorizontalRecoil": (-3, 8),
        "Convergence": (0, 4),
        "Ergonomics": (-6, 2),
        "BaseReloadSpeedMulti": (0.84, 0.95),
        "BaseChamberCheckSpeed": (0.9, 1.05),
    },
    "stockless": {
        "VerticalRecoil": (35, 120),
        "HorizontalRecoil": (25, 90),
        "Convergence": (-8, -3),
        "VisualMulti": (0.2, 0.75),
        "RecoilIntensity": (0.03, 0.14),
    },
}

# 口径关键词到档位映射（按顺序匹配，命中即返回）
CALIBER_PROFILE_KEYWORDS = [
    ("magnum_heavy", [
        ".338", "338lm", "338 lapua", ".300 wm", "300wm", "300 win mag", "12.7x", "50 bmg",
    ]),
    ("shotgun_shell", [
        "12g", "12 ga", "12 gauge", "20g", "20 gauge",
    ]),
    ("pdw_high_pen_small", [
        "4.6x30", "5.7x28",
    ]),
    ("full_power_rifle_rimmed", [
        "7.62x54", "54r", "7.62x54r",
    ]),
    ("full_power_rifle", [
        "7.62x51", "308", ".308", "6.8",
    ]),
    ("intermediate_rifle_762x39", [
        "7.62x39",
    ]),
    ("small_high_velocity", [
        "5.45x39", "5.56x45", "5.56", "223", ".223",
    ]),
    ("pistol_caliber", [
        "9x19", "9mm", ".45", "45acp", "10mm",
    ]),
]
