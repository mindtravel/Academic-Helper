import os
import json
from typing import Dict, Optional

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = ".config"):
        self.config_file = config_file
        self.config = {}
        self.load_config()
    
    def load_config(self) -> bool:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        # 跳过注释和空行
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            self.config[key.strip()] = value.strip()
                return True
            else:
                print(f"配置文件 {self.config_file} 不存在")
                return False
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return False
    
    def get(self, key: str, default: str = "") -> str:
        """获取配置值"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: str) -> None:
        """设置配置值"""
        self.config[key] = value
        
    def get_proxy_url(self) -> str:
        """获取网络代理地址"""
        return self.get("PROXY_URL")    
    
    def get_deepseek_key(self) -> str:
        """获取DeepSeek API Key"""
        return self.get("DEEPSEEK_API_KEY")
    
    def get_openai_key(self) -> str:
        """获取OpenAI API Key"""
        return self.get("OPENAI_API_KEY")
    
    def get_zotero_key(self) -> str:
        """获取Zotero API Key"""
        return self.get("ZOTERO_API_KEY")
    
    def get_zotero_user_id(self) -> str:
        """获取Zotero用户ID"""
        return self.get("ZOTERO_USER_ID")
    
    def get_default_query(self) -> str:
        """获取默认搜索查询"""
        return self.get("DEFAULT_QUERY", "搜索近五年强化学习的论文")
    
    def get_default_download_dir(self) -> str:
        """获取默认下载目录"""
        return self.get("DEFAULT_DOWNLOAD_DIR", "./downloads")
    
    def get_default_zotero_collection(self) -> str:
        """获取默认Zotero文件夹名称"""
        return self.get("DEFAULT_ZOTERO_COLLECTION", "学术智能Agent")
    
    def setup_environment(self) -> None:
        """设置环境变量"""
        for key, value in self.config.items():
            if value:  # 只设置非空值
                os.environ[key] = value
    
    def validate_config(self) -> Dict[str, bool]:
        """验证配置"""
        validation = {
            "proxy_url": bool(self.get_proxy_url()),
            "deepseek": bool(self.get_deepseek_key()),
            "openai": bool(self.get_openai_key()),
            "zotero": bool(self.get_zotero_key() and self.get_zotero_user_id())
        }
        return validation
    
    def print_config_status(self) -> None:
        """打印配置状态"""
        print("=== API配置状态 ===")
        validation = self.validate_config()
        print(f"网络代理: {'✅ 已配置' if validation['proxy_url'] else '❌ 未配置'}")
        
        print(f"DeepSeek API: {'✅ 已配置' if validation['deepseek'] else '❌ 未配置'}")
        print(f"OpenAI API: {'✅ 已配置' if validation['openai'] else '❌ 未配置'}")
        print(f"Zotero API: {'✅ 已配置' if validation['zotero'] else '❌ 未配置'}")
        
        print(f"\n默认搜索查询: {self.get_default_query()}")
        print(f"默认下载目录: {self.get_default_download_dir()}")
        print(f"默认Zotero文件夹: {self.get_default_zotero_collection()}")

# 全局配置管理器实例
config_manager = ConfigManager()

def load_api_config():
    """加载API配置到环境变量"""
    config_manager.setup_environment()

def get_config(key: str, default: str = "") -> str:
    """获取配置值"""
    return config_manager.get(key, default) 