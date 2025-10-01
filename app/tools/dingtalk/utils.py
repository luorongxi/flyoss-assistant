import requests
import time
from datetime import datetime
from app.utils import config, setup_logging, UserContext
from typing import Dict, Any, Optional, List, Tuple

# 初始化日志配置
logger = setup_logging()

# 钉钉API基础URL
DINGTALK_API_BASE = "https://api.dingtalk.com/v1.0"
# 用户API基础URL
USER_API_URL = "https://oapi.dingtalk.com"

# 访问令牌缓存
_access_token_cache = {
    "token": None,
    "expires_at": 0  # Unix时间戳
}


def get_dingtalk_access_token() -> str:
    """获取钉钉访问令牌（带缓存和自动刷新机制）"""
    global _access_token_cache

    # 检查缓存是否有效（有效期提前5分钟刷新）
    if _access_token_cache["token"] and time.time() < _access_token_cache["expires_at"] - 300:
        return _access_token_cache["token"]

    url = f"{DINGTALK_API_BASE}/oauth2/accessToken"
    payload = {
        "appKey": config.DINGTALK_APP_KEY,
        "appSecret": config.DINGTALK_APP_SECRET
    }

    try:
        logger.info("请求钉钉访问令牌...")
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()

        data = response.json()
        access_token = data.get("accessToken")
        logger.info(f"钉钉访问令牌获取成功：{access_token}")

        expires_in = data.get("expireIn", 7200)  # 默认7200秒（2小时）

        if not access_token:
            raise ValueError("钉钉访问令牌响应无效")

        # 更新缓存
        _access_token_cache = {
            "token": access_token,
            "expires_at": time.time() + expires_in
        }

        logger.info(f"钉钉访问令牌获取成功，有效期至 {datetime.fromtimestamp(_access_token_cache['expires_at'])}")
        return access_token

    except requests.exceptions.RequestException as e:
        logger.error(f"获取钉钉访问令牌失败: {str(e)}", exc_info=True)
        raise RuntimeError("无法获取钉钉访问令牌")
    except Exception as e:
        logger.error(f"处理钉钉访问令牌失败: {str(e)}", exc_info=True)
        raise RuntimeError(f"处理钉钉访问令牌失败: {str(e)}")


def get_dingtalk_union_id() -> str:
    """获取当前用户的钉钉Union ID"""
    user_id = UserContext.get_user()
    if not user_id:
        raise ValueError("无法获取用户上下文")

    try:
        # 获取访问令牌
        access_token = get_dingtalk_access_token()

        # 调用钉钉用户信息API
        user_response = requests.post(
            url=f"{USER_API_URL}/topapi/v2/user/get?access_token={access_token}",
            headers={
                "Content-Type": "application/json"
            },
            json={
                "userid": user_id
            }
        )
        result = user_response.json().get("result")
        union_id = result.get("unionid")

        if not union_id:
            raise ValueError("钉钉用户信息响应中缺少unionId")

        logger.info(f"用户钉钉Union ID获取成功: {union_id}")
        return union_id

    except requests.exceptions.RequestException as e:
        logger.error(f"获取钉钉用户信息失败: {str(e)}", exc_info=True)
        raise RuntimeError("无法获取钉钉用户信息")
    except Exception as e:
        logger.error(f"处理钉钉用户信息失败: {str(e)}", exc_info=True)
        raise RuntimeError(f"处理钉钉用户信息失败: {str(e)}")


def make_dingtalk_request(
        endpoint: str,
        method: str = "GET",
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        retry_count: int = 2
) -> Dict[str, Any]:
    """
    执行钉钉API请求（带自动重试和错误处理）

    :param endpoint: API端点路径（不包含基础URL）
    :param method: HTTP方法 (GET, POST, PUT, DELETE)
    :param json_data: JSON请求体（用于POST/PUT）
    :param params: 查询参数（用于GET/DELETE）
    :param retry_count: 重试次数（默认2次）
    :return: API响应数据
    """
    # 验证方法
    method = method.upper()
    if method not in ["GET", "POST", "PUT", "DELETE"]:
        raise ValueError(f"不支持的HTTP方法: {method}")

    # 构建完整URL
    url = f"{DINGTALK_API_BASE}{endpoint}"
    headers = {
        "x-acs-dingtalk-access-token": get_dingtalk_access_token(),
        "Content-Type": "application/json"
    }

    # 请求参数
    kwargs = {
        "headers": headers,
        "timeout": 10
    }

    if json_data:
        kwargs["json"] = json_data
    if params:
        kwargs["params"] = params

    # 重试逻辑
    attempts = 0
    last_error = None

    while attempts <= retry_count:
        try:
            logger.info(f"钉钉API请求: {method} {endpoint} (尝试 {attempts + 1}/{retry_count + 1})")

            if method == "GET":
                response = requests.get(url, **kwargs)
            elif method == "POST":
                response = requests.post(url, **kwargs)
            elif method == "PUT":
                response = requests.put(url, **kwargs)
            elif method == "DELETE":
                response = requests.delete(url, **kwargs)

            # 处理响应
            response.raise_for_status()

            # 尝试解析JSON响应
            try:
                result = response.json()
                logger.debug(f"钉钉API响应: {result}")
                return result
            except ValueError:
                # 非JSON响应
                logger.warning(f"钉钉API返回非JSON响应: {response.text[:200]}")
                return {"raw_response": response.text}

        except requests.exceptions.RequestException as e:
            last_error = e
            logger.warning(f"钉钉API请求失败 (尝试 {attempts + 1}): {str(e)}")

            # 如果是401错误，刷新令牌后重试
            if hasattr(e, 'response') and e.response.status_code == 401:
                logger.info("检测到401错误，刷新钉钉访问令牌...")
                # 清除缓存令牌
                global _access_token_cache
                _access_token_cache = {"token": None, "expires_at": 0}
                # 获取新令牌
                get_dingtalk_access_token()
                # 更新请求头
                headers["x-acs-dingtalk-access-token"] = _access_token_cache["token"]

            # 指数退避
            time.sleep(2 ** attempts)

        attempts += 1

    # 所有重试都失败
    error_msg = f"钉钉API请求失败: {method} {endpoint} - {str(last_error)}"
    logger.error(error_msg, exc_info=True)
    raise RuntimeError(error_msg)


def validate_datetime_format(value: str, format: str) -> bool:
    """验证日期时间格式"""
    try:
        datetime.strptime(value, format)
        return True
    except ValueError:
        return False