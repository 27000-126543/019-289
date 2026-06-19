import argparse
import csv
import json
import os
import sys
import hashlib
from datetime import datetime, date, timedelta

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

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

STATUS_MAP = {
    "待核实": "待核实", "已核验": "已核验", "已采用": "已采用",
    "pending": "待核实", "verified": "已核验", "adopted": "已采用",
    "未核实": "待核实", "核实中": "待核实", "已确认": "已核验",
}

VALID_STATUSES = {"待核实", "已核验", "已采用"}


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
                  source_note, collector, platform, status_raw, existing_samples):
    sentiment = SENTIMENT_MAP.get(sentiment_raw.strip(), sentiment_raw.strip())
    category = CATEGORY_MAP.get(category_raw.strip(), category_raw.strip())
    status = STATUS_MAP.get(status_raw.strip(), status_raw.strip()) if status_raw.strip() else "待核实"

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
        "status": status,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    warnings = []
    warnings.extend(_check_duplicates(sample, existing_samples))

    valid_categories = {"新增爆点", "主要质疑", "官方回应", "待核实传言"}
    if category not in valid_categories:
        warnings.append(
            f"分类「{category}」不在标准分类中，请使用：{', '.join(valid_categories)}"
        )

    if status not in VALID_STATUSES:
        warnings.append(
            f"状态「{status}」不在标准状态中，请使用：{', '.join(VALID_STATUSES)}"
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
        print(f'       --sentiment 愤怒 --category 新增爆点 --platform 微博 --collector 张三 --status 已核验\n')
        sys.exit(1)

    sample, warnings = _build_sample(
        args.title, args.link, args.reposts, args.comments,
        args.sentiment, args.category, args.source,
        args.collector, args.platform, args.status, monitor["samples"]
    )

    monitor["samples"].append(sample)
    _save_monitor(monitor)

    print(f"\n  ✅ 样本 #{sample['id']} 已追加到监测项目 {monitor['id']}")
    print(f"     状态:   {sample['status']}")
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


def _parse_csv_line(parts):
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
        "status": parts[9] if len(parts) > 9 else "",
    }
    return result


def _parse_text_block(text):
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if not lines:
        return []

    import io
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []

    header = [h.strip() for h in rows[0]]
    results = []
    for parts in rows[1:]:
        if not parts or not parts[0].strip():
            continue
        row = {}
        for i, key in enumerate(header):
            row[key] = parts[i].strip() if i < len(parts) else ""
        results.append(row)
    return results


def _batch_add_from_csv(monitor, args):
    default_collector = args.collector or ""
    default_platform = args.platform or ""
    default_status = args.status or ""

    path = args.from_csv
    if not os.path.exists(path):
        print(f"\n  ❌ CSV 文件不存在: {path}\n")
        sys.exit(1)

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows_raw = [row for row in reader if any(cell.strip() for cell in row)]

    if not rows_raw:
        print("\n  ❌ CSV 文件为空\n")
        sys.exit(1)

    rows = []
    header_keywords = {"title", "标题", "link", "链接", "情绪", "分类", "sentiment", "category", "status", "状态"}
    first_line_lower = ",".join(rows_raw[0]).lower()
    has_header = any(kw in first_line_lower for kw in header_keywords)

    if has_header:
        header = [h.strip() for h in rows_raw[0]]
        for parts in rows_raw[1:]:
            row = {}
            for i, key in enumerate(header):
                row[key] = parts[i].strip() if i < len(parts) else ""
            rows.append(row)
    else:
        for parts in rows_raw:
            parsed = _parse_csv_line([p.strip() for p in parts])
            if parsed:
                rows.append(parsed)

    _process_batch_import(monitor, rows, default_collector, default_platform, default_status)


def _batch_add_from_text(monitor, args):
    default_collector = args.collector or ""
    default_platform = args.platform or ""
    default_status = args.status or ""

    text = args.from_text
    if not text.strip():
        print("\n  ❌ 文本内容为空\n")
        sys.exit(1)

    rows = _parse_text_block(text)
    if not rows:
        print("\n  ❌ 未能解析出有效数据，请确保第一行为字段名\n")
        sys.exit(1)

    _process_batch_import(monitor, rows, default_collector, default_platform, default_status)


def _process_batch_import(monitor, rows, default_collector, default_platform, default_status=""):
    success = []
    duplicates = []
    missing_source = []
    missing_platform = []
    missing_collector = []
    invalid_category = []
    invalid_status = []
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
        status = row.get("status") or row.get("状态") or default_status

        if not title:
            errors.append(f"第 {idx} 行：缺少标题，已跳过")
            continue

        sample, warnings = _build_sample(
            title, link, reposts, comments,
            sentiment, category, source_note,
            collector, platform, status, monitor["samples"]
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

        if sample["status"] not in VALID_STATUSES:
            invalid_status.append(f"#{len(monitor['samples']) + 1}")

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
    if invalid_status:
        print(f"  ⚠ 状态待修正: {', '.join(invalid_status)}")

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


def _filter_samples_by_status(samples, status_filter):
    if not status_filter:
        return samples
    include = set()
    exclude = set()
    for s in status_filter.split(","):
        s = s.strip()
        if s.startswith("!") or s.startswith("！"):
            exclude.add(s[1:].strip())
        else:
            include.add(s)
    filtered = []
    for s in samples:
        status = s.get("status", "待核实")
        if exclude and status in exclude:
            continue
        if include and status not in include:
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

    if args.status:
        samples = _filter_samples_by_status(samples, args.status)

    if not samples:
        if args.today:
            print(f"\n  今日暂无符合条件的样本。\n")
        else:
            print(f"\n  所选条件下暂无样本。\n")
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
    if args.status:
        filter_info += f" | 状态: {args.status}"
    if args.top:
        filter_info += f" | TOP {args.top} 高互动"
    lines.append(filter_info)

    platform_stats = {}
    for s in samples:
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

    status_stats = {}
    for s in samples:
        st = s.get("status", "待核实")
        status_stats[st] = status_stats.get(st, 0) + 1
    if status_stats:
        st_items = sorted(status_stats.items(), key=lambda x: x[1], reverse=True)
        st_str = ", ".join(f"{k} {v}条" for k, v in st_items)
        lines.append(f"  状态分布:   {st_str}")

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
            if s.get("status"):
                status_emoji = {"已核验": "✅", "已采用": "📌", "待核实": "⚠️"}.get(s["status"], "")
                meta_parts.append(f"{status_emoji}{s['status']}")
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
            if s.get("status"):
                status_emoji = {"已核验": "✅", "已采用": "📌", "待核实": "⚠️"}.get(s["status"], "")
                meta_parts.append(f"{status_emoji}{s['status']}")
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


def cmd_edit(args):
    _ensure_dir()
    monitor = _load_monitor(args.monitor_id)

    sample_id = args.sample_id
    sample = next((s for s in monitor["samples"] if s["id"] == sample_id), None)
    if not sample:
        print(f"\n  ❌ 样本 #{sample_id} 不存在\n")
        sys.exit(1)

    if args.status:
        new_status = STATUS_MAP.get(args.status.strip(), args.status.strip())
        if new_status not in VALID_STATUSES:
            print(f"\n  ❌ 无效状态「{args.status}」，请使用：{', '.join(VALID_STATUSES)}\n")
            sys.exit(1)
        sample["status"] = new_status

    if args.category:
        new_category = CATEGORY_MAP.get(args.category.strip(), args.category.strip())
        valid_categories = {"新增爆点", "主要质疑", "官方回应", "待核实传言"}
        if new_category not in valid_categories:
            print(f"\n  ❌ 无效分类「{args.category}」，请使用：{', '.join(valid_categories)}\n")
            sys.exit(1)
        sample["category"] = new_category

    if args.sentiment:
        new_sentiment = SENTIMENT_MAP.get(args.sentiment.strip(), args.sentiment.strip())
        sample["sentiment"] = new_sentiment

    if args.title:
        sample["title"] = args.title.strip()

    if args.link is not None:
        sample["link"] = args.link.strip()

    if args.source is not None:
        sample["source_note"] = args.source.strip()

    if args.platform is not None:
        sample["platform"] = args.platform.strip()

    if args.collector is not None:
        sample["collector"] = args.collector.strip()

    if args.reposts is not None:
        sample["reposts"] = args.reposts

    if args.comments is not None:
        sample["comments"] = args.comments

    sample["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _save_monitor(monitor)

    print(f"\n  ✅ 样本 #{sample_id} 已更新")
    print(f"{'='*50}")
    print(f"  标题:     {sample['title']}")
    print(f"  状态:     {sample['status']}")
    print(f"  分类:     {sample['category']}")
    print(f"  情绪:     {sample['sentiment']}")
    if sample["platform"]:
        print(f"  平台:     {sample['platform']}")
    if sample["collector"]:
        print(f"  采集人:   {sample['collector']}")
    print(f"  互动:     转发{sample['reposts']} 评论{sample['comments']}")
    if sample["source_note"]:
        print(f"  来源:     {sample['source_note']}")
    if "updated_at" in sample:
        print(f"  更新时间: {sample['updated_at']}")
    print(f"{'='*50}\n")


def cmd_weekly(args):
    _ensure_dir()
    monitor = _load_monitor(args.monitor_id)

    all_samples = monitor["samples"]
    if not all_samples:
        print("\n  该监测项目尚无样本。\n")
        sys.exit(0)

    today = date.today()
    default_since = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    default_until = today.strftime("%Y-%m-%d")

    since = _parse_date(args.since or default_since)
    until = _parse_date(args.until or default_until)

    samples = _filter_samples_by_date(all_samples, since, until)
    if not samples:
        print(f"\n  {since} ~ {until} 期间暂无样本。\n")
        sys.exit(0)

    if args.status:
        samples = _filter_samples_by_status(samples, args.status)

    target_platforms = monitor.get("platforms", [])
    valid_categories = ["新增爆点", "主要质疑", "官方回应", "待核实传言"]
    category_labels = {
        "新增爆点": "🔥 新增爆点",
        "主要质疑": "❓ 主要质疑",
        "官方回应": "📢 官方回应",
        "待核实传言": "⚠️ 待核实传言",
    }

    platform_stats = {}
    category_stats = {}
    sentiment_stats = {}
    status_stats = {}
    collector_stats = {}
    top_samples = sorted(samples, key=_engagement, reverse=True)[:5]

    for s in samples:
        plat = s.get("platform", "").strip() or "未标注"
        platform_stats[plat] = platform_stats.get(plat, 0) + 1

        cat = s.get("category", "未分类")
        category_stats[cat] = category_stats.get(cat, 0) + 1

        sent = s.get("sentiment", "未标注")
        sentiment_stats[sent] = sentiment_stats.get(sent, 0) + 1

        st = s.get("status", "待核实")
        status_stats[st] = status_stats.get(st, 0) + 1

        col = s.get("collector", "").strip() or "未标注"
        collector_stats[col] = collector_stats.get(col, 0) + 1

    covered_platforms = set(platform_stats.keys()) & set(target_platforms)
    missing_platforms = [p for p in target_platforms if p not in covered_platforms]

    md = []
    md.append(f"# {monitor['product_name']} 召回舆情周报")
    md.append("")
    md.append(f"> **报告周期**：{since} ~ {until}")
    md.append(f"> **监测主题**：{monitor['recall_reason']}")
    md.append(f"> **样本总数**：{len(samples)} 条")
    md.append("")

    md.append("## 📊 核心数据概览")
    md.append("")
    md.append("| 维度 | 详情 |")
    md.append("|------|------|")
    md.append(f"| 🔥 新增爆点 | {category_stats.get('新增爆点', 0)} 条 |")
    md.append(f"| ❓ 主要质疑 | {category_stats.get('主要质疑', 0)} 条 |")
    md.append(f"| 📢 官方回应 | {category_stats.get('官方回应', 0)} 条 |")
    md.append(f"| ⚠️ 待核实传言 | {category_stats.get('待核实传言', 0)} 条 |")

    plat_str = ", ".join(f"{k} {v}条" for k, v in sorted(platform_stats.items(), key=lambda x: x[1], reverse=True))
    md.append(f"| 📱 平台分布 | {plat_str} |")

    sent_str = ", ".join(f"{k} {v}条" for k, v in sorted(sentiment_stats.items(), key=lambda x: x[1], reverse=True))
    md.append(f"| 😊 情绪分布 | {sent_str} |")

    st_str = ", ".join(f"{k} {v}条" for k, v in sorted(status_stats.items(), key=lambda x: x[1], reverse=True))
    md.append(f"| ✅ 状态分布 | {st_str} |")

    if len(collector_stats) > 1 or "未标注" not in collector_stats:
        col_str = ", ".join(f"{k} {v}条" for k, v in sorted(collector_stats.items(), key=lambda x: x[1], reverse=True))
        md.append(f"| 👥 采集人 | {col_str} |")
    md.append("")

    if missing_platforms:
        md.append(f"> ⚠️ **待补样本平台**：{', '.join(missing_platforms)}")
        md.append("")

    md.append("## 🔝 本周高互动样本 TOP 5")
    md.append("")
    for i, s in enumerate(top_samples, 1):
        total_eng = _engagement(s)
        md.append(f"### {i}. [#{s['id']}] {s['title']}")
        md.append("")
        md.append(f"- **互动量**：转发 {s['reposts']} | 评论 {s['comments']} | 合计 **{total_eng}**")
        meta = []
        if s.get("status"):
            meta.append(s["status"])
        if s.get("sentiment"):
            meta.append(s["sentiment"])
        if s.get("platform"):
            meta.append(s["platform"])
        if meta:
            md.append(f"- **标签**：{' / '.join(meta)}")
        if s.get("source_note"):
            md.append(f"- **来源**：{s['source_note']}")
        if s.get("link"):
            md.append(f"- **链接**：{s['link']}")
        md.append("")

    for cat in valid_categories:
        if cat not in category_stats or category_stats[cat] == 0:
            continue
        cat_samples = [s for s in samples if s.get("category") == cat]
        cat_samples = sorted(cat_samples, key=_engagement, reverse=True)
        md.append(f"## {category_labels.get(cat, cat)}（{len(cat_samples)} 条）")
        md.append("")
        for s in cat_samples[:3]:
            total_eng = _engagement(s)
            status_icon = {"已核验": "✅", "已采用": "📌", "待核实": "⚠️"}.get(s.get("status", ""), "")
            md.append(f"- {status_icon} [#{s['id']}] **{s['title']}**")
            md.append(f"  互动 {total_eng} · {s.get('sentiment', '')} · {s.get('platform', '')}")
            if s.get("source_note"):
                md.append(f"  来源：{s['source_note']}")
        if len(cat_samples) > 3:
            md.append(f"  ... 还有 {len(cat_samples) - 3} 条")
        md.append("")

    md.append("## 📈 趋势分析与建议")
    md.append("")
    md.append("### 本周观察")
    md.append("")
    md.append(f"- 舆情高峰出现在互动量最高的「{top_samples[0]['title'] if top_samples else 'N/A'}」")
    md.append(f"- 情绪以 **{max(sentiment_stats, key=sentiment_stats.get) if sentiment_stats else 'N/A'}** 为主，需重点关注")
    if category_stats.get("待核实传言", 0) > 0:
        md.append(f"- 待核实传言 {category_stats['待核实传言']} 条，建议尽快核实真伪并统一回应口径")
    if missing_platforms:
        md.append(f"- 以下平台样本不足：{', '.join(missing_platforms)}，建议后续重点补充")
    md.append("")
    md.append("### 下周重点")
    md.append("")
    md.append("- [ ] 持续监测舆情热度变化")
    md.append("- [ ] 核对待核实传言的真伪")
    md.append("- [ ] 补充缺失平台的样本")
    md.append("- [ ] 整理官方回应时间线")
    md.append("")

    md.append("---")
    md.append(f"*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    md_text = "\n".join(md)
    print(md_text)

    if args.save or args.markdown:
        filename = f"weekly_{monitor['id']}_{str(since).replace('-', '')}_{str(until).replace('-', '')}"
        if args.status:
            filename += f"_{args.status.replace(',', '_')}"
        filename += ".md"
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_text)
        print(f"\n  📄 周报已保存至: {filepath}\n")


def cmd_assign(args):
    _ensure_dir()
    monitor = _load_monitor(args.monitor_id)

    all_samples = monitor["samples"]
    target_platforms = monitor.get("platforms", [])
    valid_categories = ["新增爆点", "主要质疑", "官方回应", "待核实传言"]

    if not target_platforms:
        print("\n  ❌ 该监测项目尚未设置目标平台，请先编辑项目配置。\n")
        sys.exit(1)

    today = date.today()
    default_since = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    default_until = today.strftime("%Y-%m-%d")

    since = _parse_date(args.since or default_since)
    until = _parse_date(args.until or default_until)

    samples = _filter_samples_by_date(all_samples, since, until)

    if not all_samples:
        print("\n  该监测项目尚无样本。\n")
        sys.exit(0)

    print(f"\n{'='*70}")
    print(f"  👥 采集人分工统计")
    print(f"{'='*70}")
    print(f"  产品:       {monitor['product_name']}")
    print(f"  召回原因:   {monitor['recall_reason']}")
    print(f"  统计周期:   {since} ~ {until}")
    print(f"  目标平台:   {', '.join(target_platforms)}")
    print(f"  目标分类:   {', '.join(valid_categories)}")
    print(f"  样本总数:   {len(samples)}（筛选期）/ {len(all_samples)}（全库）")
    print(f"{'='*70}\n")

    collector_data = {}
    for s in samples:
        col = s.get("collector", "").strip() or "未标注"
        if col not in collector_data:
            collector_data[col] = {
                "total": 0,
                "platforms": set(),
                "categories": set(),
                "statuses": {},
                "avg_engagement": [],
                "samples": []
            }
        collector_data[col]["total"] += 1
        plat = s.get("platform", "").strip()
        if plat:
            collector_data[col]["platforms"].add(plat)
        cat = s.get("category", "")
        if cat:
            collector_data[col]["categories"].add(cat)
        st = s.get("status", "待核实")
        collector_data[col]["statuses"][st] = collector_data[col]["statuses"].get(st, 0) + 1
        collector_data[col]["avg_engagement"].append(_engagement(s))
        collector_data[col]["samples"].append(s)

    all_missing_platforms = set(target_platforms)
    all_missing_categories = set(valid_categories)
    for col_data in collector_data.values():
        all_missing_platforms -= col_data["platforms"]
        all_missing_categories -= col_data["categories"]

    if "未标注" in collector_data and len(collector_data) > 1:
        print(f"  ⚠  {collector_data['未标注']['total']} 条样本未标注采集人，请尽快补充\n")

    for col, data in sorted(collector_data.items()):
        if args.collector and col != args.collector:
            continue

        missing_platforms = set(target_platforms) - data["platforms"]
        missing_categories = set(valid_categories) - data["categories"]

        need_verify = data["statuses"].get("待核实", 0)
        avg_eng = sum(data["avg_engagement"]) // max(len(data["avg_engagement"]), 1)

        print(f"  👤 {col} （合计 {data['total']} 条，平均互动 {avg_eng}）")
        print(f"  {'-'*50}")

        status_parts = []
        for st in ["已核验", "已采用", "待核实"]:
            if data["statuses"].get(st, 0) > 0:
                status_parts.append(f"{st} {data['statuses'][st]}")
        if status_parts:
            print(f"     ✅ 状态:   {', '.join(status_parts)}")

        plat_covered = sorted(data["platforms"] & set(target_platforms))
        if plat_covered:
            print(f"     ✅ 已补平台: {', '.join(plat_covered)}")
        if missing_platforms:
            print(f"     ❌ 缺平台:   {', '.join(sorted(missing_platforms))}")

        cat_covered = sorted(data["categories"] & set(valid_categories))
        if cat_covered:
            print(f"     ✅ 已补分类: {', '.join(cat_covered)}")
        if missing_categories:
            print(f"     ❌ 缺分类:   {', '.join(sorted(missing_categories))}")

        if need_verify > 0:
            print(f"     ⚠  待核实:   {need_verify} 条需核验")

        print()

    if all_missing_platforms or all_missing_categories:
        print(f"{'='*70}")
        print(f"  📋 全局未覆盖项")
        print(f"{'='*70}")
        if all_missing_platforms:
            print(f"  ❌ 全员未覆盖平台: {', '.join(sorted(all_missing_platforms))}")
        if all_missing_categories:
            print(f"  ❌ 全员未覆盖分类: {', '.join(sorted(all_missing_categories))}")
        print()

    print(f"{'='*70}")
    print(f"  🎯 今日分工建议")
    print(f"{'='*70}")

    priority_tasks = []
    for col, data in collector_data.items():
        if col == "未标注":
            continue
        missing_platforms = set(target_platforms) - data["platforms"]
        missing_categories = set(valid_categories) - data["categories"]
        need_verify = data["statuses"].get("待核实", 0)

        if need_verify > 0:
            priority_tasks.append(f"  🔴 {col}: 先核对待核实的 {need_verify} 条样本")
        if missing_platforms:
            for p in sorted(missing_platforms)[:2]:
                priority_tasks.append(f"  🟡 {col}: 补充「{p}」平台的样本")
        if missing_categories:
            for c in sorted(missing_categories)[:1]:
                priority_tasks.append(f"  🟢 {col}: 补充「{c}」分类的样本")

    if not priority_tasks:
        print("  ✅ 所有采集人均已完成目标平台和分类的覆盖！")
    else:
        for task in priority_tasks[:10]:
            print(task)
    print()


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
    print(f"  六个命令：new / add / report / edit / weekly / assign")
    print(f"{'-'*60}")
    print(f"\n  📌 情绪分类（6 种）：")
    print(f"     愤怒 / 担忧 / 失望 / 中立 / 理解 / 支持")
    print(f"     （也支持英文简写：neg/neu/pos）")
    print(f"\n  📌 内容分类（4 种）：")
    print(f"     新增爆点    — 新出现的高热度舆情事件")
    print(f"     主要质疑    — 公众的疑问和追问")
    print(f"     官方回应    — 品牌/监管方的声明")
    print(f"     待核实传言  — 尚未证实的网传信息")
    print(f"\n  📌 样本状态（3 种）：")
    print(f"     待核实  — 默认状态，尚未核验")
    print(f"     已核验  — 已确认内容真实性")
    print(f"     已采用  — 已写入报告/周报")
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
    print(f"\n  2️⃣  追加样本（逐条或批量导入，可带状态）：")
    print(f'     python monitor.py add <监测编号> \\')
    print(f'       --title "多名家长反映婴儿腹泻" \\')
    print(f'       --link "https://weibo.com/..." \\')
    print(f'       --reposts 1200 --comments 856 \\')
    print(f'       --sentiment 愤怒 --category 新增爆点 \\')
    print(f'       --source "微博热搜第3位" --platform 微博 \\')
    print(f'       --collector "张三" --status 已核验')
    print(f"\n     批量导入 CSV（可含状态列）：")
    print(f'     python monitor.py add <监测编号> --from-csv samples.csv')
    print(f"\n  3️⃣  生成日报（按日期和状态筛选）：")
    print(f'     python monitor.py report <监测编号> --today --top 10 --save')
    print(f'     python monitor.py report <监测编号> --status 已核验 --save')
    print(f'     python monitor.py report <监测编号> --status "!待核实"')
    print(f"\n  📋 更多命令：")
    print(f'     edit   <编号> <样本ID> --status 已核验     编辑样本状态/分类等')
    print(f'     weekly <编号> --since 2026-06-12 --save    生成 Markdown 周报')
    print(f'     assign <编号>                              按采集人列出缺项')
    print(f'     list                                       查看所有项目')
    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="产品召回舆情监测助手 — 面向实习生团队的极简命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
📌 情绪分类（6 种）：愤怒 / 担忧 / 失望 / 中立 / 理解 / 支持
📌 内容分类（4 种）：新增爆点 / 主要质疑 / 官方回应 / 待核实传言
📌 样本状态（3 种）：待核实 / 已核验 / 已采用（默认待核实）
📌 平台示例：微博、抖音、小红书、知乎、B站、新闻网站、政府/监管

快速示例:
  # 新建监测项目
  python monitor.py new --product "某品牌婴幼儿奶粉" --reason "阪崎肠杆菌污染风险" \\
       --platforms "微博,抖音,新闻网站,政府/监管" --start 2026-06-01 --end 2026-06-19

  # 单条追加（可带状态）
  python monitor.py add abc12345 --title "多名家长反映婴儿腹泻" \\
       --link "https://..." --reposts 1200 --comments 856 --sentiment 愤怒 \\
       --category 新增爆点 --source "微博热搜" --platform 微博 --collector 张三 --status 已核验

  # 批量导入
  python monitor.py add abc12345 --from-csv samples.csv --collector 张三 --platform 微博
  python monitor.py add abc12345 --from-text "title,link,情绪,分类\\n标题1,url1,愤怒,新增爆点"

  # 生成日报（按日期/状态筛选）
  python monitor.py report abc12345 --today --top 10 --save
  python monitor.py report abc12345 --since 2026-06-15 --until 2026-06-19 --save
  python monitor.py report abc12345 --status 已核验
  python monitor.py report abc12345 --status "!待核实"

  # 编辑样本状态
  python monitor.py edit abc12345 1 --status 已核验
  python monitor.py edit abc12345 2 --category 官方回应 --sentiment 中立

  # 生成周报 Markdown
  python monitor.py weekly abc12345 --save
  python monitor.py weekly abc12345 --since 2026-06-12 --status 已核验 --markdown

  # 分工统计
  python monitor.py assign abc12345
  python monitor.py assign abc12345 --collector 张三

  # 查看项目列表
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
    p_add.add_argument("--status", default="",
                       help="样本状态：待核实/已核验/已采用（默认待核实）")

    p_report = subparsers.add_parser("report", help="生成结构化日报，支持日期和状态筛选")
    p_report.add_argument("monitor_id", help="监测项目编号")
    p_report.add_argument("--date", default="", help="报告日期，默认今天（YYYY-MM-DD）")
    p_report.add_argument("--today", action="store_true", help="只看今日新增样本")
    p_report.add_argument("--since", default="", help="只看此日期之后新增的样本（YYYY-MM-DD）")
    p_report.add_argument("--until", default="", help="只看此日期之前新增的样本（YYYY-MM-DD）")
    p_report.add_argument("--status", default="",
                          help="按状态筛选，如：已核验 / !待核实 / 已核验,已采用")
    p_report.add_argument("--top", type=int, default=0, help="只显示互动量最高的 N 条样本")
    p_report.add_argument("--save", action="store_true", help="同时保存为 txt 文件")

    p_edit = subparsers.add_parser("edit", help="编辑样本字段（状态、分类、情绪等）")
    p_edit.add_argument("monitor_id", help="监测项目编号")
    p_edit.add_argument("sample_id", type=int, help="样本编号，如 1、2、3")
    p_edit.add_argument("--status", default="", help="改为：待核实/已核验/已采用")
    p_edit.add_argument("--category", default="", help="改为：新增爆点/主要质疑/官方回应/待核实传言")
    p_edit.add_argument("--sentiment", default="", help="改为：愤怒/担忧/失望/中立/理解/支持")
    p_edit.add_argument("--title", default="", help="修改标题")
    p_edit.add_argument("--link", default=None, help="修改链接")
    p_edit.add_argument("--source", default=None, help="修改来源说明")
    p_edit.add_argument("--platform", default=None, help="修改平台")
    p_edit.add_argument("--collector", default=None, help="修改采集人")
    p_edit.add_argument("--reposts", type=int, default=None, help="修改转发数")
    p_edit.add_argument("--comments", type=int, default=None, help="修改评论数")

    p_weekly = subparsers.add_parser("weekly", help="生成周报/阶段复盘 Markdown，适合贴进实习周报")
    p_weekly.add_argument("monitor_id", help="监测项目编号")
    p_weekly.add_argument("--since", default="", help="起始日期（YYYY-MM-DD），默认 7 天前")
    p_weekly.add_argument("--until", default="", help="截止日期（YYYY-MM-DD），默认今天")
    p_weekly.add_argument("--status", default="", help="按状态筛选，如：已核验 / !待核实")
    p_weekly.add_argument("--save", action="store_true", help="同时保存为 .md 文件")
    p_weekly.add_argument("--markdown", action="store_true", help="同 --save，保存 Markdown 文件")

    p_assign = subparsers.add_parser("assign", help="按采集人统计缺失的平台和分类，辅助分工")
    p_assign.add_argument("monitor_id", help="监测项目编号")
    p_assign.add_argument("--since", default="", help="统计起始日期（默认昨天）")
    p_assign.add_argument("--until", default="", help="统计截止日期（默认今天）")
    p_assign.add_argument("--collector", default="", help="只看指定采集人")

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
    elif args.command == "edit":
        cmd_edit(args)
    elif args.command == "weekly":
        cmd_weekly(args)
    elif args.command == "assign":
        cmd_assign(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
