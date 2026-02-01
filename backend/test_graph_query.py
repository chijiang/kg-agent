# backend/test_graph_query.py
"""测试图查询功能"""
import asyncio
from app.core.neo4j_pool import get_neo4j_driver
from app.services.graph_tools import GraphTools


async def main():
    # 使用你的 Neo4j 配置
    uri = "neo4j+s://c9c3a1ff.databases.neo4j.io"  # 替换为你的 URI
    username = "neo4j"
    password = "your-password"  # 替换为你的密码
    database = "neo4j"

    print("连接 Neo4j...")
    driver = await get_neo4j_driver(
        uri=uri, username=username, password=password, database=database
    )

    async with driver.session(database=database) as session:
        tools = GraphTools(session)

        print("\n=== 测试 Ontology 查询 ===")

        # 1. 获取所有类
        print("\n1. 获取所有类:")
        classes = await tools.get_ontology_classes()
        for c in classes:
            print(f"  - {c['name']}: {c.get('dataProperties', [])}")

        # 2. 获取所有关系定义
        print("\n2. 获取所有关系定义:")
        rels = await tools.get_ontology_relationships()
        for r in rels:
            print(
                f"  - {r['source_class']} --[{r['relationship']}]--> {r['target_class']}"
            )

        print("\n=== 测试 Instance 查询 ===")

        # 3. 搜索实例
        print("\n3. 搜索 'PO' 实例:")
        instances = await tools.search_instances("PO")
        for i in instances:
            print(f"  - {i['name']}: {i.get('properties', {})}")

        # 4. 获取节点统计
        print("\n4. 节点统计:")
        stats = await tools.get_node_statistics()
        print(f"  {stats}")

        # 5. 获取 PurchaseOrder 实例
        print("\n5. PurchaseOrder 实例:")
        pos = await tools.get_instances_by_class("PurchaseOrder")
        for p in pos:
            print(f"  - {p['name']}: {p.get('properties', {})}")

        # 6. 测试邻居查询
        if pos:
            print(f"\n6. {pos[0]['name']} 的邻居:")
            neighbors = await tools.get_instance_neighbors(pos[0]["name"])
            for n in neighbors:
                print(f"  - {n['name']} ({n.get('relationships', [])})")

    print("\n测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
