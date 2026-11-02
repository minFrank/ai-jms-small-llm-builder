using System.Text;
using Sdcb.SimdPaddleOCR;
class ApiDump3 {
    static void Main() {
        Console.OutputEncoding = Encoding.UTF8;
        var d = new PaddleOcrOptions();
        Console.WriteLine("SimdPaddleOCR 默认 Detector 参数：");
        Console.WriteLine("   LimitSideLength = " + d.Detector.LimitSideLength);
        Console.WriteLine("   BoxThreshold    = " + d.Detector.BoxThreshold);
        Console.WriteLine("   BitmapThreshold = " + d.Detector.BitmapThreshold);
        Console.WriteLine("   UnclipRatio     = " + d.Detector.UnclipRatio);
        Console.WriteLine("   MaxCandidates   = " + d.Detector.MaxCandidates);
        Console.WriteLine("   UseDilation     = " + d.Detector.UseDilation);
    }
}