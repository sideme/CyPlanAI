# LangGraph SDK 处理流程分析

## 1. 前端调用流程

### 1.1 初始化 (`Stream.tsx`)

```typescript
// frontend-LangChain/src/providers/Stream.tsx
const streamValue = useTypedStream({
  apiUrl: "http://localhost:2024",
  apiKey: undefined,
  assistantId: "cyplanai",
  threadId: threadId ?? null,
  fetchStateHistory: true,
  onCustomEvent: (event, options) => { ... },
  onThreadId: (id) => { ... },
});
```

**SDK 内部处理：**
- `useStream` hook 来自 `@langchain/langgraph-sdk/react`
- 初始化时会检查 `threadId`，如果没有则创建新线程
- 如果 `fetchStateHistory: true`，会调用 `/threads/{thread_id}/history` 获取历史消息

### 1.2 提交消息 (`index.tsx`)

```typescript
// frontend-LangChain/src/components/thread/index.tsx
stream.submit(
  { messages: [...toolMessages, newHumanMessage], context },
  {
    streamMode: ["values"],
    streamSubgraphs: true,
    streamResumable: true,
    optimisticValues: (prev) => ({
      ...prev,
      messages: [...(prev.messages ?? []), ...toolMessages, newHumanMessage],
    }),
  },
);
```

**SDK 内部处理流程：**

1. **构建请求 URL：**
   - 如果有 `threadId`：`POST {apiUrl}/threads/{thread_id}/runs`
   - 如果没有 `threadId`：先调用 `POST {apiUrl}/threads` 创建线程，然后调用 `/runs`

2. **构建请求体：**
   ```json
   {
     "input": {
       "messages": [
         { "id": "...", "type": "human", "content": [...] }
       ]
     },
     "stream_mode": ["values"],
     "stream_subgraphs": true,
     "stream_resumable": true
   }
   ```

3. **发送请求：**
   - 使用 `fetch` API 发送 POST 请求
   - 设置 `Accept: text/event-stream` header
   - 处理 SSE 流响应

4. **处理 SSE 流：**
   - 监听 `event: data` 事件
   - 解析 `data: {"values": {"messages": [...]}}`
   - 更新 `stream.values` 状态
   - 处理 `stream.messages`（SDK 内部的消息列表）

## 2. 后端处理流程

### 2.1 接收请求 (`langgraph_server.py`)

```python
@app.post("/threads/{thread_id}/runs")
async def create_run(thread_id: str, request: MessageRequest):
    # 1. 解析请求
    messages_data = request.input["messages"]  # 或 request.messages
    
    # 2. 转换为 LangChain 消息格式
    langchain_messages = [HumanMessage(...), AIMessage(...)]
    
    # 3. 创建状态
    state: AgentState = {
        "messages": langchain_messages,
        "user_id": ...,
        "plan_id": ...
    }
    
    # 4. 流式处理
    async def stream_events():
        async for state_update in agent_graph.astream(state, stream_mode="values"):
            # 格式化消息
            formatted_state = {
                "messages": [...],  # 包含所有累积的消息
                "user_id": ...,
                "plan_id": ...
            }
            yield {
                "event": "data",
                "data": {"values": formatted_state}
            }
    
    # 5. 返回 SSE 流
    return StreamingResponse(generate(), media_type="text/event-stream")
```

### 2.2 SSE 格式

后端发送的 SSE 格式：
```
event: data
data: {"values": {"messages": [{"id": "...", "type": "human", "content": [...]}, {"id": "...", "type": "ai", "content": [...]}], "user_id": "", "plan_id": null}}

event: data
data: {"values": {"messages": [{"id": "...", "type": "human", "content": [...]}, {"id": "...", "type": "ai", "content": [...]}], "user_id": "", "plan_id": null}}

event: end
data: {}
```

## 3. SDK 如何处理 SSE 事件

### 3.1 `stream.values` 更新

当收到 `event: data` 时：
- SDK 解析 `data` 字段中的 JSON
- 提取 `data.values` 并更新 `stream.values`
- **重要：** `stream.values` 会被**完全替换**为最新的事件数据，而不是合并

### 3.2 `stream.messages` 更新

SDK 内部会：
1. 从 `stream.values.messages` 中提取消息
2. 根据消息 ID 进行去重和排序
3. 更新 `stream.messages` 列表

**可能的问题：**
- 如果多个 SSE 事件中的消息 ID 相同，SDK 可能只保留最后一个
- 如果消息 ID 格式不匹配，可能导致消息丢失

## 4. 当前问题分析

### 4.1 问题现象

- **后端发送：** 2 条消息（human + ai）
- **前端接收：** 只有 1 条消息（human）
- **Network 标签页：** 显示后端正确发送了包含 2 条消息的 SSE 事件

### 4.2 可能的原因

1. **SDK 只处理了第一个 SSE 事件**
   - 第一个事件：只有 human 消息
   - 第二个事件：包含 human + ai 消息
   - SDK 可能在处理第一个事件后就停止了

2. **消息 ID 冲突导致去重**
   - 如果两个事件中的 human 消息 ID 相同
   - SDK 可能认为这是同一条消息，只保留一个

3. **`stream.values` 更新时机问题**
   - React 的 `useEffect` 可能没有及时捕获到 `stream.values` 的更新
   - 或者 SDK 内部的状态更新有延迟

## 5. 调试建议

### 5.1 检查 SDK 内部状态

在 `Stream.tsx` 中添加日志：

```typescript
useEffect(() => {
  console.log("🔍 Stream Values Debug:", {
    values: streamValue.values,
    valuesMessages: streamValue.values?.messages,
    messages: streamValue.messages,
    isLoading: streamValue.isLoading,
  });
}, [streamValue.values, streamValue.messages]);
```

### 5.2 检查 SSE 事件接收

在浏览器 Network 标签页中：
1. 找到 `/threads/{thread_id}/runs/stream` 请求
2. 查看 Response 标签页
3. 确认是否收到了多个 `event: data` 事件
4. 确认每个事件中的 `messages` 数组内容

### 5.3 检查消息 ID

确认：
- 每个消息的 `id` 是否唯一
- 不同 SSE 事件中的消息 ID 是否一致
- SDK 是否因为 ID 相同而进行了去重

## 6. 可能的解决方案

### 方案 1：确保每个 SSE 事件都包含完整消息列表

后端已经这样做了（发送最后一个包含完整消息列表的事件），但可能 SDK 没有正确处理。

### 方案 2：检查 SDK 版本

确认 `@langchain/langgraph-sdk` 的版本，可能需要更新到最新版本。

### 方案 3：手动处理 SSE（已尝试但被拒绝）

直接使用 `fetch` API 处理 SSE 流，绕过 SDK 的处理逻辑。

## 7. 关键代码位置

- **前端 SDK Hook：** `frontend-LangChain/src/providers/Stream.tsx` (line 83)
- **前端提交消息：** `frontend-LangChain/src/components/thread/index.tsx` (line 312)
- **后端接收请求：** `backend/langgraph_server.py` (line 175)
- **后端 SSE 流：** `backend/langgraph_server.py` (line 240-526)

