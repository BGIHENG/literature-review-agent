#!/usr/bin/env python3
"""
lr-zotero-import / Zotero Web API 导入器

通过 Zotero Web API v3 批量导入文献到 Zotero 云端库。
支持：创建集合 → 批量上传条目 → 可选附加 PDF。

用法：
    # 交互式输入凭证（推荐，不会留在 shell 历史中）：
    python zotero_web_import.py <screened_literature.csv> \
        --collection-name "CRC scRNA Review"

    # 传参方式（不推荐，API Key 会留在 shell 历史中）：
    python zotero_web_import.py <screened_literature.csv> \
        --user-id 12345678 \
        --api-key AbCdEfGhIjKlMnOp \
        --collection-name "CRC scRNA Review"

    # 预览（无需凭证）：
    python zotero_web_import.py <screened_literature.csv> --dry-run

凭证获取：
    1. User ID: https://www.zotero.org/settings/keys 页面顶部显示
    2. API Key: 在同一页面点击 "Create new private key"
       - Description: 随意填写
       - Personal Library: 勾选 Allow library access + Allow write access
"""

import csv
import os
import sys
import json
import time
import argparse
import getpass
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

# ============================================================
# Zotero Web API v3 配置
# ============================================================
ZOTERO_API_BASE = "https://api.zotero.org"
BATCH_SIZE = 50  # Zotero API 单次最多 50 条
RATE_LIMIT_DELAY = 1.0  # 每次请求后的延迟（秒），避免触发速率限制
MAX_RETRIES = 3
RETRY_DELAY = 5  # 重试延迟（秒）


# ============================================================
# HTTP 工具
# ============================================================
def api_request(method, path, api_key, data=None, user_id=None):
    """
    发送 Zotero API 请求。
    返回 (status_code, response_json)
    """
    url = f"{ZOTERO_API_BASE}{path}"

    headers = {
        "Zotero-API-Key": api_key,
        "Content-Type": "application/json",
    }

    if data is not None:
        body = json.dumps(data).encode("utf-8")
    else:
        body = None

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_data = resp.read().decode("utf-8")
                status = resp.status
                # 检查 backoff 头
                backoff = resp.headers.get("Backoff")
                if backoff:
                    time.sleep(float(backoff))
                else:
                    time.sleep(RATE_LIMIT_DELAY)

                if resp_data:
                    try:
                        return status, json.loads(resp_data)
                    except json.JSONDecodeError:
                        return status, resp_data
                return status, None

        except urllib.error.HTTPError as e:
            if e.code == 429:
                # Too Many Requests
                wait = RETRY_DELAY * attempt
                print(f"    [!] Rate limited (429), waiting {wait}s... (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(wait)
                continue
            elif e.code in (502, 503, 504):
                wait = RETRY_DELAY * attempt
                print(f"    [!] Server error {e.code}, retrying in {wait}s... (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(wait)
                continue
            else:
                error_body = e.read().decode("utf-8", errors="replace")
                print(f"    [!] HTTP {e.code}: {error_body[:200]}")
                return e.code, None

        except urllib.error.URLError as e:
            print(f"    [!] Network error: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
                continue
            return 0, None

    print(f"    [!] Max retries ({MAX_RETRIES}) exceeded")
    return 0, None


def verify_credentials(api_key):
    """
    验证 API Key 并返回 user_id。
    GET /keys/<key> 返回 {"userID": ..., "username": ..., "access": {...}}
    """
    status, data = api_request("GET", f"/keys/{api_key}", api_key)

    if status == 200 and isinstance(data, dict):
        user_id = str(data.get("userID", ""))
        username = data.get("username", "")
        access = data.get("access", {})
        has_write = access.get("user", {}).get("write", False)

        if not has_write:
            print(f"[!] API Key 缺少 write 权限。请在 zotero.org/settings/keys 重新创建，勾选 'Allow write access'")
            return None, None

        print(f"[OK] 凭证验证通过: user={username} (ID: {user_id}), write=True")
        return user_id, username
    else:
        print(f"[!] API Key 验证失败 (HTTP {status})")
        return None, None


# ============================================================
# CSV → Zotero Item 转换
# ============================================================
def safe_val(row, key, default=""):
    v = row.get(key, "").strip()
    return v if v else default


def parse_creators(row):
    """
    解析作者字段，返回 Zotero creators 数组。
    CSV 中 FirstAuthor 格式: "Cai" 或 "Cai, J."
    """
    creators = []

    first_author = safe_val(row, "FirstAuthor")
    if first_author:
        # 尝试 "LastName, FirstName" 格式
        if "," in first_author:
            parts = first_author.split(",", 1)
            creators.append({
                "creatorType": "author",
                "lastName": parts[0].strip(),
                "firstName": parts[1].strip(),
            })
        else:
            creators.append({
                "creatorType": "author",
                "lastName": first_author,
                "firstName": "",
            })

    # 如果有 Authors 字段（多条）
    all_authors = safe_val(row, "Authors")
    if all_authors and not creators:
        for au in all_authors.split(";"):
            au = au.strip()
            if not au:
                continue
            if "," in au:
                parts = au.split(",", 1)
                creators.append({
                    "creatorType": "author",
                    "lastName": parts[0].strip(),
                    "firstName": parts[1].strip(),
                })
            else:
                creators.append({
                    "creatorType": "author",
                    "lastName": au,
                    "firstName": "",
                })

    if not creators:
        creators.append({
            "creatorType": "author",
            "lastName": "Unknown",
            "firstName": "",
        })

    return creators


def parse_tags(row):
    """从 Chapter 和 SourceQuery 字段生成标签"""
    tags = []

    chapter = safe_val(row, "Chapter")
    if chapter:
        for ch in chapter.split(";"):
            ch = ch.strip()
            if ch:
                tags.append({"tag": ch})

    source_query = safe_val(row, "SourceQuery")
    if source_query:
        tags.append({"tag": source_query})

    priority = safe_val(row, "ReadPriority", safe_val(row, "Priority"))
    if priority:
        tags.append({"tag": f"priority:{priority}"})

    # 统一标签
    tags.append({"tag": "lr-pipeline"})

    return tags


def csv_row_to_zotero_item(row, collection_key=None):
    """
    将 CSV 行转换为 Zotero API item JSON。
    参考: https://www.zotero.org/support/dev/web_api/v3_types_and_fields
    """
    title = safe_val(row, "Title")
    doi = safe_val(row, "DOI")
    pmid = safe_val(row, "PMID")
    year = safe_val(row, "Year")
    journal = safe_val(row, "Journal")
    volume = safe_val(row, "Volume")
    issue = safe_val(row, "Issue")
    pages = safe_val(row, "Pages")
    abstract = safe_val(row, "Abstract")

    item = {
        "itemType": "journalArticle",
        "title": title if title else "Untitled",
        "creators": parse_creators(row),
        "abstractNote": abstract if abstract else "",
        "publicationTitle": journal if journal else "",
        "volume": volume if volume else "",
        "issue": issue if issue else "",
        "pages": pages if pages else "",
        "date": year if year else "",
        "DOI": doi if doi else "",
        "url": f"https://doi.org/{doi}" if doi else "",
        "tags": parse_tags(row),
        "notes": [],
        "collections": [collection_key] if collection_key else [],
    }

    # Extra 字段放 PMID
    extra_parts = []
    if pmid:
        extra_parts.append(f"PMID: {pmid}")
        item["url"] = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        if doi:
            item["url"] = f"https://doi.org/{doi}"

    chapter = safe_val(row, "Chapter")
    if chapter:
        extra_parts.append(f"Chapter: {chapter}")

    priority = safe_val(row, "ReadPriority", safe_val(row, "Priority"))
    if priority:
        extra_parts.append(f"ReadPriority: {priority}")

    if extra_parts:
        item["extra"] = " | ".join(extra_parts)

    return item


# ============================================================
# 集合创建
# ============================================================
def create_collection(user_id, api_key, collection_name, parent_key=None):
    """
    在 Zotero 中创建一个集合。
    返回 collection_key 或 None。
    """
    data = [
        {
            "name": collection_name,
            "parentCollection": parent_key if parent_key else False,
        }
    ]

    status, resp = api_request(
        "POST",
        f"/users/{user_id}/collections",
        api_key,
        data=data,
    )

    if status == 200 and resp and "success" in resp:
        # resp["success"] = {"0": true/false}
        # resp["success"]["0"] = collectionKey
        successes = resp.get("success", {})
        if successes.get("0"):
            # 在 resp["success"]["0"] 中拿 key... 实际 Zotero 返回在 successful 里
            successful = resp.get("successful", {})
            if "0" in successful:
                return successful["0"].get("key")
        print(f"[!] 集合创建可能失败: {resp}")
        return None
    else:
        print(f"[!] 集合创建失败 (HTTP {status})")
        return None


def find_existing_collection(user_id, api_key, collection_name):
    """查找同名集合，避免重复创建"""
    status, resp = api_request(
        "GET",
        f"/users/{user_id}/collections?limit=100",
        api_key,
    )

    if status == 200 and isinstance(resp, list):
        for coll in resp:
            if coll.get("data", {}).get("name") == collection_name:
                return coll.get("key")
    return None


# ============================================================
# 批量上传
# ============================================================
def batch_upload_items(user_id, api_key, items, dry_run=False):
    """
    批量上传 items 到 Zotero。
    每次 BATCH_SIZE 条。
    返回 (成功数, 失败数, item_key_map) 其中 item_key_map 映射索引到 key。
    """
    if dry_run:
        print(f"\n[DRY RUN] 将上传 {len(items)} 条文献（不实际写入）")
        for i, item in enumerate(items[:3]):
            print(f"  [{i+1}] {item['title'][:70]}...")
        if len(items) > 3:
            print(f"  ... 共 {len(items)} 条")
        return len(items), 0, {}

    total_success = 0
    total_fail = 0
    item_keys = []  # 所有成功上传的 item key

    total_batches = (len(items) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(total_batches):
        start = batch_idx * BATCH_SIZE
        end = min(start + BATCH_SIZE, len(items))
        batch = items[start:end]

        print(f"\n  批次 {batch_idx + 1}/{total_batches}: 第 {start + 1}-{end} 条...")

        # Zotero API 要求用 "template" 形式上传，可以包装为 [{...}, {...}]
        status, resp = api_request(
            "POST",
            f"/users/{user_id}/items",
            api_key,
            data=batch,
        )

        if status == 200 and resp:
            successes = resp.get("success", {})
            successful = resp.get("successful", {})
            failures = resp.get("failed", {})

            batch_success = sum(1 for v in successes.values() if v)
            batch_fail = len(failures)

            total_success += batch_success
            total_fail += batch_fail

            # 收集成功条目的 key
            for idx_str, item_data in successful.items():
                key = item_data.get("key")
                if key:
                    item_keys.append(key)

            print(f"    成功: {batch_success}, 失败: {batch_fail}")

            if failures:
                for idx_str, err_info in failures.items():
                    idx = int(idx_str)
                    title = batch[idx].get("title", "?")[:60]
                    print(f"    [FAIL] #{start + idx + 1}: {title}")
                    if isinstance(err_info, dict):
                        print(f"           原因: {err_info.get('message', str(err_info)[:100])}")
        else:
            total_fail += len(batch)
            print(f"    [!] 批次上传失败 (HTTP {status})")

    return total_success, total_fail, item_keys


# ============================================================
# PDF 附加
# ============================================================
def attach_pdf_to_item(user_id, api_key, item_key, pdf_path):
    """将 PDF 文件作为附件关联到已上传的 Zotero 条目"""
    if not os.path.exists(pdf_path):
        return False

    filename = os.path.basename(pdf_path)
    file_size = os.path.getsize(pdf_path)

    # Step 1: 注册附件条目
    attachment_item = {
        "itemType": "attachment",
        "parentItem": item_key,
        "linkMode": "imported_file",
        "title": filename,
        "contentType": "application/pdf",
        "filename": filename,
    }

    status, resp = api_request(
        "POST",
        f"/users/{user_id}/items",
        api_key,
        data=[attachment_item],
    )

    if status != 200 or not resp or not resp.get("success", {}).get("0"):
        print(f"    [!] 附件注册失败: {filename}")
        return False

    successful = resp.get("successful", {})
    attach_key = successful.get("0", {}).get("key")
    if not attach_key:
        return False

    # Step 2: 获取上传授权
    auth_url = f"{ZOTERO_API_BASE}/users/{user_id}/items/{attach_key}/file"
    auth_headers = {
        "Zotero-API-Key": api_key,
        "Content-Type": "application/x-www-form-urlencoded",
        "If-None-Match": "*",
    }

    auth_data = urllib.parse.urlencode({
        "md5": "",
        "filename": filename,
        "filesize": file_size,
        "mtime": int(os.path.getmtime(pdf_path) * 1000),
    }).encode("utf-8")

    auth_req = urllib.request.Request(
        auth_url,
        data=auth_data,
        headers=auth_headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(auth_req, timeout=30) as auth_resp:
            auth_result = json.loads(auth_resp.read().decode("utf-8"))

        if "upload" not in auth_result:
            print(f"    [!] 上传授权失败: {filename}")
            return False

        # Step 3: 上传到 S3
        upload_info = auth_result["upload"]
        upload_url = upload_info["url"]
        upload_key = upload_info["uploadKey"]
        prefix = upload_info.get("prefix", b"")
        suffix = upload_info.get("suffix", b"")
        content_type = upload_info.get("contentType", "application/pdf")

        with open(pdf_path, "rb") as f:
            file_data = f.read()

        body = prefix + file_data + suffix

        upload_req = urllib.request.Request(
            upload_url,
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        )

        with urllib.request.urlopen(upload_req, timeout=120) as upload_resp:
            if upload_resp.status != 200 and upload_resp.status != 201:
                print(f"    [!] S3 上传失败: {filename}")
                return False

        # Step 4: 注册上传完成
        register_data = urllib.parse.urlencode({"upload": upload_key}).encode("utf-8")
        register_req = urllib.request.Request(
            auth_url,
            data=register_data,
            headers={
                "Zotero-API-Key": api_key,
                "Content-Type": "application/x-www-form-urlencoded",
                "If-None-Match": "*",
            },
            method="POST",
        )

        with urllib.request.urlopen(register_req, timeout=30) as reg_resp:
            if reg_resp.status == 204:
                return True

    except Exception as e:
        print(f"    [!] PDF 上传异常: {filename}: {e}")
        return False

    return False


# ============================================================
# 报告生成
# ============================================================
def generate_report(out_dir, stats, collection_key, collection_name):
    """生成导入报告"""
    report_path = os.path.join(out_dir, "zotero_web_import_report.md")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Zotero Web API 导入报告\n\n")
        f.write(f"**导入时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**集合名称:** {collection_name}\n\n")
        f.write(f"**集合 Key:** `{collection_key}`\n\n")
        f.write(f"**Zotero 链接:** https://www.zotero.org/select/collections/{collection_key}\n\n")

        f.write("## 导入统计\n\n")
        f.write("| 项目 | 数量 |\n")
        f.write("|------|------|\n")
        f.write(f"| CSV 总条目 | {stats['total_csv']} |\n")
        f.write(f"| included 条目 | {stats['total_included']} |\n")
        f.write(f"| 成功上传 | {stats['success']} |\n")
        f.write(f"| 上传失败 | {stats['fail']} |\n")
        f.write(f"| PDF 附件 | {stats['pdfs_attached']} |\n")

        if stats["fail"] > 0:
            f.write("\n## 失败条目\n\n")
            for fail in stats.get("failed_items", []):
                f.write(f"- {fail}\n")

        f.write("\n## 字段完整性\n\n")
        f.write("| 字段 | 已填充 | 缺失 | 完整率 |\n")
        f.write("|------|--------|------|--------|\n")
        for field, count in stats.get("field_completeness", {}).items():
            total = stats["total_included"]
            pct = f"{count / total * 100:.1f}%" if total > 0 else "0%"
            f.write(f"| {field} | {count} | {total - count} | {pct} |\n")

    return report_path


# ============================================================
# 主函数
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="通过 Zotero Web API 批量导入文献",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
凭证获取:
  1. 前往 https://www.zotero.org/settings/keys
  2. 页面顶部显示 User ID
  3. 点击 "Create new private key"
     - 勾选 Allow library access + Allow write access
  4. 将生成的 Key 和 User ID 传入本脚本

示例:
  python zotero_web_import.py screened_literature.csv \\
      --user-id 12345678 \\
      --api-key AbCdEfGhIjKlMnOp \\
      --collection-name "CRC scRNA Review"
        """,
    )
    parser.add_argument("csv", help="screened_literature.csv 路径")
    parser.add_argument("--user-id", required=False, help="Zotero User ID")
    parser.add_argument("--api-key", required=False, help="Zotero API Key (write 权限)")
    parser.add_argument("--collection-name", default="Literature Review Import",
                        help="Zotero 集合名称 (默认: Literature Review Import)")
    parser.add_argument("--attach-pdfs", default=None,
                        help="PDF 目录路径，若提供则自动附加已下载的 PDF")
    parser.add_argument("--dry-run", action="store_true",
                        help="试运行：只显示将要上传的条目，不实际写入")
    parser.add_argument("--outdir", "-o", default=".",
                        help="报告输出目录 (默认当前目录)")
    parser.add_argument("--reuse-collection", default=None,
                        help="复用已有的集合 Key，不创建新集合")

    args = parser.parse_args()

    # --- 验证文件 ---
    if not os.path.exists(args.csv):
        print(f"[ERROR] CSV 文件不存在: {args.csv}")
        sys.exit(1)

    os.makedirs(args.outdir, exist_ok=True)

    # --- 交互式输入凭证（如果未通过命令行提供）---
    if not args.dry_run:
        if not args.api_key:
            print("\n=== Zotero API 凭证 ===")
            print("前往 https://www.zotero.org/settings/keys 获取 User ID 和 API Key")
            print("（输入时 API Key 不回显，不会留在 shell 历史中）\n")

            if not args.user_id:
                args.user_id = input("Zotero User ID: ").strip()

            args.api_key = getpass.getpass("Zotero API Key: ").strip()

        if not args.user_id or not args.api_key:
            print("[ERROR] User ID 和 API Key 均为必填项")
            sys.exit(1)

        # 验证凭证
        print("\n=== 验证 Zotero API 凭证 ===")
        verified_uid, username = verify_credentials(args.api_key)
        if verified_uid is None:
            print("[ERROR] 凭证验证失败，请检查 API Key 和权限设置")
            sys.exit(1)

        # 使用验证后的 user_id（覆盖命令行参数，确保一致）
        user_id = verified_uid
    else:
        user_id = args.user_id or "DRY_RUN"
        print("\n=== DRY RUN 模式（不实际写入）===")

    # --- 读取 CSV ---
    print(f"\n=== 读取文献库: {args.csv} ===")
    included_rows = []
    with open(args.csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if safe_val(row, "ScreenStatus") == "included":
                included_rows.append(row)

    print(f"纳入文献: {len(included_rows)} 篇")

    if not included_rows:
        print("[ERROR] 没有 ScreenStatus = included 的文献")
        sys.exit(1)

    # --- 字段完整性统计 ---
    field_stats = {}
    for field_name, csv_key in [
        ("标题", "Title"), ("DOI", "DOI"), ("PMID", "PMID"),
        ("年份", "Year"), ("期刊", "Journal"), ("卷", "Volume"),
        ("期", "Issue"), ("页码", "Pages"), ("摘要", "Abstract"),
        ("第一作者", "FirstAuthor"), ("章节", "Chapter"),
    ]:
        count = sum(1 for r in included_rows if safe_val(r, csv_key))
        field_stats[field_name] = count

    # --- 创建/复用集合 ---
    collection_key = args.reuse_collection

    if not collection_key and not args.dry_run:
        print(f"\n=== 创建 Zotero 集合: {args.collection_name} ===")

        # 先检查是否已有同名集合
        existing = find_existing_collection(user_id, args.api_key, args.collection_name)
        if existing:
            print(f"[OK] 发现同名集合，复用: {existing}")
            collection_key = existing
        else:
            collection_key = create_collection(user_id, args.api_key, args.collection_name)
            if collection_key:
                print(f"[OK] 集合创建成功: {collection_key}")
            else:
                print("[ERROR] 集合创建失败")
                sys.exit(1)
    elif args.dry_run:
        collection_key = "DRY_RUN_KEY"
        print(f"\n[DRY RUN] 将创建集合: {args.collection_name}")
    else:
        print(f"\n=== 复用已有集合: {collection_key} ===")

    # --- 转换 CSV → Zotero Items ---
    print(f"\n=== 转换 {len(included_rows)} 篇文献为 Zotero 格式 ===")
    zotero_items = []
    for row in included_rows:
        item = csv_row_to_zotero_item(row, collection_key)
        zotero_items.append(item)

    print(f"[OK] 转换完成: {len(zotero_items)} 条")

    # --- 批量上传 ---
    print(f"\n=== 批量上传到 Zotero ===")
    success, fail, item_keys = batch_upload_items(
        user_id, args.api_key, zotero_items, dry_run=args.dry_run
    )

    print(f"\n上传结果: 成功 {success} 篇, 失败 {fail} 篇")

    # --- 附加 PDF（可选）---
    pdfs_attached = 0
    if args.attach_pdfs and not args.dry_run and item_keys:
        pdf_dir = args.attach_pdfs
        print(f"\n=== 附加 PDF 附件 ===")
        print(f"PDF 目录: {pdf_dir}")

        for i, (row, item_key) in enumerate(zip(included_rows, item_keys)):
            pmid = safe_val(row, "PMID")
            doi = safe_val(row, "DOI")

            # 尝试多种文件名格式匹配 PDF
            possible_names = []
            if pmid:
                possible_names.append(f"PMID_{pmid}.pdf")
                possible_names.append(f"{pmid}.pdf")
            if doi:
                safe_doi = doi.replace("/", "_").replace("\\", "_")
                possible_names.append(f"{safe_doi}.pdf")

            pdf_found = False
            for name in possible_names:
                pdf_path = os.path.join(pdf_dir, name)
                if os.path.exists(pdf_path):
                    print(f"  [{i+1}] 附加: {name}")
                    if attach_pdf_to_item(user_id, args.api_key, item_key, pdf_path):
                        pdfs_attached += 1
                        pdf_found = True
                    break

            if not pdf_found and i < 5:
                print(f"  [{i+1}] 无 PDF (PMID={pmid})")

    # --- 生成报告 ---
    stats = {
        "total_csv": len(included_rows),
        "total_included": len(included_rows),
        "success": success,
        "fail": fail,
        "pdfs_attached": pdfs_attached,
        "field_completeness": field_stats,
    }

    report_path = generate_report(args.outdir, stats, collection_key, args.collection_name)

    print(f"\n=== 完成 ===")
    print(f"报告: {report_path}")
    if not args.dry_run and collection_key != "DRY_RUN_KEY":
        print(f"Zotero 链接: https://www.zotero.org/select/collections/{collection_key}")
        print(f"同步到桌面端: 打开 Zotero → 点击右上角同步按钮")


if __name__ == "__main__":
    main()
