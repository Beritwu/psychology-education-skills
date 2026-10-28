# PEBS · 心理学教育の教材制作システム

**根拠を追跡し、変更範囲を管理し、教師が確認できる教材を作る。**

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

[![Code CI](https://github.com/Beritwu/psychology-education-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/Beritwu/psychology-education-skills/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)

[**授業・アニメーションを試す →**](https://beritwu.github.io/psychology-education-skills/)
 · [利用ガイド（英語）](docs/usage.md)
 · [利用ガイド（中国語）](docs/usage.zh-CN.md)

![古典的条件づけの三段階](examples/classical-conditioning/preview.png)

## PEBS とは

心理学の授業、教員研修、カリキュラム開発向けのローカル Python アプリケーションです。
要件、学習設計、心理学的主張、根拠資料、教材、メディア、品質確認、書き出しを、
版管理された一つのワークフローで扱います。Web 画面、CLI、REST API を提供します。

カタログには **22 個の組み込みスキルと、14 個の任意導入の外部教育スキル**があります。
SKILL.md だけではシステム全体は動作しません。別の PC では依存パッケージと実行用スキルを導入してください。

## 主な機能

| 作業 | 機能 |
|---|---|
| 授業設計 | 学習目標、評価課題、指導の流れ、事例、ワークシート |
| 根拠の確認 | 学術検索、保存した資料、位置を確認できる引用、確認状態の管理 |
| 教材作成 | 指導案、台本、学習者用・教師用資料、SVG、編集可能な PPTX |
| 部分修正 | 指定箇所を変更し、維持する箇所を保護。関連成果物の更新必要性を追跡 |
| 書き出し | 現在の版に対する品質チェック。条件を満たさない成果物は草稿として表示 |
| 評価 | ベンチマーク、スキル版の記録、版を固定した教師評価パッケージ |

## クイックスタート

Python 3.11 以降が必要です。初回は Python 3.12 を推奨します。

```bash
git clone https://github.com/Beritwu/psychology-education-skills.git
cd psychology-education-skills
python -m venv .venv
```

Windows PowerShell: `.venv\Scripts\Activate.ps1`。
macOS/Linux: `source .venv/bin/activate`。

```bash
python -m pip install -r requirements.txt
python -m pebs.cli serve --port 8710
```

**http://127.0.0.1:8710** を開きます。画面と静的な例はモデルなしで閲覧できます。
実際の教材生成にはプロバイダー設定が必要です。初期設定はログイン済みのローカル Codex CLI。
`openai_compatible` にも対応します。キーは環境変数に設定してください。

```bash
python -m pebs.cli build --project first_course --planner dynamic --max-model-calls 20 --max-research 8 --max-seconds 900 --request "Create one introductory psychology lesson with a fictional case and a formative question. No PPT and no animation."
```

モデルの利用枠を消費します。生成後は画面で変更内容を確認してから承認してください。
承認だけで正式な書き出し条件を満たすわけではありません。詳細は[利用ガイド](docs/usage.md)にあります。

## 外部教育スキル

[Gareth Manning の Education Agent Skills](https://github.com/GarethManning/education-agent-skills)
から 14 個を採用し、`6bbbce41…` に固定しています。うち 3 個には PEBS 用の修正があります。
初回クローンでは、実行キャッシュを別途準備します。

```bash
python -c "from pebs.provider_edu import install; install()"
python -c "from pebs.provider_edu import verify; r=verify(); print(r); raise SystemExit(0 if r['ok'] else 1)"
```

インストーラーは固定アーカイブを取得し、マニフェストの審査方針とパッチを適用します。
上流のスクリプトは実行しません。導入前にマニフェストを確認してください。
通常は組み込みスキルが選ばれます。再導入や独自スキルの扱いは利用ガイドを参照してください。

## 授業とアニメーションの例

[古典的条件づけのサンプル](examples/classical-conditioning/README.md)には、20 分の指導案、
ワークシート、教師用解答、スキル適用記録、絵コンテ、四言語対応のアニメーションがあります。
`examples/classical-conditioning/index.html` をブラウザーで開くだけでオフライン利用できます。
逆向き設計、診断的な問い、二重符号化のスキルを使用しています。

スキルの適用記録と出典を同梱しています。アニメーションは再生、一時停止、ステップ表示に対応し、
静的な図と併せて授業に利用できます。

## ドキュメントと貢献

[利用方法](docs/usage.md) · [スキル一覧](docs/skills.md) · [構成](documentation/architecture.md)
 · [教師評価](docs/evaluation-workflow.md) · [計画](docs/roadmap.md)
 · [貢献方法](CONTRIBUTING.md) · [セキュリティ](SECURITY.md) · [変更履歴](CHANGELOG.md)

```bash
python -m compileall -q pebs
python -m pytest tests -q -m "not integration and not live_research"
```

自動テストはソフトウェアの動作を検証します。教育効果を証明するものではありません。
日本語の紹介ページとデモを提供しますが、アプリ本体の UI は主に中国語です。

## ライセンス

独自コードと文書は [MIT](LICENSE)。外部教育スキルの改変物とサンプルの教育内容は
**CC BY-SA 4.0** です。[第三者の権利・帰属](THIRD_PARTY_NOTICES.md)を確認してください。
