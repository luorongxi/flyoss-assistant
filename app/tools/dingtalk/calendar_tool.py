from pydantic import BaseModel, Field, validator
from app.tools.base_tool import BaseTool
from datetime import datetime
from app.utils import UserContext
from typing import Dict, Any, List, Optional, Type
from .utils import make_dingtalk_request, get_dingtalk_union_id, validate_datetime_format


class CalendarEventInput(BaseModel):
    """日历事件基础输入模型"""
    summary: str = Field(..., description="日程标题")
    description: Optional[str] = Field(None, description="日程描述")
    start_time: str = Field(..., description="开始时间，格式: YYYY-MM-DDTHH:mm:ss+08:00")
    end_time: str = Field(..., description="结束时间，格式: YYYY-MM-DDTHH:mm:ss+08:00")
    location: Optional[str] = Field(None, description="地点")
    attendees: Optional[List[str]] = Field(None, description="参与者用户ID列表")
    reminder_method: str = Field("dingtalk", description="提醒方式: dingtalk（钉钉内提醒）")
    reminder_minutes: int = Field(30, description="提醒时间（分钟）", ge=0)
    is_all_day: bool = Field(False, description="是否全天事件")

    @validator('start_time', 'end_time')
    def validate_datetime(cls, v):
        if not validate_datetime_format(v, '%Y-%m-%dT%H:%M:%S%z'):
            raise ValueError("时间格式无效，请使用 'YYYY-MM-DDTHH:mm:ss+08:00' 格式")
        return v


class DingTalkCalendarCreateTool(BaseTool):
    """创建钉钉日程 - 当需要创建新的日历时使用此工具"""
    name: str = "dingtalk_calendar_create"
    description: str = "创建钉钉日程"
    args_schema: Type[BaseModel] = CalendarEventInput

    def _run(
            self,
            summary: str,
            start_time: str,
            end_time: str,
            description: Optional[str] = None,
            location: Optional[str] = None,
            attendees: Optional[List[str]] = None,
            reminder_method: str = "dingtalk",
            reminder_minutes: int = 30,
            is_all_day: bool = False
    ) -> Dict[str, Any]:
        try:
            union_id = get_dingtalk_union_id()
            payload = {
                "summary": summary,
                "start": {"dateTime": start_time, "timeZone": "Asia/Shanghai"},
                "end": {"dateTime": end_time, "timeZone": "Asia/Shanghai"},
                "isAllDay": is_all_day,
                "reminders": [{
                    "method": reminder_method,
                    "minutes": reminder_minutes
                }]
            }

            if description:
                payload["description"] = description
            if location:
                payload["location"] = {"displayName": location}
            if attendees:
                payload["attendees"] = [{"id": uid} for uid in attendees]

            result = make_dingtalk_request(
                endpoint=f"/calendar/users/{union_id}/calendars/primary/events",
                method="POST",
                json_data=payload
            )

            return {
                "success": True,
                "event_id": result.get("id"),
                "summary": result.get("summary"),
                "htmlLink": result.get("htmlLink")
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"日程创建失败: {str(e)}"
            }


class CalendarEventUpdateInput(CalendarEventInput):
    """日历事件更新输入模型"""
    event_id: str = Field(..., description="日程事件ID")


class DingTalkCalendarUpdateTool(BaseTool):
    """更新钉钉日程 - 当需要修改现有日历时使用此工具"""
    name: str = "dingtalk_calendar_update"
    description: str = "更新钉钉日程"
    args_schema: Type[BaseModel] = CalendarEventUpdateInput

    def _run(
            self,
            event_id: str,
            summary: str,
            start_time: str,
            end_time: str,
            description: Optional[str] = None,
            location: Optional[str] = None,
            attendees: Optional[List[str]] = None,
            reminder_minutes: int = 30,
            is_all_day: bool = False
    ) -> Dict[str, Any]:
        try:
            union_id = get_dingtalk_union_id()
            payload = {
                "summary": summary,
                "start": {"dateTime": start_time, "timeZone": "Asia/Shanghai"},
                "end": {"dateTime": end_time, "timeZone": "Asia/Shanghai"},
                "isAllDay": is_all_day,
                "reminders": [{"minutes": reminder_minutes}]
            }

            if description:
                payload["description"] = description
            if location:
                payload["location"] = {"displayName": location}
            if attendees:
                payload["attendees"] = [{"id": uid} for uid in attendees]

            result = make_dingtalk_request(
                endpoint=f"/calendar/users/{union_id}/calendars/primary/events/{event_id}",
                method="PUT",
                json_data=payload
            )

            return {
                "success": True,
                "event_id": result.get("id"),
                "summary": result.get("summary"),
                "htmlLink": result.get("htmlLink")
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"日程更新失败: {str(e)}"
            }


class CalendarEventIdInput(BaseModel):
    """日程事件ID输入模型"""
    event_id: str = Field(..., description="日程事件ID")


class DingTalkCalendarGetTool(BaseTool):
    """查询单个钉钉日程详情 - 当需要获取特定日程详细信息时使用此工具"""
    name: str = "dingtalk_calendar_get"
    description: str = "查询钉钉日程详情"
    args_schema: Type[BaseModel] = CalendarEventIdInput

    def _run(self, event_id: str) -> Dict[str, Any]:
        try:
            union_id = get_dingtalk_union_id()
            result = make_dingtalk_request(
                endpoint=f"/calendar/users/{union_id}/calendars/primary/events/{event_id}",
                method="GET"
            )

            return {
                "success": True,
                "event": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"日程详情查询失败: {str(e)}"
            }


class CalendarListInput(BaseModel):
    """日历列表查询输入模型"""
    start_time: str = Field(..., description="开始时间，格式: YYYY-MM-DDTHH:mm:ss+08:00")
    end_time: str = Field(..., description="结束时间，格式: YYYY-MM-DDTHH:mm:ss+08:00")
    max_results: int = Field(20, description="最大返回数量", ge=1, le=100)
    next_token: Optional[str] = Field(None, description="分页令牌")

    @validator('start_time', 'end_time')
    def validate_datetime(cls, v):
        if not validate_datetime_format(v, '%Y-%m-%dT%H:%M:%S%z'):
            raise ValueError("时间格式无效，请使用 'YYYY-MM-DDTHH:mm:ss+08:00' 格式")
        return v


class DingTalkCalendarListTool(BaseTool):
    """查询钉钉日程列表 - 当需要获取时间段内的日程列表时使用此工具"""
    name: str = "dingtalk_calendar_list"
    description: str = "查询钉钉日程列表"
    args_schema: Type[BaseModel] = CalendarListInput

    def _run(
            self,
            start_time: str,
            end_time: str,
            max_results: int = 20,
            next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            union_id = get_dingtalk_union_id()
            params = {
                "timeMin": start_time,
                "timeMax": end_time,
                "maxResults": max_results
            }
            if next_token:
                params["nextToken"] = next_token

            result = make_dingtalk_request(
                endpoint=f"/calendar/users/{union_id}/calendars/primary/events",
                method="GET",
                params=params
            )

            events = result.get("items", [])
            next_token = result.get("nextToken")

            return {
                "success": True,
                "count": len(events),
                "events": events,
                "next_token": next_token
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"日程列表查询失败: {str(e)}"
            }


class CalendarViewInput(BaseModel):
    """日历视图查询输入模型"""
    start_time: str = Field(..., description="开始时间，格式: YYYY-MM-DD")
    end_time: str = Field(..., description="结束时间，格式: YYYY-MM-DD")
    max_results: int = Field(20, description="最大返回数量", ge=1, le=100)
    next_token: Optional[str] = Field(None, description="分页令牌")

    @validator('start_time', 'end_time')
    def validate_date(cls, v):
        if not validate_datetime_format(v, '%Y-%m-%d'):
            raise ValueError("日期格式无效，请使用 'YYYY-MM-DD' 格式")
        return v


class DingTalkCalendarViewTool(BaseTool):
    """查询钉钉日程视图 - 当需要按日查看日程安排时使用此工具"""
    name: str = "dingtalk_calendar_view"
    description: str = "查询钉钉日程视图"
    args_schema: Type[BaseModel] = CalendarViewInput

    def _run(
            self,
            start_time: str,
            end_time: str,
            max_results: int = 20,
            next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            union_id = get_dingtalk_union_id()
            params = {
                "timeMin": f"{start_time}T00:00:00+08:00",
                "timeMax": f"{end_time}T23:59:59+08:00",
                "maxResults": max_results
            }
            if next_token:
                params["nextToken"] = next_token

            result = make_dingtalk_request(
                endpoint=f"/calendar/users/{union_id}/calendars/primary/events/view",
                method="GET",
                params=params
            )

            events = result.get("events", [])
            next_token = result.get("nextToken")

            return {
                "success": True,
                "count": len(events),
                "events": events,
                "next_token": next_token
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"日程视图查询失败: {str(e)}"
            }


class CalendarAttendeesInput(BaseModel):
    """日历参与者输入模型"""
    event_id: str = Field(..., description="日程事件ID")
    attendees: List[str] = Field(..., description="参与者用户ID列表")


class DingTalkCalendarAddAttendeesTool(BaseTool):
    """添加钉钉日程参与者 - 当需要向日程添加参与者时使用此工具"""
    name: str = "dingtalk_calendar_add_attendees"
    description: str = "添加钉钉日程参与者"
    args_schema: Type[BaseModel] = CalendarAttendeesInput

    def _run(self, event_id: str, attendees: List[str]) -> Dict[str, Any]:
        try:
            union_id = get_dingtalk_union_id()
            payload = {
                "attendeesToAdd": [{"id": uid} for uid in attendees]
            }

            result = make_dingtalk_request(
                endpoint=f"/calendar/users/{union_id}/calendars/primary/events/{event_id}/attendees",
                method="POST",
                json_data=payload
            )

            return {
                "success": True,
                "event_id": result.get("id"),
                "attendees": result.get("attendees", [])
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"添加参与者失败: {str(e)}"
            }


class DingTalkCalendarRemoveAttendeesTool(BaseTool):
    """删除钉钉日程参与者 - 当需要从日程移除参与者时使用此工具"""
    name: str = "dingtalk_calendar_remove_attendees"
    description: str = "删除钉钉日程参与者"
    args_schema: Type[BaseModel] = CalendarAttendeesInput

    def _run(self, event_id: str, attendees: List[str]) -> Dict[str, Any]:
        try:
            union_id = get_dingtalk_union_id()
            payload = {
                "attendeesToRemove": [{"id": uid} for uid in attendees]
            }

            result = make_dingtalk_request(
                endpoint=f"/calendar/users/{union_id}/calendars/primary/events/{event_id}/attendees",
                method="POST",
                json_data=payload
            )

            return {
                "success": True,
                "event_id": result.get("id"),
                "attendees": result.get("attendees", [])
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"删除参与者失败: {str(e)}"
            }


class CalendarResponseInput(BaseModel):
    """日历响应状态输入模型"""
    event_id: str = Field(..., description="日程事件ID")
    status: str = Field(..., description="响应状态: accept（接受）, decline（拒绝）, tentative（暂定）")


class DingTalkCalendarUpdateResponseTool(BaseTool):
    """设置钉钉日程响应邀请状态 - 当需要回复日程邀请时使用此工具"""
    name: str = "dingtalk_calendar_update_response"
    description: str = "更新钉钉日程响应状态"
    args_schema: Type[BaseModel] = CalendarResponseInput

    def _run(self, event_id: str, status: str) -> Dict[str, Any]:
        try:
            if status not in ["accept", "decline", "tentative"]:
                raise ValueError("状态必须是 'accept', 'decline' 或 'tentative'")

            union_id = get_dingtalk_union_id()
            payload = {"responseStatus": status}

            result = make_dingtalk_request(
                endpoint=f"/calendar/users/{union_id}/calendars/primary/events/{event_id}/response",
                method="PUT",
                json_data=payload
            )

            return {
                "success": True,
                "event_id": result.get("id"),
                "status": status
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"更新响应状态失败: {str(e)}"
            }


class CalendarListAttendeesInput(BaseModel):
    """日历参与者列表查询输入模型"""
    event_id: str = Field(..., description="日程事件ID")


class DingTalkCalendarListAttendeesTool(BaseTool):
    """获取钉钉日程参与者列表 - 当需要查看日程参与者时使用此工具"""
    name: str = "dingtalk_calendar_list_attendees"
    description: str = "获取钉钉日程参与者列表"
    args_schema: Type[BaseModel] = CalendarListAttendeesInput

    def _run(self, event_id: str) -> Dict[str, Any]:
        try:
            union_id = get_dingtalk_union_id()
            result = make_dingtalk_request(
                endpoint=f"/calendar/users/{union_id}/calendars/primary/events/{event_id}/attendees",
                method="GET"
            )

            return {
                "success": True,
                "event_id": event_id,
                "attendees": result.get("attendees", [])
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"获取参与者列表失败: {str(e)}"
            }


class DingTalkCalendarDeleteTool(BaseTool):
    """删除钉钉日程 - 当需要删除日历时使用此工具"""
    name: str = "dingtalk_calendar_delete"
    description: str = "删除钉钉日程"
    args_schema: Type[BaseModel] = CalendarEventIdInput

    def _run(self, event_id: str) -> Dict[str, Any]:
        try:
            union_id = get_dingtalk_union_id()
            make_dingtalk_request(
                endpoint=f"/calendar/users/{union_id}/calendars/primary/events/{event_id}",
                method="DELETE"
            )

            return {
                "success": True,
                "message": "日程删除成功"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"日程删除失败: {str(e)}"
            }