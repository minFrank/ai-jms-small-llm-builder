
# MANIFEST_V2_GUARD: 本脚本为生成期记录；samples/manifest.json 已升 v2（sample_uuid 等），
# 重跑会用旧结构覆盖交付 manifest——检测到 v2 即拒绝写入（r8 反馈：复现脚本不安全）。
import os as _os
_MP = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                    "samples", "manifest.json")
# 绝对权威路径（评审副本拷走后相对路径失效——r9 F4）
_MP_ABS = r"D:/study/ai-jms/ep13-docparse/samples/manifest.json"
if _os.environ.get("EP13_RENDER_ONLY") != "1":
    for _MP in (_MP, _MP_ABS):
        if _os.path.exists(_MP):
            import json as _json
            try:
                _m = _json.load(open(_MP, encoding="utf-8"))
                if _m.get("manifest_v") == 2 or any("sample_uuid" in x for x in _m.get("samples", [])):
                    raise SystemExit("MANIFEST_V2_GUARD: samples/manifest.json 为 v2 交付版，"
                                     "本脚本拒绝覆盖。复现请以 manifest+gt_audit 为权威；"
                                     "如确需重生成，请先手动归档旧 manifest。")
            except SystemExit:
                raise
            except Exception:
                pass

# -*- coding: utf-8 -*-
"""

口径注（r7 数据复核）：本脚本为生成期原始记录；交付以 samples/manifest.json（v2）为准。
差异点：① GT 写入为文本模式、manifest hash 以字节计（CRLF/LF 口径见 gt/gt_audit.json 以字节为准）；
② 复用样本 dpi 以原图实际为准（manifest 300），合成 8 张 150dpi 已回填。
本脚本不重跑即可复现交付数据——复现请以 manifest+gt_audit 为权威。ep13 S26 样本补齐：8 张合成版面（GT=源文本，100% 精确；沿用 ep11 三来源中的 synthetic 工艺）
S26 = ep11 复用 18 张（GT 同步复制）+ 本脚本 8 张 = 26 张
类别补缺（现有 book/hard/invoice/lc/shot/skew/table）：公文、合同、菜单、海报、
          双栏论文、表单、简历、混合版面 —— 覆盖文档解析常见版面复杂度
"""
import hashlib, json, os
from PIL import Image, ImageDraw, ImageFont

BASE = r"D:/study/ai-jms/ep13-docparse"
OUT = os.path.join(BASE, "samples")
GT = os.path.join(BASE, "gt")
EP11_GT = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep11-ocr/gt"
EP11_IMG = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep11-ocr/output/samples"
for d in (OUT, GT): os.makedirs(d, exist_ok=True)

F_SONG = "C:/Windows/Fonts/simsun.ttc"
F_HEI = "C:/Windows/Fonts/simhei.ttf"
F_KAI = "C:/Windows/Fonts/simkai.ttf"
F_YAHEI = "C:/Windows/Fonts/msyh.ttc"

def font(p, s): return ImageFont.truetype(p, s)
def sha16(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]

def para(d, xy, text, f, fill, maxw, lh):
    # r14: 断行按词边界（英文不词内断；中文仍按字），渲染与 GT 源文本对齐
    x, y = xy; line = ""; ybox = [y]
    for ch in text:
        if ch == "\n":
            if line:
                d.text((x, ybox[0]), line, font=f, fill=fill); ybox[0] += lh; line = ""
            continue
        if d.textlength(line + ch, font=f) > maxw and line:
            brk = max(line.rfind(c) for c in (" ", "，", "。", "、", ";", ",", "."))
            if 0 < brk and brk >= len(line) - 24:
                hard = line[brk+1:]
                line = line[:brk+1].rstrip()
                d.text((x, ybox[0]), line, font=f, fill=fill); ybox[0] += lh
                line = hard + ch
            else:
                d.text((x, ybox[0]), line, font=f, fill=fill); ybox[0] += lh
                line = ch
        else:
            line += ch
    if line:
        d.text((x, ybox[0]), line, font=f, fill=fill); ybox[0] += lh
    return ybox[0]

# ================= 8 张合成内容（GT=本字符串，逐字精确） =================
DOCS = {}

DOCS["cn_doc_01"] = ("公文", """【实测样例 非真实公文】
关于开展2026年度信息安全检查工作的通知
各处室、各直属单位：
为贯彻落实上级关于网络安全工作的部署要求，进一步提升我单位信息安全防护水平，经研究决定，于2026年11月至12月开展年度信息安全检查工作。现将有关事项通知如下：
一、检查范围。重点检查网络基础设施、业务系统、移动终端和云服务平台的安全状况。
二、检查内容。包括身份认证与访问控制、数据加密与备份、漏洞修补与补丁管理、安全事件应急响应四个方面。
三、时间安排。11月10日至11月30日为自查阶段，12月1日至12月15日为抽查阶段。
四、工作要求。各单位要明确责任人，如实填写检查表，发现问题立行立改。
联系人：张伟　电话：025-88886666
2026年11月4日""")

DOCS["contract_01"] = ("合同", """【实测样例 非真实合同】
技术服务合同
甲方（委托方）：南京星桥信息有限公司
乙方（受托方）：杭州云禾科技有限公司
根据《中华人民共和国民法典》有关规定，甲乙双方在平等自愿的基础上，就甲方委托乙方提供技术服务事宜达成如下协议：
第一条 服务内容。乙方向甲方提供数据平台的系统集成、性能优化与运行维护服务。
第二条 服务期限。自2026年11月10日起至2027年11月9日止，共十二个月。
第三条 服务费用。本合同总金额为人民币壹拾贰万元整（￥120,000.00），分两期支付：合同生效后十个工作日内支付百分之五十，服务期满后支付余款。
第四条 保密义务。双方对在合作过程中获知的商业秘密负有保密义务，保密期限为合同终止后三年。
第五条 违约责任。任何一方违反本合同约定，应向对方支付合同总金额百分之十的违约金。
甲方（盖章）：____________　乙方（盖章）：____________
授权代表签字：王芳　　　　授权代表签字：李明
签订日期：2026年11月4日　　签订地点：南京市""")

DOCS["menu_01"] = ("菜单", """【实测样例 非真实菜单】
老门东菜馆　价目表
凉菜
盐水鸭 38元　　凉拌黄瓜 12元　　花生米 10元　　镇江肴肉 28元
热菜
红烧狮子头 48元　　清蒸鲈鱼 68元　　美龄粥 26元　　鸭血粉丝汤 22元
时蔬
清炒时蔬 18元　　蒜蓉西兰花 20元　　干煸四季豆 22元
主食
米饭 3元/碗　　阳春面 12元　　菜包 5元/个
酒水
雨花茶 15元　　酸梅汤 8元　　啤酒 10元/瓶
地址：南京市秦淮区剪子巷54号　电话：025-52268888
营业时间：10:30—14:00　16:30—21:00　节假日照常营业""")

DOCS["poster_01"] = ("海报", """【实测样例 非真实海报】
2026南京国际马拉松
畅跑金陵　逐梦前行
比赛项目
全程马拉松（42.195公里）　报名费 200元
半程马拉松（21.0975公里）　报名费 150元
迷你健康跑（5公里）　　　　报名费 80元
比赛时间：2026年11月15日 上午7:30
起终点：南京奥林匹克体育中心
报名时间：2026年9月1日—9月30日
报名官网：www.njmarathon.example.cn
主办单位：南京市体育局
参赛须知：报名者须身体健康，年龄须在20周岁以上（迷你跑不限年龄）。
赛事咨询电话：025-84686666（工作日9:00—17:00）""")

DOCS["paper_01"] = ("双栏论文", """A SURVEY OF DOCUMENT PARSING MODELS
Zhang Wei and Li Ming
School of Computer Science, Nanjing University
Abstract—Document parsing converts heterogeneous documents into structured representations. This paper reviews recent advances in layout analysis, optical character recognition, and table recognition, and discusses benchmark datasets and evaluation metrics used in the field.
I. INTRODUCTION
Documents such as invoices, contracts, and scientific papers carry information in both textual and spatial forms. Effective parsing requires accurate detection of text blocks, reading order reconstruction, and faithful recovery of tables and formulas.
II. LAYOUT ANALYSIS
Modern detectors treat layout analysis as object detection over page images. Typical categories include title, paragraph, table, figure, and list. Anchors and feature pyramids remain common design choices.
III. CHARACTER RECOGNITION
Recognition models map image patches to character sequences. Connectionist temporal classification and attention mechanisms dominate. Subword tokenization helps with long lines and mixed scripts.
IV. EVALUATION
Character error rate is the standard metric, computed as the sum of substitutions, deletions, and insertions divided by the number of reference characters. End-to-end scores additionally penalize ordering errors.
CONCLUSION
Document parsing benefits from joint training of detection and recognition, but benchmark consistency across papers remains an open issue.""")

DOCS["form_01"] = ("表单", """【实测样例 非真实表单】
新员工入职登记表
填表日期：2026年11月4日
姓名　陈思远　性别　男　出生年月　2000年6月
民族　汉族　政治面貌　共青团员　籍贯　江苏南京
身份证号　320102200006152418　手机号　13851512345
最高学历　硕士　毕业院校　南京大学　专业　计算机科学与技术
入职部门　技术部　入职日期　2026年11月10日　岗位　算法工程师
紧急联系人　陈国庆　关系　父子　电话　13905178765
教育经历
2018.09—2022.06　南京大学　计算机科学与技术　本科
2022.09—2025.06　南京大学　计算机科学与技术　硕士
工作经历
2025.07—2026.10　上海某科技公司　算法工程师
本人承诺以上信息真实有效，如有不实愿承担相应责任。
签名：____________　日期：2026年11月4日""")

DOCS["resume_01"] = ("简历", """【实测样例 非真实简历】
个人简历
姓名：林晓雨　电话：13707331234　邮箱：xiaoyu.lin@example.cn
求职意向：前端开发工程师　期望薪资：18K—25K　到岗时间：一个月内
教育经历
2019.09—2023.06　东南大学　软件工程　本科　GPA 3.7/4.0
主修课程：数据结构、计算机网络、操作系统、Web前端开发、人机交互
专业技能
熟练掌握HTML5、CSS3、JavaScript与TypeScript，熟悉Vue3和React框架。
熟悉前端工程化体系，包括Vite、Webpack、ESLint与单元测试。
了解浏览器渲染原理与性能优化手段，有移动端适配实战经验。
项目经历
校园二手交易平台（2022.09—2023.01）　前端负责人
负责商品发布、搜索与聊天模块开发，首屏加载时间从3.2秒优化至1.1秒。
实习经历
2023.07—2023.09　某互联网公司　前端开发实习生
参与运营活动页面搭建，累计上线活动页40余个，缺陷率低于千分之五。
自我评价
做事细致，能独立排查线上问题，重视代码可维护性与团队协作。""")

DOCS["mixed_01"] = ("混合版面", """【实测样例 非真实混合版面】
年度项目验收报告（节选）
一、项目概况
项目名称：智慧园区能耗监测平台　项目编号：NJ-2026-0417
承建单位：南京星桥信息有限公司　验收日期：2026年10月28日
二、建设内容
本项目完成园区12栋楼宇的电表数据采集接入，部署边缘网关36台，
实现分钟级能耗数据汇聚与可视化展示，支撑园区年度能耗同比下降8.6%。
三、关键指标完成情况
指标名称　目标值　实际值　完成率
数据采集成功率　≥99.5%　99.82%　100%
报表生成时长　≤5分钟　3.4分钟　100%
告警响应时间　≤2分钟　1.6分钟　100%
四、验收结论
平台功能与性能指标达到合同要求，同意通过验收。
存在问题：3号楼2台网关固件版本待升级，建设单位承诺于11月20日前完成。
验收组组长签字：赵敏　　建设单位代表签字：王芳
2026年10月28日　　南京""")

# ================= 生成 =================
meta = []
for name, (cat, text) in DOCS.items():
    W, H = 1240, 1754          # A4 @150dpi（与生成一致；spec 300dpi 未采用，报告披露）
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    # 版式差异：海报大字居中、论文双栏、其余单栏
    if cat == "海报":
        f_t, f_b = font(F_HEI, 64), font(F_YAHEI, 34)
        y = para(d, (90, 110), text, f_b, (20, 20, 20), W - 180, 62)
    elif cat == "双栏论文":
        f_t, f_b = font(F_HEI, 30), font(F_SONG, 24)
        lines = text.split("\n")
        mid = len(lines) // 2
        colw = (W - 240) // 2
        para(d, (80, 90), "\n".join(lines[:mid]), f_b, (10, 10, 10), colw, 36)
        para(d, (80 + colw + 80, 90), "\n".join(lines[mid:]), f_b, (10, 10, 10), colw, 36)
        y = H - 60
    else:
        f_t, f_b = font(F_HEI, 34), font(F_SONG, 28)
        # 标题行加粗效果：首行大字
        first, _, rest = text.partition("\n")
        d.text((90, 80), first, font=f_t, fill=(0, 0, 0))
        y = para(d, (90, 150), rest, f_b, (15, 15, 15), W - 180, 48)
    # 页脚标注
    ip = os.path.join(OUT, name + ".png")
    img.save(ip)
    gp = os.path.join(GT, name + ".txt")
    open(gp, "w", encoding="utf-8").write(text)
    meta.append(dict(sample_id=name, kind="image", category=cat, source="synthetic",
                     sha256=hashlib.sha256(open(ip, "rb").read()).hexdigest(),
                     gt_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                     img=os.path.basename(ip), gt=os.path.basename(gp), dpi=150))
    print("✓", name, cat, "%.0fKB" % (os.path.getsize(ip)/1024))

# 复制 ep11 的 18 张 GT + 图（复制进本期，强关联）
import shutil
EP11_NAMES = ["book_01","book_02","book_03","hard_01","hard_02","invoice_01","invoice_02",
              "lc_01","lc_02","lc_03","shot_01","shot_02","shot_03",
              "skew_01","skew_02","skew_03","table_01","table_02"]
for n in EP11_NAMES:
    src_img = os.path.join(EP11_IMG, n + ".png")
    src_gt = os.path.join(EP11_GT, n + ".txt")
    shutil.copy2(src_img, os.path.join(OUT, n + ".png"))
    if os.path.exists(src_gt):
        shutil.copy2(src_gt, os.path.join(GT, n + ".txt"))
    else:
        # table 类可能只有 .table.json
        alt = os.path.join(EP11_GT, n + ".table.json")
        if os.path.exists(alt): shutil.copy2(alt, os.path.join(GT, n + ".table.json"))
    cat = n.rsplit("_", 1)[0]
    meta.append(dict(sample_id=n, kind="image", category=cat, source="ep11_reuse",
                     sha256=hashlib.sha256(open(os.path.join(OUT, n+".png"), "rb").read()).hexdigest(),
                     gt_sha256=(hashlib.sha256(open(os.path.join(GT, n+".txt"), "rb").read()).hexdigest()
                                if os.path.exists(os.path.join(GT, n+".txt")) else None),
                     img=n + ".png", gt=(n + ".txt" if os.path.exists(os.path.join(GT, n+".txt")) else None),
                     dpi=300))

# manifest（26 张冻结）
man = dict(version="s26-ep13-v1", spec="V6e", count=len(meta), samples=meta)
mp = os.path.join(BASE, "samples", "manifest.json")
import os as _os2
if _os2.environ.get("EP13_RENDER_ONLY") != "1":
    json.dump(man, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
missing = [m["sample_id"] for m in meta if not m.get("gt_sha256")]
print("\nmanifest: %d 张 → %s" % (len(meta), mp))
print("缺 GT:", missing or "无 ✓")
