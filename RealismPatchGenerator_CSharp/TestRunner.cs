// RealismPatchGenerator_CSharp/TestRunner.cs
// 简单测试入口，验证补丁生成流程
using System;

namespace RealismPatchGenerator_CSharp
{
    public static class TestRunner
    {
        public static void RunBasicTest()
        {
            string inputDir = "input";
            string outputDir = "output";
            var generator = new PatchGenerator();
            generator.Run(inputDir, outputDir);
            generator.ExportPatches(outputDir);
            Console.WriteLine("测试流程执行完毕。");
        }
    }
}
