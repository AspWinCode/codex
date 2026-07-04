"""
Тесты для Admin Courses API (/api/admin/courses/*)

Покрывают:
  - CRUD курсов (создание, получение, обновление, удаление)
  - Архивирование / разархивирование курсов и узлов
  - Валидация slug (уникальность, формат)
  - CRUD узлов дерева (CourseNode)
  - Ограничения: узел с детьми ≠ может принять задачу; узел с задачами ≠ может принять детей
  - Управление задачами узлов (прикрепить / открепить / переупорядочить)
  - Перемещение и переупорядочивание узлов
  - Пересчёт прогресса при удалении узла и открепления задачи
  - Контроль доступа (студент / без auth)
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

ADMIN_BASE = "/api/admin/courses"


async def _create_course(client: AsyncClient, headers: dict, **kwargs) -> dict:
    """Создать курс через Admin API и вернуть JSON."""
    payload = {"title": "Test Course", "status": "draft", **kwargs}
    resp = await client.post(f"{ADMIN_BASE}/", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_node(client: AsyncClient, course_id: int, headers: dict, **kwargs) -> dict:
    """Создать узел дерева через Admin API."""
    payload = {"type": "module", "title": "Test Node", "status": "draft", **kwargs}
    resp = await client.post(f"{ADMIN_BASE}/{course_id}/nodes", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _attach_new_task(client: AsyncClient, node_id: int, headers: dict, title: str = "Task") -> dict:
    """Создать новую задачу и сразу прикрепить к узлу."""
    resp = await client.post(
        f"{ADMIN_BASE}/nodes/{node_id}/tasks",
        json={"create_new_task": True, "task_title": title},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_standalone_task(client: AsyncClient, headers: dict, title: str = "Standalone") -> dict:
    """Создать задачу через Task API (без привязки к узлу)."""
    resp = await client.post(
        "/api/tasks",
        json={"title": title, "task_type": "python_io", "runner_type": "stdin_runner"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ===========================================================================
# 1. CRUD курсов через Admin API
# ===========================================================================

class TestAdminCourseCRUD:

    @pytest.mark.asyncio
    async def test_create_course_minimal(self, client: AsyncClient, admin_headers):
        """Минимальное создание курса — только title."""
        resp = await client.post(f"{ADMIN_BASE}/", json={"title": "Minimal"}, headers=admin_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Minimal"
        assert data["status"] == "draft"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_create_course_full(self, client: AsyncClient, admin_headers):
        """Создание курса со всеми полями."""
        resp = await client.post(
            f"{ADMIN_BASE}/",
            json={
                "title": "Full Course",
                "slug": "full-course",
                "description": "Описание",
                "short_description": "Кратко",
                "status": "published",
                "sort_order": 5,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["slug"] == "full-course"
        assert data["status"] == "published"
        assert data["sort_order"] == 5

    @pytest.mark.asyncio
    async def test_list_courses(self, client: AsyncClient, admin_headers):
        """Список курсов возвращает все созданные."""
        await _create_course(client, admin_headers, title="A")
        await _create_course(client, admin_headers, title="B")
        resp = await client.get(f"{ADMIN_BASE}/", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    @pytest.mark.asyncio
    async def test_get_course(self, client: AsyncClient, admin_headers):
        """Получение курса по ID."""
        course = await _create_course(client, admin_headers, title="GetMe")
        resp = await client.get(f"{ADMIN_BASE}/{course['id']}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "GetMe"

    @pytest.mark.asyncio
    async def test_get_course_not_found(self, client: AsyncClient, admin_headers):
        """Несуществующий курс → 404."""
        resp = await client.get(f"{ADMIN_BASE}/99999", headers=admin_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_course_title(self, client: AsyncClient, admin_headers):
        """PATCH: обновление заголовка курса."""
        course = await _create_course(client, admin_headers, title="Old Title")
        resp = await client.patch(
            f"{ADMIN_BASE}/{course['id']}",
            json={"title": "New Title"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    @pytest.mark.asyncio
    async def test_update_course_status(self, client: AsyncClient, admin_headers):
        """PATCH: перевод курса из draft в published."""
        course = await _create_course(client, admin_headers)
        resp = await client.patch(
            f"{ADMIN_BASE}/{course['id']}",
            json={"status": "published"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"

    @pytest.mark.asyncio
    async def test_delete_course(self, client: AsyncClient, admin_headers):
        """Удаление курса → 204, после — 404."""
        course = await _create_course(client, admin_headers)
        cid = course["id"]
        resp = await client.delete(f"{ADMIN_BASE}/{cid}", headers=admin_headers)
        assert resp.status_code == 204
        # Убеждаемся, что курс действительно удалён
        get_resp = await client.get(f"{ADMIN_BASE}/{cid}", headers=admin_headers)
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_course_not_found(self, client: AsyncClient, admin_headers):
        """Удаление несуществующего курса → 404."""
        resp = await client.delete(f"{ADMIN_BASE}/99999", headers=admin_headers)
        assert resp.status_code == 404


# ===========================================================================
# 2. Архивирование / разархивирование курсов
# ===========================================================================

class TestAdminCourseArchive:

    @pytest.mark.asyncio
    async def test_archive_course(self, client: AsyncClient, admin_headers):
        """Архивирование курса: status=archived, archived_at выставлен."""
        course = await _create_course(client, admin_headers)
        resp = await client.post(f"{ADMIN_BASE}/{course['id']}/archive", headers=admin_headers)
        assert resp.status_code == 204

        detail = await client.get(f"{ADMIN_BASE}/{course['id']}", headers=admin_headers)
        data = detail.json()
        assert data["status"] == "archived"
        assert data["archived_at"] is not None

    @pytest.mark.asyncio
    async def test_unarchive_course_becomes_published(self, client: AsyncClient, admin_headers):
        """Разархивирование курса → status=published (не draft!), archived_at=None."""
        course = await _create_course(client, admin_headers)
        await client.post(f"{ADMIN_BASE}/{course['id']}/archive", headers=admin_headers)

        resp = await client.post(f"{ADMIN_BASE}/{course['id']}/unarchive", headers=admin_headers)
        assert resp.status_code == 204

        detail = await client.get(f"{ADMIN_BASE}/{course['id']}", headers=admin_headers)
        data = detail.json()
        assert data["status"] == "published", "После разархивирования курс должен быть published, а не draft"
        assert data["archived_at"] is None

    @pytest.mark.asyncio
    async def test_archive_via_patch(self, client: AsyncClient, admin_headers):
        """Архивирование через PATCH status=archived выставляет archived_at."""
        course = await _create_course(client, admin_headers)
        resp = await client.patch(
            f"{ADMIN_BASE}/{course['id']}",
            json={"status": "archived"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"
        assert resp.json()["archived_at"] is not None

    @pytest.mark.asyncio
    async def test_unarchive_via_patch_clears_archived_at(self, client: AsyncClient, admin_headers):
        """При снятии архивного статуса через PATCH archived_at обнуляется."""
        course = await _create_course(client, admin_headers)
        await client.patch(f"{ADMIN_BASE}/{course['id']}", json={"status": "archived"}, headers=admin_headers)

        resp = await client.patch(
            f"{ADMIN_BASE}/{course['id']}",
            json={"status": "published"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["archived_at"] is None

    @pytest.mark.asyncio
    async def test_cannot_add_node_to_archived_course(self, client: AsyncClient, admin_headers):
        """Нельзя добавить узел к архивному курсу."""
        course = await _create_course(client, admin_headers)
        await client.post(f"{ADMIN_BASE}/{course['id']}/archive", headers=admin_headers)

        resp = await client.post(
            f"{ADMIN_BASE}/{course['id']}/nodes",
            json={"type": "module", "title": "Node"},
            headers=admin_headers,
        )
        assert resp.status_code == 400


# ===========================================================================
# 3. Валидация slug
# ===========================================================================

class TestAdminCourseSlug:

    @pytest.mark.asyncio
    async def test_duplicate_slug_on_create_rejected(self, client: AsyncClient, admin_headers):
        """Дублирующийся slug при создании → 400."""
        await _create_course(client, admin_headers, slug="my-slug")
        resp = await client.post(
            f"{ADMIN_BASE}/",
            json={"title": "Another", "slug": "my-slug"},
            headers=admin_headers,
        )
        assert resp.status_code == 400
        assert "slug" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_duplicate_slug_on_update_rejected(self, client: AsyncClient, admin_headers):
        """Дублирующийся slug при PATCH → 400."""
        await _create_course(client, admin_headers, slug="taken-slug")
        course2 = await _create_course(client, admin_headers, slug="other-slug", title="C2")

        resp = await client.patch(
            f"{ADMIN_BASE}/{course2['id']}",
            json={"slug": "taken-slug"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_with_same_slug_ok(self, client: AsyncClient, admin_headers):
        """Обновление курса с тем же slug (не меняется) → 200."""
        course = await _create_course(client, admin_headers, slug="my-slug")
        resp = await client.patch(
            f"{ADMIN_BASE}/{course['id']}",
            json={"title": "New Title", "slug": "my-slug"},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_slug_uppercase_rejected(self, client: AsyncClient, admin_headers):
        """Slug с заглавными буквами → 422 (Pydantic pattern validation)."""
        resp = await client.post(
            f"{ADMIN_BASE}/",
            json={"title": "C", "slug": "My-Slug"},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_slug_with_spaces_rejected(self, client: AsyncClient, admin_headers):
        """Slug с пробелами → 422."""
        resp = await client.post(
            f"{ADMIN_BASE}/",
            json={"title": "C", "slug": "my slug"},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_slug_with_underscore_rejected(self, client: AsyncClient, admin_headers):
        """Slug с подчёркиванием → 422."""
        resp = await client.post(
            f"{ADMIN_BASE}/",
            json={"title": "C", "slug": "my_slug"},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_title_rejected(self, client: AsyncClient, admin_headers):
        """Пустой title → 422."""
        resp = await client.post(
            f"{ADMIN_BASE}/",
            json={"title": ""},
            headers=admin_headers,
        )
        assert resp.status_code == 422


# ===========================================================================
# 4. CRUD узлов дерева (CourseNode)
# ===========================================================================

class TestAdminNodeCRUD:

    @pytest.mark.asyncio
    async def test_create_root_node(self, client: AsyncClient, admin_headers):
        """Создание корневого узла (без parent_id)."""
        course = await _create_course(client, admin_headers)
        resp = await client.post(
            f"{ADMIN_BASE}/{course['id']}/nodes",
            json={"type": "module", "title": "Module 1", "sort_order": 0},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Module 1"
        assert data["type"] == "module"
        assert data["parent_id"] is None
        assert data["course_id"] == course["id"]

    @pytest.mark.asyncio
    async def test_create_child_node(self, client: AsyncClient, admin_headers):
        """Создание дочернего узла (с parent_id)."""
        course = await _create_course(client, admin_headers)
        parent = await _create_node(client, course["id"], admin_headers, type="module", title="Parent")
        resp = await client.post(
            f"{ADMIN_BASE}/{course['id']}/nodes",
            json={"type": "submodule", "title": "Child", "parent_id": parent["id"]},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["parent_id"] == parent["id"]
        assert data["type"] == "submodule"

    @pytest.mark.asyncio
    async def test_get_tree_empty(self, client: AsyncClient, admin_headers):
        """Пустое дерево для нового курса."""
        course = await _create_course(client, admin_headers)
        resp = await client.get(f"{ADMIN_BASE}/{course['id']}/tree", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_get_tree_with_nodes(self, client: AsyncClient, admin_headers):
        """Дерево содержит созданные узлы."""
        course = await _create_course(client, admin_headers)
        parent = await _create_node(client, course["id"], admin_headers, title="Root")
        await client.post(
            f"{ADMIN_BASE}/{course['id']}/nodes",
            json={"type": "submodule", "title": "Child", "parent_id": parent["id"]},
            headers=admin_headers,
        )

        resp = await client.get(f"{ADMIN_BASE}/{course['id']}/tree", headers=admin_headers)
        assert resp.status_code == 200
        tree = resp.json()
        assert len(tree) == 1
        assert tree[0]["title"] == "Root"
        assert len(tree[0]["children"]) == 1
        assert tree[0]["children"][0]["title"] == "Child"

    @pytest.mark.asyncio
    async def test_get_node_by_id(self, client: AsyncClient, admin_headers):
        """Получение узла по ID."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers, title="MyNode")
        resp = await client.get(f"{ADMIN_BASE}/nodes/{node['id']}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "MyNode"

    @pytest.mark.asyncio
    async def test_get_node_not_found(self, client: AsyncClient, admin_headers):
        """Несуществующий узел → 404."""
        resp = await client.get(f"{ADMIN_BASE}/nodes/99999", headers=admin_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_node_title(self, client: AsyncClient, admin_headers):
        """PATCH: обновление заголовка узла."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers, title="Old")
        resp = await client.patch(
            f"{ADMIN_BASE}/nodes/{node['id']}",
            json={"title": "New"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New"

    @pytest.mark.asyncio
    async def test_update_node_status_to_published(self, client: AsyncClient, admin_headers):
        """PATCH: перевод узла в статус published."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)
        resp = await client.patch(
            f"{ADMIN_BASE}/nodes/{node['id']}",
            json={"status": "published"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"

    @pytest.mark.asyncio
    async def test_delete_node(self, client: AsyncClient, admin_headers):
        """Удаление узла → 204, после — 404."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)
        nid = node["id"]

        resp = await client.delete(f"{ADMIN_BASE}/nodes/{nid}", headers=admin_headers)
        assert resp.status_code == 204

        get_resp = await client.get(f"{ADMIN_BASE}/nodes/{nid}", headers=admin_headers)
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_node_cascades_children(self, client: AsyncClient, admin_headers):
        """Удаление родительского узла каскадно удаляет дочерние."""
        course = await _create_course(client, admin_headers)
        parent = await _create_node(client, course["id"], admin_headers, title="Parent")
        child_resp = await client.post(
            f"{ADMIN_BASE}/{course['id']}/nodes",
            json={"type": "submodule", "title": "Child", "parent_id": parent["id"]},
            headers=admin_headers,
        )
        child_id = child_resp.json()["id"]

        # Удаляем родителя
        await client.delete(f"{ADMIN_BASE}/nodes/{parent['id']}", headers=admin_headers)

        # Дочерний узел тоже должен быть удалён
        get_child = await client.get(f"{ADMIN_BASE}/nodes/{child_id}", headers=admin_headers)
        assert get_child.status_code == 404

    @pytest.mark.asyncio
    async def test_tree_node_flags_leaf(self, client: AsyncClient, admin_headers):
        """Конечный узел (без детей): can_attach_tasks=True, can_create_children=True."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)

        resp = await client.get(f"{ADMIN_BASE}/nodes/{node['id']}", headers=admin_headers)
        data = resp.json()
        assert data["can_attach_tasks"] is True
        assert data["can_create_children"] is True
        assert data["has_children"] is False
        assert data["task_count"] == 0


# ===========================================================================
# 5. Архивирование / разархивирование узлов
# ===========================================================================

class TestAdminNodeArchive:

    @pytest.mark.asyncio
    async def test_archive_node(self, client: AsyncClient, admin_headers):
        """Архивирование узла: status=archived, archived_at выставлен."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)

        resp = await client.post(f"{ADMIN_BASE}/nodes/{node['id']}/archive", headers=admin_headers)
        assert resp.status_code == 204

        detail = await client.get(f"{ADMIN_BASE}/nodes/{node['id']}", headers=admin_headers)
        data = detail.json()
        assert data["status"] == "archived"
        assert data["archived_at"] is not None

    @pytest.mark.asyncio
    async def test_unarchive_node_becomes_published(self, client: AsyncClient, admin_headers):
        """Разархивирование узла → status=published (НЕ draft!)."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)
        await client.post(f"{ADMIN_BASE}/nodes/{node['id']}/archive", headers=admin_headers)

        resp = await client.post(f"{ADMIN_BASE}/nodes/{node['id']}/unarchive", headers=admin_headers)
        assert resp.status_code == 204

        detail = await client.get(f"{ADMIN_BASE}/nodes/{node['id']}", headers=admin_headers)
        data = detail.json()
        assert data["status"] == "published", (
            "После разархивирования узел должен стать published, а не draft"
        )
        assert data["archived_at"] is None

    @pytest.mark.asyncio
    async def test_cannot_attach_task_to_archived_node(self, client: AsyncClient, admin_headers):
        """Нельзя прикрепить задачу к архивному узлу."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)
        await client.post(f"{ADMIN_BASE}/nodes/{node['id']}/archive", headers=admin_headers)

        resp = await client.post(
            f"{ADMIN_BASE}/nodes/{node['id']}/tasks",
            json={"create_new_task": True, "task_title": "T"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_cannot_create_child_under_archived_node(self, client: AsyncClient, admin_headers):
        """Нельзя добавить дочерний узел к архивному родителю."""
        course = await _create_course(client, admin_headers)
        parent = await _create_node(client, course["id"], admin_headers)
        await client.post(f"{ADMIN_BASE}/nodes/{parent['id']}/archive", headers=admin_headers)

        resp = await client.post(
            f"{ADMIN_BASE}/{course['id']}/nodes",
            json={"type": "submodule", "title": "Child", "parent_id": parent["id"]},
            headers=admin_headers,
        )
        assert resp.status_code == 400


# ===========================================================================
# 6. Ограничения: дети vs задачи
# ===========================================================================

class TestNodeTaskChildConstraints:

    @pytest.mark.asyncio
    async def test_cannot_attach_task_to_node_with_children(self, client: AsyncClient, admin_headers):
        """Нельзя прикрепить задачу к узлу, у которого уже есть дочерние узлы."""
        course = await _create_course(client, admin_headers)
        parent = await _create_node(client, course["id"], admin_headers, title="Parent")
        # Создаём дочерний узел
        await client.post(
            f"{ADMIN_BASE}/{course['id']}/nodes",
            json={"type": "submodule", "title": "Child", "parent_id": parent["id"]},
            headers=admin_headers,
        )
        # Пытаемся прикрепить задачу к родителю — должно быть запрещено
        resp = await client.post(
            f"{ADMIN_BASE}/nodes/{parent['id']}/tasks",
            json={"create_new_task": True, "task_title": "T"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_cannot_create_child_under_node_with_tasks(self, client: AsyncClient, admin_headers):
        """Нельзя создать дочерний узел у узла, к которому уже прикреплены задачи."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers, title="Leaf")
        # Прикрепляем задачу
        await _attach_new_task(client, node["id"], admin_headers)

        # Пытаемся создать дочерний узел — должно быть запрещено
        resp = await client.post(
            f"{ADMIN_BASE}/{course['id']}/nodes",
            json={"type": "submodule", "title": "Child", "parent_id": node["id"]},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_node_with_tasks_cannot_create_children_flag(self, client: AsyncClient, admin_headers):
        """После прикрепления задачи флаг can_create_children=False."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)
        await _attach_new_task(client, node["id"], admin_headers)

        resp = await client.get(f"{ADMIN_BASE}/nodes/{node['id']}", headers=admin_headers)
        data = resp.json()
        assert data["can_create_children"] is False
        assert data["can_attach_tasks"] is True

    @pytest.mark.asyncio
    async def test_node_with_children_cannot_attach_tasks_flag(self, client: AsyncClient, admin_headers):
        """После добавления дочернего узла флаг can_attach_tasks=False."""
        course = await _create_course(client, admin_headers)
        parent = await _create_node(client, course["id"], admin_headers)
        await client.post(
            f"{ADMIN_BASE}/{course['id']}/nodes",
            json={"type": "submodule", "title": "Child", "parent_id": parent["id"]},
            headers=admin_headers,
        )

        resp = await client.get(f"{ADMIN_BASE}/nodes/{parent['id']}", headers=admin_headers)
        data = resp.json()
        assert data["can_attach_tasks"] is False
        assert data["can_create_children"] is True


# ===========================================================================
# 7. Управление задачами узлов
# ===========================================================================

class TestAdminNodeTasks:

    @pytest.mark.asyncio
    async def test_attach_existing_task(self, client: AsyncClient, admin_headers):
        """Прикрепить существующую задачу к узлу."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)
        task = await _create_standalone_task(client, admin_headers, "Existing")

        resp = await client.post(
            f"{ADMIN_BASE}/nodes/{node['id']}/tasks",
            json={"task_id": task["id"], "create_new_task": False},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["task_id"] == task["id"]
        assert data["task_title"] == "Existing"

    @pytest.mark.asyncio
    async def test_create_and_attach_new_task(self, client: AsyncClient, admin_headers):
        """Создать новую задачу inline и прикрепить к узлу."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)

        resp = await client.post(
            f"{ADMIN_BASE}/nodes/{node['id']}/tasks",
            json={"create_new_task": True, "task_title": "New Inline Task"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["task_title"] == "New Inline Task"
        assert data["node_id"] == node["id"]

    @pytest.mark.asyncio
    async def test_list_node_tasks(self, client: AsyncClient, admin_headers):
        """Список задач узла."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)
        await _attach_new_task(client, node["id"], admin_headers, "T1")
        await _attach_new_task(client, node["id"], admin_headers, "T2")

        resp = await client.get(f"{ADMIN_BASE}/nodes/{node['id']}/tasks", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_detach_task(self, client: AsyncClient, admin_headers):
        """Открепить задачу от узла."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)
        node_task = await _attach_new_task(client, node["id"], admin_headers)

        resp = await client.delete(
            f"{ADMIN_BASE}/nodes/{node['id']}/tasks/{node_task['id']}",
            headers=admin_headers,
        )
        assert resp.status_code == 204

        # Задача должна отсутствовать в списке
        tasks = await client.get(f"{ADMIN_BASE}/nodes/{node['id']}/tasks", headers=admin_headers)
        assert len(tasks.json()) == 0

    @pytest.mark.asyncio
    async def test_cannot_attach_same_task_twice(self, client: AsyncClient, admin_headers):
        """Повторное прикрепление той же задачи к тому же узлу → 400."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)
        task = await _create_standalone_task(client, admin_headers)

        await client.post(
            f"{ADMIN_BASE}/nodes/{node['id']}/tasks",
            json={"task_id": task["id"], "create_new_task": False},
            headers=admin_headers,
        )
        resp = await client.post(
            f"{ADMIN_BASE}/nodes/{node['id']}/tasks",
            json={"task_id": task["id"], "create_new_task": False},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_new_task_requires_title(self, client: AsyncClient, admin_headers):
        """create_new_task=True без task_title → 400."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)

        resp = await client.post(
            f"{ADMIN_BASE}/nodes/{node['id']}/tasks",
            json={"create_new_task": True},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_attach_without_task_id_rejected(self, client: AsyncClient, admin_headers):
        """create_new_task=False без task_id → 400."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)

        resp = await client.post(
            f"{ADMIN_BASE}/nodes/{node['id']}/tasks",
            json={"create_new_task": False},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_reorder_node_tasks(self, client: AsyncClient, admin_headers):
        """Переупорядочивание задач в узле."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)
        nt1 = await _attach_new_task(client, node["id"], admin_headers, "T1")
        nt2 = await _attach_new_task(client, node["id"], admin_headers, "T2")

        resp = await client.post(
            f"{ADMIN_BASE}/nodes/{node['id']}/tasks/reorder",
            json=[
                {"id": nt1["id"], "sort_order": 10},
                {"id": nt2["id"], "sort_order": 5},
            ],
            headers=admin_headers,
        )
        assert resp.status_code == 204

        tasks = await client.get(f"{ADMIN_BASE}/nodes/{node['id']}/tasks", headers=admin_headers)
        by_id = {t["id"]: t for t in tasks.json()}
        assert by_id[nt1["id"]]["sort_order"] == 10
        assert by_id[nt2["id"]]["sort_order"] == 5

    @pytest.mark.asyncio
    async def test_task_sort_order_auto_assigned(self, client: AsyncClient, admin_headers):
        """sort_order задач автоматически инкрементируется."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)
        nt1 = await _attach_new_task(client, node["id"], admin_headers, "T1")
        nt2 = await _attach_new_task(client, node["id"], admin_headers, "T2")

        assert nt2["sort_order"] > nt1["sort_order"]

    @pytest.mark.asyncio
    async def test_node_task_count_updates(self, client: AsyncClient, admin_headers):
        """task_count узла корректно отображает количество задач."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)

        resp_before = await client.get(f"{ADMIN_BASE}/nodes/{node['id']}", headers=admin_headers)
        assert resp_before.json()["task_count"] == 0

        nt = await _attach_new_task(client, node["id"], admin_headers)

        resp_after = await client.get(f"{ADMIN_BASE}/nodes/{node['id']}", headers=admin_headers)
        assert resp_after.json()["task_count"] == 1

        await client.delete(
            f"{ADMIN_BASE}/nodes/{node['id']}/tasks/{nt['id']}",
            headers=admin_headers,
        )
        resp_final = await client.get(f"{ADMIN_BASE}/nodes/{node['id']}", headers=admin_headers)
        assert resp_final.json()["task_count"] == 0


# ===========================================================================
# 8. Перемещение узлов (move)
# ===========================================================================

class TestAdminNodeMove:

    @pytest.mark.asyncio
    async def test_move_node_to_new_parent(self, client: AsyncClient, admin_headers):
        """Перемещение узла в нового родителя."""
        course = await _create_course(client, admin_headers)
        parent_a = await _create_node(client, course["id"], admin_headers, title="ParentA")
        parent_b = await _create_node(client, course["id"], admin_headers, title="ParentB")
        child = await client.post(
            f"{ADMIN_BASE}/{course['id']}/nodes",
            json={"type": "submodule", "title": "Child", "parent_id": parent_a["id"]},
            headers=admin_headers,
        )
        child_id = child.json()["id"]

        # Перемещаем child из ParentA в ParentB
        resp = await client.post(
            f"{ADMIN_BASE}/nodes/{child_id}/move",
            json={"new_parent_id": parent_b["id"], "new_sort_order": 0},
            headers=admin_headers,
        )
        assert resp.status_code == 204

        # Проверяем, что parent_id изменился
        node_detail = await client.get(f"{ADMIN_BASE}/nodes/{child_id}", headers=admin_headers)
        assert node_detail.json()["parent_id"] == parent_b["id"]

    @pytest.mark.asyncio
    async def test_move_node_to_root(self, client: AsyncClient, admin_headers):
        """Перемещение узла на корневой уровень (new_parent_id=None)."""
        course = await _create_course(client, admin_headers)
        parent = await _create_node(client, course["id"], admin_headers, title="Parent")
        child_resp = await client.post(
            f"{ADMIN_BASE}/{course['id']}/nodes",
            json={"type": "submodule", "title": "Child", "parent_id": parent["id"]},
            headers=admin_headers,
        )
        child_id = child_resp.json()["id"]

        resp = await client.post(
            f"{ADMIN_BASE}/nodes/{child_id}/move",
            json={"new_parent_id": None},
            headers=admin_headers,
        )
        assert resp.status_code == 204

        node_detail = await client.get(f"{ADMIN_BASE}/nodes/{child_id}", headers=admin_headers)
        assert node_detail.json()["parent_id"] is None

    @pytest.mark.asyncio
    async def test_cannot_move_node_into_itself(self, client: AsyncClient, admin_headers):
        """Нельзя переместить узел в самого себя → 400."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)

        resp = await client.post(
            f"{ADMIN_BASE}/nodes/{node['id']}/move",
            json={"new_parent_id": node["id"]},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_cannot_move_node_into_descendant(self, client: AsyncClient, admin_headers):
        """Нельзя переместить узел внутрь его собственного потомка → 400."""
        course = await _create_course(client, admin_headers)
        root = await _create_node(client, course["id"], admin_headers, title="Root")
        child_resp = await client.post(
            f"{ADMIN_BASE}/{course['id']}/nodes",
            json={"type": "submodule", "title": "Child", "parent_id": root["id"]},
            headers=admin_headers,
        )
        child_id = child_resp.json()["id"]

        # Пытаемся переместить root в его потомка child
        resp = await client.post(
            f"{ADMIN_BASE}/nodes/{root['id']}/move",
            json={"new_parent_id": child_id},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_cannot_move_to_parent_with_tasks(self, client: AsyncClient, admin_headers):
        """Нельзя переместить узел в родителя, у которого есть задачи → 400."""
        course = await _create_course(client, admin_headers)
        target_parent = await _create_node(client, course["id"], admin_headers, title="WithTasks")
        await _attach_new_task(client, target_parent["id"], admin_headers)
        moving_node = await _create_node(client, course["id"], admin_headers, title="Mover")

        resp = await client.post(
            f"{ADMIN_BASE}/nodes/{moving_node['id']}/move",
            json={"new_parent_id": target_parent["id"]},
            headers=admin_headers,
        )
        assert resp.status_code == 400


# ===========================================================================
# 9. Переупорядочивание соседних узлов (reorder)
# ===========================================================================

class TestAdminNodeReorder:

    @pytest.mark.asyncio
    async def test_reorder_nodes(self, client: AsyncClient, admin_headers):
        """Переупорядочивание корневых узлов."""
        course = await _create_course(client, admin_headers)
        n1 = await _create_node(client, course["id"], admin_headers, title="N1", sort_order=0)
        n2 = await _create_node(client, course["id"], admin_headers, title="N2", sort_order=1)

        resp = await client.post(
            f"{ADMIN_BASE}/nodes/reorder",
            json=[
                {"id": n1["id"], "sort_order": 99},
                {"id": n2["id"], "sort_order": 0},
            ],
            headers=admin_headers,
        )
        assert resp.status_code == 204

        # Проверяем что sort_order изменились
        n1_updated = await client.get(f"{ADMIN_BASE}/nodes/{n1['id']}", headers=admin_headers)
        n2_updated = await client.get(f"{ADMIN_BASE}/nodes/{n2['id']}", headers=admin_headers)
        assert n1_updated.json()["sort_order"] == 99
        assert n2_updated.json()["sort_order"] == 0

    @pytest.mark.asyncio
    async def test_reorder_empty_list_ok(self, client: AsyncClient, admin_headers):
        """Пустой список в reorder — 204 без ошибок."""
        resp = await client.post(
            f"{ADMIN_BASE}/nodes/reorder",
            json=[],
            headers=admin_headers,
        )
        assert resp.status_code == 204


# ===========================================================================
# 10. Пересчёт прогресса при изменениях
# ===========================================================================

class TestProgressRecalculation:

    @pytest.mark.asyncio
    async def test_progress_recalculated_after_node_delete(
        self, client: AsyncClient, admin_headers, db: AsyncSession, student_user
    ):
        """
        Сценарий: студент имеет прогресс по курсу.
        После удаления узла счётчики пересчитываются.
        """
        from app.models.user_course_progress import UserCourseProgress
        from app.models.user_course_node_task_progress import UserCourseNodeTaskProgress, NodeTaskProgressStatus
        from app.models.course_node_task import CourseNodeTask

        # Создаём опубликованный курс и опубликованный узел с задачей
        course = await _create_course(client, admin_headers, status="published")
        node_resp = await client.post(
            f"{ADMIN_BASE}/{course['id']}/nodes",
            json={"type": "module", "title": "Leaf", "status": "published"},
            headers=admin_headers,
        )
        node = node_resp.json()
        nt = await _attach_new_task(client, node["id"], admin_headers)

        # Вручную создаём записи прогресса как если бы студент решил задачу
        course_progress = UserCourseProgress(
            user_id=student_user.id,
            course_id=course["id"],
            completed_tasks_count=1,
            total_tasks_count=1,
            progress_percent=100.0,
        )
        db.add(course_progress)

        task_progress = UserCourseNodeTaskProgress(
            user_id=student_user.id,
            node_task_id=nt["id"],
            status=NodeTaskProgressStatus.completed,
        )
        db.add(task_progress)
        await db.flush()

        # Удаляем узел с задачей
        del_resp = await client.delete(f"{ADMIN_BASE}/nodes/{node['id']}", headers=admin_headers)
        assert del_resp.status_code == 204

        # Проверяем, что прогресс пересчитан: 0 задач
        await db.refresh(course_progress)
        assert course_progress.total_tasks_count == 0, (
            "После удаления узла total_tasks_count должен стать 0"
        )
        assert course_progress.completed_tasks_count == 0, (
            "После удаления задачи completed_tasks_count должен стать 0"
        )
        assert course_progress.progress_percent == 0.0

    @pytest.mark.asyncio
    async def test_progress_recalculated_after_task_detach(
        self, client: AsyncClient, admin_headers, db: AsyncSession, student_user
    ):
        """
        Сценарий: студент имеет прогресс по курсу (2 задачи, 1 решена).
        После открепления задачи счётчики пересчитываются.
        """
        from app.models.user_course_progress import UserCourseProgress
        from app.models.user_course_node_task_progress import UserCourseNodeTaskProgress, NodeTaskProgressStatus

        # Создаём опубликованный курс, узел с двумя задачами
        course = await _create_course(client, admin_headers, status="published")
        node_resp = await client.post(
            f"{ADMIN_BASE}/{course['id']}/nodes",
            json={"type": "module", "title": "Node", "status": "published"},
            headers=admin_headers,
        )
        node = node_resp.json()
        nt1 = await _attach_new_task(client, node["id"], admin_headers, "Task1")
        nt2 = await _attach_new_task(client, node["id"], admin_headers, "Task2")

        # Студент решил первую задачу
        course_progress = UserCourseProgress(
            user_id=student_user.id,
            course_id=course["id"],
            completed_tasks_count=1,
            total_tasks_count=2,
            progress_percent=50.0,
        )
        db.add(course_progress)
        task_progress = UserCourseNodeTaskProgress(
            user_id=student_user.id,
            node_task_id=nt1["id"],
            status=NodeTaskProgressStatus.completed,
        )
        db.add(task_progress)
        await db.flush()

        # Откренпяем первую задачу (решённую)
        del_resp = await client.delete(
            f"{ADMIN_BASE}/nodes/{node['id']}/tasks/{nt1['id']}",
            headers=admin_headers,
        )
        assert del_resp.status_code == 204

        # Прогресс: 1 задача осталась, 0 решено (т.к. именно эта была решена)
        await db.refresh(course_progress)
        assert course_progress.total_tasks_count == 1
        assert course_progress.completed_tasks_count == 0
        assert course_progress.progress_percent == 0.0


# ===========================================================================
# 11. Контроль доступа
# ===========================================================================

class TestAccessControl:

    @pytest.mark.asyncio
    async def test_student_cannot_list_admin_courses(self, client: AsyncClient, student_headers):
        """Студент не имеет доступа к /api/admin/courses/ → 403."""
        resp = await client.get(f"{ADMIN_BASE}/", headers=student_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_student_cannot_create_admin_course(self, client: AsyncClient, student_headers):
        """Студент не может создать курс через Admin API → 403."""
        resp = await client.post(f"{ADMIN_BASE}/", json={"title": "Hack"}, headers=student_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_student_cannot_delete_course(self, client: AsyncClient, admin_headers, student_headers):
        """Студент не может удалить курс → 403."""
        course = await _create_course(client, admin_headers)
        resp = await client.delete(f"{ADMIN_BASE}/{course['id']}", headers=student_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_student_cannot_archive_course(self, client: AsyncClient, admin_headers, student_headers):
        """Студент не может архивировать курс → 403."""
        course = await _create_course(client, admin_headers)
        resp = await client.post(f"{ADMIN_BASE}/{course['id']}/archive", headers=student_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_student_cannot_create_node(self, client: AsyncClient, admin_headers, student_headers):
        """Студент не может создать узел дерева → 403."""
        course = await _create_course(client, admin_headers)
        resp = await client.post(
            f"{ADMIN_BASE}/{course['id']}/nodes",
            json={"type": "module", "title": "Hack"},
            headers=student_headers,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_student_cannot_delete_node(self, client: AsyncClient, admin_headers, student_headers):
        """Студент не может удалить узел → 403."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)
        resp = await client.delete(f"{ADMIN_BASE}/nodes/{node['id']}", headers=student_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_student_cannot_attach_task(self, client: AsyncClient, admin_headers, student_headers):
        """Студент не может прикрепить задачу → 403."""
        course = await _create_course(client, admin_headers)
        node = await _create_node(client, course["id"], admin_headers)
        resp = await client.post(
            f"{ADMIN_BASE}/nodes/{node['id']}/tasks",
            json={"create_new_task": True, "task_title": "Hack"},
            headers=student_headers,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_access_admin(self, client: AsyncClient):
        """Без токена → 403 (или 401) для admin endpoints."""
        resp = await client.get(f"{ADMIN_BASE}/")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_student_sees_only_published_courses(
        self, client: AsyncClient, admin_headers, student_headers
    ):
        """Студент видит только опубликованные курсы в /api/courses."""
        await _create_course(client, admin_headers, title="Draft Course", status="draft")
        await _create_course(client, admin_headers, title="Published Course", status="published")

        resp = await client.get("/api/courses", headers=student_headers)
        assert resp.status_code == 200
        titles = [c["title"] for c in resp.json()]
        assert "Published Course" in titles
        assert "Draft Course" not in titles

    @pytest.mark.asyncio
    async def test_admin_sees_all_courses(
        self, client: AsyncClient, admin_headers
    ):
        """Админ видит все курсы включая draft."""
        await _create_course(client, admin_headers, title="Draft", status="draft")
        await _create_course(client, admin_headers, title="Published", status="published")

        resp = await client.get("/api/courses", headers=admin_headers)
        assert resp.status_code == 200
        titles = [c["title"] for c in resp.json()]
        assert "Draft" in titles
        assert "Published" in titles
