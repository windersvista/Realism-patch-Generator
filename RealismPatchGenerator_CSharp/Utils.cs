// RealismPatchGenerator_CSharp/Utils.cs
// 工具类：文件读写、JSON处理等
using System;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace RealismPatchGenerator_CSharp
{
    public static class Utils
    {
        public static T? ReadJsonFile<T>(string path)
        {
            if (!File.Exists(path)) return default;
            string json = File.ReadAllText(path);
            return JsonSerializer.Deserialize<T>(json);
        }

        public static void WriteJsonFile<T>(string path, T data)
        {
            var options = new JsonSerializerOptions { WriteIndented = true };
            string json = JsonSerializer.Serialize(data, options);
            File.WriteAllText(path, json);
        }

        public static T DeepClone<T>(T obj)
        {
            if (obj == null) return default!;
            string json = JsonSerializer.Serialize(obj);
            return JsonSerializer.Deserialize<T>(json)!;
        }
    }
}
