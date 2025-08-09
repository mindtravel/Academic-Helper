import os
import requests
from tqdm import tqdm
import re
from typing import List, Dict


def download_pdfs(papers: List[Dict], download_dir: str) -> Dict[str, int]:
    """批量下载论文 PDF 到指定目录。

    参数 papers: 每项需包含 {title, pdf_url}
    返回: {"success": 成功数, "failed": 失败数}
    """
    os.makedirs(download_dir, exist_ok=True)
    success = 0
    failed = 0
    for paper in papers:
        pdf_url = paper.get("pdf_url")
        title = paper.get("title", "untitled")
        if not pdf_url:
            print(f"未找到PDF链接: {title}")
            failed += 1
            continue

        clean_title = re.sub(r"[\n\r\t]", " ", title)
        clean_title = re.sub(r"[<>:\"/\\|?*]", "_", clean_title)
        clean_title = re.sub(r"\s+", " ", clean_title).strip()
        filename = (clean_title[:80] or "untitled") + ".pdf"
        filepath = os.path.join(download_dir, filename)

        print(f"下载: {title}")
        try:
            with requests.get(pdf_url, stream=True, timeout=30, proxies={}) as r:
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in tqdm(r.iter_content(chunk_size=8192), desc=filename, unit='KB'):
                        if chunk:
                            f.write(chunk)
            print(f"已保存到: {filepath}\n")
            success += 1
        except Exception as e:
            print(f"下载失败: {e}")
            failed += 1
    return {"success": success, "failed": failed}

