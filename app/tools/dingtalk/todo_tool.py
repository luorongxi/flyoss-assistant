from pydantic import BaseModel, Field, validator
from app.tools.base_tool import BaseTool
from datetime import datetime
from app.utils import UserContext
from typing import Dict, Any, List, Optional, Type
from .utils import make_dingtalk_request, get_dingtalk_union_id, validate_datetime_format


class TodoCreateInput(BaseModel):
    """钉钉待办创建输入模型"""
    subject: str = Field(..., description="待办事项标题")
    description: str = Field(..., description="待办事项详细内容")
    due_time: str = Field(..., description="截止时间，格式: YYYY-MM-DD HH:mm")
    ding_notify: str = Field("1", description="是否发送钉钉弹框通知：0：不发送，1：发送")
    priority: int = Field(20, description="优先级: 10：较低，20：普通，30：紧急，40：非常紧急")
    executor_id: Optional[str] = Field(None, description="执行者用户ID（默认为当前用户）")

    @validator('due_time')
    def validate_due_time(cls, v):
        if not validate_datetime_format(v, '%Y-%m-%d %H:%M'):
            raise ValueError("截止时间格式无效，请使用 'YYYY-MM-DD HH:mm' 格式")
        return v


class DingTalkTodoCreateTool(BaseTool):
    """创建钉钉待办事项 - 当需要创建新的待办任务时使用此工具"""
    name: str = "dingtalk_todo_create"
    description: str = "创建钉钉待办事项"
    args_schema: Type[BaseModel] = TodoCreateInput

    def _run(
            self,
            subject: str,
            description: str,
            due_time: str,
            ding_notify: str,
            priority: int = 20,
            executor_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            union_id = get_dingtalk_union_id()
            if executor_id:
                executor_id = union_id

            due_timestamp = int(datetime.strptime(due_time, '%Y-%m-%d %H:%M').timestamp() * 1000)

            payload = {
                "subject": subject,
                "description": description,
                "dueTime": due_timestamp,
                "priority": priority,
                "creatorId": union_id,
                "executorId": executor_id,
                "notifyConfigs": {"dingNotify": ding_notify}
            }

            result = make_dingtalk_request(
                endpoint=f"/todo/users/{union_id}/tasks",
                method="POST",
                json_data=payload
            )

            return {
                "success": True,
                "task_id": result.get("id"),
                "subject": result.get("subject"),
                "description": result.get("description"),
                "url": result.get("url"),
                "due_time": result.get("dueTime"),
                "created_time": result.get("createdTime"),
                "modified_time": result.get("modifiedTime"),
                "message": "待办创建成功"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"待办创建失败: {str(e)}"
            }


class TodoDeleteInput(BaseModel):
    """钉钉待办删除输入模型"""
    task_id: str = Field(..., description="待办任务ID")


class DingTalkTodoDeleteTool(BaseTool):
    """删除钉钉待办事项 - 当需要删除现有待办任务时使用此工具"""
    name: str = "dingtalk_todo_delete"
    description: str = "删除钉钉待办事项"
    args_schema: Type[BaseModel] = TodoDeleteInput

    def _run(self, task_id: str) -> Dict[str, Any]:
        try:
            union_id = get_dingtalk_union_id()
            result = make_dingtalk_request(
                endpoint=f"/todo/users/{union_id}/tasks/{task_id}",
                method="DELETE"
            )

            return {
                "success": result.get("result"),
                "requestId": result.get("requestId"),
                "message": "待办删除成功"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"待办删除失败: {str(e)}"
            }


class TodoUpdateInput(BaseModel):
    """钉钉待办更新输入模型"""
    task_id: str = Field(..., description="待办任务ID")
    subject: Optional[str] = Field(None, description="待办事项标题")
    description: Optional[str] = Field(None, description="待办事项详细内容")
    due_time: Optional[str] = Field(None, description="截止时间，格式: YYYY-MM-DD HH:mm")

    @validator('due_time')
    def validate_due_time(cls, v):
        if v and not validate_datetime_format(v, '%Y-%m-%d %H:%M'):
            raise ValueError("截止时间格式无效，请使用 'YYYY-MM-DD HH:mm' 格式")
        return v


class DingTalkTodoUpdateTool(BaseTool):
    """更新钉钉待办事项 - 当需要修改现有待办任务时使用此工具"""
    name: str = "dingtalk_todo_update"
    description: str = "更新钉钉待办事项"
    args_schema: Type[BaseModel] = TodoUpdateInput

    def _run(
            self,
            task_id: str,
            subject: Optional[str] = None,
            description: Optional[str] = None,
            due_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            update_data = {}
            if subject: update_data["subject"] = subject
            if description: update_data["description"] = description
            if due_time:
                update_data["dueTime"] = int(datetime.strptime(due_time, '%Y-%m-%d %H:%M').timestamp() * 1000)

            if not update_data:
                return {"success": False, "error": "没有提供任何更新字段"}

            union_id = get_dingtalk_union_id()
            result = make_dingtalk_request(
                endpoint=f"/todo/users/{union_id}/tasks/{task_id}",
                method="PUT",
                json_data=update_data
            )

            return {
                "success": result.get("result"),
                "message": "待办更新成功"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"待办更新失败: {str(e)}"
            }


class TodoStatusInput(BaseModel):
    """钉钉待办状态更新输入模型"""
    task_id: str = Field(..., description="待办任务ID")
    status: bool = Field(..., description="待办状态: true（完成）, false（未完成）")


class DingTalkTodoUpdateStatusTool(BaseTool):
    """更新钉钉待办执行者状态 - 当需要更改待办任务完成状态时使用此工具"""
    name: str = "dingtalk_todo_update_status"
    description: str = "更新钉钉待办状态"
    args_schema: Type[BaseModel] = TodoStatusInput

    def _run(self, task_id: str, status: bool) -> Dict[str, Any]:
        try:
            if status not in [True, False]:
                raise ValueError("状态必须是 True 或 False")

            union_id = get_dingtalk_union_id()
            payload = {
                "executorStatusList": [{"id": union_id, "isDone": status}]
            }

            result = make_dingtalk_request(
                endpoint=f"/todo/users/{union_id}/tasks/{task_id}/executorStatus",
                method="PUT",
                json_data=payload,
                params={"operatorId": union_id}
            )

            return {
                "success": result.get("result"),
                "message": "待办状态更新成功"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"待办状态更新失败: {str(e)}"
            }


class TodoListInput(BaseModel):
    """钉钉待办列表查询输入模型"""
    status: bool = Field(..., description="待办状态: true（已完成）, false（未完成）")
    next_token: Optional[str] = Field(None, description="分页令牌")


class DingTalkTodoListTool(BaseTool):
    """查询企业下用户待办列表 - 当需要获取待办任务列表时使用此工具"""
    name: str = "dingtalk_todo_list"
    description: str = "查询钉钉待办列表"
    args_schema: Type[BaseModel] = TodoListInput

    def _run(
            self,
            status: bool,
            next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            if status not in [True, False]:
                raise ValueError("状态必须是 True, False")

            union_id = get_dingtalk_union_id()
            payload = {"isDone": status}
            if next_token:
                payload["nextToken"] = next_token

            result = make_dingtalk_request(
                endpoint=f"/todo/users/{union_id}/org/tasks/query",
                method="POST",
                json_data=payload
            )

            tasks = result.get("todoCards", [])
            next_token = result.get("nextToken")

            return {
                "success": True,
                "count": len(tasks),
                "tasks": tasks,
                "next_token": next_token,
                "message": "待办列表查询成功"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"待办列表查询失败: {str(e)}"
            }