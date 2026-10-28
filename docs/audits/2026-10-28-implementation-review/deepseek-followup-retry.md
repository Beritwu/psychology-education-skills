## 静态复核结论（仅基于该 delta）

未发现新的 P1。以下为按代码路径可确认的 P2 风险；未执行测试，属于静态审查结论。

### P2-1 `record_run` 部分身份字段调用会被误判为“换版”

文件：`pebs/benchmark/performance.py`

`record_run` 新增的身份比较：

```python
identity = {"version": version, "provider_sha": provider_sha,
            "package_sha256": package_sha256, "patch": patch}
if version and any(record.get(key, "") != value for key, value in identity.items()):
    data.setdefault("skill_history", []).append(dict(record))
    record = {**_empty_record(skill, version), **identity}
```

问题：函数签名允许只传 `skill` 和 `version`（现有测试也这样调用），其余身份字段默认空串。如果已有记录带有非空 `provider_sha/package_sha256/patch`，下一次同版本、但未传这些字段的 `record_run` 会被误判为身份变化，从而：

- 把旧记录移入 `skill_history`；
- 清空当前记录的 `runs`、`human_score`、`teacher_edit_ratio` 等聚合值。

这会造成同版本更新丢失教师评分/运行统计。建议只比较本次显式提供的字段，或要求完整身份并显式区分“未知字段”和“空值”。

### P2-2 `record_trace` 重放不会刷新已记录的状态/修复数

文件：`pebs/benchmark/performance.py`

`record_run` 对相同 `run_key` 直接返回旧记录：

```python
if run_key and run_key in data.get("build_records", {}):
    return data["build_records"][run_key]
```

而 `run_key` 只包含 `run_id + skill identity`。如果同一个 run 的 trace 后续发生变化（例如重试后 `SUCCEEDED`、`schema_repairs` 增加、`failure_mode` 修正），再次 `record_trace` 仍会命中旧 key，展示层继续保留旧状态。当前测试只验证“重放不增加 runs 数”，没有验证“重放能更新状态”。

影响：性能账本可能永久保留一次失败或旧修复数，无法反映后续修正。建议改成幂等 upsert（更新已有 build record）而不是直接跳过。

### P2-3 历史 trace 的 `review_record` 仍读取当前 accepted revision

文件：`pebs/benchmark/trace.py`

`route`、`plan`、`gate_result` 已改为按 `target_for_run` 的精确 revision 读取，但 `review_record` 仍使用：

```python
content = store.accepted_content(artifact["artifact_id"]) or {}
revision = store.get_revision(artifact["accepted_rev"])
if revision.get("produced_by_run") != run_id:
    continue
```

场景：run A 产生 review_record 并被接受；随后 run B 的 review_record 成为当前 accepted。此时查询 run A 的历史 trace：

- `target_for_run(A)` 仍可能包含 A 的 review revision；
- 但代码读取的是当前 `artifact["accepted_rev"]`，其 `produced_by_run` 为 B；
- 结果直接 `continue`，A 的历史 review 被丢弃。

这与本次对 route/gate 的历史精确读取修复不一致。建议像 `run_content` 一样从 `target` 中取 review_record 的精确 revision，而不是只看当前 accepted revision。

### 限制

以上结论基于 diff 静态推断；未验证 `target_for_run` 的返回结构、`direct_evaluation_run` 是否有副作用，以及现有调用方是否总是传完整身份字段。若这些前置条件在未展示代码中已被保证，相关风险等级可下调。
