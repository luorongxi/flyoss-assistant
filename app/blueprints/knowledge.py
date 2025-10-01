import asyncio
import uuid
import re

from flask import request
from urllib.parse import urlparse
from flask_restx import Namespace, Resource, fields
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.core import knowledge_base
from app.utils import config, setup_logging, load_documents_from_urls

# 初始化日志配置
logger = setup_logging()

# 创建命名空间
knowledge_ns = Namespace('knowledge', description='知识库管理操作')

# 定义数据模型
document_model = knowledge_ns.model('Document', {
    'content': fields.String(required=True, description='文档内容'),
    'metadata': fields.Raw(description='元数据', default={}),
    'doc_id': fields.String(description='文档ID')
})

url_upload_model = knowledge_ns.model('UrlUpload', {
    'urls': fields.List(fields.String, required=True, description='URL列表')
})

upload_response_model = knowledge_ns.model('UploadResponse', {
    'success': fields.Boolean(description='操作状态'),
    'doc_id': fields.String(description='文档ID'),
    'message': fields.String(description='消息'),
    'error': fields.String(description='错误信息', default=None),
    'details': fields.String(description='错误详情', default=None)
})

search_request_model = knowledge_ns.model('SearchRequest', {
    'query': fields.String(required=True, description='搜索查询'),
    'top_k': fields.Integer(description='结果数量', default=3),
    'score_threshold': fields.Float(description='分数阈值', default=0.7)
})

search_result_model = knowledge_ns.model('SearchResult', {
    'id': fields.String(description='文档ID'),
    'content': fields.String(description='文档内容'),
    'score': fields.Float(description='匹配分数'),
    'metadata': fields.Raw(description='元数据')
})

search_response_model = knowledge_ns.model('SearchResponse', {
    'success': fields.Boolean(description='操作状态'),
    'query': fields.String(description='查询内容'),
    'results': fields.List(fields.Nested(search_result_model))
})

knowledge_status_model = knowledge_ns.model('KnowledgeStatus', {
    'collection': fields.String(description='集合名称'),
    'status': fields.String(description='状态'),
    'vectors_count': fields.Integer(description='向量数量'),
    'indexed_vectors_count': fields.Integer(description='已索引向量数量'),
    'points_count': fields.Integer(description='点数量')
})


@knowledge_ns.route('/upload')
class DocumentUpload(Resource):
    @knowledge_ns.doc('upload_document')
    @knowledge_ns.expect(document_model)
    @knowledge_ns.response(200, '文档上传成功', upload_response_model)
    @knowledge_ns.response(400, '无效请求')
    @knowledge_ns.response(500, '服务器内部错误')
    def post(self):
        """上传文档到知识库"""
        try:
            data = request.json
            content = data.get('content')
            metadata = data.get('metadata', {})
            doc_id = data.get('doc_id')

            if not content:
                return {
                    "success": False,
                    "error": "缺少必填字段: content"
                }, 400

            # 生成文档ID
            base_doc_id = doc_id or str(uuid.uuid4())

            # 从配置获取文本分割参数
            chunk_size = getattr(config, 'DOCUMENT_CHUNK_SIZE', 1000)
            chunk_overlap = getattr(config, 'DOCUMENT_CHUNK_OVERLAP', 200)

            # 创建文本分割器
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", "。", "！", "？", "；", " ", "．", "?", "!", ";"]
            )

            # 清理多余空白
            cleaned_content = re.sub(r'\s+', ' ', content).strip()

            # 分割文本
            documents = splitter.create_documents([cleaned_content])
            chunks = [doc.page_content for doc in documents]

            # 如果只有一个块，直接添加整个文档
            if len(chunks) == 1:
                document = {
                    "id": base_doc_id,
                    "content": chunks[0],
                    "metadata": metadata
                }

                # 添加到知识库
                knowledge_base.add_document_sync(document)

                return {
                    "success": True,
                    "doc_id": base_doc_id,
                    "message": "文档已添加到知识库",
                    "chunks_count": 1
                }

            # 为每个块创建文档并添加到知识库
            processed_count = 0
            chunk_ids = []

            for idx, chunk in enumerate(chunks):
                # 生成块ID
                chunk_id = f"{base_doc_id}_chunk_{idx}"
                chunk_ids.append(chunk_id)

                # 创建块文档对象
                chunk_doc = {
                    "id": chunk_id,
                    "content": chunk,
                    "metadata": {
                        **metadata,
                        "document_id": base_doc_id,
                        "chunk_index": idx,
                        "total_chunks": len(chunks)
                    }
                }

                # 添加到知识库
                knowledge_base.add_document_sync(chunk_doc)
                processed_count += 1

            logger.info(f"文档分割处理完成: 原文档ID={base_doc_id}, 分割为{len(chunks)}个块, 成功添加{processed_count}个块")

            return {
                "success": True,
                "doc_id": base_doc_id,
                "chunk_ids": chunk_ids,
                "chunks_count": len(chunks),
                "message": f"文档已分割为{len(chunks)}个片段并添加到知识库"
            }
        except Exception as e:
            logger.exception(f"文档上传失败: {str(e)}")
            return {
                "success": False,
                "error": "服务器内部错误"
            }, 500


@knowledge_ns.route('/upload_from_urls')
class UrlUpload(Resource):
    @knowledge_ns.doc('upload_from_urls')
    @knowledge_ns.expect(url_upload_model)
    @knowledge_ns.response(200, 'URL文档上传成功', upload_response_model)
    @knowledge_ns.response(400, '无效请求')
    @knowledge_ns.response(500, '服务器内部错误')
    def post(self):
        """从URL列表加载文档并添加到知识库"""
        try:
            data = request.json
            urls = data.get('urls', [])

            if not urls:
                return {
                    "success": False,
                    "error": "URL列表不能为空"
                }, 400

            # 安全过滤URL（仅允许http/https协议）
            filtered_urls = []
            for url in urls:
                # 确保URL是字符串
                url_str = str(url).strip()
                if not url_str:
                    continue

                parsed = urlparse(url_str)
                if parsed.scheme not in ['http', 'https']:
                    logger.warning(f"跳过非HTTP(S)协议URL: {url_str}")
                    continue
                filtered_urls.append(url_str)

            if not filtered_urls:
                return {
                    "success": False,
                    "error": "没有有效的URL可处理"
                }, 400

            # 调用异步函数加载并分割文档
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(
                    load_documents_from_urls(urls=filtered_urls)
                )

                # 添加到知识库（同步方式）
                processed_count = 0
                for doc in results:
                    try:
                        knowledge_base.add_document_sync(doc)
                        processed_count += 1
                    except Exception as e:
                        logger.error(f"添加文档失败 (ID: {doc.get('id', 'unknown')}): {str(e)}")

                return {
                    "success": True,
                    "total_urls": len(filtered_urls),
                    "processed_chunks": processed_count,
                    "message": f"成功处理 {len(results)} 个文档片段"
                }
            finally:
                loop.close()
        except Exception as e:
            logger.exception(f"URL文档处理失败: {str(e)}")
            return {
                "success": False,
                "error": "服务器内部错误"
            }, 500


@knowledge_ns.route('/search')
class KnowledgeSearch(Resource):
    @knowledge_ns.doc('search_knowledge')
    @knowledge_ns.expect(search_request_model)
    @knowledge_ns.response(200, '搜索成功', search_response_model)
    @knowledge_ns.response(400, '无效请求')
    @knowledge_ns.response(500, '服务器内部错误')
    def post(self):
        """在知识库中搜索"""
        try:
            data = request.json
            query = data.get('query')
            top_k = data.get('top_k', 3)
            score_threshold = data.get('score_threshold', 0.7)

            if not query or not isinstance(query, str):
                return {
                    "success": False,
                    "error": "缺少或无效的查询参数"
                }, 400

            # 执行搜索
            results = knowledge_base.retrieve_sync(
                query=query,
                top_k=top_k,
                score_threshold=score_threshold
            )

            # 转换为字典
            results_data = [result.dict() for result in results]

            return {
                "success": True,
                "query": query,
                "results": results_data
            }
        except Exception as e:
            logger.exception(f"知识库搜索失败: {str(e)}")
            return {
                "success": False,
                "error": "服务器内部错误"
            }, 500


@knowledge_ns.route('/status')
class KnowledgeStatus(Resource):
    @knowledge_ns.doc('knowledge_status')
    @knowledge_ns.response(200, '成功获取知识库状态', knowledge_status_model)
    @knowledge_ns.response(500, '服务器内部错误')
    def get(self):
        """获取知识库状态"""
        try:
            # 获取集合信息
            collection_info = knowledge_base.client.get_collection(
                knowledge_base.collection_name
            )

            return {
                "collection": knowledge_base.collection_name,
                "status": "active",
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count
            }
        except Exception as e:
            logger.exception(f"获取知识库状态失败: {str(e)}")
            return {
                "success": False,
                "error": "服务器内部错误"
            }, 500