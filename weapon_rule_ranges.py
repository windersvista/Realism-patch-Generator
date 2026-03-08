# -*- coding: utf-8 -*-
"""武器规则范围配置。

将武器规则范围独立到此文件，便于用户直接调整数值区间。
"""

# 武器规则范围（来自“武器属性规则指南”）
WEAPON_PROFILE_RANGES = {
    "assault": {
        "VerticalRecoil": (75, 105),
        "HorizontalRecoil": (140, 185),
        "Convergence": (2, 25),
        "Dispersion": (4, 8),
        "VisualMulti": (1.05, 1.25),
        "Ergonomics": (90, 99),
        "RecoilIntensity": (0.12, 0.22),
    },
    "pistol": {
        "VerticalRecoil": (320, 520),
        "HorizontalRecoil": (280, 480),
        "Convergence": (12, 18),
        "Dispersion": (10, 18),
        "VisualMulti": (2.0, 2.6),
        "Ergonomics": (92, 100),
        "BaseTorque": (-2.0, -1.0),
    },
    "smg": {
        "VerticalRecoil": (55, 78),
        "HorizontalRecoil": (70, 120),
        "Convergence": (16, 22),
        "Dispersion": (6, 12),
        "VisualMulti": (0.85, 1.15),
        "Ergonomics": (88, 98),
        "RecoilIntensity": (0.08, 0.16),
    },
    "sniper": {
        "VerticalRecoil": (110, 220),
        "HorizontalRecoil": (150, 300),
        "Convergence": (8, 13),
        "Dispersion": (0.5, 3.0),
        "VisualMulti": (1.1, 1.8),
        "Ergonomics": (62, 79),
    },
    "shotgun": {
        "VerticalRecoil": (240, 420),
        "HorizontalRecoil": (240, 460),
        "Dispersion": (15, 30),
        "VisualMulti": (1.8, 2.3),
        "Ergonomics": (68, 88),
        "RecoilIntensity": (0.32, 0.52),
        "ShotgunDispersion": (1, 1),
    },
    "machinegun": {
        "VerticalRecoil": (130, 240),
        "HorizontalRecoil": (200, 360),
        "Convergence": (4, 14),
        "Dispersion": (6, 14),
        "VisualMulti": (1.1, 1.6),
        "Ergonomics": (70, 90),
        "RecoilIntensity": (0.2, 0.35),
    },
    "launcher": {
        "VerticalRecoil": (180, 360),
        "HorizontalRecoil": (240, 500),
        "Convergence": (2, 10),
        "Dispersion": (8, 18),
        "VisualMulti": (1.6, 2.6),
        "Ergonomics": (45, 68),
        "RecoilIntensity": (0.28, 0.5),
    },
}
