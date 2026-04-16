"""QueryQueue - 优先级队列实现."""

from __future__ import annotations

import heapq
import threading
import uuid
from typing import Optional

from .types import QueryPriority, QueryRequest, QueryStatus, QueryType, QueueStats


class QueryQueue:
    """线程安全的优先级队列.

    支持：
    - 优先级队列（FIFO + 优先级）
    - Query 取消
    - 队列统计
    """

    def __init__(self, max_size: int = 1000):
        self._max_size = max_size
        self._lock = threading.Lock()
        self._heap: list[tuple[int, float, str]] = []  # (priority, timestamp, query_id)
        self._queries: dict[str, QueryRequest] = {}
        self._running: set[str] = set()  # 正在执行的 query
        self._completed: dict[str, QueryRequest] = {}  # 已完成的 query

    def enqueue(
        self,
        content: str,
        query_type: QueryType = QueryType.NORMAL,
        priority: QueryPriority = QueryPriority.NORMAL,
        team_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """入队新 query.

        Args:
            content: query 内容
            query_type: query 类型
            priority: 优先级
            team_id: 指定 team（可选）
            metadata: 额外元数据

        Returns:
            query_id

        Raises:
            RuntimeError: 队列已满
        """
        with self._lock:
            if len(self._queries) >= self._max_size:
                raise RuntimeError(f"Queue full (max={self._max_size})")

            query_id = str(uuid.uuid4())
            query = QueryRequest(
                id=query_id,
                content=content,
                query_type=query_type,
                priority=priority,
                team_id=team_id,
                metadata=metadata or {},
            )

            # 使用负优先级（Python heapq 是最小堆）
            heap_item = (-priority.value, query.created_at, query_id)
            heapq.heappush(self._heap, heap_item)
            self._queries[query_id] = query

            return query_id

    def dequeue(self) -> Optional[QueryRequest]:
        """出队最高优先级 query.

        Returns:
            QueryRequest 或 None（队列为空）
        """
        with self._lock:
            while self._heap:
                _, _, query_id = heapq.heappop(self._heap)
                query = self._queries.get(query_id)

                if query is None:
                    continue  # 已被取消

                if query.status == QueryStatus.PENDING:
                    query.status = QueryStatus.RUNNING
                    self._running.add(query_id)
                    return query

            return None

    def get(self, query_id: str) -> Optional[QueryRequest]:
        """获取 query（不改变状态）."""
        with self._lock:
            return self._queries.get(query_id)

    def cancel(self, query_id: str) -> bool:
        """取消 query.

        Returns:
            是否成功取消
        """
        with self._lock:
            query = self._queries.get(query_id)
            if query is None:
                return False

            if query.status == QueryStatus.RUNNING:
                query.status = QueryStatus.CANCELLED
                self._running.discard(query_id)
            elif query.status == QueryStatus.PENDING:
                query.status = QueryStatus.CANCELLED
                # 从堆中移除（需要重建）
                self._rebuild_heap()

            return True

    def complete(self, query_id: str, result: dict) -> None:
        """标记 query 为完成.

        Args:
            query_id: query ID
            result: 执行结果
        """
        with self._lock:
            query = self._queries.get(query_id)
            if query is None:
                return

            query.status = QueryStatus.COMPLETED
            query.result = result
            self._running.discard(query_id)
            self._completed[query_id] = query

    def fail(self, query_id: str, error: str) -> None:
        """标记 query 为失败.

        Args:
            query_id: query ID
            error: 错误信息
        """
        with self._lock:
            query = self._queries.get(query_id)
            if query is None:
                return

            query.status = QueryStatus.FAILED
            query.error = error
            self._running.discard(query_id)
            self._completed[query_id] = query

    def requeue(self, query_id: str) -> bool:
        """重新入队已完成的 query.

        Returns:
            是否成功
        """
        with self._lock:
            query = self._queries.get(query_id)
            if query is None:
                return False

            if query.status not in (QueryStatus.COMPLETED, QueryStatus.FAILED, QueryStatus.CANCELLED):
                return False

            # 重置状态并重新入队
            query.status = QueryStatus.PENDING
            query.result = None
            query.error = None
            query.created_at = self._get_timestamp()

            heap_item = (-query.priority.value, query.created_at, query_id)
            heapq.heappush(self._heap, query_id)

            if query_id in self._completed:
                del self._completed[query_id]

            return True

    def preempt(self, query_id: str) -> bool:
        """插入高优先级 query 到正在运行的 query 之前.

        实际上是将目标 query 的状态设为 CANCELLED，让新 query 先执行。

        Returns:
            是否成功
        """
        return self.cancel(query_id)

    def get_stats(self) -> QueueStats:
        """获取队列统计."""
        with self._lock:
            pending = sum(1 for q in self._queries.values() if q.status == QueryStatus.PENDING)
            running = len(self._running)
            completed = sum(1 for q in self._queries.values() if q.status == QueryStatus.COMPLETED)
            failed = sum(1 for q in self._queries.values() if q.status == QueryStatus.FAILED)
            cancelled = sum(1 for q in self._queries.values() if q.status == QueryStatus.CANCELLED)

            return QueueStats(
                pending_count=pending,
                running_count=running,
                completed_count=completed,
                failed_count=failed,
                cancelled_count=cancelled,
            )

    def _rebuild_heap(self) -> None:
        """重建堆（移除已取消的 query）."""
        self._heap = [
            (-q.priority.value, q.created_at, qid)
            for qid, q in self._queries.items()
            if q.status == QueryStatus.PENDING
        ]
        heapq.heapify(self._heap)

    def _get_timestamp(self) -> float:
        """获取当前时间戳."""
        import time
        return time.time()
