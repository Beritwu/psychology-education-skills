"""生成三个 M6 政策补丁的 overlay 文件（§11 / §12 / §14）。

输入：`skills/provider-cache/education-agent-skills/<sha>/.../SKILL.md`
输出：`providers/education-agent-skills/patches/<alias>/<patch_version>/SKILL.md`

每个输出都是上游 SKILL.md 的修改版本（CC BY-SA 4.0，注明修改），
仅做本仓库需要的替换与"PEBS 输出契约"追加；不重写上游教学框架。
运行：python providers/education-agent-skills/patches/build_patches.py
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MANIFEST = yaml.safe_load((HERE.parent / "provider.yaml").read_text(encoding="utf-8"))
SHA = MANIFEST["repository"]["commit_sha"]
UPSTREAM = REPO / "skills" / "provider-cache" / "education-agent-skills" / SHA

DISCLAIMER = (
    "> **PEBS 修改声明（CC BY-SA 4.0）**：本文件是 education-agent-skills（作者 Gareth Manning，"
    f"{MANIFEST['repository']['url']}@{SHA[:12]}）的修改版本，按 CC BY-SA 4.0 发布。\n"
    "> 修改内容：按 PEBS M6 政策修订删除/修正了伪精确与越界表述，并追加 PEBS 输出契约；"
    "教学框架本身保持上游设计。\n\n"
)


def _load_upstream(alias: str) -> str:
    matches = [path for path in UPSTREAM.rglob("SKILL.md") if path.parent.name == alias]
    if not matches:
        raise SystemExit(f"上游 Skill 未缓存：{alias}（先运行 provider fetch）")
    return matches[0].read_text(encoding="utf-8")


def _with_disclaimer(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            end += len("\n---")
            return text[:end] + "\n\n" + DISCLAIMER + text[end:].lstrip("\n")
    return DISCLAIMER + text


# ---------------------------------------------------------------- §11 load
LOAD_BRIDGE = """
## PEBS 输出契约（M6 §11，必须遵守）

1. 禁止给出任何数字化"认知负荷评分"（例如 `Cognitive Load = 7.4`）。
2. 禁止把工作记忆容量写成固定元素数量规则（例如"只能保持 4–7 个元素"）；
   工作记忆限制只能作为**理论框架**讨论，并标注适用条件与不确定性。
3. 认知负荷只能输出等级：`LOW` / `MEDIUM` / `HIGH`，并给出理由与不确定性。
4. 只输出如下 JSON（对应 PEBS canonical `load_review` schema）：

```json
{
  "section_id": "sec1",
  "cognitive_load": {
    "level": "MEDIUM",
    "reasons": ["..."],
    "intrinsic": ["..."],
    "extraneous": ["..."],
    "germane_support": ["..."],
    "uncertainties": ["..."],
    "improvements": ["..."]
  },
  "dual_coding": {"pairings": []},
  "notes": "本分析基于教学设计文本，未对学生实测；结论为教学判断而非心理测量。"
}
```

5. 不确定的地方必须写入 `uncertainties`，不得写成确定事实。
"""


def patch_cognitive_load(text: str) -> str:
    text = _with_disclaimer(text)
    text = re.sub(
        r"human working memory can hold approximately 4[–-]7 elements simultaneously",
        "human working memory is limited (the classic “4–7 elements” shorthand is a simplification "
        "and should not be treated as a fixed rule)",
        text,
    )
    text = re.sub(r"4[–-]7 elements", "a limited number of elements", text)
    return text.rstrip() + "\n" + LOAD_BRIDGE


# ---------------------------------------------------------------- §12 hinge
HINGE_BRIDGE = """
## PEBS 输出契约（M6 §12，必须遵守）

1. 上游示例只用于说明题型，**不得**作为可信 few-shot 直接复用；示例中的数字、答案与
   解析必须重新计算、重新核验。
2. 正确答案必须二次校验：先独立求解，再与选项比对，并把校验过程写入
   `answer_verification`。数值题必须逐步计算并给出中间结果。
3. 心理学事实题必须引用 PEBS Evidence（`claim_refs` 必须非空，只能引用已 SUPPORTED 的 claim）。
4. 每个 distractor 必须映射一个具体 misconception，写入 `distractors_detail`。
5. 输出 JSON（对应 PEBS canonical `assessment` schema，每节可含多题）：

```json
{
  "section_id": "sec1",
  "items": [
    {
      "assessment_id": "q1",
      "kind": "hinge_question",
      "question": "...",
      "options": ["A ...", "B ...", "C ...", "D ..."],
      "answer": "B",
      "answer_verification": "独立求解：... = 6；与选项 B 一致。",
      "distractors": ["A ...", "C ...", "D ..."],
      "distractors_detail": [
        {"answer": "A ...", "misconception": "把中位数当作平均数"},
        {"answer": "C ...", "misconception": "..."},
        {"answer": "D ...", "misconception": "..."}
      ],
      "claim_refs": [],
      "target_goal": "g1",
      "rationale": "用于判断学生是否已具备进入下一步的先决理解"
    }
  ],
  "diagnostic_use": "根据答案分布决定是否重讲"
}
```
"""


def patch_hinge(text: str) -> str:
    text = _with_disclaimer(text)
    text = re.sub(
        r"### The Question\b",
        "### The Question（PEBS：此上游示例已隔离，仅示题型，不得作为可信 few-shot 复用；答案须重新校验）",
        text,
    )
    text = re.sub(
        r"\*\*Correct answer:\*\*\s*([^\n]+)",
        r"**Correct answer（上游示例答案，PEBS 要求重新校验后方可使用）:** \1",
        text,
    )
    return text.rstrip() + "\n" + HINGE_BRIDGE


# ---------------------------------------------------------------- §14 UDL
UDL_BRIDGE = """
## PEBS 输出契约（M6 §14，必须遵守）

1. **禁止**输出"这个学生应该转介 / 必须转介"这类自动转介结论。
2. 需要专业支持的情形只能写成 `individual_support_review_flags`，措辞例如：
   "这一障碍可能无法仅靠通用教学调整解决；如果已有正式评估或支持方案，应由相关人员据此判断。"
3. 输出 JSON（对应 PEBS canonical `load_review` schema，其中 `udl` 为扩展块）：

```json
{
  "section_id": "sec1",
  "cognitive_load": {"level": "LOW", "reasons": ["..."]},
  "dual_coding": {"pairings": []},
  "udl": {
    "barriers": ["..."],
    "individual_support_review_flags": [
      {
        "flag": "长期阅读困难",
        "reason": "该障碍可能无法仅靠通用教学调整解决",
        "suggested_action": "如已有正式评估或支持方案，由相关人员据此判断"
      }
    ],
    "design_adjustments": ["..."]
  }
}
```

4. `individual_support_review_flags` 只描述"需要谁来判断"，不给出诊断或标签。
"""


def patch_udl_barrier(text: str) -> str:
    text = _with_disclaimer(text)
    text = text.replace("specialist_referral_barriers", "individual_support_review_flags")
    text = re.sub(r"Specialist referral", "Specialist support review", text)
    text = re.sub(
        r"those requiring specialist support",
        "those requiring individual support review",
        text,
    )
    return text.rstrip() + "\n" + UDL_BRIDGE


PATCHERS = {
    "cognitive-load-analyser": (patch_cognitive_load, "cognitive-load-analyser-pebs-1"),
    "hinge-question-designer": (patch_hinge, "hinge-question-designer-pebs-1"),
    "udl-barrier-anticipator": (patch_udl_barrier, "udl-barrier-anticipator-pebs-1"),
}


def main() -> None:
    for alias, (patcher, version) in PATCHERS.items():
        upstream = _load_upstream(alias)
        patched = patcher(upstream)
        target = HERE / alias / version
        target.mkdir(parents=True, exist_ok=True)
        (target / "SKILL.md").write_text(patched, encoding="utf-8")
        print("wrote", target / "SKILL.md", len(patched), "chars")


if __name__ == "__main__":
    main()
