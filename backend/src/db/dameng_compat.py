"""达梦 dmSQLAlchemy 方言的兼容性补丁。

dmSQLAlchemy 2.0.17 的反射实现有两处 bug，都会在 Alembic autogenerate 时触发：

1. ``get_multi_table_comment`` 在 ``filter_names`` 为空列表时（反射全库表注释的
   必经路径）不会生成 ``WHERE ... IN (...)`` 子句，却无条件追加 ``)``，拼出
   ``SELECT ... FROM user_tab_comments)`` 非法 SQL（达梦报 CODE:-2007）。
   这里替换为修正版本：仅在确实生成 IN 子句时才追加右括号。

2. ``get_table_options`` 会返回 ``dm_tablespace``，但 ``construct_arguments``
   的 Table 项只声明了 resolve_synonyms/on_commit/compress，导致 SQLAlchemy
   的 ``Table._validate_dialect_kwargs`` 校验抛
   ``ArgumentError: Argument 'dm_tablespace' is not accepted``。
   这里为 Table 项补声明 ``tablespace``。

此外模块还提供 ``compare_dameng_type`` 供 Alembic ``compare_type`` 使用，
消除达梦 VARCHAR 长度反射为 ``Decimal`` 造成的假阳性类型变更。

这些补丁只影响元数据反射/比较，不涉及任何数据读写。
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import String as _sa_String
from sqlalchemy import schema as _sa_schema
from sqlalchemy import sql as _sa_sql

import dmSQLAlchemy.base as _dm_base
from dmSQLAlchemy.dmpython import DMDialect_dmPython


def _get_multi_table_comment(
    self,
    connection,
    schema,
    filter_names,
    scope,
    kind,
    dblink=None,
    **kw,
):
    if type(filter_names) is str:
        filter_names = [filter_names]

    if filter_names is None:
        all_objects = self._get_all_objects(
            connection, schema, scope, kind, filter_names, dblink, **kw
        )
    else:
        all_objects = [self.denormalize_name(n) for n in filter_names]

    schema = self.denormalize_name(schema or self.default_schema_name)

    params: dict = {}
    param_count = 1
    comment_sql = "SELECT table_name, comments FROM \n"
    if schema.upper() == self.default_schema_name.upper():
        comment_sql += "user_tab_comments"
    else:
        comment_sql += "all_tab_comments"

    if len(all_objects) > 0:
        comment_sql += " WHERE table_name IN (:param_0"
        params["param_0"] = all_objects[0]
        if len(all_objects) > 1:
            for i in range(len(all_objects) - 1):
                param_name = "param_" + str(param_count)
                param_count = param_count + 1
                comment_sql += ", :" + param_name
                params[param_name] = all_objects[i + 1]
        comment_sql += ")"  # 仅在生成了 IN 子句时追加右括号
    elif schema.upper() != self.default_schema_name.upper():
        param_name = "param_" + str(param_count)
        comment_sql += " WHERE owner = :" + param_name
        params[param_name] = schema

    default = _dm_base.ReflectionDefaults.table_comment
    result = connection.execute(_sa_sql.text(comment_sql), parameters=params)
    ignore_mat_view = "snapshot table for snapshot "
    return tuple(
        (
            (schema, self.normalize_name(table)),
            {"text": comment}
            if comment is not None and not comment.startswith(ignore_mat_view)
            else default(),
        )
        for table, comment in result
    )


DMDialect_dmPython.get_multi_table_comment = _get_multi_table_comment


# get_table_options 返回 dm_tablespace，但 construct_arguments 的 Table 项未声明，
# 导致 autogenerate 反射表时 _validate_dialect_kwargs 抛 ArgumentError。
# 复制一份 construct_arguments 并补上 tablespace，避免改动共享的基类列表影响其他方言。
_construct_arguments = []
for _target, _opts in DMDialect_dmPython.construct_arguments:
    if _target is _sa_schema.Table:
        _construct_arguments.append((_target, {**_opts, "tablespace": False}))
    else:
        _construct_arguments.append((_target, dict(_opts)))
DMDialect_dmPython.construct_arguments = _construct_arguments


def compare_dameng_type(context, inspected_column, metadata_column, inspected_type, metadata_type):
    """Alembic ``compare_type`` 回调：消除达梦 VARCHAR 长度反射为 Decimal 的假阳性。

    达梦反射回来的 String 长度是 ``Decimal('128')``，而模型里是 ``int`` 128，
    Alembic 默认逐字段比对会误报类型变更。这里仅当二者都是 String、反射长度为
    Decimal、且数值与模型长度相等时判定为"无变化"；其余情况返回 ``None`` 交回
    Alembic 默认逻辑，保证真实类型变更仍会被检出。此回调对非达梦数据库无副作用。
    """
    if isinstance(inspected_type, _sa_String) and isinstance(metadata_type, _sa_String):
        db_len = getattr(inspected_type, "length", None)
        model_len = getattr(metadata_type, "length", None)
        if isinstance(db_len, Decimal) and model_len is not None and int(db_len) == int(model_len):
            return False
    return None
