import requests
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Optional, Union
from config_manager import load_api_config, get_config

# 加载API配置
load_api_config()

class ZoteroIntegration:
    def __init__(self, api_key: str, user_id: str, library_type: str = "user"):
        """
        初始化Zotero集成
        
        Args:
            api_key: Zotero API Key
            user_id: Zotero用户ID
            library_type: "user" 或 "group"
        """
        self.api_key = api_key
        self.user_id = user_id
        self.library_type = library_type
        self.base_url = f"https://api.zotero.org/{library_type}s/{user_id}"
        self.headers = {
            "Zotero-API-Key": api_key,
            "Zotero-API-Version": "3",
            "Content-Type": "application/json"
        }
    
    def get_collections(self) -> List[Dict]:
        """获取所有文件夹"""
        try:
            response = requests.get(f"{self.base_url}/collections", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取Zotero文件夹失败: {e}")
            return []
    
    def create_collection(self, name: str, parent_collection: Optional[str] = None) -> Optional[str]:
        """创建新文件夹"""
        try:
            data = [{
                "name": name,
                "parentCollection": parent_collection
            }]
            response = requests.post(
                f"{self.base_url}/collections",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            print(f"成功创建文件夹: {name}")
            
            # 修复：正确解析Zotero API返回结构
            if isinstance(result, dict):
                # 检查success字段
                if "success" in result and "0" in result["success"]:
                    return result["success"]["0"]
                # 检查successful字段
                elif "successful" in result and "0" in result["successful"]:
                    return result["successful"]["0"].get("key")
                else:
                    print(f"意外的返回结果格式: {result}")
                    return None
            elif isinstance(result, list) and len(result) > 0:
                return result[0].get("key")
            else:
                print(f"意外的返回结果格式: {result}")
                return None
        except Exception as e:
            print(f"创建文件夹失败: {e}")
            return None
    
    def _add_single_item(self, paper: Dict, collection_key: Optional[str] = None) -> bool:
        """添加单条论文到Zotero（内部使用，带容错）。"""
        # 标题
        title = str(paper.get("title", "")).strip()
        if not title:
            # 从链接回退生成标题
            fallback_url = paper.get("pdf_url") or paper.get("page_url") or ""
            if fallback_url:
                base = fallback_url.strip().rstrip('/').split('/')[-1]
                title = base[:120] or "(无标题)"
        # 作者标准化
        authors_raw = paper.get("authors")
        if not authors_raw:
            # 兼容单字段作者字符串
            single = paper.get("author") or paper.get("authors_text") or ""
            if isinstance(single, str) and single.strip():
                authors_raw = [s.strip() for s in re.split(r"[,;]", single) if s.strip()]
            else:
                authors_raw = []
        creators = [
            {"creatorType": "author", "firstName": "", "lastName": str(a).strip()}
            for a in authors_raw if str(a).strip()
        ]

        # 摘要/日期/来源/链接
        abstract_note = str(paper.get("summary", "")).strip()
        date_str = str(paper.get("published", "")).strip()
        source = str(paper.get("source", "")).strip() or "web"
        url = paper.get("pdf_url") or paper.get("page_url") or ""

        # 构建论文数据
        item_data = [{
            "itemType": "journalArticle",
            "title": title or "(无标题)",
            "creators": creators,
            "abstractNote": abstract_note,
            "date": date_str,
            "publicationTitle": source,
            "url": url,
            "tags": [
                {"tag": source},
                {"tag": "学术智能Agent"}
            ]
        }]

        # 如果指定了文件夹，直接在创建时设置collections
        if collection_key:
            item_data[0]["collections"] = [collection_key]

        # 发送请求
        response = requests.post(
            f"{self.base_url}/items",
            headers=self.headers,
            json=item_data
        )
        response.raise_for_status()
        result = response.json()

        if isinstance(result, dict) and "success" in result and result["success"]:
            print(f"成功添加论文到Zotero: {title or '(无标题)'}")
            return True
        else:
            print(f"添加论文失败: {result}")
            return False

    def add_item(self, paper: Union[Dict, List[Dict]], collection_key: Optional[str] = None) -> bool:
        """添加论文到Zotero。支持单条或多条，返回是否至少成功添加一条。"""
        try:
            if isinstance(paper, list):
                success = 0
                total = len(paper)
                for p in paper:
                    if self._add_single_item(p or {}, collection_key=collection_key):
                        success += 1
                print(f"批量添加完成：{success}/{total}")
                return success > 0
            else:
                return self._add_single_item(paper or {}, collection_key=collection_key)
        except Exception as e:
            print(f"添加论文到Zotero失败: {e}")
            return False
    
    def move_item_to_collection(self, item_key: str, collection_key: str) -> bool:
        """将论文移动到指定文件夹"""
        try:
            # 首先获取item的当前信息
            response = requests.get(f"{self.base_url}/items/{item_key}", headers=self.headers)
            response.raise_for_status()
            item_info = response.json()
            
            # 获取当前版本
            current_version = item_info.get("version", 0)
            
            # 构建更新数据，包含itemType和版本信息
            data = [{
                "itemType": item_info.get("data", {}).get("itemType", "journalArticle"),
                "collections": [collection_key],
                "version": current_version
            }]
            
            response = requests.patch(
                f"{self.base_url}/items/{item_key}",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"移动论文到文件夹失败: {e}")
            return False
    
    def find_or_create_collection(self, collection_name: str) -> Optional[str]:
        """查找或创建文件夹"""
        collections = self.get_collections()
        
        # 查找现有文件夹
        for collection in collections:
            if collection["data"]["name"] == collection_name:
                print(f"找到现有文件夹: {collection_name}")
                return collection["key"]
        
        # 创建新文件夹
        print(f"创建新文件夹: {collection_name}")
        return self.create_collection(collection_name)


def _generate_collection_name(papers: List[Dict]) -> str:
    """基于首篇论文标题自动生成集合名，避免回退到默认值。"""
    if papers:
        title0 = str(papers[0].get("title", "")).strip()
        if not title0:
            # 回退：用链接末段
            fallback_url = papers[0].get("pdf_url") or papers[0].get("page_url") or ""
            if fallback_url:
                title0 = fallback_url.strip().rstrip('/').split('/')[-1]
        if title0:
            # 提取前若干个可见字符/词作为主题
            title0 = re.sub(r"[\n\r\t]", " ", title0)
            title0 = re.sub(r"\s+", " ", title0).strip()
            # 中文场景：截取前 16 个字符；英文：截取前 6 个词
            if re.search(r"[\u4e00-\u9fff]", title0):
                base = title0[:16]
            else:
                words = title0.split()
                base = " ".join(words[:6])
            date_part = datetime.now().strftime("%Y%m%d")
            return f"{base} 调研 {date_part}"
    # 兜底
    return f"自动收藏 {datetime.now().strftime('%Y%m%d')}"


def save_papers_to_zotero(papers: List[Dict], collection_name: str = None) -> bool:
    """将论文保存到Zotero（若未提供集合名则自动生成）。"""
    if collection_name is None or not str(collection_name).strip():
        collection_name = _generate_collection_name(papers)

    api_key = get_config("ZOTERO_API_KEY")
    user_id = get_config("ZOTERO_USER_ID")
    if not api_key or not user_id:
        print("请配置Zotero API：")
        print("- 在 .api_config 中设置 ZOTERO_API_KEY")
        print("- 在 .api_config 中设置 ZOTERO_USER_ID")
        print("\n或者运行以下命令进行配置：")
        print("python debug/setup_zotero.py")
        return False

    try:
        zotero = ZoteroIntegration(api_key, user_id)
        collection_key = zotero.find_or_create_collection(collection_name)
        if not collection_key:
            print("无法创建或找到Zotero文件夹")
            return False

        success_count = 0
        for paper in papers:
            if zotero.add_item(paper, collection_key):
                success_count += 1

        print(f"成功添加 {success_count}/{len(papers)} 篇论文到Zotero文件夹: {collection_name}")
        return success_count > 0
    except Exception as e:
        print(f"Zotero集成失败: {e}")
        return False

