# Ontology-Driven Agent (KG-Agent)

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English Version

**KG-Agent** is an **Ontology-First** intelligent platform designed for complex semantic reasoning and automation. At its core, the system is defined by a rigorous **Ontology**, while the **Knowledge Graph** serves as the dynamic realization and data organization form. By prioritizing the ontological model, KG-Agent ensures that every interaction, rule, and data synchronization is governed by a consistent semantic framework.

### 🚀 Core Features

- **🛠️ Ontology-First Schema Management**:
  - **Core Definition**: Move beyond flat data models; define your world through classes, properties, and complex relationships.
  - **Visual Editor**: Real-time schema manipulation supporting data types (rdfs:range) and semantic aliases.
  - **Standard Support**: Seamlessly import and export **OWL/TTL** ontology files to leverage existing semantic standards.
- **🤖 Ontology-Guided Agent**:
  - **Semantic Reasoning**: Natural language interaction that understands the underlying ontology, not just keyword matching.
  - **Agentic Extensibility**: Integrated **MCP (Model Context Protocol)** servers that expose query and action tools derived directly from your ontology.
- **⚡ Semantic Rule Engine**:
  - **Relationship-Driven**: Define business logic using a custom DSL that operates on ontological patterns and event-driven graph changes.
  - **Action Orchestration**: Trigger gRPC calls and asynchronous actions based on semantic triggers within the graph.
- **🔄 Semantic Data Synchronization**:
  - **Ontology Alignment**: Automatically map and sync external data products (ERP, CRM) to your central ontological model.
  - **Conflict Resolution**: Intelligent merging based on semantic identity (source_id).
- **� Interactive Visualization**:
  - **Structural Insight**: High-performance rendering with **Cytoscape.js** to explore the graph realization of your ontology.
  - **Path Analysis**: Highlight multi-hop relationships and semantic paths.

### 💻 Tech Stack

- **Frontend**: Next.js 15 (App Router), TypeScript, TailwindCSS 4, Shadcn UI, Zustand (State Management)
- **Backend**: FastAPI, Python 3.12+, SQLModel/SQLAlchemy (PostgreSQL/SQLite), LangChain
- **Graph Realization**: Multi-adapter support (Neo4j, NetworkX, PG-Graph)
- **Package Management**: **UV** (Backend), **PNPM** (Frontend)

### 📂 Project Structure

```text
kg_agent/
├── backend/                # Fast API Backend
│   ├── app/                # Application Core logic
│   │   ├── api/            # REST API Routes
│   │   ├── mcp/            # Model Context Protocol Servers
│   │   ├── rule_engine/    # Custom DSL & Event-driven logic
│   │   └── services/       # Business services (Sync, Graph, Ontology)
│   ├── main.py             # Server Entry Point
│   └── Dockerfile
├── frontend/               # Next.js Frontend
│   ├── src/
│   │   ├── app/            # App Router (i18n)
│   │   ├── components/     # UI Components (Shadcn)
│   │   └── store/          # Global State (Zustand)
│   └── Dockerfile
└── docker-compose.yml      # Full-stack Container Orchestration
```

### 🏁 Quick Start

#### Using Docker Compose (Recommended)

1.  **Environment Setup**:
    Copy `.env.example` to `.env` and fill in necessary API keys.
2.  **Start Services**:
    ```bash
    docker-compose up --build
    ```
3.  **Access**:
    - Web UI: [http://localhost:3000](http://localhost:3000)
    - API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

#### Local Development

**Backend** (Requires `uv`)
```bash
cd backend
uv sync
uv run main.py
```

**Frontend** (Requires `pnpm`)
```bash
cd frontend
pnpm install
pnpm dev
```

---

<a name="中文"></a>
## 中文版本

**KG-Agent** 是一个**本体驱动**（Ontology-Driven）的智能平台，专为复杂的语义推理和自动化设计。系统的核心由严谨的**本体论**（Ontology）定义，而**知识图谱**（Knowledge Graph）则是其动态的实现与数据组织形式。通过坚持“本体优先”原则，KG-Agent 确保每一次交互、规则执行和数据同步都受统一的语义框架约束。

### 🚀 核心功能

- **🛠️ 本体优先的模式管理**:
  - **核心定义**: 超越扁平化数据模型；通过类、属性和复杂关系定义您的业务世界。
  - **可视化编辑器**: 实时 Schema 操作，支持数据类型（rdfs:range）与语义别名。
  - **标准支持**: 无缝导入/导出 **OWL/TTL** 本体文件。
- **🤖 本地引导的智能 Agent**:
  - **语义推理**: 基于本体结构的自然语言交互，理解底层逻辑而非简单的关键词匹配。
  - **能力扩展**: 集成 **MCP (Model Context Protocol)** 服务，提供直接源自本体定义的查询与动作工具。
- **⚡ 语义规则引擎**:
  - **关系驱动**: 使用自定义 DSL 定义业务逻辑，基于本体模式和图数据变更进行实时触发。
  - **动作编排**: 基于图谱中的语义触发器，自动执行 gRPC 调用和异步操作。
- **🔄 语义数据同步**:
  - **本体对齐**: 将外部数据产品（如 ERP, CRM）自动映射并同步至核心本体模型。
  - **语义冲突解决**: 基于语义标识（source_id）的智能数据合并。
- **� 交互式可视化分析**:
  - **结构洞察**: 使用 **Cytoscape.js** 高性能渲染，直观展示本体模型在图谱中的具体实现。
  - **路径分析**: 高亮显示多跳关系与语义路径。

### 💻 技术栈

- **前端**: Next.js 15 (App Router), TypeScript, TailwindCSS 4, Shadcn UI, Zustand
- **后端**: FastAPI, Python 3.12+, SQLModel/SQLAlchemy, LangChain
- **图实现**: 多适配器支持 (Neo4j, NetworkX, PG-Graph)
- **包管理**: **UV** (后端), **PNPM** (前端)

### 📂 项目结构

```text
kg_agent/
├── backend/                # FastAPI 后端
│   ├── app/                # 应用核心逻辑
│   │   ├── api/            # REST API 路由
│   │   ├── mcp/            # MCP 服务实现
│   │   ├── rule_engine/    # 自定义 DSL 与规则引擎
│   │   └── services/       # 业务服务 (同步, 图, 本体)
│   ├── main.py             # 服务器入口
│   └── Dockerfile
├── frontend/               # Next.js 前端
│   ├── src/
│   │   ├── app/            # App Router (i18n)
│   │   ├── components/     # UI 组件 (Shadcn)
│   │   └── store/          # 全局状态管理
│   └── Dockerfile
└── docker-compose.yml      # 全栈容器编排
```

### 🏁 快速开始

#### 使用 Docker Compose (推荐)

1.  **环境配置**:
    复制 `.env.example` 为 `.env` 并填入 API 密钥。
2.  **启动服务**:
    ```bash
    docker-compose up --build
    ```
3.  **访问**:
    - 网页端: [http://localhost:3000](http://localhost:3000)
    - API 文档: [http://localhost:8000/docs](http://localhost:8000/docs)

#### 本地开发

**后端** (需安装 `uv`)
```bash
cd backend
uv sync
uv run main.py
```

**前端** (需安装 `pnpm`)
```bash
cd frontend
pnpm install
pnpm dev
```

---

## License / 许可证

**Non-Commercial License Only** / **仅限非商业用途**

This project is licensed under a restrictive Non-Commercial License. 
- **Prohibited**: Commercial use, for-profit distribution, or commercial use of derivative works.
- **Allowed**: Personal, educational, and non-commercial research use.

For detailed terms, please see the [LICENSE](file:///Users/chijiangduan/projs/kg_agent/LICENSE) file.

本项目采用限制性非商业许可协议。
- **禁止**: 商业用途、营利性分发或二次开发后的商业用途。
- **允许**: 个人学习、教育及非商业性研究使用。

详细条款请参阅 [LICENSE](file:///Users/chijiangduan/projs/kg_agent/LICENSE) 文件。
