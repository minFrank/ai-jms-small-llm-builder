using System.Drawing;
using System.Drawing.Imaging;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using Sdcb.SimdPaddleOCR;
using Sdcb.SimdPaddleOCR.ModelProvider;

class DetProbe {
    static void Main(string[] args) {
        Console.OutputEncoding = Encoding.UTF8;
        string img = args[0];
        int[] limits = args.Length>1 ? args[1].Split(',').Select(int.Parse).ToArray()
                                     : new[]{736,960,960000};
        var asm = Assembly.Load("Sdcb.SimdPaddleOCR.Models.ChineseV6Medium");
        var mt = asm.GetExportedTypes().First(t => t.Name.EndsWith("Models") &&
            t.GetProperty("Default", BindingFlags.Public|BindingFlags.Static) != null);
        var bundle = (PaddleOcrModelBundle)mt.GetProperty("Default",
            BindingFlags.Public|BindingFlags.Static)!.GetValue(null)!;
        byte[] bgra; int w,h;
        using (var bmp = new Bitmap(img)) {
            w=bmp.Width; h=bmp.Height;
            var bd = bmp.LockBits(new Rectangle(0,0,w,h), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
            try { bgra = new byte[bd.Stride*h]; Marshal.Copy(bd.Scan0, bgra, 0, bgra.Length); }
            finally { bmp.UnlockBits(bd); }
        }
        Console.WriteLine("图 %dx%d", w, h);
        foreach (var lim in limits) {
            var opt = new PaddleOcrOptions { LineWorkerCount=1, DetIntraOpThreads=1,
                Detector = new PaddleOcrDetectorOptions { LimitSideLength = lim } };
            using var ocr = PaddleOcrAll.Load(bundle, opt);
            var t0 = System.Diagnostics.Stopwatch.GetTimestamp();
            var r = ocr.Run(bgra, w, h, bgra.Length/h, ImagePixelFormat.Bgra32);
            var ms = System.Diagnostics.Stopwatch.GetElapsedTime(t0).TotalMilliseconds;
            var hist = r.Lines.GroupBy(l => (int)(l.Box.Y1+l.Box.Y2+l.Box.Y3+l.Box.Y4)/4/200*200)
                              .ToDictionary(g=>g.Key, g=>g.Count());
            Console.WriteLine("  LimitSideLength={0,-8} 框数={1,-4} 用时={2,6:F0}ms  检测缩放后={3}x{4}",
                lim, r.DetectedCount, ms, r.DetectorResizedWidth, r.DetectorResizedHeight);
            Console.WriteLine("     y 直方图(200px): " +
                string.Join(" ", hist.OrderBy(k=>k.Key).Select(kv=>kv.Key+":"+kv.Value)));
        }
    }
}