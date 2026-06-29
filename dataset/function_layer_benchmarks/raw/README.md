# Raw Paper 1 Benchmark Sources

This directory stores downloaded raw source datasets for Paper 1 benchmark
construction. Raw files are not gold labels and should not be committed.

## Downloaded Sources

### ToolFactory / APIdoc2json

Source:

- HuggingFace dataset: `billyfin/APIdoc2json`
- Paper/GitHub context: ToolFactory API Extraction Benchmark

Downloaded files:

```text
toolfactory_apidoc2json/hf_dataset_info.json
toolfactory_apidoc2json/README.md
toolfactory_apidoc2json/train-00000-of-00001.parquet
```

The HuggingFace metadata reports 167 train examples with fields:

```text
text_content
json_form
```

The current local environment does not include `pandas`, `pyarrow`, or
`fastparquet`, so the parquet file has only been file-level checked. Install a
parquet reader before converting it to JSONL.

### APIs.guru OpenAPI Directory

Source:

- Repository metadata: `https://api.github.com/repos/APIs-guru/openapi-directory`
- API list: `https://api.apis.guru/v2/list.json`

Downloaded files:

```text
apis_guru/github_repo_info.json
apis_guru/list.json
apis_guru/specs/*.openapi.json
```

Downloaded OpenAPI subset:

```text
stripe.com.openapi.json
github.com.openapi.json
slack.com.openapi.json
twilio_conversations_v1.openapi.json
atlassian_jira.openapi.json
xero_accounting.openapi.json
box.com.openapi.json
docusign.openapi.json
sendgrid.openapi.json
```

This is a curated starting subset, not the full APIs.guru repository. The full
repository is much larger and should not be committed.

## Next Step

Use these raw files to produce reviewed benchmark layers:

```text
raw API docs / OpenAPI
  -> ontology draft
  -> ontology review
  -> ontology overlay draft
  -> reviewed overlay
  -> gold_functions.jsonl
```
