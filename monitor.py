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
    print(f"         --category 分类 --source \"来源说明\" \\")
    print(f"         --collector 你的名字 --platform 平台")
    print(f"  批量导入: python monitor.py add {monitor_id} --from-csv samples.csv --collector 姓名")
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


def _check_duplicates(sample, existing_samples):
    warnings = []
    for s in existing_samples:
        sim = _title_similarity(s["title"], sample["title"])
        if sim >= 0.8:
            warnings.append(
                f"标题与已有样本 #{s['id']} 高度相似（相似度 {sim:.0%}）：「{s['title'][:30]}…」"
            )
        if sample.get("link") and s.get("link") and sample["link"] == s["link"]:
            warnings.append(f"链接与已有样本 #{s['id']} 完全相同")
    return warnings


def _build_sample(title, link, reposts, comments, sentiment_raw, category_raw,
                  source_note, collector, platform, existing_samples):
    sentiment = SENTIMENT_MAP.get(sentiment_raw.strip(), sentiment_raw.strip())
    category = CATEGORY_MAP.get(category_raw.strip(), category_raw.strip())

    def _safe_int(v):
        try:
            return int(v) if str(v).strip() else 0
        except (ValueError, TypeError):
            return 0

    sample = {
        "id": len(existing_samples) + 1,
        "title": title.strip(),
        "link": link.strip(),
        "reposts": _safe_int(reposts),
        "comments": _safe_int(comments),
        "sentiment": sentiment,
        "category": category,
        "source_note": source_note.strip(),
        "collector": collector.strip() if collector else "",
        "platform": platform.strip() if platform else "",
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    warnings = []
    warnings.extend(_check_duplicates(sample, existing_samples))

    valid_categories = {"新增爆点", "主要质疑", "官方回应", "待核实传言"}
    if category not in valid_categories:
        warnings.append(
            f"分类「{category}」不在标准分类中，请使用：{', '.join(valid_categories)}"
        )

    if not sample["link"]:
        warnings.append("缺少链接，后续核验可能困难")
    if not sample["source_note"]:
        warnings.append("缺少来源说明，请在课堂/周报引用时补充出处")
    if not sample["platform"]:
        warnings.append("缺少平台来源，后续统计可能不全")
    if not sample["collector"]:
        warnings.append("缺少采集人，团队协作时请注明")

    return sample, warnings


def cmd_add(args):
    _ensure_dir()
    monitor = _load_monitor(args.monitor_id)

    if args.from_csv:
        _batch_add_from_csv(monitor, args)
        return
    if args.from_text:
        _batch_add_from_text(monitor, args)
        return

    if not args.title.strip():
        print("\n  ❌ 单条追加样本必须提供 --title 参数\n")
        print(f"     使用示例：")
        print(f'     python monitor.py add {args.monitor_id} --title "标题" --link "https://..." \\')
        print(f'       --sentiment 愤怒 --category 新增爆点 --platform 微博 --collector 张三\n')
        sys.exit(1)

    sample, warnings = _build_sample(
        args.title, args.link, args.reposts, args.comments,
        args.sentiment, args.category, args.source,
        args.collector, args.platform, monitor["samples"]
    )

    monitor["samples"].append(sample)
    _save_monitor(monitor)

    print(f"\n  ✅ 样本 #{sample['id']} 已追加到监测项目 {monitor['id']}")
    if sample["collector"]:
        print(f"     采集人: {sample['collector']}")
    if sample["platform"]:
        print(f"     平台:   {sample['platform']}")
    if warnings:
        print(f"\n  系统提示：")
        for w in warnings:
            print(f"    ⚠ {w}")
    print(f"\n  当前样本总数: {len(monitor['samples'])}")
    print()


def _parse_csv_line(line):
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 3:
        return None
    result = {
        "title": parts[0] if len(parts) > 0 else "",
        "link": parts[1] if len(parts) > 1 else "",
        "reposts": parts[2] if len(parts) > 2 else "0",
        "comments": parts[3] if len(parts) > 3 else "0",
        "sentiment": parts[4] if len(parts) > 4 else "",
        "category": parts[5] if len(parts) > 5 else "",
        "source_note": parts[6] if len(parts) > 6 else "",
        "collector": parts[7] if len(parts) > 7 else "",
        "platform": parts[8] if len(parts) > 8 else "",
    }
    return result


def _parse_text_block(text):
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if not lines:
        return []

    header = [h.strip() for h in lines[0].split(",")]
    results = []
    for line in lines[1:]:
        parts = [p.strip() for p in line.split(",")]
        if not parts or not parts[0]:
            continue
        row = {}
        for i, key in enumerate(header):
            row[key] = parts[i] if i < len(parts) else ""
        results.append(row)
    return results


def _batch_add_from_csv(monitor, args):
    default_collector = args.collector or ""
    default_platform = args.platform or ""

    path = args.from_csv
    if not os.path.exists(path):
        print(f"\n  ❌ CSV 文件不存在: {path}\n")
        sys.exit(1)

    with open(path, "r", encoding="utf-8-sig") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    if not lines:
        print("\n  ❌ CSV 文件为空\n")
        sys.exit(1)

    rows = []
    header_keywords = {"title", "标题", "link", "链接", "情绪", "分类", "sentiment", "category"}
    first_line_lower = lines[0].lower()
    has_header = any(kw in first_line_lower for kw in header_keywords)

    if has_header:
        header = [h.strip() for h in lines[0].split(",")]
        for line in lines[1:]:
            parts = [p.strip() for p in line.split(",")]
            row = {}
            for i, key in enumerate(header):
                row[key] = parts[i] if i < len(parts) else ""
            rows.append(row)
    else:
        for line in lines:
            parsed = _parse_csv_line(line)
            if parsed:
                rows.append(parsed)

    _process_batch_import(monitor, rows, default_collector, default_platform)


def _batch_add_from_text(monitor, args):
    default_collector = args.collector or ""
    default_platform = args.platform or ""

    text = args.from_text
    if not text.strip():
        print("\n  ❌ 文本内容为空\n")
        sys.exit(1)

    rows = _parse_text_block(text)
    if not rows:
        print("\n  ❌ 未能解析出有效数据，请确保第一行为字段名\n")
        sys.exit(1)

    _process_batch_import(monitor, rows, default_collector, default_platform)


def _process_batch_import(monitor, rows, default_collector, default_platform):
    success = []
    duplicates = []
    missing_source = []
    missing_platform = []
    missing_collector = []
    invalid_category = []
    errors = []

    initial_count = len(monitor["samples"])

    for idx, row in enumerate(rows, 1):
        title = row.get("title") or row.get("标题") or ""
        link = row.get("link") or row.get("链接") or ""
        reposts = row.get("reposts") or row.get("转发") or row.get("repost") or 0
        comments = row.get("comments") or row.get("评论") or row.get("comment") or 0
        sentiment = row.get("sentiment") or row.get("情绪") or ""
        category = row.get("category") or row.get("分类") or ""
        source_note = row.get("source") or row.get("source_note") or row.get("来源") or ""
        collector = row.get("collector") or row.get("采集人") or default_collector
        platform = row.get("platform") or row.get("平台") or default_platform

        if not title:
            errors.append(f"第 {idx} 行：缺少标题，已跳过")
            continue

        sample, warnings = _build_sample(
            title, link, reposts, comments,
            sentiment, category, source_note,
            collector, platform, monitor["samples"]
        )

        is_duplicate = any("高度相似" in w or "完全相同" in w for w in warnings)
        if is_duplicate:
            duplicates.append(f"[{idx}] {title[:30]}…")

        if not sample["source_note"]:
            missing_source.append(f"#{len(monitor['samples']) + 1}")

        if not sample["platform"]:
            missing_platform.append(f"#{len(monitor['samples']) + 1}")

        if not sample["collector"]:
            missing_collector.append(f"#{len(monitor['samples']) + 1}")

        if sample["category"] not in {"新增爆点", "主要质疑", "官方回应", "待核实传言"}:
            invalid_category.append(f"#{len(monitor['samples']) + 1}")

        monitor["samples"].append(sample)
        success.append(sample)

    _save_monitor(monitor)

    print(f"\n{'='*60}")
    print(f"  批量导入结果汇总")
    print(f"{'='*60}")
    print(f"  总处理:     {len(rows)} 行")
    print(f"  ✅ 成功导入: {len(success)} 条")
    print(f"  ⚠ 疑似重复: {len(duplicates)} 条")
    print(f"  ❌ 错误跳过: {len(errors)} 条")
    print(f"  当前总数:   {len(monitor['samples'])} 条")
    print(f"{'-'*60}")

    if duplicates:
        print(f"\n  疑似重复条目：")
        for d in duplicates:
            print(f"    {d}")

    if missing_source:
        print(f"\n  ⚠ 缺来源说明: {', '.join(missing_source)}")
    if missing_platform:
        print(f"  ⚠ 缺平台来源: {', '.join(missing_platform)}")
    if missing_collector:
        print(f"  ⚠ 缺采集人:   {', '.join(missing_collector)}")
    if invalid_category:
        print(f"  ⚠ 分类待修正: {', '.join(invalid_category)}")

    if errors:
        print(f"\n  ❌ 错误：")
        for e in errors:
            print(f"    {e}")

    if success:
        print(f"\n  成功导入的样本：")
        for s in success[:10]:
            print(f"    [#{s['id']}] {s['title'][:40]}…")
        if len(success) > 10:
            print(f"    ... 还有 {len(success) - 10} 条")

    print(f"{'='*60}\n")


def _parse_date(datestr):
    if not datestr:
        return None
    try:
        return datetime.strptime(datestr.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _filter_samples_by_date(samples, since, until):
    if not since and not until:
        return samples

    filtered = []
    for s in samples:
        added_str = s.get("added_at", "")[:10]
        added = _parse_date(added_str)
        if not added:
            continue
        if since and added < since:
            continue
        if until and added > until:
            continue
        filtered.append(s)
    return filtered


def _engagement(sample):
    return sample.get("reposts", 0) + sample.get("comments", 0)


def cmd_report(args):
    _ensure_dir()
    monitor = _load_monitor(args.monitor_id)

    all_samples = monitor["samples"]
    if not all_samples:
        print("\n  该监测项目尚无样本，请先追加样本后再生成日报。\n")
        sys.exit(0)

    report_date = args.date or date.today().strftime("%Y-%m-%d")

    since = None
    until = None
    if args.today:
        since = _parse_date(date.today().strftime("%Y-%m-%d"))
        until = since
    else:
        if args.since:
            since = _parse_date(args.since)
        if args.until:
            until = _parse_date(args.until)

    samples = _filter_samples_by_date(all_samples, since, until)
    if not samples:
        if args.today:
            print(f"\n  今日暂无新增样本。\n")
        else:
            print(f"\n  所选日期范围内暂无样本。\n")
        sys.exit(0)

    if args.top:
        samples = sorted(samples, key=_engagement, reverse=True)[:args.top]

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

    for cat in categories_order:
        grouped[cat] = sorted(grouped[cat], key=_engagement, reverse=True)
    uncategorized = sorted(uncategorized, key=_engagement, reverse=True)

    lines = []
    lines.append("=" * 60)
    lines.append(f"  产品召回舆情日报")
    lines.append("=" * 60)
    lines.append(f"  报告日期:   {report_date}")
    lines.append(f"  产品名称:   {monitor['product_name']}")
    lines.append(f"  召回原因:   {monitor['recall_reason']}")
    lines.append(f"  监测周期:   {monitor['date_range']['start']} ~ {monitor['date_range']['end']}")

    filter_info = f"  样本总数:   {len(samples)}（全库 {len(all_samples)}）"
    if args.today:
        filter_info += " | 筛选: 今日新增"
    elif since or until:
        if since and until:
            filter_info += f" | 筛选: {since} ~ {until}"
        elif since:
            filter_info += f" | 筛选: >= {since}"
        elif until:
            filter_info += f" | 筛选: <= {until}"
    if args.top:
        filter_info += f" | TOP {args.top} 高互动"
    lines.append(filter_info)

    platform_stats = {}
    for s in all_samples:
        plat = s.get("platform", "").strip() or "未标注"
        platform_stats[plat] = platform_stats.get(plat, 0) + 1
    target_platforms = monitor.get("platforms", [])
    covered_platforms = set(k for k in platform_stats.keys() if k != "未标注") & set(target_platforms)
    missing_platforms = [p for p in target_platforms if p not in covered_platforms]

    if platform_stats:
        plat_items = sorted(platform_stats.items(), key=lambda x: x[1], reverse=True)
        plat_str = ", ".join(f"{k} {v}条" for k, v in plat_items)
        lines.append(f"  平台分布:   {plat_str}")
    if missing_platforms:
        lines.append(f"  ⚠ 待补样本: {', '.join(missing_platforms)}")

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
            total_eng = s.get("reposts", 0) + s.get("comments", 0)
            lines.append(f"    [#{s['id']}] {s['title']}")
            meta_parts = []
            if s["sentiment"]:
                meta_parts.append(f"情绪: {s['sentiment']}")
            if s.get("platform"):
                meta_parts.append(f"平台: {s['platform']}")
            if s.get("collector"):
                meta_parts.append(f"采集人: {s['collector']}")
            meta_str = " | ".join(meta_parts)
            if meta_str:
                lines.append(f"         {meta_str}")
            lines.append(f"         互动: {engagement}（合计 {total_eng}）")
            if s["link"]:
                lines.append(f"         链接: {s['link']}")
            if s["source_note"]:
                lines.append(f"         来源: {s['source_note']}")

    if uncategorized:
        lines.append(f"\n  📝 【未分类】（{len(uncategorized)} 条）")
        lines.append("-" * 40)
        for s in uncategorized:
            engagement = f"转发{s['reposts']} 评论{s['comments']}"
            total_eng = s.get("reposts", 0) + s.get("comments", 0)
            lines.append(f"    [#{s['id']}] {s['title']}")
            meta_parts = []
            if s["sentiment"]:
                meta_parts.append(f"情绪: {s['sentiment']}")
            if s.get("platform"):
                meta_parts.append(f"平台: {s['platform']}")
            if s.get("collector"):
                meta_parts.append(f"采集人: {s['collector']}")
            meta_str = " | ".join(meta_parts)
            if meta_str:
                lines.append(f"         {meta_str}")
            lines.append(f"         互动: {engagement}（合计 {total_eng}）")

    lines.append("\n" + "=" * 60)

    sentiment_summary = {}
    for s in samples:
        sent = s.get("sentiment", "未标注")
        sentiment_summary[sent] = sentiment_summary.get(sent, 0) + 1

    lines.append(f"  情绪分布:   {', '.join(f'{k} {v}条' for k, v in sentiment_summary.items())}")

    collector_stats = {}
    for s in samples:
        col = s.get("collector", "").strip() or "未标注"
        collector_stats[col] = collector_stats.get(col, 0) + 1
    if len(collector_stats) > 1 or "未标注" not in collector_stats:
        col_items = sorted(collector_stats.items(), key=lambda x: x[1], reverse=True)
        col_str = ", ".join(f"{k} {v}条" for k, v in col_items)
        lines.append(f"  采集人统计: {col_str}")

    missing_source = [s for s in samples if not s.get("source_note")]
    if missing_source:
        ids = ", ".join(f"#{s['id']}" for s in missing_source)
        lines.append(f"  ⚠ 缺来源说明: {ids}")

    missing_link = [s for s in samples if not s.get("link")]
    if missing_link:
        ids = ", ".join(f"#{s['id']}" for s in missing_link)
        lines.append(f"  ⚠ 缺链接:     {ids}")

    missing_platform_samples = [s for s in samples if not s.get("platform")]
    if missing_platform_samples:
        ids = ", ".join(f"#{s['id']}" for s in missing_platform_samples)
        lines.append(f"  ⚠ 缺平台:     {ids}")

    lines.append("=" * 60)

    report_text = "\n".join(lines)
    print(report_text)

    if args.save:
        filename = f"report_{monitor['id']}_{report_date.replace('-', '')}"
        if args.today:
            filename += "_today"
        elif since or until:
            if since:
                filename += f"_from{str(since).replace('-', '')}"
            if until:
                filename += f"_to{str(until).replace('-', '')}"
        if args.top:
            filename += f"_top{args.top}"
        filename += ".txt"
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


def _show_welcome():
    print(f"\n{'='*60}")
    print(f"  📊 产品召回舆情监测助手")
    print(f"{'='*60}")
    print(f"  面向舆情分析实习生和研究生团队的极简工具")
    print(f"  三个核心命令，每天生成规范的召回观察摘要")
    print(f"{'-'*60}")
    print(f"\n  📌 情绪分类（6 种）：")
    print(f"     愤怒 / 担忧 / 失望 / 中立 / 理解 / 支持")
    print(f"     （也支持英文简写：neg/neu/pos）")
    print(f"\n  📌 内容分类（4 种）：")
    print(f"     新增爆点    — 新出现的高热度舆情事件")
    print(f"     主要质疑    — 公众的疑问和追问")
    print(f"     官方回应    — 品牌/监管方的声明")
    print(f"     待核实传言  — 尚未证实的网传信息")
    print(f"\n  📌 平台示例：")
    print(f"     微博、抖音、小红书、知乎、B站、新闻网站、")
    print(f"     微信公众号、政府/监管、豆瓣、论坛/贴吧")
    print(f"{'-'*60}")
    print(f"\n  💡 快速开始 3 步：")
    print(f"\n  1️⃣  新建监测（输入产品信息，得到待检查清单）：")
    print(f'     python monitor.py new \\')
    print(f'       --product "某品牌婴幼儿奶粉" \\')
    print(f'       --reason "阪崎肠杆菌污染风险" \\')
    print(f'       --platforms "微博,抖音,新闻网站,政府/监管" \\')
    print(f'       --start 2026-06-01 --end 2026-06-19')
    print(f"\n  2️⃣  追加样本（逐条或批量导入）：")
    print(f'     python monitor.py add <监测编号> \\')
    print(f'       --title "多名家长反映婴儿腹泻" \\')
    print(f'       --link "https://weibo.com/..." \\')
    print(f'       --reposts 1200 --comments 856 \\')
    print(f'       --sentiment 愤怒 --category 新增爆点 \\')
    print(f'       --source "微博热搜第3位" --platform 微博 \\')
    print(f'       --collector "张三"')
    print(f"\n     批量导入 CSV：")
    print(f'     python monitor.py add <监测编号> --from-csv samples.csv')
    print(f"\n  3️⃣  生成日报（按四类结构化输出）：")
    print(f'     python monitor.py report <监测编号> --today --top 10 --save')
    print(f'     python monitor.py report <监测编号> --since 2026-06-15 --save')
    print(f"\n  📋 查看所有项目：")
    print(f'     python monitor.py list')
    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="产品召回舆情监测助手 — 面向实习生团队的极简命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
📌 情绪分类（6 种）：愤怒 / 担忧 / 失望 / 中立 / 理解 / 支持
📌 内容分类（4 种）：新增爆点 / 主要质疑 / 官方回应 / 待核实传言
📌 平台示例：微博、抖音、小红书、知乎、B站、新闻网站、政府/监管

快速示例:
  python monitor.py new --product "某品牌婴幼儿奶粉" --reason "阪崎肠杆菌污染风险" \\
       --platforms "微博,抖音,新闻网站,政府/监管" --start 2026-06-01 --end 2026-06-19
  python monitor.py add abc12345 --title "多名家长反映婴儿腹泻" \\
       --link "https://..." --reposts 1200 --comments 856 --sentiment 愤怒 \\
       --category 新增爆点 --source "微博热搜" --platform 微博 --collector 张三
  python monitor.py add abc12345 --from-csv samples.csv --collector 张三 --platform 微博
  python monitor.py add abc12345 --from-text "title,link,情绪,分类
家长反映腹泻,https://...,愤怒,新增爆点
监管局通报,https://...,中立,官方回应"
  python monitor.py report abc12345 --today --top 10 --save
  python monitor.py report abc12345 --since 2026-06-15 --until 2026-06-19 --save
  python monitor.py list
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    p_new = subparsers.add_parser("new", help="新建监测项目，生成待检查清单")
    p_new.add_argument("--product", required=True, help="产品名称，如：某品牌婴幼儿奶粉")
    p_new.add_argument("--reason", required=True, help="召回原因，如：阪崎肠杆菌污染风险")
    p_new.add_argument("--platforms", required=True,
                       help="关注平台，逗号分隔。可用: 微博,抖音,小红书,知乎,B站,新闻网站,政府/监管,微信公众号,豆瓣,论坛/贴吧")
    p_new.add_argument("--start", required=True, help="监测起始日期，格式 YYYY-MM-DD")
    p_new.add_argument("--end", required=True, help="监测截止日期，格式 YYYY-MM-DD")

    p_add = subparsers.add_parser("add", help="追加样本（单条或批量导入）")
    p_add.add_argument("monitor_id", help="监测项目编号，如：bd50baec")
    p_add.add_argument("--title", default="", help="样本标题")
    p_add.add_argument("--link", default="", help="原始链接，便于后续核验")
    p_add.add_argument("--reposts", type=int, default=0, help="转发数，默认 0")
    p_add.add_argument("--comments", type=int, default=0, help="评论数，默认 0")
    p_add.add_argument("--sentiment", default="",
                       help="情绪判断：愤怒/担忧/失望/中立/理解/支持（或 neg/neu/pos）")
    p_add.add_argument("--category", default="",
                       help="内容分类：新增爆点/主要质疑/官方回应/待核实传言")
    p_add.add_argument("--source", default="", help="来源说明，如：微博热搜第3位")
    p_add.add_argument("--collector", default="", help="采集人姓名，便于团队协作")
    p_add.add_argument("--platform", default="",
                       help="平台来源：微博/抖音/小红书/知乎/B站/新闻网站/政府/监管 等")
    p_add.add_argument("--from-csv", default="",
                       help="批量导入 CSV 文件路径。字段顺序：标题,链接,转发,评论,情绪,分类,来源,采集人,平台")
    p_add.add_argument("--from-text", default="",
                       help='批量导入多行文本，首行为字段名。如: --from-text "title,link,情绪\\n标题1,url1,愤怒"')

    p_report = subparsers.add_parser("report", help="生成结构化日报，支持日期筛选和高互动排序")
    p_report.add_argument("monitor_id", help="监测项目编号")
    p_report.add_argument("--date", default="", help="报告日期，默认今天（YYYY-MM-DD）")
    p_report.add_argument("--today", action="store_true", help="只看今日新增样本")
    p_report.add_argument("--since", default="", help="只看此日期之后新增的样本（YYYY-MM-DD）")
    p_report.add_argument("--until", default="", help="只看此日期之前新增的样本（YYYY-MM-DD）")
    p_report.add_argument("--top", type=int, default=0, help="只显示互动量最高的 N 条样本")
    p_report.add_argument("--save", action="store_true", help="同时保存为 txt 文件")

    subparsers.add_parser("list", help="列出所有监测项目及样本数量")

    args = parser.parse_args()

    if not args.command:
        _show_welcome()
        return

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
