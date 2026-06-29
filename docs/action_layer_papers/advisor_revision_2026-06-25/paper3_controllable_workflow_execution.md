# Adversarially Robust and Controllable Execution of Ontology Workflows

## Abstract

Ontology Workflow Skills provide typed operations, object bindings, state
predicates, and control-flow constraints, but their execution by LLM agents
remains vulnerable to benign faults and adversarial manipulation. Tool outputs
may be incomplete or malicious, tool descriptions may hijack selection, user
instructions may induce policy violations or objective drift, and runtime state
may be stale or poisoned. We formulate **robust controlled workflow
execution**: preserve task utility and workflow constraints under bounded noise
and attack while preventing irreversible unsafe effects. We propose an
Ontology-Compiled Execution Envelope that separates trusted control semantics
from untrusted natural-language content, maintains an uncertainty set over
runtime ontology state, restricts candidate actions to workflow-consistent
object and state transitions, applies worst-case admissibility to irreversible
operations, and permits bounded information acquisition and recovery for
reversible operations. Adaptive attack search probes the envelope rather than
evaluating only fixed attacks. Experiments combine AgentDojo, InjecAgent, Agent
Security Bench, tau-bench, SOP-Bench, and controlled fault injection. Evaluation
reports clean utility, utility under attack, attack success, constraint
violations, unsafe effects, over-blocking, degradation slope, robust radius,
and empirical worst-case lower bounds. The objective is not post-hoc
explanation or formal universal safety, but a measurable improvement in the
utility--control boundary under realistic and adaptive perturbations.

## 1. Introduction

LLM agents increasingly execute long-horizon tasks through external tools.
Their operational environment is neither clean nor trustworthy. Tool calls can
time out, responses can omit fields, schemas can drift, user goals can change,
and external content can contain malicious instructions. These failures are
especially consequential when agents execute multi-step workflows with
irreversible side effects.

Prompt-injection research shows that tool-integrated agents can be hijacked by
instructions embedded in external content. InjecAgent reports substantial
indirect-prompt-injection vulnerability across tool agents
[@zhan2024injecagent]. AgentDojo evaluates utility and security in dynamic
stateful environments [@debenedetti2024agentdojo]. Agent Security Bench covers
prompt injection, memory poisoning, backdoors, and mixed attacks while
introducing a utility-security trade-off metric [@zhang2024asb]. More recent
work demonstrates that adaptive attacks bypass defenses evaluated only against
fixed attacks [@zhan2025adaptive].

Runtime constraint systems provide another line of defense. AgentSpec enforces
custom rules [@wang2025agentspec], Progent controls privileges
[@shi2025progent], and Agent-C enforces temporal properties
[@kamath2025agentc]. These methods establish that agent behavior can be
restricted, but strict restriction can reduce task success. The Verifier Tax
shows that long-horizon agents may fail after a verifier intervention
[@sah2026verifiertax]. A robust method must therefore control harmful behavior
without collapsing benign utility.

We study this trade-off for agents executing the Ontology Workflow Skills
defined in Paper 2. Such workflows provide more than a tool list: they define
allowed function nodes, ontology object variables, typed parameter bindings,
state predicates, effects, invariants, and exceptional branches. We use this
structure to compile an **Execution Envelope** that bounds the set of valid
runtime transitions.

The key distinction is between a trusted control plane and untrusted data.
Workflow definitions and registered Function contracts form the control plane.
User text, retrieved documents, tool descriptions, and free-text tool outputs
are untrusted unless converted into typed observations through validated
parsers. Untrusted text can supply data values but cannot directly modify the
workflow state or authorize an external effect.

Runtime state is also uncertain. A missing field is not equivalent to a false
condition, and one tool response may conflict with another. The method
maintains a set of ontology states consistent with trusted observations. For
irreversible actions, execution is permitted only when constraints hold across
the complete uncertainty set. For information-gathering and reversible actions,
the system permits bounded exploration to avoid excessive blocking.

The paper does not claim a universal certified guarantee. Natural-language
attack spaces are effectively unbounded. Instead, it defines an explicit threat
model, attack budget, and adaptive adversary, then reports an **empirical
worst-case lower bound** and robust radius under that model.

We address:

- **RQ1:** Does the ontology-compiled envelope reduce attack success and
  constraint violations at matched clean utility?
- **RQ2:** Does uncertainty-aware action control outperform uniform blocking
  under benign faults and incomplete observations?
- **RQ3:** How rapidly does performance degrade as attack or noise budget
  increases?
- **RQ4:** Do object, state, and effect constraints defend against attacks that
  bypass text-only filters?
- **RQ5:** Does the method generalize to a new domain by replacing only the
  ontology and workflow, without domain-specific control code?

The contributions are:

1. a threat model for ontology-workflow execution covering noise, injection,
   tool hijacking, poisoning, and objective drift;
2. an Ontology-Compiled Execution Envelope with typed trust boundaries and
   uncertainty-aware admissibility;
3. bounded exploration and recovery that preserve workflow and side-effect
   budgets;
4. an adaptive evaluation protocol emphasizing worst-group and empirical
   worst-case performance rather than average clean success.

## 2. Related Work

### 2.1 Tool-Agent Robustness and Security Benchmarks

InjecAgent targets indirect prompt injection in tool-integrated agents
[@zhan2024injecagent]. AgentDojo provides dynamic tasks, attacks, and defenses
over untrusted tool data [@debenedetti2024agentdojo]. Agent Security Bench
formalizes attacks at multiple agent stages and defines Net Resilient
Performance [@zhang2024asb]. MCP Security Bench expands attacks to tool
discovery, invocation, and response handling [@zhang2025mcpsecurity].
AgentLAB studies long-horizon intent hijacking, tool chaining, task injection,
objective drift, and memory poisoning [@jiang2026agentlab].

These benchmarks motivate our threat model and metrics. Our method differs by
using an ontology workflow to define the allowed transition boundary rather
than relying only on textual instruction separation or attack detection.

### 2.2 Prompt Injection and Tool Hijacking

Adaptive attacks bypass multiple indirect-prompt-injection defenses
[@zhan2025adaptive]. ToolHijacker manipulates tool retrieval and selection
through malicious tool descriptions [@shi2025toolhijacker]. Principled design
patterns isolate untrusted data and constrain agent capabilities
[@beurerkellner2025patterns]. Tool-result parsing filters instructions embedded
in free-text outputs [@yu2026toolparsing].

We adopt structural separation as a premise but add ontology-level object,
state, effect, and workflow constraints. A syntactically clean tool response can
still induce an invalid state transition; text filtering alone cannot detect
that failure.

### 2.3 Runtime Enforcement

AgentSpec provides customizable runtime rules [@wang2025agentspec]. Progent
enforces privileges [@shi2025progent]. Solver-aided policy verification and
Agent-C provide stronger logical or temporal checks
[@winston2026solver; @kamath2025agentc]. Agentproof verifies workflow graph
structure and temporal policies before deployment [@xavier2026agentproof].

Our method does not claim stronger formal safety. It studies robustness and
control under uncertain observations and adversarial content, including the
utility loss created by conservative enforcement.

### 2.4 Reliability under Environmental Perturbations

ReliabilityBench evaluates repeated consistency, semantic robustness, and fault
tolerance under timeouts, rate limits, partial responses, and schema drift
[@gupta2026reliabilitybench]. Safe reinforcement learning studies robustness to
adversarial state observations and minimax training
[@liu2022saferlrobustness]. These ideas motivate uncertainty sets, perturbation
budgets, and degradation curves in our agent setting.

### 2.5 Adversarial Training and Control Boundaries

Adversarial RL for agent safety co-trains attackers and defenders to generate
new indirect injections [@wang2025arlas]. Control safety cases emphasize
red-team evaluation and conservative extrapolation rather than unsupported
universal safety claims [@korbak2025controlcase].

Our adaptive attacker searches workflow-specific weak points: untrusted values
that can alter object binding, state predicates, branch selection, or external
effects.

### 2.6 Research Gap

Existing defenses typically focus on malicious text detection, privilege
control, or general temporal constraints. They do not jointly exploit:

- ontology object identity and typed parameter roles;
- workflow-local enabled actions;
- state uncertainty and effect semantics;
- irreversible-effect budgets;
- adaptive attacks targeting workflow transitions;
- a worst-case utility--control evaluation.

## 3. Method

### 3.1 Threat Model

The agent executes a gold or extracted Ontology Workflow \(W\) through a
registered Function Layer \(F\). The adversary can perturb untrusted channels
within budget \(B\):

- user messages;
- retrieved or external text;
- free-text tool results;
- tool names, descriptions, or ranking metadata;
- non-authoritative memory;
- selected state observations.

The adversary cannot modify the signed Workflow, Function contracts, trusted
validators, or benchmark environment state directly. Benign faults share some
channels but are sampled independently rather than optimized adversarially.

### 3.2 Ontology-Compiled Execution Envelope

Workflow \(W\) is compiled into:

```text
ExecutionEnvelope {
  control_states,
  enabled_functions(state),
  typed_object_variables,
  admissible_bindings,
  state_predicates,
  transition_relation,
  invariants,
  trust_policy,
  side_effect_budget,
  recovery_budget
}
```

At runtime, a proposed action is accepted only if it lies inside the envelope
for the current control and ontology state.

### 3.3 Trusted Control Plane and Tainted Data Plane

Inputs are assigned provenance and trust labels:

- `trusted_control`: signed workflow and Function contracts;
- `trusted_observation`: validated structured tool fields;
- `untrusted_data`: user and external content used as values;
- `untrusted_instruction`: natural-language directives originating outside the
  control plane.

Only validated structured fields can update ontology runtime state. Natural
language embedded in tool results cannot introduce a new function call,
authorize an effect, or modify workflow control state.

### 3.4 Typed Observation Parsing

Each tool result passes through a Function-specific parser generated from its
output contract. The parser:

- selects declared output fields;
- validates datatypes and ontology identifiers;
- rejects out-of-schema instructions;
- assigns object ownership and provenance;
- records missing, stale, and conflicting values.

This step generalizes tool-result parsing by validating semantic compatibility
with ontology objects, not only response format.

### 3.5 Uncertainty-Aware Ontology State

The system maintains an uncertainty set:

\[
\mathcal{U}_t = \{s : s \text{ is consistent with trusted observations up to }t\}.
\]

Unknown, conflicting, and stale predicates widen \(\mathcal{U}_t\). Untrusted
text does not reduce uncertainty. A state estimator intersects new structured
observations with ontology constraints and temporal consistency.

### 3.6 Risk-Sensitive Admissibility

Functions are divided by effect risk:

- **information/reversible functions:** no irreversible external effect;
- **irreversible functions:** mutation, transfer, deletion, payment, disclosure,
  or other committed effect.

For irreversible action \(a\), the system requires:

\[
\forall s \in \mathcal{U}_t,\quad
\mathrm{Precondition}(a,s) \land \mathrm{Invariant}(a,s).
\]

For information or reversible actions, the system permits bounded exploration
when it reduces uncertainty and remains inside the workflow. This avoids the
failure mode in which uniform conservative blocking prevents the agent from
acquiring the state needed for a safe decision.

### 3.7 Workflow-Local Control

A proposed function must:

- be enabled by the current workflow control state;
- bind arguments to compatible ontology objects;
- preserve object identity and relation scope;
- satisfy control and state predicates;
- remain within side-effect and repetition budgets;
- not follow instructions originating from untrusted content.

Tool descriptions are never sufficient authority for an out-of-workflow call,
which directly limits ToolHijacker-style selection attacks.

### 3.8 Bounded Recovery

When a candidate is rejected or a benign fault occurs, recovery is limited to:

- acquire a declared observation;
- retry an idempotent function;
- rebind to a validated ontology object;
- select a workflow-defined alternative branch;
- execute registered compensation;
- request missing user input;
- escalate.

The LLM can rank instantiated recovery candidates but cannot introduce an
operation outside the Function Layer or Workflow envelope.

### 3.9 Adaptive Boundary Search

An attack generator searches for perturbations maximizing:

\[
L_{\mathrm{adv}} =
\lambda_1 \mathbb{1}[\mathrm{unsafe\ effect}]
+\lambda_2 \mathbb{1}[\mathrm{workflow\ violation}]
+\lambda_3 \mathbb{1}[\mathrm{task\ failure}]
\]

under budget \(B\). The generator mutates tool text, user instructions,
registry metadata, observation values, and multi-turn timing. Population-based
attack search retains successful attacks across rounds to reduce overfitting to
one attack template.

## 4. Experiment

### 4.1 Environments

- AgentDojo for indirect prompt injection and utility under attack
  [@debenedetti2024agentdojo];
- InjecAgent for tool-integrated attack cases [@zhan2024injecagent];
- Agent Security Bench for mixed attack types and NRP [@zhang2024asb];
- tau-bench Retail and Airline for stateful policy workflows
  [@yao2024taubench];
- SOP-Bench for complex procedure execution [@nandi2025sopbench];
- controlled workflow microbenchmarks with exact attack targets and state
  transitions.

Primary experiments use gold workflows and Function contracts. Extracted
artifacts are evaluated separately.

### 4.2 Perturbation Families

**Benign noise**

- timeout and rate limit;
- partial or duplicated response;
- missing or renamed fields;
- stale and conflicting state;
- irrelevant or similar tools;
- benign paraphrase and incomplete user input.

**Adversarial attack**

- indirect prompt injection;
- malicious tool descriptions and name collisions;
- tool-selection hijacking;
- out-of-scope parameter requests;
- memory/state poisoning;
- objective drift and task injection;
- false-error escalation;
- mixed and multi-turn attacks.

### 4.3 Attack Budgets

Each attack family defines intensity \(B\), such as number of injected messages,
modified fields, malicious tools, poisoned memories, or turns under attack.
Results are reported over multiple budgets and adaptive attack rounds.

### 4.4 Baselines

- ReAct;
- workflow text in prompt;
- instruction hierarchy or text-only isolation;
- tool-result parsing;
- prompt-injection detector/filter;
- action-local schema verifier;
- AgentSpec;
- Agent-C where reproducible;
- Execution Envelope without uncertainty sets;
- Execution Envelope without workflow control;
- Execution Envelope without adaptive hardening;
- full method.

### 4.5 Metrics

**Utility**

- clean task success \(U_{\mathrm{clean}}\);
- utility under attack \(U_{\mathrm{attack}}\);
- benign-noise success.

**Security and control**

- attack success rate;
- workflow conformance rate;
- constraint violation rate;
- unsafe side-effect rate;
- object-binding violation rate;
- over-blocking rate.

**Robustness**

- adversarial regret:
  \(U_{\mathrm{clean}}-U_{\mathrm{attack}}\);
- degradation slope over attack budget;
- worst-attack success;
- worst-group success across attack families and domains;
- 95% lower confidence bound of robust success;
- robust radius: largest \(B\) satisfying
  \(ASR \leq \tau\) and \(U_{\mathrm{attack}}\geq\alpha\);
- Net Resilient Performance.

**Recovery and cost**

- recovery success;
- unnecessary recovery;
- average repair steps;
- escalation rate;
- latency, token, and tool-call overhead.

No explanation-quality metric is included.

### 4.6 Empirical Worst-Case Protocol

For task \(i\) and allowed attack set \(\mathcal{A}(B)\):

\[
\widehat{WCS}(B) =
\frac{1}{N}\sum_i \min_{a\in\mathcal{A}(B)}
\mathrm{Success}(i,a).
\]

Because \(\mathcal{A}(B)\) is finite and search is incomplete, this is an
empirical lower bound under the evaluated threat model, not a formal global
guarantee. We report bootstrap and binomial lower confidence bounds.

### 4.7 Adaptive Evaluation

Defenses are first tuned against a development attack set. The test phase
includes:

- held-out attack templates;
- transfer attacks generated against another model;
- adaptive attacks with access to defense outputs;
- attack combinations;
- unseen domains.

Static-attack results are reported separately and cannot support the primary
robustness claim.

### 4.8 Statistical Analysis

All methods run on matched tasks, seeds, attack families, and budgets. Paired
task success and attack outcomes use McNemar tests. Task-cluster bootstrap
intervals account for repeated attacks on the same task. Degradation slopes are
estimated with mixed-effects logistic regression. Holm correction controls
multiple attack-family comparisons.

## 5. Analysis Plan

### 5.1 Primary Claim

The full method must improve the utility--control frontier. Evidence is
sufficient if, compared with baselines, it:

- lowers ASR at matched clean utility; or
- raises utility under attack at matched constraint violation; and
- improves worst-group or empirical worst-case success.

More rejected actions alone are not evidence of robustness.

### 5.2 Clean-Utility Tax

Every defense is evaluated for over-blocking and clean-task degradation. If the
method improves attack resistance only by refusing benign tasks, it has not
improved the operational boundary.

### 5.3 Attack-Specific Attribution

Results are decomposed by:

- untrusted text isolation;
- typed output parsing;
- object binding;
- workflow enabled-set control;
- uncertainty-aware admissibility;
- side-effect budget;
- bounded recovery.

This identifies whether ontology semantics add value beyond text sanitization.

### 5.4 Worst-Group Analysis

Average performance can hide catastrophic weakness. We report the lowest
success and highest violation across:

- attack families;
- domains;
- irreversible versus reversible actions;
- short versus long workflows;
- low versus high tool-registry ambiguity.

### 5.5 Generalization Criterion

The control implementation is frozen after development on one domain. A new
domain may supply a new ontology, Function Layer, and Workflow, but no
domain-specific `if action == ...` code. If code changes are required for each
scenario, the method is scenario engineering rather than ontology-driven
control.

### 5.6 Limitations

The method cannot guarantee robustness outside the threat model. Attack search
may miss stronger perturbations, and benchmark tool environments may not
represent production systems. Ontology workflows can also contain incorrect
constraints. The paper therefore reports bounded empirical robustness, not
universal safety or formal certification.

## 6. Conclusion

This paper reframes ontology-grounded execution as an adversarial robustness and
control problem. The proposed Execution Envelope uses workflow, object, state,
and effect semantics to constrain how untrusted information can influence
actions. Its success must be demonstrated through utility under attack,
constraint violations, unsafe effects, degradation curves, robust radius, and
empirical worst-case lower bounds.
