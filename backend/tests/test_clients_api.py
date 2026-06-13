def _create(api, biz_id, **kw):
    return api.post(f"/api/businesses/{biz_id}/clients", json={"name": "נועה גולן", **kw})

def test_create_and_get_client(api, db, make_business):
    biz = make_business()
    r = _create(api, biz["id"], phone="050-1234567")
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "נועה גולן" and body["businessId"] == biz["id"] and "id" in body
    assert api.get(f"/api/businesses/{biz['id']}/clients/{body['id']}").json()["phone"] == "050-1234567"

def test_list_sorted_and_patch(api, db, make_business):
    biz = make_business()
    _create(api, biz["id"]); api.post(f"/api/businesses/{biz['id']}/clients", json={"name": "אבי"})
    names = [c["name"] for c in api.get(f"/api/businesses/{biz['id']}/clients").json()]
    assert names == ["אבי", "נועה גולן"]
    cid = api.get(f"/api/businesses/{biz['id']}/clients").json()[1]["id"]
    r = api.patch(f"/api/businesses/{biz['id']}/clients/{cid}", json={"email": "noa@example.com"})
    assert r.status_code == 200 and r.json()["email"] == "noa@example.com"

def test_get_missing_client_404(api, db, make_business):
    biz = make_business()
    r = api.get(f"/api/businesses/{biz['id']}/clients/nope")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "client_not_found"

def test_find_by_name_case_insensitive_contains(db, make_business):
    from app.schemas.client import ClientCreate
    from app.services.client_service import create_client, find_clients_by_name
    biz = make_business()
    create_client(db, biz["id"], ClientCreate(name="Eden Studio"))
    assert [c.name for c in find_clients_by_name(db, biz["id"], "eden")] == ["Eden Studio"]
    assert find_clients_by_name(db, biz["id"], "נועה") == []


def test_patch_missing_client_404(api, make_business):
    biz = make_business()
    r = api.patch(f"/api/businesses/{biz['id']}/clients/nope", json={"name": "X"})
    assert r.status_code == 404 and r.json()["detail"]["code"] == "client_not_found"
