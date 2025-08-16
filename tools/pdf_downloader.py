import os
import requests
from tqdm import tqdm
import re
from typing import List, Dict


def download_pdfs(papers: List[Dict], download_dir: str) -> Dict[str, int]:
    """批量下载论文 PDF 到指定目录。

    参数 papers: 每项需包含 {title, pdf_url}
    返回: {"all_success": 是否全部成功, "failed": 失败原因}
    """
    os.makedirs(download_dir, exist_ok=True)
    all_success = True
    failed = {}
    for paper in papers:
        pdf_url = paper.get("pdf_url")
        title = paper.get("title", "untitled")
        
        if not pdf_url:
            failed[title] = {"PDF url not found"}
            continue

        def clean_pdf_title(raw_title):
            rstr = r"[\/\\\:\*\?\"\<\>\|]"  # 替换Windows文件名非法字符为空格，非法字符'/ \ : * ? " < > |'
            cleaned = re.sub(rstr, " ", raw_title) # 移除首尾空格和多余空格
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            return cleaned[:80] if cleaned else "untitled" # 限制文件名长度（Windows最大255字符，这里设为80）

        clean_title = clean_pdf_title(title)
        filename = clean_title + ".pdf"
        filepath = os.path.join(download_dir, filename)

        try:
            with requests.get(pdf_url, stream=True, timeout=30, proxies={}) as r:
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in tqdm(r.iter_content(chunk_size=8192), desc=filename, unit='KB'):
                        if chunk:
                            f.write(chunk)
        except Exception as e:
            failed[title] = {"download failed"}

            
    return {"all_success": all_success, "failed": failed}

