// RealismPatchGenerator_CSharp/ItemFileScanner.cs
// 递归扫描input目录下所有JSON文件
using System;
using System.Collections.Generic;
using System.IO;

namespace RealismPatchGenerator_CSharp
{
    public static class ItemFileScanner
    {
        public static List<string> GetAllJsonFiles(string inputDir)
        {
            var files = new List<string>();
            if (!Directory.Exists(inputDir)) return files;
            foreach (var file in Directory.GetFiles(inputDir, "*.json", SearchOption.AllDirectories))
            {
                files.Add(file);
            }
            return files;
        }
    }
}
