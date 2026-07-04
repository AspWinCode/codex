"""
Тесты для Legacy Courses API (/api/courses/*)

Покрывают:
  - CRUD курсов (legacy /api/courses)
  - CRUD модулей и подмодулей
  - Видимость курсов для студентов (только published)
  - Дерево узлов через /api/courses/{id}/tree
  - Контроль доступа (студент не может создавать/удалять)
  - Каскадное удаление модулей и подмодулей
"""
import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

async def _create_course(client: AsyncClient, headers: dict, **kwargs) -> dict:
    payload = {"title": "Test Course", **kwargs}
    resp = await client.post("/api/courses", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_module(client: AsyncClient, course_id: int, headers: dict, **kwargs) -> dict:
    payload = {"course_id": course_id, "title": "Module", "order_index": 0, **kwargs}
    resp = await client.post(f"/api/courses/{course_id}/modules", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_submodule(client: AsyncClient, module_id: int, headers: dict, **kwargs) -> dict:
    payload = {"module_id": module_id, "title": "Submodule", "order_index": 0, **kwargs}
    resp = await client.post(f"/api/courses/modules/{module_id}/submodules", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ===========================================================================
# 1. CRUD курсов (legacy API)
# ===========================================================================

class TestLegacyCourseCRUD:

    @pytest.mark.asyncio
    async def test_create_course_minimal(self, client: AsyncClient, admin_headers):
        """Создание курса с минимальным набором полей."""
        resp = await client.post(
            "/api/courses",
            json={"title": "Python Basics"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Python Basics"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_create_course_with_status(self, client: AsyncClient, admin_headers):
        """Создание курса со статусом published."""
        resp = await client.post(
            "/api/courses",
            json={"title": "Published", "description": "Desc", "status": "published"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "published"

    @pytest.mark.asyncio
    async def test_list_courses_admin_sees_all(self, client: AsyncClient, admin_headers):
        """Админ видит все курсы (draft и published)."""
        await _create_course(client, admin_headers, title="Draft", status="draft")
        await _create_course(client, admin_headers, title="Published", status="published")

        resp = await client.get("/api/courses", headers=admin_headers)
        assert resp.status_code == 200
        titles = [c["title"] for c in resp.json()]
        assert "Draft" in titles
        assert "Published" in titles

    @pytest.mark.asyncio
    async def test_list_courses_student_sees_only_published(
        self, client: AsyncClient, admin_headers, student_headers
    ):
        """Студент видит только опубликованные курсы."""
        await _create_course(client, admin_headers, title="Hidden Draft", status="draft")
        await _create_course(client, admin_headers, title="Visible", status="published")

        resp = await client.get("/api/courses", headers=student_headers)
        assert resp.status_code == 200
        titles = [c["title"] for c in resp.json()]
        assert "Visible" in titles
        assert "Hidden Draft" not in titles

    @pytest.mark.asyncio
    async def test_get_course_detail(self, client: AsyncClient, admin_headers):
        """Детальная информация о курсе содержит поле modules."""
        course = await _create_course(client, admin_headers)
        resp = await client.get(f"/api/courses/{course['id']}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "modules" in data

    @pytest.mark.asyncio
    async def test_get_course_not_found(self, client: AsyncClient, admin_headers):
        """Несуществующий курс → 404."""
        resp = await client.get("/api/courses/99999", headers=admin_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_course(self, client: AsyncClient, admin_headers):
        """PUT: обновление курса меняет данные."""
        course = await _create_course(client, admin_headers, title="Old")
        resp = await client.put(
            f"/api/courses/{course['id']}",
            json={"title": "New Title"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    @pytest.mark.asyncio
    async def test_update_course_not_found(self, client: AsyncClient, admin_headers):
        """PUT несуществующего курса → 404."""
        resp = await client.put(
            "/api/courses/99999",
            json={"title": "X"},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_course(self, client: AsyncClient, admin_headers):
        """Удаление курса → 204."""
        course = await _create_course(client, admin_headers)
        cid = course["id"]
        resp = await client.delete(f"/api/courses/{cid}", headers=admin_headers)
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_course_removes_it_from_list(self, client: AsyncClient, admin_headers):
        """После удаления курс больше не появляется в списке."""
        course = await _create_course(client, admin_headers, title="ToDelete")
        await client.delete(f"/api/courses/{course['id']}", headers=admin_headers)

        resp = await client.get("/api/courses", headers=admin_headers)
        ids = [c["id"] for c in resp.json()]
        assert course["id"] not in ids

    @pytest.mark.asyncio
    async def test_delete_course_not_found(self, client: AsyncClient, admin_headers):
        """Удаление несуществующего курса → 404."""
        resp = await client.delete("/api/courses/99999", headers=admin_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_student_cannot_create_course(self, client: AsyncClient, student_headers):
        """Студент не может создать курс → 403."""
        resp = await client.post("/api/courses", json={"title": "Hack"}, headers=student_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_student_cannot_update_course(self, client: AsyncClient, admin_headers, student_headers):
        """Студент не может обновить курс → 403."""
        course = await _create_course(client, admin_headers)
        resp = await client.put(
            f"/api/courses/{course['id']}",
            json={"title": "Hack"},
            headers=student_headers,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_student_cannot_delete_course(self, client: AsyncClient, admin_headers, student_headers):
        """Студент не может удалить курс → 403."""
        course = await _create_course(client, admin_headers)
        resp = await client.delete(f"/api/courses/{course['id']}", headers=student_headers)
        assert resp.status_code == 403


# ===========================================================================
# 2. CRUD модулей
# ===========================================================================

class TestLegacyModules:

    @pytest.mark.asyncio
    async def test_create_module(self, client: AsyncClient, admin_headers):
        """Создание модуля курса."""
        course = await _create_course(client, admin_headers)
        resp = await client.post(
            f"/api/courses/{course['id']}/modules",
            json={"course_id": course["id"], "title": "Module 1", "order_index": 0},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Module 1"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_list_modules(self, client: AsyncClient, admin_headers):
        """Список модулей курса."""
        course = await _create_course(client, admin_headers)
        await _create_module(client, course["id"], admin_headers, title="M1")
        await _create_module(client, course["id"], admin_headers, title="M2", order_index=1)

        resp = await client.get(f"/api/courses/{course['id']}/modules", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_update_module(self, client: AsyncClient, admin_headers):
        """PUT: обновление заголовка модуля."""
        course = await _create_course(client, admin_headers)
        module = await _create_module(client, course["id"], admin_headers, title="Old")

        resp = await client.put(
            f"/api/courses/modules/{module['id']}",
            json={"title": "New Module"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Module"

    @pytest.mark.asyncio
    async def test_update_module_not_found(self, client: AsyncClient, admin_headers):
        """PUT несуществующего модуля → 404."""
        resp = await client.put(
            "/api/courses/modules/99999",
            json={"title": "X"},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_module(self, client: AsyncClient, admin_headers):
        """Удаление модуля → 204."""
        course = await _create_course(client, admin_headers)
        module = await _create_module(client, course["id"], admin_headers)

        resp = await client.delete(f"/api/courses/modules/{module['id']}", headers=admin_headers)
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_module_removes_from_course(self, client: AsyncClient, admin_headers):
        """После удаления модуль не появляется в списке."""
        course = await _create_course(client, admin_headers)
        module = await _create_module(client, course["id"], admin_headers)
        await client.delete(f"/api/courses/modules/{module['id']}", headers=admin_headers)

        resp = await client.get(f"/api/courses/{course['id']}/modules", headers=admin_headers)
        assert len(resp.json()) == 0

    @pytest.mark.asyncio
    async def test_delete_module_not_found(self, client: AsyncClient, admin_headers):
        """Удаление несуществующего модуля → 404."""
        resp = await client.delete("/api/courses/modules/99999", headers=admin_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_student_cannot_create_module(self, client: AsyncClient, admin_headers, student_headers):
        """Студент не может создать модуль → 403."""
        course = await _create_course(client, admin_headers)
        resp = await client.post(
            f"/api/courses/{course['id']}/modules",
            json={"title": "Hack", "order_index": 0},
            headers=student_headers,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_student_cannot_delete_module(self, client: AsyncClient, admin_headers, student_headers):
        """Студент не может удалить модуль → 403."""
        course = await _create_course(client, admin_headers)
        module = await _create_module(client, course["id"], admin_headers)
        resp = await client.delete(
            f"/api/courses/modules/{module['id']}",
            headers=student_headers,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_course_cascades_modules(self, client: AsyncClient, admin_headers):
        """Удаление курса каскадно удаляет все его модули."""
        course = await _create_course(client, admin_headers)
        await _create_module(client, course["id"], admin_headers, title="M1")
        await _create_module(client, course["id"], admin_headers, title="M2", order_index=1)

        await client.delete(f"/api/courses/{course['id']}", headers=admin_headers)

        # Курс удалён — при попытке получить модули вернётся пустой список
        # или 404 (в зависимости от реализации)
        resp = await client.get(f"/api/courses/{course['id']}/modules", headers=admin_headers)
        # Либо 404, либо пустой список — главное, модулей нет
        if resp.status_code == 200:
            assert resp.json() == []
        else:
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_module_sort_order(self, client: AsyncClient, admin_headers):
        """Модули возвращаются в порядке order_index."""
        course = await _create_course(client, admin_headers)
        await _create_module(client, course["id"], admin_headers, title="Second", order_index=1)
        await _create_module(client, course["id"], admin_headers, title="First", order_index=0)

        resp = await client.get(f"/api/courses/{course['id']}/modules", headers=admin_headers)
        modules = resp.json()
        assert modules[0]["title"] == "First"
        assert modules[1]["title"] == "Second"


# ===========================================================================
# 3. CRUD подмодулей
# ===========================================================================

class TestLegacySubmodules:

    @pytest.mark.asyncio
    async def test_create_submodule(self, client: AsyncClient, admin_headers):
        """Создание подмодуля."""
        course = await _create_course(client, admin_headers)
        module = await _create_module(client, course["id"], admin_headers)

        resp = await client.post(
            f"/api/courses/modules/{module['id']}/submodules",
            json={"module_id": module["id"], "title": "Submodule 1", "order_index": 0},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Submodule 1"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_submodule_appears_in_module_detail(self, client: AsyncClient, admin_headers):
        """Созданный подмодуль отображается в списке модулей."""
        course = await _create_course(client, admin_headers)
        module = await _create_module(client, course["id"], admin_headers)
        await _create_submodule(client, module["id"], admin_headers, title="Sub1")

        resp = await client.get(f"/api/courses/{course['id']}/modules", headers=admin_headers)
        submodules = resp.json()[0]["submodules"]
        assert len(submodules) == 1
        assert submodules[0]["title"] == "Sub1"

    @pytest.mark.asyncio
    async def test_update_submodule(self, client: AsyncClient, admin_headers):
        """PUT: обновление заголовка подмодуля."""
        course = await _create_course(client, admin_headers)
        module = await _create_module(client, course["id"], admin_headers)
        sub = await _create_submodule(client, module["id"], admin_headers, title="Old")

        resp = await client.put(
            f"/api/courses/submodules/{sub['id']}",
            json={"title": "New Sub"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Sub"

    @pytest.mark.asyncio
    async def test_update_submodule_not_found(self, client: AsyncClient, admin_headers):
        """PUT несуществующего подмодуля → 404."""
        resp = await client.put(
            "/api/courses/submodules/99999",
            json={"title": "X"},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_submodule(self, client: AsyncClient, admin_headers):
        """Удаление подмодуля → 204."""
        course = await _create_course(client, admin_headers)
        module = await _create_module(client, course["id"], admin_headers)
        sub = await _create_submodule(client, module["id"], admin_headers)

        resp = await client.delete(f"/api/courses/submodules/{sub['id']}", headers=admin_headers)
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_submodule_removes_from_module(self, client: AsyncClient, admin_headers):
        """После удаления подмодуль не появляется в модуле."""
        course = await _create_course(client, admin_headers)
        module = await _create_module(client, course["id"], admin_headers)
        sub = await _create_submodule(client, module["id"], admin_headers)
        await client.delete(f"/api/courses/submodules/{sub['id']}", headers=admin_headers)

        resp = await client.get(f"/api/courses/{course['id']}/modules", headers=admin_headers)
        submodules = resp.json()[0]["submodules"]
        assert len(submodules) == 0

    @pytest.mark.asyncio
    async def test_delete_submodule_not_found(self, client: AsyncClient, admin_headers):
        """Удаление несуществующего подмодуля → 404."""
        resp = await client.delete("/api/courses/submodules/99999", headers=admin_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_module_cascades_submodules(self, client: AsyncClient, admin_headers):
        """Удаление модуля каскадно удаляет подмодули."""
        course = await _create_course(client, admin_headers)
        module = await _create_module(client, course["id"], admin_headers)
        sub1 = await _create_submodule(client, module["id"], admin_headers, title="S1")
        sub2 = await _create_submodule(client, module["id"], admin_headers, title="S2", order_index=1)

        await client.delete(f"/api/courses/modules/{module['id']}", headers=admin_headers)

        # Подмодули больше не доступны
        for sub_id in [sub1["id"], sub2["id"]]:
            resp = await client.delete(f"/api/courses/submodules/{sub_id}", headers=admin_headers)
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_student_cannot_create_submodule(self, client: AsyncClient, admin_headers, student_headers):
        """Студент не может создать подмодуль → 403."""
        course = await _create_course(client, admin_headers)
        module = await _create_module(client, course["id"], admin_headers)
        resp = await client.post(
            f"/api/courses/modules/{module['id']}/submodules",
            json={"title": "Hack", "order_index": 0},
            headers=student_headers,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_student_cannot_delete_submodule(self, client: AsyncClient, admin_headers, student_headers):
        """Студент не может удалить подмодуль → 403."""
        course = await _create_course(client, admin_headers)
        module = await _create_module(client, course["id"], admin_headers)
        sub = await _create_submodule(client, module["id"], admin_headers)
        resp = await client.delete(
            f"/api/courses/submodules/{sub['id']}",
            headers=student_headers,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_module_and_multiple_submodules(self, client: AsyncClient, admin_headers):
        """Полный цикл: курс → модуль → несколько подмодулей."""
        course = await _create_course(client, admin_headers, title="Python")
        module = await _create_module(client, course["id"], admin_headers, title="Basics")

        for i in range(3):
            await _create_submodule(
                client, module["id"], admin_headers,
                title=f"Sub {i}", order_index=i
            )

        resp = await client.get(f"/api/courses/{course['id']}/modules", headers=admin_headers)
        submodules = resp.json()[0]["submodules"]
        assert len(submodules) == 3


# ===========================================================================
# 4. Дерево узлов через legacy API
# ===========================================================================

class TestLegacyCourseTree:

    @pytest.mark.asyncio
    async def test_course_tree_empty(self, client: AsyncClient, admin_headers):
        """Дерево нового курса пустое."""
        course = await _create_course(client, admin_headers)
        resp = await client.get(f"/api/courses/{course['id']}/tree", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_course_tree_with_nodes(self, client: AsyncClient, admin_headers):
        """Дерево содержит опубликованные узлы (видны и адмнину)."""
        course = await _create_course(client, admin_headers, status="published")

        # Создаём узел через admin API
        node_resp = await client.post(
            f"/api/admin/courses/{course['id']}/nodes",
            json={"type": "module", "title": "Module", "status": "published"},
            headers=admin_headers,
        )
        assert node_resp.status_code == 201

        resp = await client.get(f"/api/courses/{course['id']}/tree", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["title"] == "Module"

    @pytest.mark.asyncio
    async def test_student_sees_only_published_nodes_in_tree(
        self, client: AsyncClient, admin_headers, student_headers
    ):
        """Студент видит в дереве только опубликованные узлы."""
        course = await _create_course(client, admin_headers, status="published")

        await client.post(
            f"/api/admin/courses/{course['id']}/nodes",
            json={"type": "module", "title": "Published Node", "status": "published"},
            headers=admin_headers,
        )
        await client.post(
            f"/api/admin/courses/{course['id']}/nodes",
            json={"type": "module", "title": "Draft Node", "status": "draft"},
            headers=admin_headers,
        )

        resp = await client.get(f"/api/courses/{course['id']}/tree", headers=student_headers)
        assert resp.status_code == 200
        titles = [n["title"] for n in resp.json()]
        assert "Published Node" in titles
        assert "Draft Node" not in titles

    @pytest.mark.asyncio
    async def test_student_cannot_see_draft_course_tree(
        self, client: AsyncClient, admin_headers, student_headers
    ):
        """Студент не может получить дерево неопубликованного курса → 404."""
        course = await _create_course(client, admin_headers, status="draft")
        resp = await client.get(f"/api/courses/{course['id']}/tree", headers=student_headers)
        assert resp.status_code == 404
