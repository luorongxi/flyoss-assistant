from .tool_registry import tool_registry
from .dingtalk import (
    DingTalkTodoCreateTool,
    DingTalkTodoDeleteTool,
    DingTalkTodoUpdateTool,
    DingTalkTodoUpdateStatusTool,
    DingTalkTodoListTool,
    DingTalkCreateWorkLogTool,
    DingTalkCalendarCreateTool,
    DingTalkCalendarDeleteTool,
    DingTalkCalendarUpdateTool,
    DingTalkCalendarGetTool,
    DingTalkCalendarListTool,
    DingTalkCalendarViewTool,
    DingTalkCalendarAddAttendeesTool,
    DingTalkCalendarRemoveAttendeesTool,
    DingTalkCalendarUpdateResponseTool,
    DingTalkCalendarListAttendeesTool
)

# 注册所有工具
tool_registry.register(DingTalkTodoCreateTool)
tool_registry.register(DingTalkTodoDeleteTool)
tool_registry.register(DingTalkTodoUpdateTool)
tool_registry.register(DingTalkTodoUpdateStatusTool)
tool_registry.register(DingTalkTodoListTool)
tool_registry.register(DingTalkCreateWorkLogTool)
tool_registry.register(DingTalkCalendarCreateTool)
tool_registry.register(DingTalkCalendarDeleteTool)
tool_registry.register(DingTalkCalendarUpdateTool)
tool_registry.register(DingTalkCalendarGetTool)
tool_registry.register(DingTalkCalendarListTool)
tool_registry.register(DingTalkCalendarViewTool)
tool_registry.register(DingTalkCalendarAddAttendeesTool)
tool_registry.register(DingTalkCalendarRemoveAttendeesTool)
tool_registry.register(DingTalkCalendarUpdateResponseTool)
tool_registry.register(DingTalkCalendarListAttendeesTool)

__all__ = [
    "tool_registry",
    "DingTalkTodoCreateTool",
    "DingTalkTodoDeleteTool",
    "DingTalkTodoUpdateTool",
    "DingTalkTodoUpdateStatusTool",
    "DingTalkTodoListTool",
    "DingTalkCreateWorkLogTool",
    "DingTalkCalendarCreateTool",
    "DingTalkCalendarDeleteTool",
    "DingTalkCalendarUpdateTool",
    "DingTalkCalendarGetTool",
    "DingTalkCalendarListTool",
    "DingTalkCalendarViewTool",
    "DingTalkCalendarAddAttendeesTool",
    "DingTalkCalendarRemoveAttendeesTool",
    "DingTalkCalendarUpdateResponseTool",
    "DingTalkCalendarListAttendeesTool"
]