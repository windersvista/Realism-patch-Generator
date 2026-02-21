// RealismPatchGenerator_CSharp/TemplateLoader.cs
// 负责加载所有模板文件到内存
using System;
using System.Collections.Generic;
using System.IO;

namespace RealismPatchGenerator_CSharp
{
    public class TemplateLoader
    {
        public Dictionary<string, Dictionary<string, object>> Templates { get; private set; } = new();
        private readonly string _basePath;

        public TemplateLoader(string basePath)
        {
            _basePath = basePath;
        }

        public void LoadAllTemplates()
        {
            Templates.Clear();
            string[] subDirs = { "weapons", "attatchments", "ammo", "gear", "consumables" };
            foreach (var dir in subDirs)
            {
                string fullDir = Path.Combine(_basePath, "现实主义物品模板", dir);
                if (!Directory.Exists(fullDir)) continue;
                foreach (var file in Directory.GetFiles(fullDir, "*.json"))
                {
                    try
                    {
                        var dict = Utils.ReadJsonFile<Dictionary<string, object>>(file);
                        if (dict != null)
                            Templates[Path.GetFileName(file)] = dict;
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"[模板加载] 读取失败: {file} - {ex.Message}");
                    }
                }
            }
        }
    }
}
