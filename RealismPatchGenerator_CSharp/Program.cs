// RealismPatchGenerator_CSharp/Program.cs
// EFT 现实主义MOD兼容补丁生成器 C# 版本雏形
// 仅主入口和基础结构，后续将逐步完善

using System;
using System.IO;
using System.Text.Json;
using System.Collections.Generic;

namespace RealismPatchGenerator_CSharp
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine("EFT 现实主义MOD兼容补丁生成器 - C# 版本");
            string inputDir = "input";
            string outputDir = "output";
            if (args.Length >= 1) inputDir = args[0];
            if (args.Length >= 2) outputDir = args[1];
            var generator = new PatchGenerator();
            generator.Run(inputDir, outputDir);
            generator.ExportPatches(outputDir);
            // 可选：运行测试
            // TestRunner.RunBasicTest();
        }
    }
}
