using System;
using System.Linq;
using System.Reflection;
using System.Text;
using Sdcb.SimdPaddleOCR;
using Sdcb.SimdPaddleOCR.ModelProvider;

class ThreadProbe
{
    static void Main()
    {
        Console.OutputEncoding = Encoding.UTF8;
        Console.WriteLine("=== 环境 ===");
        Console.WriteLine("  处理器数: " + Environment.ProcessorCount);

        var asm = Assembly.Load("Sdcb.SimdPaddleOCR.Models.ChineseV6Medium");
        var mt = asm.GetExportedTypes()
            .First(t => t.Name.EndsWith("Models") &&
                        t.GetProperty("Default", BindingFlags.Public | BindingFlags.Static) != null);
        var bundle = (PaddleOcrModelBundle)mt.GetProperty("Default",
            BindingFlags.Public | BindingFlags.Static)!.GetValue(null)!;

        // 默认 options 下各线程相关字段
        var def = new PaddleOcrOptions();
        Console.WriteLine("\n=== PaddleOcrOptions 默认值 ===");
        foreach (var p in typeof(PaddleOcrOptions).GetProperties())
        {
            object? v;
            try { v = p.GetValue(def); } catch { continue; }
            Console.WriteLine("  {0,-30} = {1}", p.Name, v);
        }

        // 三个子 options
        foreach (var name in new[] { "Detector", "Classifier", "Recognizer" })
        {
            var p = typeof(PaddleOcrOptions).GetProperty(name);
            object? o = p?.GetValue(def);
            if (o == null) continue;
            Console.WriteLine("\n  --- {0} ---", name);
            foreach (var q in o.GetType().GetProperties())
            {
                object? v;
                try { v = q.GetValue(o); } catch { continue; }
                Console.WriteLine("      {0,-30} = {1}", q.Name, v);
            }
        }

        // 加载后看 EffectiveLineWorkerCount
        Console.WriteLine("\n=== 加载后实际生效 ===");
        using var ocr = PaddleOcrAll.Load(bundle, new PaddleOcrOptions());
        Console.WriteLine("  EffectiveLineWorkerCount = " + ocr.EffectiveLineWorkerCount);

        // 显式限 1 线程时的值（供后续受控对照用）
        using var ocr1 = PaddleOcrAll.Load(bundle, new PaddleOcrOptions
        {
            LineWorkerCount = 1,
            DetIntraOpThreads = 1,
        });
        Console.WriteLine("  显式 LineWorkerCount=1/DetIntraOpThreads=1 → Effective = " + ocr1.EffectiveLineWorkerCount);
    }
}
