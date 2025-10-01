import re
import hashlib
import time
import aiohttp
import asyncio

from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict, Any
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from app.utils.config_loader import config
from app.utils.logger import setup_logging

# 初始化日志配置
logger = setup_logging()


async def load_documents_from_urls(urls: List[str]) -> List[Dict[str, Any]]:
    """
    从URL列表加载文档并分割处理
    所有配置参数必须从 .env 获取

    返回:
    - 文档字典列表: [{
        "id": str,
        "content": str,
        "metadata": {
            "source": str,
            "chunk_index": int,
            "total_chunks": int
        }
    }]
    """
    # 从配置获取所有参数
    max_retries = config.URL_MAX_RETRIES
    retry_delay = config.URL_RETRY_DELAY
    chunk_size = config.URL_CHUNK_SIZE
    chunk_overlap = config.URL_CHUNK_OVERLAP
    max_concurrent = config.URL_MAX_CONCURRENT
    timeout = config.URL_TIMEOUT

    # 记录使用的配置
    logger.info(f"URL加载配置: max_retries={max_retries}, retry_delay={retry_delay}, "
                f"chunk_size={chunk_size}, chunk_overlap={chunk_overlap}, "
                f"max_concurrent={max_concurrent}, timeout={timeout}")

    # 创建文本分割器
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "；", " ", "．", "?", "!", ";"]
    )

    results = []
    semaphore = asyncio.Semaphore(max_concurrent)
    session_timeout = aiohttp.ClientTimeout(total=timeout)

    async def fetch_url(session, url):
        nonlocal results
        async with semaphore:
            content = None
            for attempt in range(1, max_retries + 1):
                try:
                    start_time = time.time()
                    async with session.get(url) as response:
                        if response.status == 200:
                            # 检测内容类型
                            content_type = response.headers.get('Content-Type', '')
                            if 'text/html' in content_type:
                                html_content = await response.text()
                                # 使用BeautifulSoup提取文本
                                soup = BeautifulSoup(html_content, 'html.parser')
                                content = soup.get_text(separator=' ', strip=True)
                            else:
                                content = await response.text()

                            duration = time.time() - start_time
                            logger.info(f"成功获取URL内容: {url} (大小: {len(content)}字节, 耗时: {duration:.2f}s)")
                            break
                        else:
                            logger.warning(
                                f"URL返回非200状态: {url}, 状态码: {response.status}, 尝试 {attempt}/{max_retries}")
                except Exception as e:
                    logger.warning(f"URL获取失败: {url}, 尝试 {attempt}/{max_retries}, 错误: {str(e)}")

                # 如果不是最后一次尝试，则等待重试延迟
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)

            # 处理获取的内容
            if content:
                try:
                    # 清理多余空白
                    cleaned_content = re.sub(r'\s+', ' ', content).strip()
                    # 分割文本
                    documents = splitter.create_documents([cleaned_content])
                    chunks = [doc.page_content for doc in documents]

                    # 为每个块创建文档
                    for idx, chunk in enumerate(chunks):
                        # 生成唯一ID: URL哈希 + 块索引
                        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                        doc_id = f"url_{url_hash}_chunk_{idx}"

                        results.append({
                            "id": doc_id,
                            "content": chunk,
                            "metadata": {
                                "source": url,
                                "chunk_index": idx,
                                "total_chunks": len(chunks)
                            }
                        })
                except Exception as e:
                    logger.error(f"内容处理失败: {url}, 错误: {str(e)}")

    async with aiohttp.ClientSession(
            timeout=session_timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AI-Assistant/1.0)"}
    ) as session:
        # 创建所有URL的获取任务
        tasks = []
        for url in urls:
            # 验证URL格式
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                logger.warning(f"跳过无效URL: {url}")
                continue

            tasks.append(fetch_url(session, url))

        # 并行执行所有任务
        await asyncio.gather(*tasks)

    logger.info(f"URL处理完成: URL数={len(urls)} -> 文档块数={len(results)}")
    return results