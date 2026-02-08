import asyncio
import httpx
import uuid

async def test_ontology_edit():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Register a temporary user
        username = f"testuser_{uuid.uuid4().hex[:8]}"
        password = "testpassword"
        response = await client.post("/auth/register", json={"username": username, "password": password})
        if response.status_code != 200:
            print(f"Register failed: {response.status_code} {response.text}")
            return
        
        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # 1. Add class
        class_name = f"TestClass_{uuid.uuid4().hex[:4]}"
        print(f"Adding class: {class_name}")
        response = await client.post("/graph/ontology/classes", json={"name": class_name, "label": "Test Label"}, headers=headers)
        print(f"Add class response: {response.status_code}")
        assert response.status_code == 200
        
        # 2. Update class
        print(f"Updating class: {class_name}")
        response = await client.put(f"/graph/ontology/classes/{class_name}", json={"label": "Updated Label", "data_properties": ["prop1:string"]}, headers=headers)
        print(f"Update class response: {response.status_code}")
        assert response.status_code == 200
        
        # 3. Add relationship
        target_name = f"TargetClass_{uuid.uuid4().hex[:4]}"
        await client.post("/graph/ontology/classes", json={"name": target_name}, headers=headers)
        print(f"Adding relationship: {class_name} -> {target_name}")
        response = await client.post("/graph/ontology/relationships", json={"source": class_name, "type": "CONNECTED_TO", "target": target_name}, headers=headers)
        print(f"Add relationship response: {response.status_code}")
        assert response.status_code == 200
        
        # 4. Delete relationship
        print(f"Deleting relationship")
        # Note: I used @router.request("DELETE", ...) which might be tricky in httpx. 
        # Actually I should have used @router.api_route(..., methods=["DELETE"]) or just delete with content if supported.
        # FastAPI's router.request is for generic requests.
        response = await client.request("DELETE", "/graph/ontology/relationships", json={"source": class_name, "type": "CONNECTED_TO", "target": target_name}, headers=headers)
        print(f"Delete relationship response: {response.status_code}")
        assert response.status_code == 200
        
        # 5. Delete class
        print(f"Deleting class: {class_name}")
        response = await client.delete(f"/graph/ontology/classes/{class_name}", headers=headers)
        print(f"Delete class response: {response.status_code}")
        assert response.status_code == 200

        print("Ontology edit verification successful!")

if __name__ == "__main__":
    asyncio.run(test_ontology_edit())
