from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course_node import CourseNode, CourseNodeStatus
from app.models.course_node_task import CourseNodeTask


async def get_node(db: AsyncSession, node_id: int) -> Optional[CourseNode]:
    r = await db.execute(
        select(CourseNode)
        .options(
            selectinload(CourseNode.children),
            selectinload(CourseNode.node_tasks),
        )
        .where(CourseNode.id == node_id)
    )
    return r.scalar_one_or_none()


def is_leaf_node(node: CourseNode) -> bool:
    return not node.children


def can_create_child(node: CourseNode) -> bool:
    """Можно ли добавить дочерний узел. Единственное ограничение — архив."""
    return node.status != CourseNodeStatus.archived


def can_attach_task(node: CourseNode) -> bool:
    """Можно ли прикрепить задачу. Единственное ограничение — архив."""
    return node.status != CourseNodeStatus.archived


async def validate_move(
    db: AsyncSession,
    *,
    node_id: int,
    new_parent_id: Optional[int],
) -> tuple[CourseNode, Optional[CourseNode]]:
    """Проверка перед перемещением узла.

    Возвращает (node, new_parent).
    """
    node = await get_node(db, node_id)
    if not node:
        raise ValueError("Node not found")

    new_parent: Optional[CourseNode] = None
    if new_parent_id is not None:
        new_parent = await get_node(db, new_parent_id)
        if not new_parent:
            raise ValueError("New parent not found")

        # Нельзя переместить в другой курс
        if new_parent.course_id != node.course_id:
            raise ValueError("New parent must belong to the same course")

        # Новый родитель не должен быть архивирован и иметь задачи
        if new_parent.status == CourseNodeStatus.archived:
            raise ValueError("New parent is archived")
        if new_parent.node_tasks:
            raise ValueError("New parent has tasks")

        # Нельзя переместить узел внутрь самого себя или своего потомка
        if new_parent.id == node.id:
            raise ValueError("Cannot move node into itself")
        # Проверяем, является ли new_parent потомком node, обходя вверх по parent_id
        current_parent_id = new_parent.parent_id
        while current_parent_id is not None:
            if current_parent_id == node.id:
                raise ValueError("Cannot move node into its descendant")
            r_parent = await db.execute(
                select(CourseNode.parent_id).where(CourseNode.id == current_parent_id)
            )
            current_parent_id = r_parent.scalar_one_or_none()

    return node, new_parent

