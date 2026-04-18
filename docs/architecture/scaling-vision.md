# 架构扩展性愿景 - 百万级Agent支持

**版本**: 0.1
**日期**: 2026-04-17
**状态**: 概念设计 (Conceptual)

---

## 1. 当前架构评估

### 1.1 现状

```
当前架构: 单进程 + asyncio + 内存存储

OrchestrationEngine
    │
    ├── _teams: dict[str, AgentTeam]      # 内存字典
    ├── _queue: QueryQueue                 # 内存队列
    └── asyncio.gather()                   # 单机并行
```

### 1.2 支持规模

| 指标 | 当前 | 理论上限 |
|------|------|----------|
| Agent数量 | 10-100 | ~1000 (受限于内存) |
| 并发Query | 10-50 | ~100 (受限于asyncio) |
| 路由复杂度 | O(n) 关键词 | O(n) 无法优化 |

### 1.3 瓶颈分析

| 组件 | 当前实现 | 瓶颈 | 影响 |
|------|----------|------|------|
| Team存储 | `dict[str, AgentTeam]` | 内存连续性 | 百万Agent会OOM |
| 并行执行 | `asyncio.gather()` | 单进程GIL | CPU利用率低 |
| 路由 | 关键词匹配 | O(n)扫描 | 延迟随规模线性增长 |
| 状态 | InMemory | 无持久化 | 进程崩溃数据丢失 |
| 容错 | 无 | 单点故障 | 任何故障导致服务中断 |

---

## 2. 目标架构 (百万级Agent)

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      Global Load Balancer                         │
│                  (L4/L7 + Anycast + GeoDNS)                     │
└─────────────────────────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ Region  │ │ Region  │ │ Region  │ │ Region  │
   │  华东    │ │  华北    │ │  华南    │ │  海外    │
   └─────────┘ └─────────┘ └─────────┘ └─────────┘
        │           │           │           │
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │  Zone   │ │  Zone   │ │  Zone   │ │  Zone   │
   │  汽车   │ │  医疗   │ │  法律   │ │  教育   │
   └─────────┘ └─────────┘ └─────────┘ └─────────┘
        │           │           │           │
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │Cluster  │ │Cluster  │ │Cluster  │ │Cluster  │
   │ Agent群  │ │ Agent群  │ │ Agent群  │ │ Agent群  │
   └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

### 2.2 每层职责

| 层级 | 职责 | 扩展方式 |
|------|------|----------|
| **Global LB** | 地域级流量分发 | DNS/Anycast |
| **Region** | 地理分区容灾 | 增加Region |
| **Zone** | 领域/行业分区 | 按业务线拆分 |
| **Cluster** | Agent能力集群 | 按技能/角色拆分 |
| **Agent** | 具体执行单元 | 水平扩展 |

### 2.3 数据流

```
用户Query
    │
    ▼
Global Router (语义路由 + 能力匹配)
    │
    ├──→ Vector DB (Agent能力embedding)
    │         │
    │         ▼
    │    Top-K 最匹配Agent群
    │
    ▼
Region Router (地域 + Zone选择)
    │
    ▼
Cluster Executor (任务分发 + 并行执行)
    │
    ├──→ Kafka/RabbitMQ (任务队列)
    ├──→ Redis Cluster (状态存储)
    └──→ Ray/DP (分布式计算)
    │
    ▼
结果聚合 + 质量检查
    │
    ▼
用户响应
```

---

## 3. 核心组件演进

### 3.1 当前 vs 目标

| 组件 | 当前 | 目标 |
|------|------|------|
| **任务队列** | asyncio.gather | Kafka/SQS |
| **状态存储** | InMemory | Redis Cluster |
| **服务发现** | 静态配置 | Consul/Etcd |
| **负载均衡** | 无 | Envoy/LB |
| **容错** | 无 | 熔断 + 重试 |
| **路由** | 关键词 | 向量检索 |

### 3.2 详细演进

#### 任务队列 (当前 → Kafka)

```python
# 当前
results = await asyncio.gather(*[team.run_async() for team in teams])

# 目标
task_id = kafka_producer.send("agent_tasks", {
    "teams": [team.serialize() for team in teams],
    "callback": "kafka://result-topic",
})
# 异步等待结果
result = await kafka_consumer.recv(task_id)
```

#### 状态存储 (当前 → Redis)

```python
# 当前
engine._teams[team_id] = team  # 内存

# 目标
redis.hset(f"team:{team_id}", mapping=team.to_dict())
redis.expire(f"team:{team_id}", ttl=3600)
```

#### 路由 (当前 → 向量检索)

```python
# 当前
if "空调" in query:
    return climate_team

# 目标
query_embedding = embedding_model.encode(query)
candidates = vector_db.search(query_embedding, top_k=5)
# 返回最匹配的Agent群
```

---

## 4. 迁移路径

### 4.1 阶段规划

```
Phase 1: 垂直扩展 (当前 → 单机增强)
├── 添加: Redis缓存 (状态)
├── 添加: 熔断器 (容错)
└── 目标: 1000 Agent / 单机

Phase 2: 水平扩展 (单机 → 多机)
├── 引入: Kafka (任务队列)
├── 引入: Consul (服务发现)
└── 目标: 10万 Agent / 集群

Phase 3: 分层架构 (集群 → 全球)
├── 引入: Region/Zone 分层
├── 引入: 向量路由
└── 目标: 100万 Agent / 全球
```

### 4.2 兼容性策略

```python
# 保持API兼容，逐步替换底层实现

# v1 (当前)
class OrchestrationEngine:
    async def run(self, query):
        return await self._run_local(query)

# v2 (中间态)
class OrchestrationEngine:
    async def run(self, query):
        if self.config.distributed:
            return await self._run_distributed(query)
        return await self._run_local(query)

# v3 (目标)
class OrchestrationEngine:
    # 完全分布式实现
    pass
```

---

## 5. 技术选型建议

### 5.1 消息队列

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **Kafka** | 高吞吐、持久化 | 运维复杂 | ⭐⭐⭐⭐⭐ |
| **RabbitMQ** | 易用、灵活路由 | 扩展性一般 | ⭐⭐⭐ |
| **SQS** | 托管、无运维 | 延迟高 | ⭐⭐⭐ |
| **Redis Streams** | 低延迟、集成简单 | 持久化弱 | ⭐⭐⭐ |

### 5.2 分布式计算

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **Ray** | Python原生、高扩展 | 生态较新 | ⭐⭐⭐⭐ |
| **Celery** | 成熟、稳定 | 配置复杂 | ⭐⭐⭐⭐ |
| **Temporal** | 工作流友好 | 锁定供应商 | ⭐⭐⭐ |
| **Dask** | 科学计算强 | 非实时 | ⭐⭐ |

### 5.3 向量数据库

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **Pinecone** | 托管、简单 | 成本 | ⭐⭐⭐⭐ |
| **Milvus** | 开源、功能全 | 运维 | ⭐⭐⭐⭐ |
| **Qdrant** | Rust高性能 | 生态小 | ⭐⭐⭐ |
| **pgvector** | Postgres集成 | 规模有限 | ⭐⭐⭐ |

---

## 6. 当前代码标记

建议在代码中添加扩展性标记：

```python
# TODO(scaling): 当前实现为单进程原型
# - Team存储: 使用dict，后续迁移到Redis Cluster
# - 并行执行: 使用asyncio.gather，后续迁移到Ray
# - 路由: 关键词匹配，后续迁移到向量检索
class OrchestrationEngine:
    """
    当前限制:
    - Agent数量: ~1000 (受限于单机内存)
    - 并发Query: ~100 (受限于asyncio)

    扩展目标: 百万级Agent
    参见: docs/architecture/scaling-vision.md
    """
    pass
```

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 供应商锁定 | 迁移成本高 | 使用抽象接口 |
| 分布式复杂度 | 开发/调试困难 | 逐步迁移、保持兼容 |
| 数据一致性 | 跨区域同步延迟 | 最终一致性模型 |
| 运维复杂度 | 故障定位困难 | 全链路追踪 |

---

## 8. 下一步行动

- [ ] 在代码中添加 `TODO(scaling)` 标记
- [ ] 设计抽象接口层 (Engine → Adapter)
- [ ] 评估 Phase 1 所需的Redis集成
- [ ] 设计分布式状态同步协议

---

*本文档为概念设计，具体实现需要进一步的技术调研和原型验证。*
