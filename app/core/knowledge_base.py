import asyncio
import hashlib  # 添加哈希模块用于ID转换

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct
from typing import List, Dict, Any
from app.utils import config, setup_logging
from app.schemas import KnowledgeResult
from app.services import llm_service

# 初始化日志配置
logger = setup_logging()


class KnowledgeBase:
    """基于Qdrant的知识库系统"""

    def __init__(self):
        self.client = QdrantClient(
            host=config.QDRANT_HOST,
            port=config.QDRANT_PORT,
            api_key=config.QDRANT_API_KEY or None,
            prefer_grpc=True
        )
        self.collection_name = config.KNOWLEDGE_COLLECTION
        self.dimension_size = config.DIMENSION_SIZE
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """确保知识库集合存在"""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if self.collection_name in collection_names:
                logger.info(f"知识库集合已存在: {self.collection_name}")
                return

            # 创建新集合
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.dimension_size,
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"创建新的知识库集合: {self.collection_name}")
        except Exception as e:
            logger.exception(f"确保集合存在失败: {str(e)}")
            raise RuntimeError(f"知识库初始化失败: {str(e)}")

    def _str_to_int_id(self, str_id: str) -> int:
        """将字符串ID转换为64位整数ID"""
        # 使用MD5哈希确保唯一性，取前16位十六进制转换为整数
        hex_hash = hashlib.md5(str_id.encode()).hexdigest()[:16]
        return int(hex_hash, 16)  # 64位整数

    async def add_document(self, document: Dict[str, Any]):
        """添加文档到知识库"""
        try:
            # 生成文本嵌入
            content = document.get("content", "")
            if not content:
                logger.warning("尝试添加空内容文档")
                return

            # 转换ID为整数格式
            str_id = document["id"]
            int_id = self._str_to_int_id(str_id)

            embedding = await llm_service.get_embeddings(content)

            # 创建点结构 - 使用整数ID
            point = PointStruct(
                id=int_id,  # 使用转换后的整数ID
                vector=embedding,
                payload=document
            )

            # 上传到Qdrant
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                points=[point],
                wait=True
            )

            if operation_info.status == "completed":
                logger.info(f"文档已添加到知识库: ID={str_id} (映射为 {int_id})")
            else:
                logger.error(f"文档添加失败: ID={str_id}, 状态={operation_info.status}")
        except Exception as e:
            logger.exception(f"添加文档失败: ID={document.get('id', 'unknown')}, 错误={str(e)}")
            raise

    def add_document_sync(self, document: Dict[str, Any]):
        """同步添加文档到知识库"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.add_document(document))
        except Exception as e:
            logger.error(f"同步添加文档失败: {str(e)}")
        finally:
            loop.close()

    async def retrieve(self, query: str, top_k: int = 3, score_threshold: float = 0.7) -> List[KnowledgeResult]:
        """检索相关知识"""
        try:
            if not query:
                return []

            # 生成查询嵌入
            query_embedding = await llm_service.get_embeddings(query)

            # 执行相似度搜索
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=score_threshold
            )

            # 转换为标准格式 - 从payload获取原始ID
            knowledge_results = []
            for result in results:
                # 注意：这里使用payload中的原始ID，而不是点ID
                knowledge_results.append(KnowledgeResult(
                    id=result.payload.get("id", ""),  # 原始字符串ID
                    content=result.payload.get("content", ""),
                    metadata=result.payload.get("metadata", {}),
                    score=result.score
                ))

            logger.info(f"知识检索完成: 查询='{query[:50]}...', 结果数={len(knowledge_results)}")
            return knowledge_results
        except Exception as e:
            logger.exception(f"知识检索失败: 查询='{query}', 错误={str(e)}")
            return []

    def retrieve_sync(self, query: str, top_k: int = 3, score_threshold: float = 0.7) -> List[KnowledgeResult]:
        """同步检索相关知识"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.retrieve(query, top_k, score_threshold))
        finally:
            loop.close()


# 全局知识库实例
knowledge_base = KnowledgeBase()