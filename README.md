# ai-research-intel

NeurIPS / ICML / ICLR / ACL の論文情報を自動取得するためのスクリプトです。

## 使い方

```bash
python3 fetch_conference_papers.py --years 2023 2024
```

実行後に次のファイルが生成されます。

- `outputs/papers.json`
- `outputs/papers.csv`

## オプション例

```bash
# ICLR と ACL の 2024 年だけ取得
python3 fetch_conference_papers.py \
  --conferences iclr acl \
  --years 2024 \
  --max-results 300 \
  --json-output outputs/iclr_acl_2024.json \
  --csv-output outputs/iclr_acl_2024.csv
```

## 仕様

- データソース: DBLP API (`https://dblp.org/search/publ/api`)
- 取得対象: `NeurIPS`, `ICML`, `ICLR`, `ACL`
- 取得項目:
  - conference
  - year
  - title
  - authors
  - venue
  - url
