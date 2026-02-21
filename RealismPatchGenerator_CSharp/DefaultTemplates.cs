using System.Collections.Generic;

namespace RealismPatchGenerator_CSharp
{
    public static class DefaultTemplates
    {
        public static Dictionary<string, object> Weapon = new Dictionary<string, object>
        {
            { "$type", "RealismMod.Gun, RealismMod" },
            { "WeapType", "rifle" },
            { "OperationType", "" },
            { "WeapAccuracy", 0 },
            { "BaseTorque", 4.5 },
            { "HasShoulderContact", true },
            { "Ergonomics", 85 },
            { "VerticalRecoil", 65 },
            { "HorizontalRecoil", 160 },
            { "Dispersion", 6 },
            { "CameraRecoil", 0.037 },
            { "VisualMulti", 1.1 },
            { "Convergence", 13.5 },
            { "RecoilAngle", 80 },
            { "BaseMalfunctionChance", 0.0012 },
            { "HeatFactorGun", 0.22 },
            { "HeatFactorByShot", 1 },
            { "CoolFactorGun", 0.1 },
            { "CoolFactorGunMods", 1 },
            { "AllowOverheat", true },
            { "CenterOfImpact", 0 },
            { "HipAccuracyRestorationDelay", 0.2 },
            { "HipAccuracyRestorationSpeed", 7 },
            { "HipInnaccuracyGain", 0.16 },
            { "ShotgunDispersion", 0 },
            { "Velocity", 0 },
            { "RecoilDamping", 0.82 },
            { "RecoilHandDamping", 0.6 },
            { "WeaponAllowADS", false },
            { "Weight", 1.5 },
            { "DurabilityBurnRatio", 0.28 },
            { "AutoROF", 600 },
            { "SemiROF", 340 },
            { "LoyaltyLevel", 2 },
            { "BaseReloadSpeedMulti", 1.0 },
            { "BaseChamberSpeedMulti", 1 },
            { "MinChamberSpeed", 0.7 },
            { "MaxChamberSpeed", 1.5 },
            { "IsManuallyOperated", false },
            { "BaseChamberCheckSpeed", 1 },
            { "BaseFixSpeed", 1 },
            { "OffsetRotation", 0.011 },
            { "RecoilIntensity", 0.19 },
            { "RecoilCenter", new Dictionary<string, double> { { "x", 0 }, { "y", -0.35 }, { "z", 0 } } }
        };

        public static Dictionary<string, object> Ammo = new Dictionary<string, object>
        {
            { "$type", "RealismMod.Ammo, RealismMod" },
            { "Name", "" },
            { "Damage", 50 },
            { "PenetrationPower", 20 },
            { "LoyaltyLevel", 1 },
            { "BasePriceModifier", 1 }
        };

        public static Dictionary<string, object> Consumable = new Dictionary<string, object>
        {
            { "$type", "RealismMod.Consumable, RealismMod" },
            { "Name", "" },
            { "TemplateType", "consumable" },
            { "LoyaltyLevel", 1 },
            { "BasePriceModifier", 1 },
            { "ConsumableType", "other" },
            { "Duration", 0 },
            { "Delay", 0 },
            { "EffectPeriod", 0 },
            { "WaitPeriod", 0 },
            { "Strength", 0 },
            { "TunnelVisionStrength", 0 },
            { "CanBeUsedInRaid", true }
        };

        public static Dictionary<string, object> Mod = new Dictionary<string, object>
        {
            { "$type", "RealismMod.WeaponMod, RealismMod" },
            { "ModType", "" },
            { "Ergonomics", 0 },
            { "Weight", 0.1 },
            { "ConflictingItems", new List<string>() },
            { "LoyaltyLevel", 1 },
            { "VerticalRecoil", 0 },
            { "HorizontalRecoil", 0 },
            { "AimSpeed", 0 },
            { "Accuracy", 0 }
        };

        public static Dictionary<string, Dictionary<string, object>> ModTypeSpecificAttrs = new Dictionary<string, Dictionary<string, object>>
        {
            { "Stock", new Dictionary<string, object> {
                { "Dispersion", 0 }, { "CameraRecoil", 0 }, { "HasShoulderContact", false },
                { "BlocksFolding", false }, { "StockAllowADS", false }, { "Handling", 0 },
                { "AutoROF", 0 }, { "SemiROF", 0 }, { "ModMalfunctionChance", 0 }
            }},
            { "grip", new Dictionary<string, object> {
                { "Dispersion", 0 }, { "Handling", 0 }, { "AimStability", 0 }
            }},
            { "handguard", new Dictionary<string, object> {
                { "Dispersion", 0 }, { "HeatFactor", 1 }, { "CoolFactor", 1 }, { "Handling", 0 }
            }},
            { "barrel", new Dictionary<string, object> {
                { "Dispersion", 0 }, { "Convergence", 0 }, { "CenterOfImpact", 0 },
                { "HeatFactor", 1 }, { "CoolFactor", 1 }, { "DurabilityBurnModificator", 1 },
                { "Velocity", 0 }, { "ShotgunDispersion", 1 }, { "Loudness", 0 },
                { "Flash", 0 }, { "AutoROF", 0 }, { "SemiROF", 0 }, { "ModMalfunctionChance", 0 }
            }},
            { "muzzle", new Dictionary<string, object> {
                { "Dispersion", 0 }, { "CameraRecoil", 0 }, { "Convergence", 0 },
                { "HeatFactor", 1 }, { "CoolFactor", 1 }, { "DurabilityBurnModificator", 1 },
                { "Velocity", 0 }, { "Loudness", 0 }, { "CanCycleSubs", false },
                { "RecoilAngle", 0 }, { "AutoROF", 0 }, { "SemiROF", 0 }, { "ModMalfunctionChance", 0 }
            }},
            { "magazine", new Dictionary<string, object> {
                { "ReloadSpeed", 0 }, { "MalfunctionChance", 0 }, { "LoadUnloadModifier", 0 }, { "CheckTimeModifier", 0 }
            }},
            { "sight", new Dictionary<string, object>() },
            { "bayonet", new Dictionary<string, object> {
                { "Dispersion", 0 }, { "CameraRecoil", 0 }, { "MeleeDamage", 0 }, { "MeleePen", 0 },
                { "HeatFactor", 1 }, { "CoolFactor", 1 }, { "DurabilityBurnModificator", 1 },
                { "Velocity", 0 }, { "Loudness", 0 }, { "Convergence", 0 }, { "RecoilAngle", 0 },
                { "AutoROF", 0 }, { "SemiROF", 0 }, { "ModMalfunctionChance", 0 }, { "CanCycleSubs", false }
            }}
        };
    }
}
