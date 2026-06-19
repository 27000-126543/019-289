import argparse
import json
import os
import sys
import hashlib
from datetime import datetime, date

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".monitors")


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _monitor_path(monitor_id):
    return os.path.join(DATA_DIR, f"{monitor_id}.json")


def _load_monitor(monitor_id):
    path = _monitor_path(monitor_id)
    if not os.path.exists(path):
        print(f"[错误] 监测项目 '{monitor_id}' 不存在。")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_monitor(data):
    path = _monitor_path(data["id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _gen_id(product_name):
    raw = f"{product_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]


PLATFORM_CHANNELS = {
    "微博": [
        "微博热搜榜",
        "微博话题页（#产品名+召回#）",
        "品牌官方微博",
        "12315 官方微博转评",
        "相关 KOL/大 V 原发帖",
    ],
    "微信公众号": [
        "品牌官方公众号",
        "消费者权益类公众号（如'消费者报道'）",
        "行业媒体公众号",
        "地方市场监管公众号",
    ],
    "抖音": [
        "抖音热搜榜",
        "品牌官方抖音号",
        "测评/维权类博主视频",
        "相关话题标签页",
    ],
    "小红书": [
        "小红书搜索（产品名+召回/质量问题）",
        "用户真实体验笔记",
        "品牌官方账号声明",
    ],
    "知乎": [
        "知乎热搜",
        "相关问答（'如何评价某产品召回'）",
        "专业领域答主分析",
    ],
    "B站": [
        "B站热搜",
        "测评/科普 UP 主视频",
        "品牌官方账号",
    ],
    "豆瓣": [
        "相关小组讨论",
        "消费者维权小组",
    ],
    "论坛/贴吧": [
        "百度贴吧（品牌/产品吧）",
        "天涯/猫鱼等社区",
        "汽车之家/母婴论坛等垂直社区",
    ],
    "新闻网站": [
        "国家市场监督管理总局公告",
        "新华网/人民网等央媒",
        "财新/第一财经等财经媒体",
        "地方新闻媒体",
        "界面/澎湃等数字媒体",
    ],
    "政府/监管": [
        "国家市场监督管理总局官网",
        "12315 投诉平台",
        "海关总署召回公告",
        "地方市场监管局通报",
    ],
}


def cmd_new(args):
    _ensure_dir()
    product_name = args.product
    recall_reason = args.reason
    platforms = [p.strip() for p in args.platforms.split(",")]
    date_start = args.start
    date_end = args.end

    monitor_id = _gen_id(product_name)
    monitor = {
        "id": monitor_id,
        "product_name": product_name,
        "recall_reason": recall_reason,
        "platforms": platforms,
        "date_range": {"start": date_start, "end": date_end},
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "samples": [],
    }
    _save_monitor(monitor)

    print(f"\n{'='*60}")
    print(f"  监测项目已创建")
    print(f"{'='*60}")
    print(f"  编号:       {monitor_id}")
    print(f"  产品名称:   {product_name}")
    print(f"  召回原因:   {recall_reason}")
    print(f"  关注平台:   {', '.join(platforms)}")
    print(f"  日期范围:   {date_start} ~ {date_end}")
    print(f"{'='*60}")

    print(f"\n📋 待检查清单 — 请到以下渠道补充样本：\n")
    for i, platform in enumerate(platforms, 1):
        channels = PLATFORM_CHANNELS.get(platform, [f"{platform} 搜索（产品名+召回关键词）"])
        print(f"  【{i}】{platform}")
        for ch in channels:
            print(f"       □  {ch}")
        print()

    unmatched = [p for p in platforms if p not in PLATFORM_CHANNELS]
    if unmatched:
        print("  ⚠ 以下平台无预设渠道提示，请自行检索：")
        for p in unmatched:
            print(f"       □  {p} 搜索「{product_name} {recall_reason}」")
        print()

    print(f"  提示：使用以下命令追加样本——")
    print(f"  python monitor.py add {monitor_id} --title \"标题\" --link \"链接\" \\")
    print(f"         --reposts 转发数 --comments 评论数 --sentiment 情绪 \\")
    print(f"         --category 分类 --source \"来源说明\"")
    print()


SENTIMENT_MAP = {
    "愤怒": "愤怒", "担忧": "担忧", "失望": "失望",
    "中立": "中立", "理解": "理解", "支持": "支持",
    "negative": "愤怒", "neutral": "中立", "positive": "支持",
    "neg": "愤怒", "neu": "中立", "pos": "支持",
}

CATEGORY_MAP = {
    "新增爆点": "新增爆点", "主要质疑": "主要质疑",
    "官方回应": "官方回应", "待核实传言": "待核实传言",
    "hotspot": "新增爆点", "questioning": "主要质疑",
    "official": "官方回应", "rumor": "待核实传言",
    "爆点": "新增爆点", "质疑": "主要质疑",
    "回应": "官方回应", "传言": "待核实传言",
}


def _title_similarity(t1, t2):
    if t1 == t2:
        return 1.0
    set1 = set(t1)
    set2 = set(t2)
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)


def cmd_add(args):
    _ensure_dir()
    monitor = _load_monitor(args.monitor_id)

    title = args.title
    link = args.link or ""
    reposts = args.reposts or 0
    comments = args.comments or 0
    sentiment_raw = args.sentiment or ""
    category_raw = args.category or ""
    source_note = args.source or ""

    sentiment = SENTIMENT_MAP.get(sentiment_raw, sentiment_raw)
    category = CATEGORY_MAP.get(category_raw, category_raw)

    warnings = []

    for s in monitor["samples"]:
        sim = _title_similarity(s["title"], title)
        if sim >= 0.8:
            warnings.append(
                f"⚠ 标题与已有样本 #{s['id']} 高度相似（相似度 {sim:.0%}）：「{s['title'][:30]}…」"
            )
        if link and s.get("link") and link == s["link"]:
            warnings.append(f"⚠ 链接与已有样本 #{s['id']} 完全相同")

    valid_categories = {"新增爆点", "主要质疑", "官方回应", "待核实传言"}
    if category not in valid_categories:
        warnings.append(
            f"⚠ 分类「{category}」不在标准分类中，请使用：{', '.join(valid_categories)}"
        )

    if not link:
        warnings.append("⚠ 缺少链接，后续核验可能困难")
    if not source_note:
        warnings.append("⚠ 缺少来源说明，请在课堂/周报引用时补充出处")

    sample_id = len(monitor["samples"]) + 1
    sample = {
        "id": sample_id,
        "title": title,
        "link": link,
        "reposts": reposts,
        "comments": comments,
        "sentiment": sentiment,
        "category": category,
        "source_note": source_note,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    monitor["samples"].append(sample)
    _save_monitor(monitor)

    print(f"\n  ✅ 样本 #{sample_id} 已追加到监测项目 {monitor['id']}")
    if warnings:
        print(f"\n  系统提示：")
        for w in warnings:
            print(f"    {w}")
    print(f"\n  当前样本总数: {len(monitor['samples'])}")
    print()


def cmd_report(args):
    _ensure_dir()
    monitor = _load_monitor(args.monitor_id)

    samples = monitor["samples"]
    if not samples:
        print("\n  该监测项目尚无样本，请先追加样本后再生成日报。\n")
        sys.exit(0)

    report_date = args.date or date.today().strftime("%Y-%m-%d")

    categories_order = ["新增爆点", "主要质疑", "官方回应", "待核实传言"]
    category_emoji = {
        "新增爆点": "🔥",
        "主要质疑": "❓",
        "官方回应": "📢",
        "待核实传言": "⚠️",
    }

    grouped = {c: [] for c in categories_order}
    uncategorized = []
    for s in samples:
        cat = s.get("category", "")
        if cat in grouped:
            grouped[cat].append(s)
        else:
            uncategorized.append(s)

    lines = []
    lines.append("=" * 60)
    lines.append(f"  产品召回舆情日报")
    lines.append("=" * 60)
    lines.append(f"  报告日期:   {report_date}")
    lines.append(f"  产品名称:   {monitor['product_name']}")
    lines.append(f"  召回原因:   {monitor['recall_reason']}")
    lines.append(f"  监测周期:   {monitor['date_range']['start']} ~ {monitor['date_range']['end']}")
    lines.append(f"  样本总数:   {len(samples)}")
    lines.append("-" * 60)

    for cat in categories_order:
        items = grouped[cat]
        emoji = category_emoji.get(cat, "")
        lines.append(f"\n  {emoji} 【{cat}】（{len(items)} 条）")
        lines.append("-" * 40)
        if not items:
            lines.append("    （暂无）")
        for s in items:
            engagement = f"转发{s['reposts']} 评论{s['comments']}"
            lines.append(f"    [#{s['id']}] {s['title']}")
            lines.append(f"         情绪: {s['sentiment']} | {engagement}")
            if s["link"]:
                lines.append(f"         链接: {s['link']}")
            if s["source_note"]:
                lines.append(f"         来源: {s['source_note']}")

    if uncategorized:
        lines.append(f"\n  📝 【未分类】（{len(uncategorized)} 条）")
        lines.append("-" * 40)
        for s in uncategorized:
            engagement = f"转发{s['reposts']} 评论{s['comments']}"
            lines.append(f"    [#{s['id']}] {s['title']}")
            lines.append(f"         情绪: {s['sentiment']} | {engagement}")

    lines.append("\n" + "=" * 60)

    sentiment_summary = {}
    for s in samples:
        sent = s.get("sentiment", "未标注")
        sentiment_summary[sent] = sentiment_summary.get(sent, 0) + 1

    lines.append(f"  情绪分布:   {', '.join(f'{k} {v}条' for k, v in sentiment_summary.items())}")

    missing_source = [s for s in samples if not s.get("source_note")]
    if missing_source:
        ids = ", ".join(f"#{s['id']}" for s in missing_source)
        lines.append(f"  ⚠ 缺来源说明: {ids}")

    missing_link = [s for s in samples if not s.get("link")]
    if missing_link:
        ids = ", ".join(f"#{s['id']}" for s in missing_link)
        lines.append(f"  ⚠ 缺链接:     {ids}")

    lines.append("=" * 60)

    report_text = "\n".join(lines)
    print(report_text)

    if args.save:
        filename = f"report_{monitor['id']}_{report_date.replace('-', '')}.txt"
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"\n  📄 日报已保存至: {filepath}\n")


def cmd_list(args):
    _ensure_dir()
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]
    if not files:
        print("\n  尚无监测项目。使用 `python monitor.py new` 创建第一个。\n")
        return

    print(f"\n{'='*60}")
    print(f"  监测项目列表")
    print(f"{'='*60}")
    for fname in sorted(files):
        path = os.path.join(DATA_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            m = json.load(f)
        sample_count = len(m.get("samples", []))
        print(f"  {m['id']}  |  {m['product_name']}  |  {m['recall_reason'][:20]}  |  样本{sample_count}条  |  创建于 {m['created_at']}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="产品召回舆情监测助手 — 极简命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python monitor.py new --product "某品牌汽车" --reason "制动系统缺陷" --platforms "微博,抖音,新闻网站" --start 2026-06-01 --end 2026-06-19
  python monitor.py add abc12345 --title "车主集体投诉" --link "https://..." --reposts 500 --comments 200 --sentiment 愤怒 --category 新增爆点 --source "微博热搜"
  python monitor.py report abc12345 --date 2026-06-19 --save
  python monitor.py list
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    p_new = subparsers.add_parser("new", help="新建监测项目")
    p_new.add_argument("--product", required=True, help="产品名称")
    p_new.add_argument("--reason", required=True, help="召回原因")
    p_new.add_argument("--platforms", required=True, help="关注平台，逗号分隔（如: 微博,抖音,新闻网站）")
    p_new.add_argument("--start", required=True, help="监测起始日期 (YYYY-MM-DD)")
    p_new.add_argument("--end", required=True, help="监测截止日期 (YYYY-MM-DD)")

    p_add = subparsers.add_parser("add", help="追加样本")
    p_add.add_argument("monitor_id", help="监测项目编号")
    p_add.add_argument("--title", required=True, help="样本标题")
    p_add.add_argument("--link", default="", help="原始链接")
    p_add.add_argument("--reposts", type=int, default=0, help="转发数")
    p_add.add_argument("--comments", type=int, default=0, help="评论数")
    p_add.add_argument("--sentiment", default="", help="情绪判断（愤怒/担忧/失望/中立/理解/支持）")
    p_add.add_argument("--category", default="", help="分类（新增爆点/主要质疑/官方回应/待核实传言）")
    p_add.add_argument("--source", default="", help="来源说明")

    p_report = subparsers.add_parser("report", help="生成日报")
    p_report.add_argument("monitor_id", help="监测项目编号")
    p_report.add_argument("--date", default="", help="报告日期 (YYYY-MM-DD)，默认今天")
    p_report.add_argument("--save", action="store_true", help="保存为文本文件")

    subparsers.add_parser("list", help="列出所有监测项目")

    args = parser.parse_args()

    if args.command == "new":
        cmd_new(args)
    elif args.command == "add":
        cmd_add(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
