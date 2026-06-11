# Open Datasets for SOP / Procedural Extraction Evaluation

This note lists open or partially open datasets that can be used to test extraction of Standard Operating Procedure (SOP)-like structures from unstructured or semi-structured sources.

## Recommended First

| Dataset | Source | What it contains | Fit for SOP extraction testing | Caveats |
|---|---|---|---|---|
| PET | https://huggingface.co/datasets/patriziobellan/PET | 45 English business process descriptions annotated with activities, actors, gateways, conditions, and flow relations. | Best first choice for text-to-process extraction. It has entity and relation labels close to SOP steps, actors, decisions, and control flow. | Small dataset; only test split; process descriptions are cleaner than messy enterprise SOP documents. |
| WONDERBREAD | https://github.com/HazyResearch/wonderbread | 2,928 web workflow demonstrations over 598 workflows; each demo includes intent, recording, action trace, key frames, and a written SOP. | Good for SOP generation/extraction from multimodal workflow traces, especially if the input is video/action logs rather than PDF text. | Not primarily a document-to-SOP dataset; workflow domain is web navigation. |
| SOPBench | https://huggingface.co/datasets/Zekunli/SOPBench and https://github.com/Leezekun/SOPBench | 903 tasks across customer-service domains, with SOP-like constraints, tools/functions, directed action graphs, prompts, and verifiers. | Useful for testing whether extracted SOPs can drive compliant tool use or be converted to executable action graphs. | More about SOP following than extracting SOPs from raw documents. |

## Strong Related Datasets

| Dataset | Source | What it contains | Fit for SOP extraction testing | Caveats |
|---|---|---|---|---|
| PcMSP | https://aclanthology.org/2022.findings-emnlp.446/ | 305 open-access materials synthesis procedures with synthesis sentences, entity mentions, and intra-sentence relations for scientific action graph extraction. | Good for step/action/relation extraction from procedural scientific text. | Domain-specific to materials synthesis, not business SOPs. |
| FlaMBé | https://huggingface.co/datasets/bigbio/flambe and https://zenodo.org/records/10050681 | Biomedical procedural knowledge extraction data from 55 full papers and 1,195 abstracts, with workflow/tool/context annotations. | Good for testing extraction from scientific methodology text and workflow relations. | Biomedical/single-cell domain; requires domain-specific normalization. |
| ProPara | http://data.allenai.org/propara | 488 natural process paragraphs with entity state/location/existence annotations. | Useful for testing whether extracted procedures preserve state changes and implicit effects. | It is process comprehension, not SOP structure extraction. |
| FlowExtract | https://github.com/guille-gil/FlowExtract | Code and evaluation setup for extracting directed graphs from industrial maintenance flowcharts; paper reports annotated industrial troubleshooting flowchart data. | Relevant if inputs include scanned flowcharts or maintenance diagrams. | Underlying industrial dataset may be redacted/proprietary; repo is mainly code and redacted examples. |

## Weaker / Use With Caution

| Dataset / Benchmark | Source | Why it is weaker for this objective |
|---|---|---|
| PAGED | https://aclanthology.org/2024.acl-long.583/ | Highly relevant procedurally, but I did not find a primary open dataset repository during this pass. Treat as a paper/benchmark reference unless the authors release data separately. |
| SOP-Bench: Complex Industrial SOPs | http://sop-bench.s3-website-us-west-2.amazonaws.com/ | Directly SOP-related, but mainly evaluates agent execution of synthetic SOP tasks; the public site should be verified before relying on it as downloadable data. |
| TechQA / IBM Technotes | https://research.ibm.com/publications/the-techqa-dataset | Useful technical-support raw documents and QA context, but not annotated for SOP/procedure extraction. Better as raw stress-test corpus after creating your own labels. |

## Practical Ranking

1. Use PET first for a small, directly labeled text-to-process benchmark.
2. Add PcMSP or FlaMBé if you need procedural extraction from long scientific/technical text.
3. Add WONDERBREAD if your input includes demonstrations, action traces, screenshots, or video.
4. Use SOPBench after extraction to test whether a structured SOP can drive rule-compliant execution.
5. Treat PAGED and SOP-Bench Industrial as references until their downloadable data availability is confirmed.

## Local State

The repo currently contains a local PET parquet file:

`papers/datasets/data/test-00000-of-00001-4cd746ae057084a3.parquet`

It has 45 examples according to `papers/datasets/dataset_infos.json`, with fields:

- `document name`
- `tokens`
- `tokens-IDs`
- `ner_tags`
- `sentence-IDs`
- `relations`

