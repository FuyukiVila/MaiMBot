import os
import sqlite3
from typing import Dict, Any, List, Optional, Tuple, Union
import json
from threading import Lock

class SqliteCollection:
    def __init__(self, db_path: str, collection_name: str):
        self.db_path = db_path
        self.collection_name = collection_name
        self.lock = Lock()
        self._ensure_table_exists()
        self._indexes = {}  # 存储索引信息

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table_exists(self):
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 检查表是否存在
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{self.collection_name}'")
            if cursor.fetchone() is None:
                # 创建表
                cursor.execute(f"""
                CREATE TABLE {self.collection_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document TEXT NOT NULL
                )
                """)
                conn.commit()

                # 创建索引表
                index_table_name = f"{self.collection_name}_indexes"
                cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {index_table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    index_name TEXT NOT NULL,
                    fields TEXT NOT NULL,
                    unique_index INTEGER NOT NULL
                )
                """)
                conn.commit()
            conn.close()

    def insert_one(self, document: Dict[str, Any]) -> str:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 将文档转换为JSON字符串
            doc_json = json.dumps(document)
            
            # 插入数据
            cursor.execute(f"INSERT INTO {self.collection_name} (document) VALUES (?)", (doc_json,))
            conn.commit()
            
            # 获取最后插入的ID
            inserted_id = cursor.lastrowid
            conn.close()
            
            # 返回插入的ID
            return str(inserted_id)

    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 由于SQLite没有JSON查询能力，我们需要获取所有文档并在Python中进行过滤
            cursor.execute(f"SELECT document FROM {self.collection_name}")
            results = cursor.fetchall()
            conn.close()
            
            # 在Python中进行查询
            for row in results:
                doc = json.loads(row['document'])
                match = True
                for key, value in query.items():
                    # 简单的等值查询
                    if key not in doc or doc[key] != value:
                        match = False
                        break
                    
                if match:
                    return doc
            
            return None

    def find(self, query: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if query is None:
            query = {}
            
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取所有文档
            cursor.execute(f"SELECT document FROM {self.collection_name}")
            results = cursor.fetchall()
            conn.close()
            
            # 在Python中进行过滤
            docs = []
            for row in results:
                doc = json.loads(row['document'])
                
                if not query:  # 如果没有查询条件，添加所有文档
                    docs.append(doc)
                    continue
                
                # 处理查询条件
                match = True
                for key, value in query.items():
                    # 处理比较操作符
                    if isinstance(value, dict) and all(k.startswith('$') for k in value.keys()):
                        for op, v in value.items():
                            if op == '$lt':
                                if key not in doc or not (doc[key] < v):
                                    match = False
                                    break
                            elif op == '$gt':
                                if key not in doc or not (doc[key] > v):
                                    match = False
                                    break
                            # 可以添加更多操作符支持
                    else:
                        # 简单等值查询
                        if key not in doc or doc[key] != value:
                            match = False
                            break
                
                if match:
                    docs.append(doc)
            
            return docs

    def update_one(self, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        # 这里为简单起见，仅实现全文档替换的更新
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取所有文档
            cursor.execute(f"SELECT id, document FROM {self.collection_name}")
            results = cursor.fetchall()
            
            updated_count = 0
            for row in results:
                doc_id = row['id']
                doc = json.loads(row['document'])
                
                # 检查是否匹配查询条件
                match = True
                for key, value in query.items():
                    if key not in doc or doc[key] != value:
                        match = False
                        break
                
                if match:
                    # 更新文档
                    if '$set' in update:
                        for k, v in update['$set'].items():
                            doc[k] = v
                    else:
                        # 将update直接作为文档替换
                        doc = update
                    
                    # 更新数据库
                    cursor.execute(
                        f"UPDATE {self.collection_name} SET document = ? WHERE id = ?", 
                        (json.dumps(doc), doc_id)
                    )
                    updated_count += 1
                    break  # 只更新第一个匹配的文档
            
            conn.commit()
            conn.close()
            return updated_count

    def delete_many(self, query: Dict[str, Any]) -> int:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取所有文档
            cursor.execute(f"SELECT id, document FROM {self.collection_name}")
            results = cursor.fetchall()
            
            deleted_ids = []
            for row in results:
                doc_id = row['id']
                doc = json.loads(row['document'])
                
                # 检查是否匹配查询条件
                match = True
                for key, value in query.items():
                    # 处理比较操作符
                    if isinstance(value, dict) and all(k.startswith('$') for k in value.keys()):
                        for op, v in value.items():
                            if op == '$lt':
                                if key not in doc or not (doc[key] < v):
                                    match = False
                                    break
                            # 可以添加更多操作符支持
                    else:
                        # 简单等值查询
                        if key not in doc or doc[key] != value:
                            match = False
                            break
                
                if match:
                    deleted_ids.append(doc_id)
            
            # 删除匹配的文档
            if deleted_ids:
                placeholders = ','.join(['?'] * len(deleted_ids))
                cursor.execute(f"DELETE FROM {self.collection_name} WHERE id IN ({placeholders})", deleted_ids)
                conn.commit()
                deleted_count = len(deleted_ids)
            else:
                deleted_count = 0
            
            conn.close()
            return deleted_count
    
    def drop_indexes(self):
        """删除所有索引（MongoDB兼容方法）"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取索引表名
            index_table_name = f"{self.collection_name}_indexes"
            
            # 检查索引表是否存在
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{index_table_name}'")
            if cursor.fetchone() is not None:
                # 清空索引表
                cursor.execute(f"DELETE FROM {index_table_name}")
                conn.commit()
            
            # 清空内存中的索引记录
            self._indexes = {}
            
            conn.close()
            return True
    
    def create_index(self, keys: Union[str, List[Tuple[str, int]]], unique: bool = False):
        """创建索引（MongoDB兼容方法）"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取索引表名
            index_table_name = f"{self.collection_name}_indexes"
            
            # 确保索引表存在
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {index_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                index_name TEXT NOT NULL,
                fields TEXT NOT NULL,
                unique_index INTEGER NOT NULL
            )
            """)
            
            # 处理索引键
            if isinstance(keys, str):
                # 如果是字符串，转换为元组
                keys_list = [(keys, 1)]
            else:
                keys_list = keys
            
            # 生成索引名
            index_fields = "_".join([f"{k}_{d}" for k, d in keys_list])
            index_name = f"{self.collection_name}_{index_fields}_idx"
            
            # 将索引信息存储到索引表中
            cursor.execute(
                f"INSERT INTO {index_table_name} (index_name, fields, unique_index) VALUES (?, ?, ?)",
                (index_name, json.dumps(keys_list), 1 if unique else 0)
            )
            
            conn.commit()
            conn.close()
            
            # 在内存中记录索引
            self._indexes[index_name] = {
                "keys": keys_list,
                "unique": unique
            }
            
            return index_name


class SqliteDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._collections = {}
        
        # 确保db目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 初始化连接以创建数据库文件
        conn = sqlite3.connect(db_path)
        conn.close()

    def __getattr__(self, name):
        if name not in self._collections:
            self._collections[name] = SqliteCollection(self.db_path, name)
        return self._collections[name]

    def __getitem__(self, key):
        if key not in self._collections:
            self._collections[key] = SqliteCollection(self.db_path, key)
        return self._collections[key]

    def list_collection_names(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '%_indexes'")
        collections = [row[0] for row in cursor.fetchall()]
        conn.close()
        return collections

    def create_collection(self, name):
        if name not in self._collections:
            self._collections[name] = SqliteCollection(self.db_path, name)
        return self._collections[name]


class DBWrapper:
    """数据库代理类，保持接口兼容性同时实现懒加载。"""
    def __init__(self):
        self._db = None

    def _get_db(self):
        if self._db is None:
            db_path = os.path.join(os.getcwd(), 'db', 'maimbot.db')
            self._db = SqliteDatabase(db_path)
        return self._db

    def __getattr__(self, name):
        return getattr(self._get_db(), name)

    def __getitem__(self, key):
        return self._get_db()[key]


# 全局数据库访问点
db = DBWrapper()
