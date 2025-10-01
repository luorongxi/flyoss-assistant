from pydantic import BaseModel, Field
from app.tools.base_tool import BaseTool
from datetime import datetime, timedelta
from app.utils import UserContext
from typing import Dict, Any, Type
from .utils import make_dingtalk_request, get_dingtalk_union_id


class DingTalkWorkLogInput(BaseModel):
    """钉钉日志创建输入模型"""
    content: str = Field(..., description="日志内容")
    duration: float = Field(1.0, description="工作时间(小时)", gt=0)
    log_date: str = Field(..., description="日志日期，格式: YYYY-MM-DD")


class DingTalkCreateWorkLogTool(BaseTool):
    """创建钉钉工作日志 - 当需要记录工作日志时使用此工具"""
    name: str = "dingtalk_create_work_log"
    description: str = "创建钉钉工作日志"
    args_schema: Type[BaseModel] = DingTalkWorkLogInput

    def _run(self, content: str, duration: float, log_date: str) -> Dict[str, Any]:
        try:
            user_id = UserContext.get_user()
            log_date_obj = datetime.strptime(log_date, '%Y-%m-%d')
            start_time = int(log_date_obj.replace(hour=9).timestamp() * 1000)
            end_time = int((log_date_obj + timedelta(hours=duration)).timestamp() * 1000)

            payload = {
                "userId": user_id,
                "content": content,
                "recordDate": int(log_date_obj.timestamp() * 1000),
                "startTime": start_time,
                "endTime": end_time
            }

            result = make_dingtalk_request(
                endpoint="/attendance/workRecords",
                method="POST",
                json_data=payload
            )

            return {
                "success": True,
                "record_id": result.get("id"),
                "content": result.get("content"),
                "date": log_date
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"工作日志创建失败: {str(e)}"
            }