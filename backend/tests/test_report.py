import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_wealth_chart(client: AsyncClient, auth_headers: dict, sample_account):
    # Setup: ensure account has balance
    await client.patch(
        f"/accounts/{sample_account}",
        json={"current_balance": 5000.0},
        headers=auth_headers
    )
    
    response = await client.get("/wealth/chart", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "data_points" in data
    assert len(data["data_points"]) > 0
    assert data["data_points"][0]["assets"] == 5000.0
