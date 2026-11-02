// ep12 SimdPaddleOCR 批量跑测入口。
//
// 为什么新建项目而不改 SimdGate：SimdGate 是线程探针桩（只 dump options），无批量入口。
//
// 两档（方案 §4.7 受控对照）：
//   default    引擎默认值（读者装完拿到的体验）。EffectiveLineWorkerCount 默认 4。
//   controlled 并行度与输入契约对齐 PaddleOCR 参照栈：LineWorkerCount=1、
//              DetIntraOpThreads=1、Recognizer.AdaptiveWidth=false、TargetWidth=320。
//   只有 controlled 档能归因"栈"；default 档只能写"默认配置下快多少"。两档分开报。
//
// 行分组不在这里做：C# 只吐原始 (y_center, x_min, text)，由 Python 调 ep11 的
// _group_lines 统一分组 —— 判据只允许有一份实现（skill §8.6）。
//
// API 全部经 ApiDump 反射确认，无一处靠猜：
//   PaddleOcrOptions 属性全是 init-only → 只能用对象初始化器一次给全
//   TargetWidth / AdaptiveWidth 在 Recognizer 子对象上，不在顶层
//   PaddleOcrAll.Run 无单参重载 → 需 (ReadOnlySpan<byte>, w, h, stride, ImagePixelFormat)
//   PaddleOcrLine 上是 Box（四点 X1..Y4），没有 Rect
//   图像解码：System.Drawing 读 PNG → Bgra32 字节

using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using Sdcb.SimdPaddleOCR;
using Sdcb.SimdPaddleOCR.ModelProvider;

class SimdBench
{
    static int Main(string[] args)
    {
        Console.OutputEncoding = Encoding.UTF8;
        string manifest = "", profile = "default", outFile = "";
        int runs = 3, warmup = 2;
        for (int i = 0; i < args.Length - 1; i++)
        {
            switch (args[i])
            {
                case "--manifest": manifest = args[++i]; break;
                case "--profile": profile = args[++i]; break;
                case "--out": outFile = args[++i]; break;
                case "--runs": runs = int.Parse(args[++i]); break;
                case "--warmup": warmup = int.Parse(args[++i]); break;
            }
        }
        if (manifest == "" || outFile == "")
        {
            Console.Error.WriteLine("usage: SimdBench --manifest <list.txt> --profile default|controlled --runs N --warmup N --out <json>");
            return 2;
        }
        var imgs = File.ReadAllLines(manifest)
                      .Where(l => !string.IsNullOrWhiteSpace(l))
                      .Select(l => l.Trim()).ToList();
        if (imgs.Count == 0) { Console.Error.WriteLine("manifest 为空"); return 2; }

        var doc = new Dictionary<string, object?>
        {
            ["schema"] = "ep12-simdbench-v1",
            ["profile"] = profile,
            ["runs"] = runs,
            ["warmup"] = warmup,
            ["processor_count"] = Environment.ProcessorCount,
            ["images"] = new List<object?>(),
        };

        var tProc = Stopwatch.GetTimestamp();
        PaddleOcrAll ocr;
        try
        {
            var asm = Assembly.Load("Sdcb.SimdPaddleOCR.Models.ChineseV6Medium");
            var mt = asm.GetExportedTypes()
                .First(t => t.Name.EndsWith("Models") &&
                            t.GetProperty("Default", BindingFlags.Public | BindingFlags.Static) != null);
            var bundle = (PaddleOcrModelBundle)mt.GetProperty("Default",
                BindingFlags.Public | BindingFlags.Static)!.GetValue(null)!;
            doc["bundle_name"] = bundle.Name;

            // 全部 init-only → 必须用对象初始化器一次给全，不能逐个赋值
            var opt = new PaddleOcrOptions();
            if (profile == "controlled")
            {
                // 受控档 = 把检测参数对齐到 PaddleOCR predict() 的**运行时实际值**。
                //
                // 为什么不直接用 inference.yml 里的值（0.45/0.2/1.4）：
                // 那是模型默认，PaddleOCR 3.7.0 的 predict() 会覆盖成 0.6/0.3/1.5。
                // 实测取自 predict() 返回的 text_det_params 字段（证据链见
                // PLAN §4.7）。只读 yml 会得出错误判断。
                //
                // 各参数对应关系（Simd 名 ← PaddleOCR 名）：
                //   BoxThreshold    ← box_thresh    = 0.6
                //   BitmapThreshold ← thresh        = 0.3
                //   UnclipRatio     ← unclip_ratio  = 1.5
                //   LimitSideLength ← limit_side_len = 64 + limit_type="min"。
                //     ⚠️ 两者语义**相反**，这是实测踩出来的（2026-10-25）：
                //       PaddleOCR 的 limit_side_len 配 limit_type="min" 是**短边下限**
                //         → 我们样本短边 1347 > 64，所以它根本不缩图（原分辨率跑检测）
                //       Simd 的 LimitSideLength 是**长边上限**
                //         → 设 64 等于把图压到 64px，检测直接全废（实测 book_01 42框→0框）
                //     正确映射：设成 ≥ 长边的值 = 不缩图。取 4096（样本长边最大 1743）。
                //     实测对齐后 book_02 框数 27 → 95，与 PaddleOCR 的 87 同量级；
                //     剩余差来自对齐不了的归一化 mean/std。
                //   MaxCandidates   ← max_candidates = 3000（Simd 默认即同值）
                //
                // ⚠️ 有一项**对齐不了**：归一化 mean/std。PaddleOCR 用
                //    ImageNet 值 (0.485,0.456,0.406)/(0.229,0.224,0.225)，
                //    而 PaddleOcrDetectorOptions 不暴露 mean/std，Simd 内部写死。
                //    这一项写进正文当已知局限，不能假装对齐了。
                opt = new PaddleOcrOptions
                {
                    LineWorkerCount = 1,
                    DetIntraOpThreads = 1,
                    Detector = new PaddleOcrDetectorOptions
                    {
                        LimitSideLength = 4096,
                        BoxThreshold = 0.6f,
                        BitmapThreshold = 0.3f,
                        UnclipRatio = 1.5f,
                        MaxCandidates = 3000,
                    },
                    Recognizer = new PaddleOcrRecognizerOptions
                    {
                        AdaptiveWidth = true,   // 跟随 PaddleOCR 的自适应行为（见上）
                        TargetWidth = 320,      // 下限，与 PaddleOCR 的 imgW/imgH 基线一致
                    },
                };
            }
            else if (profile != "default")
            {
                Console.Error.WriteLine("unknown profile: " + profile);
                return 2;
            }

            var t0 = Stopwatch.GetTimestamp();
            ocr = PaddleOcrAll.Load(bundle, opt);
            doc["t_session_s"] = Math.Round(Stopwatch.GetElapsedTime(t0).TotalSeconds, 6);

            // 把三个子 options 也展开成真字典 —— 只 ToString() 会得到类型名，
            // 参数没进产物，事后无法核对"这一档到底用了什么参数"。
            var opts = new Dictionary<string, object?>();
            foreach (var p in typeof(PaddleOcrOptions).GetProperties())
            {
                if (p.PropertyType.Name.Contains("Options")) continue;
                object? v;
                try { v = p.GetValue(opt); } catch { continue; }
                opts[p.Name] = v?.ToString();
            }
            opts["Detector"] = DumpProps(typeof(PaddleOcrDetectorOptions), opt.Detector);
            opts["Classifier"] = DumpProps(typeof(PaddleOcrClassifierOptions), opt.Classifier);
            opts["Recognizer"] = DumpProps(typeof(PaddleOcrRecognizerOptions), opt.Recognizer);
            doc["options"] = opts;
            doc["effective_line_worker_count"] = ocr.EffectiveLineWorkerCount;
        }
        catch (Exception e)
        {
            doc["load_err"] = e.GetType().Name + ": " + e.Message;
            WriteJson(outFile, doc);
            Console.WriteLine("SIMDBENCH_DONE load_err={0}", e.Message);
            return 1;
        }

        // 预热（不计时），收敛判据 <2%，不收敛再加一轮 —— 与 ep11 bench_cell L111-124 一致
        var wt = new List<double>();
        bool conv = true;
        for (int w = 0; w < warmup; w++)
        {
            var tw = Stopwatch.GetTimestamp();
            RunOnce(ocr, imgs[0]);
            wt.Add(Math.Round(Stopwatch.GetElapsedTime(tw).TotalSeconds, 4));
        }
        if (wt.Count >= 2)
        {
            conv = Math.Abs(wt[^1] - wt[^2]) / Math.Max(wt[^2], 1e-9) < 0.02;
            if (!conv)
            {
                var tw = Stopwatch.GetTimestamp();
                RunOnce(ocr, imgs[0]);
                wt.Add(Math.Round(Stopwatch.GetElapsedTime(tw).TotalSeconds, 4));
                conv = Math.Abs(wt[^1] - wt[^2]) / Math.Max(wt[^2], 1e-9) < 0.02;
            }
        }
        doc["warmup_times"] = wt;
        doc["warmup_converged"] = conv;

        var images = (List<object?>)doc["images"]!;
        foreach (var img in imgs)
        {
            var one = new Dictionary<string, object?> { ["img"] = img };
            var ts = new List<double>();
            string err = "";
            List<object?> raw = new();
            for (int r = 0; r < runs; r++)
            {
                var t0 = Stopwatch.GetTimestamp();
                var (items, e) = RunOnce(ocr, img);
                ts.Add(Stopwatch.GetElapsedTime(t0).TotalSeconds);
                if (r == 0) raw = items;
                if (e != "") { err = e; break; }
            }
            one["t_infers"] = ts.Select(x => Math.Round(x, 6)).ToList();
            if (ts.Count > 0)
            {
                var s = ts.OrderBy(x => x).ToList();
                one["median"] = Math.Round(s[s.Count / 2], 6);
                one["min"] = Math.Round(s[0], 6);
                one["max"] = Math.Round(s[^1], 6);
                one["spread_pct"] = Math.Round((s[^1] - s[0]) / Math.Max(s[s.Count / 2], 1e-9) * 100, 2);
            }
            one["raw_items"] = raw;
            one["err"] = err;
            images.Add(one);
            Console.WriteLine("IMG_DONE {0} median={1} lines={2} err={3}",
                Path.GetFileNameWithoutExtension(img),
                one.TryGetValue("median", out var m) ? m : "-", raw.Count, err);
        }

        ocr.Dispose();
        doc["t_total_s"] = Math.Round(Stopwatch.GetElapsedTime(tProc).TotalSeconds, 6);
        WriteJson(outFile, doc);
        Console.WriteLine("SIMDBENCH_DONE profile={0} n={1}", profile, imgs.Count);
        return 0;
    }

    /// <summary>把子 options 的属性展开成真字典，供产物记录用。</summary>
    static System.Collections.Generic.Dictionary<string, object?> DumpProps(Type t, object src)
    {
        var d = new System.Collections.Generic.Dictionary<string, object?>();
        foreach (var p in t.GetProperties())
        {
            object? v;
            try { v = p.GetValue(src); } catch { continue; }
            d[p.Name] = v?.ToString();
        }
        return d;
    }

    static (List<object?> items, string err) RunOnce(PaddleOcrAll ocr, string img)
    {
        var items = new List<object?>();
        try
        {
            byte[] bgra;
            int w, h;
            using (var bmp = new Bitmap(img))
            {
                w = bmp.Width; h = bmp.Height;
                var rect = new Rectangle(0, 0, w, h);
                var bd = bmp.LockBits(rect, ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
                try
                {
                    int stride = bd.Stride;
                    bgra = new byte[stride * h];
                    Marshal.Copy(bd.Scan0, bgra, 0, bgra.Length);
                }
                finally { bmp.UnlockBits(bd); }
            }
            var result = ocr.Run(bgra, w, h, bgra.Length / h, ImagePixelFormat.Bgra32);
            foreach (var line in result.Lines)
            {
                var box = line.Box;
                double yc = (box.Y1 + box.Y2 + box.Y3 + box.Y4) / 4.0;
                double xmin = Math.Min(Math.Min(box.X1, box.X2), Math.Min(box.X3, box.X4));
                items.Add(new object?[] { Math.Round(yc, 2), Math.Round(xmin, 2), line.Text });
            }
            return (items, "");
        }
        catch (Exception e)
        {
            return (items, e.GetType().Name + ": " + e.Message);
        }
    }

    static void WriteJson(string path, object doc)
    {
        var o = new JsonSerializerOptions { WriteIndented = true };
        File.WriteAllText(path, JsonSerializer.Serialize(doc, o), Encoding.UTF8);
    }
}
