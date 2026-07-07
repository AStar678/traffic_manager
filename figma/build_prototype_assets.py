from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
W, H = 1600, 1000

FONT_REG = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
if not Path(FONT_BOLD).exists():
    FONT_BOLD = FONT_REG

COLORS = {
    "bg": "#F5F7FA",
    "panel": "#FFFFFF",
    "text": "#1F2937",
    "muted": "#667085",
    "line": "#D8DEE8",
    "blue": "#1A73E8",
    "green": "#34A853",
    "red": "#EA4335",
    "yellow": "#FBBC04",
    "dark": "#102033",
    "soft_blue": "#EAF2FF",
    "soft_green": "#EAF7EF",
    "soft_red": "#FDECEC",
    "soft_yellow": "#FFF7DF",
}


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def rounded(draw, box, radius=12, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def write(draw, xy, value, size=22, fill=None, bold=False, max_width=None):
    fill = fill or COLORS["text"]
    fnt = font(size, bold)
    x, y = xy
    if not max_width:
        draw.text((x, y), value, font=fnt, fill=fill)
        return y + size

    line = ""
    for ch in value:
        test = line + ch
        if draw.textlength(test, font=fnt) <= max_width:
            line = test
        else:
            draw.text((x, y), line, font=fnt, fill=fill)
            y += size + 8
            line = ch
    if line:
        draw.text((x, y), line, font=fnt, fill=fill)
    return y + size


def pill(draw, x, y, label, fill, fg="#FFFFFF", width=None):
    fnt = font(16, True)
    width = width or int(draw.textlength(label, font=fnt) + 34)
    rounded(draw, (x, y, x + width, y + 34), 17, fill=fill)
    draw.text((x + width / 2, y + 17), label, font=fnt, fill=fg, anchor="mm")


def button(draw, box, label, fill=None):
    fill = fill or COLORS["blue"]
    rounded(draw, box, 8, fill=fill)
    draw.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), label, font=font(18, True), fill="#FFFFFF", anchor="mm")


def build_overall_layout():
    img = Image.new("RGB", (W, H), COLORS["bg"])
    draw = ImageDraw.Draw(img)

    write(draw, (48, 34), "VisionDrive 智视驾交互原型图（整体布局）", 34, COLORS["text"], True)
    write(
        draw,
        (48, 82),
        "用于插入《产品需求文档》“界面原型图 / 交互原型”章节，展示系统主要页面结构、核心交互入口和结果展示区域。",
        18,
        COLORS["muted"],
        max_width=1380,
    )

    # Browser/app frame
    rounded(draw, (48, 135, 1552, 915), 20, fill="#EDF2F8", outline=COLORS["line"])
    rounded(draw, (70, 160, 1530, 890), 16, fill=COLORS["panel"], outline=COLORS["line"])

    # Sidebar
    rounded(draw, (70, 160, 330, 890), 16, fill=COLORS["dark"])
    write(draw, (100, 195), "VisionDrive", 28, "#FFFFFF", True)
    write(draw, (102, 235), "车载视觉感知与人机交互系统", 14, "#AFC0D8")
    menu = [
        ("车牌识别", True),
        ("交警手势识别", False),
        ("车主手势控车", False),
        ("告警仪表盘", False),
        ("历史记录", False),
        ("系统设置", False),
    ]
    y = 300
    for label, active in menu:
        rounded(draw, (94, y, 306, y + 48), 10, fill=COLORS["blue"] if active else COLORS["dark"])
        write(draw, (124, y + 12), label, 18, "#FFFFFF" if active else "#B8C4D6", active)
        y += 62

    # Top bar
    rounded(draw, (330, 160, 1530, 236), 0, fill="#FFFFFF")
    write(draw, (370, 184), "车牌识别 / 交警手势 / 车主手势统一工作台", 24, COLORS["text"], True)
    pill(draw, 1120, 182, "模型服务正常", COLORS["soft_green"], COLORS["green"], 132)
    pill(draw, 1270, 182, "WebSocket 已连接", COLORS["soft_blue"], COLORS["blue"], 156)
    pill(draw, 1440, 182, "管理员", COLORS["soft_blue"], COLORS["blue"], 72)

    # Main content panels
    content_x, content_y = 370, 270
    rounded(draw, (content_x, content_y, content_x + 330, content_y + 430), 12, fill=COLORS["panel"], outline=COLORS["line"])
    write(draw, (content_x + 24, content_y + 24), "输入区", 24, COLORS["text"], True)
    write(draw, (content_x + 24, content_y + 62), "FileUploader 选择图片或视频，前端先校验格式与大小，再上传到后端。", 17, COLORS["muted"], max_width=275)
    rounded(draw, (content_x + 36, content_y + 150, content_x + 294, content_y + 300), 12, fill="#F8FAFE", outline="#BBD3FF")
    draw.text((content_x + 165, content_y + 198), "上传图片 / 视频", font=font(24, True), fill=COLORS["blue"], anchor="mm")
    draw.text((content_x + 165, content_y + 238), "jpg/png/mp4/rtsp", font=font(16), fill=COLORS["muted"], anchor="mm")
    button(draw, (content_x + 36, content_y + 338, content_x + 294, content_y + 390), "开始识别")

    preview_x = content_x + 370
    rounded(draw, (preview_x, content_y, preview_x + 500, content_y + 430), 12, fill="#111827", outline=COLORS["line"])
    write(draw, (preview_x + 24, content_y + 24), "识别预览区", 24, "#FFFFFF", True)
    rounded(draw, (preview_x + 36, content_y + 76, preview_x + 464, content_y + 340), 10, fill="#1F2937", outline="#374151")
    draw.rectangle((preview_x + 98, content_y + 160, preview_x + 250, content_y + 216), outline=COLORS["green"], width=4)
    pill(draw, preview_x + 98, content_y + 122, "京A12345", COLORS["green"], "#FFFFFF", 110)
    pts = [(preview_x + 334, content_y + 130), (preview_x + 300, content_y + 186), (preview_x + 374, content_y + 186), (preview_x + 282, content_y + 260), (preview_x + 394, content_y + 260)]
    for a, b in [(0, 1), (0, 2), (1, 3), (2, 4), (1, 2)]:
        draw.line((*pts[a], *pts[b]), fill="#FFFFFF", width=3)
    for px, py in pts:
        draw.ellipse((px - 6, py - 6, px + 6, py + 6), fill=COLORS["yellow"])
    write(draw, (preview_x + 58, content_y + 368), "Canvas 叠加检测框、车牌文字、人体/手部关键点骨架", 17, "#CBD5E1", max_width=420)

    result_x = preview_x + 535
    rounded(draw, (result_x, content_y, result_x + 270, content_y + 430), 12, fill=COLORS["panel"], outline=COLORS["line"])
    write(draw, (result_x + 24, content_y + 24), "结果区", 24, COLORS["text"], True)
    rows = [
        ("任务类型", "license_plate", COLORS["soft_blue"]),
        ("检测结果", "2 个目标", COLORS["soft_green"]),
        ("置信度", "96%", COLORS["soft_yellow"]),
        ("当前指令", "STOP / 接听电话", COLORS["soft_red"]),
    ]
    yy = content_y + 80
    for k, v, bg in rows:
        rounded(draw, (result_x + 24, yy, result_x + 246, yy + 58), 8, fill=bg)
        write(draw, (result_x + 40, yy + 10), k, 15, COLORS["muted"], True)
        write(draw, (result_x + 128, yy + 10), v, 18, COLORS["text"], True)
        yy += 72
    button(draw, (result_x + 24, content_y + 356, result_x + 246, content_y + 402), "保存到历史记录")

    # Bottom section
    bottom_y = 735
    rounded(draw, (370, bottom_y, 980, 860), 12, fill=COLORS["panel"], outline=COLORS["line"])
    write(draw, (398, bottom_y + 24), "历史记录 / 查询筛选", 22, COLORS["text"], True)
    write(draw, (398, bottom_y + 64), "按任务类型、时间范围、状态筛选；表格展示识别摘要，点击详情可回看标注图和结构化结果。", 16, COLORS["muted"], max_width=520)
    rounded(draw, (398, bottom_y + 108, 920, bottom_y + 118), 5, fill="#EEF2F7")
    for i, h in enumerate(["时间", "任务", "结果", "状态"]):
        write(draw, (410 + i * 125, bottom_y + 128), h, 15, COLORS["muted"], True)

    rounded(draw, (1020, bottom_y, 1490, 860), 12, fill=COLORS["panel"], outline=COLORS["line"])
    write(draw, (1048, bottom_y + 24), "告警消息 / Agent 推送", 22, COLORS["text"], True)
    write(draw, (1048, bottom_y + 64), "Alert Agent 监听识别失败、低置信度、LLM超时等异常，通过 WebSocket 推送告警摘要。", 16, COLORS["muted"], max_width=390)
    pill(draw, 1048, bottom_y + 116, "严重", COLORS["red"], "#FFFFFF", 70)
    write(draw, (1135, bottom_y + 120), "车牌识别连续失败，建议检查输入图片质量。", 15, COLORS["text"], max_width=320)

    # Notes
    write(draw, (92, 930), "说明：本图是需求文档用交互原型，不等同于最终前端实现；后续 Vue 页面可在此布局基础上按真实接口继续细化。", 18, COLORS["muted"], max_width=1380)

    img.save(OUT / "交互原型图_整体布局.png")


def write_readme():
    (OUT / "README.md").write_text(
        """# VisionDrive 交互原型图资料

本目录用于保存可插入《产品需求文档》的交互原型图资料。

当前保留文件：
- `交互原型图_整体布局.png`：系统整体交互布局图，可直接插入需求文档的“界面原型图 / 交互原型”章节。

说明：
- 这张图只是需求分析阶段的原型说明材料，用来表达页面结构和核心交互入口。
- 它不影响后续 Vue 前端开发；前端实现可以在后续详细设计阶段继续按接口、组件和真实数据流细化。
- 图中布局与需求文档保持一致：左侧功能导航、顶部状态栏、输入区、识别预览区、结果区、历史记录区、告警推送区。
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    build_overall_layout()
    write_readme()
