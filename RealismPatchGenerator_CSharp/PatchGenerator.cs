// RealismPatchGenerator_CSharp/PatchGenerator.cs
// 补丁生成主逻辑（雏形）
using System.Text.Json;
using System.Text.RegularExpressions;

namespace RealismPatchGenerator_CSharp
{
    public class PatchGenerator
    {
        private TemplateLoader _templateLoader;
        // 补丁存储结构
        private Dictionary<string, Dictionary<string, object>> fileBasedPatches = new();
        private Dictionary<string, object> weaponPatches = new();
        private Dictionary<string, object> attachmentPatches = new();
        private Dictionary<string, object> ammoPatches = new();
        private Dictionary<string, object> gearPatches = new();
        private Dictionary<string, object> consumablesPatches = new();

        public string? NormalizeParentId(string? parentId)
        {
            if (string.IsNullOrEmpty(parentId)) return parentId;
            if (parentId.All(char.IsUpper) || parentId.Contains("_"))
            {
                if (ItemTypeMappings.ItemTypeNameToId.TryGetValue(parentId, out var normalizedId))
                {
                    return normalizedId;
                }
            }
            return parentId;
        }

        public string DetectItemFormat(Dictionary<string, object> itemData)
        {
            if (itemData.ContainsKey("TemplateID") && itemData.ContainsKey("$type"))
                return "TEMPLATE_ID";
            if (itemData.TryGetValue("item", out var itemObj) && itemObj is JsonElement itemEl && itemEl.ValueKind == JsonValueKind.Object)
            {
                if (itemEl.TryGetProperty("_id", out _) && itemEl.TryGetProperty("_parent", out _))
                    return "VIR";
            }
            if (itemData.ContainsKey("ItemToClone")) return "ITEMTOCLONE";
            if (itemData.ContainsKey("clone")) return "CLONE";
            if (itemData.ContainsKey("parentId") || itemData.ContainsKey("itemTplToClone"))
                return "STANDARD";
            return "UNKNOWN";
        }

        public Dictionary<string, object> ExtractItemInfo(string itemId, Dictionary<string, object> itemData, string formatType)
        {
            var info = new Dictionary<string, object>
            {
                { "item_id", itemId },
                { "parent_id", null },
                { "clone_id", null },
                { "template_id", null },
                { "name", null },
                { "is_weapon", false },
                { "is_gear", false },
                { "is_consumable", false },
                { "item_type", null },
                { "properties", new Dictionary<string, object>() }
            };

            if (formatType == "TEMPLATE_ID")
            {
                info["template_id"] = GetString(itemData, "TemplateID");
                info["name"] = GetString(itemData, "Name");
                info["item_type"] = GetString(itemData, "$type");
                string typeStr = info["item_type"]?.ToString() ?? "";
                if (typeStr.Contains("RealismMod.Gun")) info["is_weapon"] = true;
                else if (typeStr.Contains("RealismMod.Gear")) info["is_gear"] = true;
                else if (typeStr.Contains("RealismMod.Consumable")) info["is_consumable"] = true;
            }
            else if (formatType == "VIR")
            {
                if (itemData.TryGetValue("item", out var itemObj) && itemObj is JsonElement itemEl)
                {
                    info["parent_id"] = NormalizeParentId(GetJsonString(itemEl, "_parent"));
                    info["name"] = GetJsonString(itemEl, "_name");
                    info["properties"] = ToDict(itemEl.GetProperty("_props"));
                    if (itemData.TryGetValue("isweapon", out var isw) && isw is JsonElement iswEl)
                        info["is_weapon"] = iswEl.GetBoolean();
                    else
                        info["is_weapon"] = IsWeapon(info["parent_id"]?.ToString());
                }
            }
            else if (formatType == "STANDARD")
            {
                info["parent_id"] = NormalizeParentId(GetString(itemData, "parentId"));
                info["clone_id"] = GetString(itemData, "itemTplToClone");
                if (itemData.TryGetValue("overrideProperties", out var props) && props is JsonElement propsEl)
                    info["properties"] = ToDict(propsEl);
                if (itemData.TryGetValue("locales", out var locales) && locales is JsonElement localesEl)
                {
                    string[] langs = { "en", "ch", "zh", "ru" };
                    foreach (var lang in langs)
                    {
                        if (localesEl.TryGetProperty(lang, out var langEl) && langEl.TryGetProperty("name", out var nameEl))
                        {
                            info["name"] = nameEl.GetString();
                            break;
                        }
                    }
                }
                string pId = info["parent_id"]?.ToString();
                if (!string.IsNullOrEmpty(pId))
                {
                    info["is_weapon"] = IsWeapon(pId);
                    info["is_gear"] = IsGearSimple(pId);
                    info["is_consumable"] = IsConsumable(pId);
                }
                else if (info["clone_id"] != null)
                {
                    info["is_weapon"] = IsWeaponByCloneId(info["clone_id"].ToString());
                }
            }
            else if (formatType == "ITEMTOCLONE")
            {
                info["clone_id"] = GetString(itemData, "ItemToClone");
                if (itemData.TryGetValue("LocalePush", out var locale) && locale is JsonElement localeEl && localeEl.TryGetProperty("name", out var nameVal))
                    info["name"] = nameVal.GetString();
                if (itemData.TryGetValue("OverrideProperties", out var oprops) && oprops is JsonElement opropsEl)
                    info["properties"] = ToDict(opropsEl);
            }
            else if (formatType == "CLONE")
            {
                info["clone_id"] = GetString(itemData, "clone");
                if (itemData.TryGetValue("locales", out var locales) && locales is JsonElement localesEl)
                {
                    string[] langs = { "en", "ch", "zh", "ru" };
                    foreach (var lang in langs)
                    {
                        if (localesEl.TryGetProperty(lang, out var langEl) && langEl.TryGetProperty("Name", out var nameEl))
                        {
                            info["name"] = nameEl.GetString();
                            break;
                        }
                    }
                    if (string.IsNullOrEmpty(info["name"]?.ToString()) && localesEl.TryGetProperty("Name", out var topNameEl))
                        info["name"] = topNameEl.GetString();
                }
                if (itemData.TryGetValue("handbook", out var handbook) && handbook is JsonElement hbEl)
                {
                    string p = GetJsonString(hbEl, "ParentId") ?? GetJsonString(hbEl, "parentId");
                    if (p != null) info["parent_id"] = NormalizeParentId(p);
                }
                string key = itemData.ContainsKey("items") ? "items" : (itemData.ContainsKey("item") ? "item" : null);
                if (key != null && itemData[key] is JsonElement itemEl && itemEl.TryGetProperty("_props", out var propsEl))
                {
                    info["properties"] = ToDict(propsEl);
                    if (string.IsNullOrEmpty(info["parent_id"]?.ToString()) && itemEl.TryGetProperty("_parent", out var parentEl))
                        info["parent_id"] = NormalizeParentId(parentEl.GetString());
                }
            }

            return info;
        }

        private string? GetString(Dictionary<string, object> dict, string key)
        {
            if (dict.TryGetValue(key, out var val))
            {
                if (val is JsonElement el) return el.GetString();
                return val.ToString();
            }
            return null;
        }

        private string? GetJsonString(JsonElement el, string prop)
        {
            if (el.TryGetProperty(prop, out var val)) return val.GetString();
            return null;
        }

        private Dictionary<string, object> ToDict(JsonElement el)
        {
            return JsonSerializer.Deserialize<Dictionary<string, object>>(el.GetRawText()) ?? new Dictionary<string, object>();
        }

        public bool IsWeapon(string? pId)
        {
            if (string.IsNullOrEmpty(pId)) return false;
            string templateFile = GetTemplateForParentId(pId);
            if (templateFile != null && _templateLoader.Templates.TryGetValue(templateFile, out var tDict))
            {
                foreach (var item in tDict.Values)
                {
                    if (item is JsonElement el && el.TryGetProperty("$type", out var typeEl))
                    {
                        return typeEl.GetString()?.Contains("RealismMod.Gun") ?? false;
                    }
                }
            }
            return false;
        }

        public string GetTemplateForParentId(string pId)
        {
            string p = NormalizeParentId(pId);
            if (ItemTypeMappings.ParentIdToTemplate.TryGetValue(p, out var path))
                return Path.GetFileName(path);
            return null;
        }

        private Dictionary<string, object>? SelectTemplateData(string templateFile, string itemId, string? cloneId)
        {
            if (_templateLoader.Templates.TryGetValue(templateFile, out var tDict))
            {
                if (tDict.TryGetValue(itemId, out var data) && data is JsonElement el) 
                    return ToDict(el);
                if (!string.IsNullOrEmpty(cloneId) && tDict.TryGetValue(cloneId, out var cel) && cel is JsonElement cel2) 
                    return ToDict(cel2);
            }
            return null;
        }

        public bool IsGearSimple(string pId)
        {
            string[] gearIds = {
                "5448e54d4bdc2dcc718b4568", "644120aa86ffbe10ee032b6f", "5b5f704686f77447ec5d76d7",
                "5448e53e4bdc2d60728b4567", "5448e5284bdc2dcb718b4567", "57bef4c42459772e8d35a53b",
                "5a341c4086f77401f2541505", "5a341c4686f77469e155819e", "5645bcb74bdc2ded0b8b4578",
                "5b3f15d486f77432d0509248"
            };
            return gearIds.Contains(pId);
        }

        public bool IsAmmo(string pId) => pId == "5485a8684bdc2da71d8b4567";

        public bool IsConsumable(string pId)
        {
            string[] consIds = {
                "5448e8d04bdc2ddf718b4569", "5448e8d64bdc2dce718b4568", "5448f3ac4bdc2dce718b4569",
                "5448f39d4bdc20a728b4568", "5448f3a14bdc2d27728b4569", "5448f3a64bdc2d60728b456a"
            };
            return consIds.Contains(pId);
        }

        public bool IsWeaponByCloneId(string cloneId)
        {
            var template = FindTemplateById(cloneId);
            if (template != null && template.TryGetValue("$type", out var type))
                return type.ToString().Contains("RealismMod.Gun");
            return false;
        }

        public Dictionary<string, object> FindTemplateById(string cloneId)
        {
            if (string.IsNullOrEmpty(cloneId)) return null;
            foreach (var tDict in _templateLoader.Templates.Values)
            {
                if (tDict.TryGetValue(cloneId, out var val) && val is JsonElement el)
                    return ToDict(el);
            }
            return null;
        }

        public Dictionary<string, object> FindTemplateByTemplateId(string tid)
        {
            return FindTemplateById(tid);
        }

        public void MergeInputProperties(Dictionary<string, object> patch, Dictionary<string, object> itemInfo)
        {
            if (itemInfo.TryGetValue("name", out var name) && name != null)
            {
                string inputName = name.ToString();
                if (!(patch.TryGetValue("Name", out var pName) && pName != null && inputName.StartsWith("ammo_") && !pName.ToString().StartsWith("ammo_")))
                {
                    patch["Name"] = inputName;
                }
            }

            if (itemInfo.TryGetValue("properties", out var props) && props is Dictionary<string, object> inputProps)
            {
                string[] sensitiveFields = { "Ergonomics", "VerticalRecoil", "HorizontalRecoil", "Dispersion", "Convergence", "RecoilDamping", "RecoilHandDamping", "HipAccuracyRestorationDelay", "HipAccuracyRestorationSpeed", "HipInnaccuracyGain", "CameraRecoil", "VisualMulti", "RecoilAngle", "RecoilIntensity" };
                string[] realismFields = { "Ergonomics", "Weight", "VerticalRecoil", "HorizontalRecoil", "Velocity", "Loudness", "Accuracy", "Name", "ModType", "ConflictingItems", "LoyaltyLevel", "DurabilityBurnModificator", "AutoROF", "SemiROF", "ModMalfunctionChance", "PenetrationPower", "Damage", "InitialSpeed", "BulletMassGram", "BallisticCoeficient" };

                foreach (var kv in inputProps)
                {
                    string key = kv.Key;
                    object value = kv.Value;

                    if (realismFields.Contains(key) || patch.ContainsKey(key))
                    {
                        if (value != null)
                        {
                            if (sensitiveFields.Contains(key) && patch.TryGetValue(key, out var pVal) && pVal != null && Convert.ToDouble(pVal) != 0)
                                continue;
                            if (key == "Name" && string.IsNullOrEmpty(value.ToString()) && !string.IsNullOrEmpty(name?.ToString()))
                                continue;
                            patch[key] = value;
                        }
                    }
                    else if (key == "Recoil" && patch.ContainsKey("VerticalRecoil"))
                    {
                        if (Convert.ToDouble(patch["VerticalRecoil"]) == 0) patch["VerticalRecoil"] = value;
                    }
                    else if (key == "Weight" && patch.ContainsKey("Weight"))
                    {
                        patch["Weight"] = value;
                    }
                }
            }
        }

        public void ApplyRealismSanityCheck(Dictionary<string, object> patch)
        {
            string itemId = patch.TryGetValue("ItemID", out var id) ? id.ToString() : "Unknown";
            string itemName = patch.TryGetValue("Name", out var n) ? n.ToString().ToLower() : "";
            string itemType = patch.TryGetValue("$type", out var t) ? t.ToString() : "";

            if (itemType.Contains("RealismMod.Gun"))
            {
                if (patch.ContainsKey("Ergonomics")) patch["Ergonomics"] = Math.Max(10.0, Math.Min(100.0, ToDouble(patch["Ergonomics"])));
                if (patch.ContainsKey("VerticalRecoil")) patch["VerticalRecoil"] = Math.Max(10.0, Math.Min(1800.0, ToDouble(patch["VerticalRecoil"])));
                if (patch.ContainsKey("Convergence")) patch["Convergence"] = Math.Max(1.0, Math.Min(40.0, ToDouble(patch["Convergence"])));
                if (patch.ContainsKey("RecoilAngle"))
                {
                    double ra = ToDouble(patch["RecoilAngle"]);
                    if (ra < 30 || ra > 150) patch["RecoilAngle"] = 90.0;
                }
            }
            else if (itemType.Contains("RealismMod.WeaponMod"))
            {
                if (patch.ContainsKey("VerticalRecoil")) patch["VerticalRecoil"] = Math.Max(-35.0, Math.Min(35.0, ToDouble(patch["VerticalRecoil"])));
                if (patch.ContainsKey("HorizontalRecoil")) patch["HorizontalRecoil"] = Math.Max(-35.0, Math.Min(35.0, ToDouble(patch["HorizontalRecoil"])));
                if (patch.ContainsKey("Dispersion")) patch["Dispersion"] = Math.Max(-55.0, Math.Min(55.0, ToDouble(patch["Dispersion"])));
                if (patch.ContainsKey("Velocity"))
                {
                    double maxV = itemName.Contains("barrel") ? 15.0 : 5.0;
                    patch["Velocity"] = Math.Max(-maxV, Math.Min(maxV, ToDouble(patch["Velocity"])));
                }
                if (patch.ContainsKey("Loudness")) patch["Loudness"] = Math.Max(-45.0, Math.Min(50.0, ToDouble(patch["Loudness"])));
                if (patch.ContainsKey("Accuracy")) patch["Accuracy"] = Math.Max(-15.0, Math.Min(15.0, ToDouble(patch["Accuracy"])));
            }
            else if (itemType.Contains("RealismMod.Gear"))
            {
                if (patch.ContainsKey("ReloadSpeedMulti")) patch["ReloadSpeedMulti"] = Math.Max(0.85, Math.Min(1.25, ToDouble(patch["ReloadSpeedMulti"])));
                if (patch.ContainsKey("Comfort")) patch["Comfort"] = Math.Max(0.6, Math.Min(1.4, ToDouble(patch["Comfort"])));
                if (patch.ContainsKey("speedPenaltyPercent")) patch["speedPenaltyPercent"] = Math.Max(-40.0, Math.Min(10.0, ToDouble(patch["speedPenaltyPercent"])));
            }

            // Keyword based inference
            if (itemName.Contains("titanium") || itemName.Contains("ti-") || itemName.Contains("carbon"))
            {
                if (patch.ContainsKey("Weight")) patch["Weight"] = Math.Round(ToDouble(patch["Weight"]) * 0.8, 3);
                if (patch.ContainsKey("CoolFactor")) patch["CoolFactor"] = Math.Round(ToDouble(patch["CoolFactor"]) * 1.15, 2);
                if (patch.ContainsKey("Ergonomics")) patch["Ergonomics"] = Math.Round(ToDouble(patch["Ergonomics"]) * 1.05, 1);
            }
            else if (itemName.Contains("steel"))
            {
                if (patch.ContainsKey("Weight")) patch["Weight"] = Math.Round(ToDouble(patch["Weight"]) * 1.25, 3);
                if (patch.ContainsKey("DurabilityBurnModificator")) patch["DurabilityBurnModificator"] = Math.Round(ToDouble(patch["DurabilityBurnModificator"]) * 0.9, 2);
            }

            if (itemName.Contains("compact") || itemName.Contains("mini") || itemName.Contains("short") || itemName.Contains("k-") || itemName.Contains("kurz"))
            {
                if (patch.ContainsKey("Weight")) patch["Weight"] = Math.Round(ToDouble(patch["Weight"]) * 0.75, 3);
                if (patch.ContainsKey("Loudness") && ToDouble(patch["Loudness"]) < 0) patch["Loudness"] = Math.Round(ToDouble(patch["Loudness"]) * 0.7, 1);
                if (patch.ContainsKey("VerticalRecoil") && ToDouble(patch["VerticalRecoil"]) < 0) patch["VerticalRecoil"] = Math.Round(ToDouble(patch["VerticalRecoil"]) * 0.7, 2);
            }
            else if (itemName.Contains("long") || itemName.Contains("extended") || itemName.Contains("heavy") || itemName.Contains("full"))
            {
                if (patch.ContainsKey("Weight")) patch["Weight"] = Math.Round(ToDouble(patch["Weight"]) * 1.3, 3);
                if (patch.ContainsKey("Accuracy")) patch["Accuracy"] = Math.Round(ToDouble(patch["Accuracy"]) * 1.1 + 1, 1);
            }

            // Barrel length inference
            if (itemName.Contains("barrel"))
            {
                var match = Regex.Match(itemName, @"(\d+(?:\.\d+)?)\s*(?:mm|inch|in|"")");
                if (match.Success)
                {
                    try
                    {
                        double val = double.Parse(match.Groups[1].Value);
                        double mmVal = (itemName.Contains("inch") || itemName.Contains("in") || itemName.Contains("\"")) ? val * 25.4 : val;
                        double inferredV = (mmVal - 370) / 25.4 * 1.5;
                        if (!patch.ContainsKey("Velocity") || ToDouble(patch["Velocity"]) == 0)
                            patch["Velocity"] = Math.Round(Math.Max(-18.0, Math.Min(18.0, inferredV)), 2);
                    }
                    catch { }
                }
            }

            // Clamp everything
            var keys = new List<string>(patch.Keys);
            foreach (var key in keys)
            {
                if (patch[key] is int || patch[key] is double || patch[key] is float || patch[key] is long)
                {
                    double val = ToDouble(patch[key]);
                    if (key.Contains("Recoil")) patch[key] = Math.Max(-2000.0, Math.Min(2000.0, val));
                    else if (key.Contains("Ergonomics")) patch[key] = Math.Max(-50.0, Math.Min(100.0, val));
                    else if (key.Contains("Weight")) patch[key] = Math.Max(0.0, Math.Min(50.0, val));
                    else if (key.Contains("Multi") || key.Contains("Factor")) patch[key] = Math.Max(0.01, Math.Min(10.0, val));
                }
            }
        }

        private double ToDouble(object obj)
        {
            if (obj == null) return 0;
            if (obj is JsonElement el)
            {
                if (el.ValueKind == JsonValueKind.Number) return el.GetDouble();
                return 0;
            }
            try { return Convert.ToDouble(obj); } catch { return 0; }
        }

        public Dictionary<string, object> CreateDefaultWeaponPatch(string itemId, Dictionary<string, object> info)
        {
            var patch = Utils.DeepClone(DefaultTemplates.Weapon);
            patch["ItemID"] = itemId;
            patch["Name"] = info.TryGetValue("name", out var n) && n != null ? n.ToString() : $"weapon_{itemId}";
            if (info.TryGetValue("properties", out var props) && props is Dictionary<string, object> p)
            {
                if (p.TryGetValue("Weight", out var w)) patch["Weight"] = w;
                if (p.TryGetValue("Ergonomics", out var erg)) patch["Ergonomics"] = erg;
                if (p.TryGetValue("bFirerate", out var rof)) patch["AutoROF"] = rof;
            }
            return patch;
        }

        public Dictionary<string, object> CreateDefaultModPatch(string itemId, Dictionary<string, object> info, string templateFile)
        {
            var patch = Utils.DeepClone(DefaultTemplates.Mod);
            patch["ItemID"] = itemId;
            string modType = GetModTypeFromTemplate(templateFile);
            patch["ModType"] = modType;
            patch["Name"] = info.TryGetValue("name", out var n) && n != null ? n.ToString() : $"mod_{itemId}";
            if (DefaultTemplates.ModTypeSpecificAttrs.TryGetValue(modType, out var attrs))
            {
                foreach (var kv in attrs) patch[kv.Key] = kv.Value;
            }
            if (info.TryGetValue("properties", out var props) && props is Dictionary<string, object> p)
            {
                if (p.TryGetValue("Weight", out var w)) patch["Weight"] = w;
                if (p.TryGetValue("Ergonomics", out var erg)) patch["Ergonomics"] = erg;
            }
            return patch;
        }

        private string GetModTypeFromTemplate(string templateFile)
        {
            var map = new Dictionary<string, string> {
                { "BarrelTemplates.json", "barrel" },
                { "ForegripTemplates.json", "grip" },
                { "HandguardTemplates.json", "handguard" },
                { "MuzzleDeviceTemplates.json", "muzzle" },
                { "MagazineTemplates.json", "magazine" },
                { "ScopeTemplates.json", "sight" },
                { "IronSightTemplates.json", "sight" },
                { "StockTemplates.json", "Stock" }
            };
            if (string.IsNullOrEmpty(templateFile)) return "";
            return map.TryGetValue(templateFile, out var type) ? type : "";
        }

        public Dictionary<string, object> CreateDefaultAmmoPatch(string itemId, Dictionary<string, object> info)
        {
            var patch = Utils.DeepClone(DefaultTemplates.Ammo);
            patch["ItemID"] = itemId;
            patch["Name"] = info.TryGetValue("name", out var n) && n != null ? n.ToString() : $"ammo_{itemId}";
            if (info.TryGetValue("properties", out var props) && props is Dictionary<string, object> p)
            {
                if (p.TryGetValue("Damage", out var d)) patch["Damage"] = d;
                if (p.TryGetValue("PenetrationPower", out var pen)) patch["PenetrationPower"] = pen;
                if (p.TryGetValue("InitialSpeed", out var s)) patch["InitialSpeed"] = s;
                if (p.TryGetValue("BulletMassGram", out var m)) patch["BulletMassGram"] = m;
                if (p.TryGetValue("BallisticCoeficient", out var c)) patch["BallisticCoeficient"] = c;
            }
            return patch;
        }

        public Dictionary<string, object> CreateDefaultConsumablePatch(string itemId, Dictionary<string, object> info)
        {
            var patch = Utils.DeepClone(DefaultTemplates.Consumable);
            patch["ItemID"] = itemId;
            patch["Name"] = info.TryGetValue("name", out var n) && n != null ? n.ToString() : $"consumable_{itemId}";
            return patch;
        }

        public PatchGenerator()
        {
            string basePath = Directory.GetCurrentDirectory();
            _templateLoader = new TemplateLoader(basePath);
        }

        public void ExportPatches(string outputDir)
        {
            Directory.CreateDirectory(outputDir);
            Console.WriteLine("\n正在导出补丁文件...");
            foreach (var kv in fileBasedPatches)
            {
                if (kv.Value.Count == 0) continue;
                string fileName = Path.Combine(outputDir, kv.Key + "_realism_patch.json");
                Utils.WriteJsonFile(fileName, kv.Value);
                Console.WriteLine($"  [源文件分类] 补丁已保存到: {fileName}");
            }
            
            // 类型分类导出
            if (weaponPatches.Count > 0) Utils.WriteJsonFile(Path.Combine(outputDir, "weapons_realism_patch.json"), weaponPatches);
            if (attachmentPatches.Count > 0) Utils.WriteJsonFile(Path.Combine(outputDir, "attachments_realism_patch.json"), attachmentPatches);
            if (ammoPatches.Count > 0) Utils.WriteJsonFile(Path.Combine(outputDir, "ammo_realism_patch.json"), ammoPatches);
            if (gearPatches.Count > 0) Utils.WriteJsonFile(Path.Combine(outputDir, "gear_realism_patch.json"), gearPatches);
            if (consumablesPatches.Count > 0) Utils.WriteJsonFile(Path.Combine(outputDir, "consumables_realism_patch.json"), consumablesPatches);

            var allPatches = new Dictionary<string, object>();
            foreach (var kv in weaponPatches) allPatches[kv.Key] = kv.Value;
            foreach (var kv in attachmentPatches) allPatches[kv.Key] = kv.Value;
            foreach (var kv in ammoPatches) allPatches[kv.Key] = kv.Value;
            foreach (var kv in gearPatches) allPatches[kv.Key] = kv.Value;
            foreach (var kv in consumablesPatches) allPatches[kv.Key] = kv.Value;
            if (allPatches.Count > 0) Utils.WriteJsonFile(Path.Combine(outputDir, "all_items_realism_patch.json"), allPatches);
            
            Console.WriteLine("\n[导出统计]");
            Console.WriteLine($"  武器: {weaponPatches.Count}, 配件: {attachmentPatches.Count}, 弹药: {ammoPatches.Count}, 装备: {gearPatches.Count}, 消耗品: {consumablesPatches.Count}");
        }

        private HashSet<string> processedItems = new HashSet<string>();

        public bool ProcessSingleItem(string itemId, Dictionary<string, object> itemData, Dictionary<string, object> context, string sourceName)
        {
            if (processedItems.Contains(itemId)) return true;

            string format = DetectItemFormat(itemData);
            if (format == "UNKNOWN") return false;

            var itemInfo = ExtractItemInfo(itemId, itemData, format);
            string cloneId = itemInfo.TryGetValue("clone_id", out var cid) ? cid?.ToString() : null;
            string templateId = itemInfo.TryGetValue("template_id", out var tid) ? tid?.ToString() : null;
            string parentId = itemInfo.TryGetValue("parent_id", out var pid) ? pid?.ToString() : null;

            Dictionary<string, object> patch = null;

            if (format == "TEMPLATE_ID" && templateId != null)
            {
                patch = FindTemplateByTemplateId(templateId);
                if (patch != null) patch["ItemID"] = itemId;
            }
            else if (format == "CLONE" && cloneId != null)
            {
                patch = FindTemplateById(cloneId);
                if (patch == null && context.TryGetValue(cloneId, out var cloneData) && cloneData is JsonElement cloneEl)
                {
                    if (ProcessSingleItem(cloneId, ToDict(cloneEl), context, sourceName))
                    {
                        if (weaponPatches.TryGetValue(cloneId, out var wp)) patch = Utils.DeepClone(ToDictFromObj(wp));
                        else if (attachmentPatches.TryGetValue(cloneId, out var ap)) patch = Utils.DeepClone(ToDictFromObj(ap));
                        else if (gearPatches.TryGetValue(cloneId, out var gp)) patch = Utils.DeepClone(ToDictFromObj(gp));
                        else if (ammoPatches.TryGetValue(cloneId, out var amp)) patch = Utils.DeepClone(ToDictFromObj(amp));
                        else if (consumablesPatches.TryGetValue(cloneId, out var cp)) patch = Utils.DeepClone(ToDictFromObj(cp));
                    }
                }
                if (patch != null) patch["ItemID"] = itemId;
            }
            else if (format == "ITEMTOCLONE" && cloneId != null)
            {
                if (itemData.TryGetValue("HandbookParent", out var hb) && hb != null)
                {
                    string hbs = hb.ToString();
                    if (hbs.Length == 24) parentId = hbs;
                    else if (ItemTypeMappings.HandbookParentToId.TryGetValue(hbs, out var pid2)) parentId = pid2;
                }
                if (parentId == null) parentId = InferParentIdFromItemToClone(cloneId);
                if (parentId != null) itemInfo["parent_id"] = parentId;
            }

            if (patch == null && parentId != null)
            {
                string templateFile = GetTemplateForParentId(parentId);
                if (IsAmmo(parentId))
                {
                    patch = CreateDefaultAmmoPatch(itemId, itemInfo);
                }
                else if (IsConsumable(parentId))
                {
                    if (templateFile != null) patch = SelectTemplateData(templateFile, itemId, cloneId);
                    if (patch == null) patch = CreateDefaultConsumablePatch(itemId, itemInfo);
                }
                else if (templateFile != null)
                {
                    patch = SelectTemplateData(templateFile, itemId, cloneId);
                }
            }

            if (patch == null && parentId != null)
            {
                if ((bool)itemInfo["is_weapon"]) patch = CreateDefaultWeaponPatch(itemId, itemInfo);
                else patch = CreateDefaultModPatch(itemId, itemInfo, GetTemplateForParentId(parentId));
            }

            if (patch != null)
            {
                MergeInputProperties(patch, itemInfo);
                ApplyRealismSanityCheck(patch);

                // Add to file-based patches
                if (!fileBasedPatches.ContainsKey(sourceName)) fileBasedPatches[sourceName] = new Dictionary<string, object>();
                fileBasedPatches[sourceName][itemId] = patch;

                // Add to type-based patches
                string type = patch.TryGetValue("$type", out var t) ? t.ToString() : "";
                if (type.Contains("RealismMod.Gun")) weaponPatches[itemId] = patch;
                else if (type.Contains("RealismMod.Gear")) gearPatches[itemId] = patch;
                else if (type.Contains("RealismMod.Consumable")) consumablesPatches[itemId] = patch;
                else if (type.Contains("RealismMod.Ammo")) ammoPatches[itemId] = patch;
                else attachmentPatches[itemId] = patch;

                processedItems.Add(itemId);
                return true;
            }

            return false;
        }

        private string? InferParentIdFromItemToClone(string cloneId)
        {
            if (cloneId.Contains("AMMO_")) return "5485a8684bdc2da71d8b4567";
            if (cloneId.Contains("ASSAULTRIFLE_") || cloneId.Contains("RIFLE_") || cloneId.Contains("SMG_") || cloneId.Contains("PISTOL_") || cloneId.Contains("SHOTGUN_"))
            {
                if (cloneId.Contains("ASSAULTRIFLE_")) return "5447b5f14bdc2d61278b4567";
                if (cloneId.Contains("RIFLE_")) return "5447b6194bdc2d67278b4567";
                if (cloneId.Contains("SNIPER")) return "5447b6254bdc2dc3278b4568";
                if (cloneId.Contains("SMG_")) return "5447b5e04bdc2d62278b4567";
                if (cloneId.Contains("PISTOL_")) return "5447b5cf4bdc2d65278b4567";
                if (cloneId.Contains("SHOTGUN_")) return "5447b6094bdc2dc3278b4567";
            }
            if (cloneId.Contains("MAGAZINE_") || cloneId.Contains("MAG_")) return "5448bc234bdc2d3c308b4569";
            if (cloneId.Contains("ARMOR_") || cloneId.Contains("VEST_")) return "5448e54d4bdc2dcc718b4568";
            if (cloneId.Contains("BARREL_")) return "555ef6e44bdc2de9068b457e";
            if (cloneId.Contains("STOCK_")) return "55818a594bdc2db9688b456a";
            if (cloneId.Contains("HANDGUARD_")) return "55818a104bdc2db9688b4569";
            if (cloneId.Contains("SIGHT_") || cloneId.Contains("SCOPE_")) return cloneId.Contains("SCOPE_") ? "55818ae44bdc2dde698b456c" : "55818ad54bdc2ddc698b4569";
            if (cloneId.Contains("SILENCER_") || cloneId.Contains("SUPPRESSOR_")) return "550aa4cd4bdc2dd8348b456c";
            return null;
        }

        private Dictionary<string, object> ToDictFromObj(object obj)
        {
            if (obj is Dictionary<string, object> d) return d;
            return ToDict(JsonSerializer.Deserialize<JsonElement>(JsonSerializer.Serialize(obj)));
        }

        public void Run(string inputDir, string outputDir)
        {
            if (!Directory.Exists(inputDir))
            {
                Console.WriteLine($"输入目录不存在: {inputDir}");
                return;
            }
            Directory.CreateDirectory(outputDir);
            Console.WriteLine($"扫描目录: {inputDir}");

            // 加载模板
            _templateLoader.LoadAllTemplates();
            Console.WriteLine($"已加载模板文件: {_templateLoader.Templates.Count} 个");

            // 扫描所有物品JSON文件
            var jsonFiles = ItemFileScanner.GetAllJsonFiles(inputDir);
            Console.WriteLine($"找到 {jsonFiles.Count} 个JSON文件");

            foreach (var file in jsonFiles)
            {
                try
                {
                    var itemsDict = Utils.ReadJsonFile<Dictionary<string, object>>(file);
                    if (itemsDict == null) continue;
                    string sourceName = Path.GetFileNameWithoutExtension(file);
                    foreach (var itemKv in itemsDict)
                    {
                        ProcessSingleItem(itemKv.Key, ToDictFromObj(itemKv.Value), itemsDict, sourceName);
                    }
                    Console.WriteLine($"处理文件: {Path.GetFileName(file)}");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[物品处理] 异常: {file} - {ex.Message}");
                }
            }
        }
    }
}
