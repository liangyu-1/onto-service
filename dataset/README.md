# Dataset Index

This directory contains crawled industrial template materials used for ontology enrichment experiments.

## Benchmark and annotation status

Current crawled materials are source evidence, not publication-ready gold
benchmarks. Before running Paper 1 or Paper 2 experiments, prepare the missing
benchmark layers:

- `annotation_guidelines/`: annotation rules for ontology Function Layer and
  ontology Workflow Skill construction.
- `full_ontology_workflow_benchmark/`: working directory for documents,
  ontology, curated function layer, gold workflow annotations, and train/dev/test
  splits.
- `function_layer_benchmarks/`: expected Paper 1 benchmark layout for API or
  OpenAPI driven Function Layer construction.

The required construction order is:

```text
source documents / API artifacts
  -> domain ontology
  -> function layer
  -> gold annotations
  -> structural validation
  -> experiments
```

Do not treat PET, MyFixit, MSPT, OMIn, Huawei iDME pages, AAS, OPC UA, SysML,
or BoM/BoP materials as complete gold labels by themselves. They can provide
documents, schemas, or evidence spans, but ontology bindings and workflow
grounding still need annotation and review.

## Huawei iDME documentation

Official pages downloaded from Huawei support:

- `huawei_idme/idme_productdesc_0001.html`
- `huawei_idme/idme_productdesc_0005.html`
- `huawei_idme/idme_api_0002.html`
- `huawei_idme/EDOC1100403062_f966c6b.html`
- `huawei_idme/EDOC1100370207_6f51e58e.html`

## AAS submodel templates

Representative Asset Administration Shell template materials from `admin-shell-io/submodel-templates`:

- `aas/IDTA-02050_Template_PurchaseOrder.json`
- `aas/PurchaseOrder_README.md`
- `aas/IDTA-02031-1_Template_ProcessParameters_Type.json`
- `aas/ProcessParametersType_README.md`
- `aas/IDTA-02049_Template_QualityControlForMachining.json`
- `aas/QualityControlForMachining_README.md`

## BoM / BoP related materials

Additional BoM / BoP seed materials are stored under `bom_bop/`:

- `bom_bop/aas_hsebom/`: AAS `Hierarchical Structures enabling Bills of Material` template.
- `bom_bop/aas_hsebom_iec81346/`: AAS BoM extension based on IEC 81346.
- `bom_bop/process_plan_network/`: Zenodo process plan network dataset metadata and `job1.docx`.
- `bom_bop/open_hardware_bom_refs/`: open hardware / CAD BOM tool references.

These files are useful as schema and evidence seed material, but they are not a complete industrial BoM/BoP benchmark.

## OPC UA NodeSets

Representative industrial information model materials from `OPCFoundation/UA-Nodeset`:

- `opcua/Opc.Ua.PackML.NodeSet2.xml`
- `opcua/PackML.NodeIds.csv`
- `opcua/Opc.Ua.Robotics.NodeSet2.xml`
- `opcua/Opc.Ua.Robotics.NodeIds.csv`
- `opcua/Opc.Ua.Robotics.Nodeset2.documentation.csv`

## SysML v2 examples

Representative SysML v2 example models from `Systems-Modeling/SysML-v2-Release`:

- `sysml/VehicleDefinitions.sysml`
- `sysml/VehicleIndividuals.sysml`
- `sysml/HSUVRequirements.sysml`
- `sysml/VehicleRequirementDerivation.sysml`

## How to use these materials for semantic enrichment

Do not overwrite the ontology backbone with document text. Use the materials in two stages:

1. Extract candidates:
   - classes / object types
   - properties and allowed values
   - relations
   - lifecycle states and transitions
   - process parameters
   - constraints and business rules
   - synonyms and aliases
   - evidence spans

2. Attach enrichment records to the existing ontology:
   - `definition`
   - `alias`
   - `constraint`
   - `business_rule`
   - `lifecycle_semantics`
   - `procedure`
   - `role_policy`
   - `evidence`

Practical rule:

- Use metadata and existing industrial templates as the backbone.
- Use documents and standards as evidence and semantic augmentation.
- Promote only reviewed, evidence-backed candidates into the formal ontology.
