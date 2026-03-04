# 去重索引管理器
# 管理FIT文件指纹索引，实现去重功能

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional


class IndexManager:
    """去重索引管理器"""

    def __init__(self, index_file: Optional[Path] = None):
        """
        初始化索引管理器

        Args:
            index_file: 索引文件路径，不指定则使用默认路径
        """
        self.index_file = (
            index_file or Path.home() / ".nanobot-runner" / "data" / "index.json"
        )
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        self.index = self._load_index()

    def _load_index(self) -> Dict[str, any]:
        """加载索引文件"""
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {"fingerprints": [], "metadata": {}}
        return {"fingerprints": [], "metadata": {"created": None, "updated": None}}

    def _save_index(self):
        """保存索引文件"""
        self.index["metadata"]["updated"] = str(Path.home())
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)

    def generate_fingerprint(self, metadata: Dict[str, any]) -> str:
        """
        生成文件指纹

        Args:
            metadata: 文件元数据字典

        Returns:
            str: 指纹字符串
        """
        # 提取关键字段
        serial = metadata.get("serial_number", "")
        time_created = metadata.get("time_created", "")
        total_distance = metadata.get("total_distance", 0)
        filename = metadata.get("filename", "")

        # 构建指纹字符串
        fingerprint_str = f"{serial}:{time_created}:{total_distance}:{filename}"

        # 使用SHA256生成哈希
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()

    def exists(self, fingerprint: str) -> bool:
        """
        检查指纹是否已存在

        Args:
            fingerprint: 指纹字符串

        Returns:
            bool: 是否存在
        """
        return fingerprint in self.index.get("fingerprints", [])

    def add(self, fingerprint: str, metadata: Dict[str, any] = None) -> bool:
        """
        添加指纹到索引

        Args:
            fingerprint: 指纹字符串
            metadata: 相关元数据

        Returns:
            bool: 是否成功
        """
        if self.exists(fingerprint):
            return False

        self.index.setdefault("fingerprints", []).append(fingerprint)

        if metadata:
            self.index.setdefault("metadata", {}).setdefault("files", {})[
                fingerprint
            ] = {
                "filename": metadata.get("filename", ""),
                "filepath": metadata.get("filepath", ""),
                "timestamp": str(metadata.get("time_created", "")),
            }

        self._save_index()
        return True

    def remove(self, fingerprint: str) -> bool:
        """
        从索引中移除指纹

        Args:
            fingerprint: 指纹字符串

        Returns:
            bool: 是否成功
        """
        if not self.exists(fingerprint):
            return False

        fingerprints = self.index.get("fingerprints", [])
        fingerprints.remove(fingerprint)

        if fingerprint in self.index.get("metadata", {}).get("files", {}):
            del self.index["metadata"]["files"][fingerprint]

        self._save_index()
        return True

    def get_all_fingerprints(self) -> List[str]:
        """
        获取所有指纹

        Returns:
            list: 指纹列表
        """
        return self.index.get("fingerprints", [])

    def get_file_info(self, fingerprint: str) -> Optional[Dict[str, any]]:
        """
        获取指纹对应的文件信息

        Args:
            fingerprint: 指纹字符串

        Returns:
            dict: 文件信息，不存在返回None
        """
        return self.index.get("metadata", {}).get("files", {}).get(fingerprint)

    def clear(self):
        """清空索引"""
        self.index = {
            "fingerprints": [],
            "metadata": {"created": None, "updated": None},
        }
        self._save_index()
