// RealismPatchGenerator_CSharp/ItemData.cs
// 物品数据结构（根据实际JSON结构后续补充字段）
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace RealismPatchGenerator_CSharp
{
    public class ItemData
    {
        [JsonPropertyName("_id")]
        public string? Id { get; set; }
        [JsonPropertyName("_name")]
        public string? Name { get; set; }
        [JsonPropertyName("_parent")]
        public string? ParentId { get; set; }
        [JsonPropertyName("_props")]
        public Dictionary<string, object>? Props { get; set; }
        // ...根据实际JSON结构继续补充...
    }
}
