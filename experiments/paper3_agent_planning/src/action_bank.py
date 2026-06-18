"""Action schema definitions for ontology-grounded action planning."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ActionSchema:
    """An action schema with preconditions, effects, and constraints."""
    action_id: str
    description: str
    parameters: Dict[str, str]  # param_name -> type/description
    preconditions: List[str]  # boolean expressions as strings
    effects: List[str]  # state updates as strings
    constraints: List[str]  # policy constraints
    target_object: str = ""  # primary object type this action operates on
    action_kind: str = "mutate"  # epistemic, mutate, communicate, transfer, compute, confirm, finish
    grounding_mode: str = "strong"  # weak for epistemic reads, strong for state-changing actions
    parameter_semantics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    target_binding: Dict[str, Any] = field(default_factory=dict)
    ontology_action_id: str = ""
    target_type_id: str = ""
    control_flow: Dict[str, List[str]] = field(default_factory=dict)

    def to_prompt_text(self) -> str:
        """Convert to a concise text for LLM prompting."""
        lines = [
            f"Action: {self.action_id}",
            f"  Kind: {self.action_kind}",
            f"  Grounding: {self.grounding_mode}",
            f"  Description: {self.description}",
            f"  Target: {self.target_object}",
            f"  Parameters: {json.dumps(self.parameters, ensure_ascii=False)}",
        ]
        if self.parameter_semantics:
            lines.append(
                f"  Parameter semantics: {json.dumps(self.parameter_semantics, ensure_ascii=False)}"
            )
        if self.preconditions:
            lines.append(f"  Preconditions:")
            for p in self.preconditions:
                lines.append(f"    - {p}")
        if self.effects:
            lines.append(f"  Effects:")
            for e in self.effects:
                lines.append(f"    - {e}")
        if self.constraints:
            lines.append(f"  Constraints:")
            for c in self.constraints:
                lines.append(f"    - {c}")
        return "\n".join(lines)


class ActionBank:
    """A collection of action schemas."""

    def __init__(
        self,
        schemas: List[ActionSchema],
        predicate_providers: Optional[Dict[str, List[Dict[str, str]]]] = None,
    ):
        self.schemas = {s.action_id: s for s in schemas}
        self.predicate_providers = predicate_providers or {}

    def get(self, action_id: str) -> Optional[ActionSchema]:
        return self.schemas.get(action_id)

    def list_actions(self) -> List[str]:
        return list(self.schemas.keys())

    def to_prompt_text(self) -> str:
        return "\n\n".join(s.to_prompt_text() for s in self.schemas.values())

    def providers_for(self, predicate: str) -> List[Dict[str, str]]:
        return list(self.predicate_providers.get(normalize_predicate(predicate), []))

    @classmethod
    def from_json(cls, path: pathlib.Path) -> "ActionBank":
        with open(path) as f:
            data = json.load(f)
        if "action_ir_version" in data:
            return cls.from_action_ir_data(data)
        schemas = [ActionSchema(**s) for s in data.get("actions", [])]
        return cls(schemas, predicate_providers=data.get("predicate_providers", {}))

    @classmethod
    def from_action_ir_json(cls, path: pathlib.Path) -> "ActionBank":
        with open(path) as f:
            data = json.load(f)
        return cls.from_action_ir_data(data)

    @classmethod
    def from_action_ir_data(cls, data: Dict[str, Any]) -> "ActionBank":
        """Project canonical Action IR records into the runtime ActionBank view."""
        actions = data.get("actions", [])
        schemas = [action_ir_to_schema(action) for action in actions]
        return cls(
            [schema for schema in schemas if schema is not None],
            predicate_providers=project_predicate_providers(actions),
        )

    def save(self, path: pathlib.Path) -> None:
        data = {
            "actions": [
                {
                    "action_id": s.action_id,
                    "description": s.description,
                    "parameters": s.parameters,
                    "preconditions": s.preconditions,
                    "effects": s.effects,
                    "constraints": s.constraints,
                    "target_object": s.target_object,
                    "action_kind": s.action_kind,
                    "grounding_mode": s.grounding_mode,
                    "parameter_semantics": s.parameter_semantics,
                    "target_binding": s.target_binding,
                    "ontology_action_id": s.ontology_action_id,
                    "target_type_id": s.target_type_id,
                    "control_flow": s.control_flow,
                }
                for s in self.schemas.values()
            ],
            "predicate_providers": self.predicate_providers,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")


def action_ir_to_schema(action: Dict[str, Any]) -> Optional[ActionSchema]:
    """Convert one canonical Action IR record into the Paper3 runtime schema."""
    runtime = action.get("runtime") or {}
    if runtime.get("enabled") is False:
        return None
    if runtime.get("tau2_compatible") is False:
        return None

    action_id = runtime.get("tool_name") or action.get("name") or action.get("id")
    if not action_id:
        raise ValueError(f"Action IR record missing id/name/runtime.tool_name: {action}")

    target = action.get("target") or {}
    target_object = target.get("object_type", "") if isinstance(target, dict) else ""
    grounding = action.get("grounding") or {}

    return ActionSchema(
        action_id=action_id,
        description=str(action.get("description", "")),
        parameters=project_parameters(action.get("parameters", [])),
        preconditions=project_expressions(action.get("preconditions", [])),
        effects=project_expressions(action.get("effects", [])),
        constraints=project_expressions(action.get("constraints", [])),
        target_object=target_object,
        action_kind=project_action_kind(action),
        grounding_mode=project_grounding_mode(action),
        parameter_semantics=project_parameter_semantics(
            action.get("parameters", []),
            grounding.get("parameter_ids", {}),
        ),
        target_binding=dict(target.get("binding") or {}) if isinstance(target, dict) else {},
        ontology_action_id=str(grounding.get("ontology_action_id", "")),
        target_type_id=str(grounding.get("target_type_id", "")),
        control_flow=project_control_flow(action.get("control_flow")),
    )


def project_action_kind(action: Dict[str, Any]) -> str:
    """Project domain-specific Action IR types into domain-independent kinds."""
    explicit = action.get("action_kind")
    if explicit:
        return str(explicit)
    action_type = str(action.get("type", "")).lower()
    action_id = str(action.get("id") or action.get("name") or "").lower()
    if "lookup" in action_type or "read" in action_type or action_id.startswith("get_") or action_id.startswith("list_"):
        return "epistemic"
    if "computation" in action_type or action_id == "calculate":
        return "compute"
    if "confirmation" in action_type or "confirmation" in action_id:
        return "confirm"
    if "escalation" in action_type or "transfer" in action_id:
        return "transfer"
    if "completion" in action_type or action_id == "finish_task":
        return "finish"
    return "mutate"


def project_grounding_mode(action: Dict[str, Any]) -> str:
    explicit = action.get("grounding_mode")
    if explicit:
        return str(explicit)
    return "weak" if project_action_kind(action) in {"epistemic", "compute", "confirm"} else "strong"


def project_parameters(parameters: Any) -> Dict[str, str]:
    """Project structured IR parameters to the compact prompt/runtime form."""
    if isinstance(parameters, dict):
        return {str(name): str(value) for name, value in parameters.items()}
    projected: Dict[str, str] = {}
    for param in parameters or []:
        if not isinstance(param, dict):
            continue
        name = param.get("name")
        if not name:
            continue
        param_type = str(param.get("type", ""))
        description = str(param.get("description", "")).strip()
        allowed = param.get("allowed_values")
        if allowed:
            description = f"{description} - allowed values: {allowed}".strip(" -")
        projected[str(name)] = f"{param_type} - {description}" if description else param_type
    return projected


def project_parameter_semantics(
    parameters: Any,
    parameter_ids: Any,
) -> Dict[str, Dict[str, Any]]:
    ids = parameter_ids if isinstance(parameter_ids, dict) else {}
    projected: Dict[str, Dict[str, Any]] = {}
    if isinstance(parameters, dict):
        for name, value in parameters.items():
            projected[str(name)] = {
                "type": str(value),
                "required": True,
                "role": "",
                "ontology_property_id": str(ids.get(name, "")),
            }
        return projected
    for parameter in parameters or []:
        if not isinstance(parameter, dict) or not parameter.get("name"):
            continue
        name = str(parameter["name"])
        projected[name] = {
            "type": str(parameter.get("type", "")),
            "required": bool(parameter.get("required", False)),
            "role": str(parameter.get("role", "")),
            "description": str(parameter.get("description", "")),
            "allowed_values": list(parameter.get("allowed_values") or []),
            "ontology_property_id": str(ids.get(name, "")),
        }
    return projected


def project_control_flow(control_flow: Any) -> Dict[str, List[str]]:
    if not isinstance(control_flow, dict):
        return {"requires_previous": [], "forbidden_after": []}
    return {
        "requires_previous": [str(item) for item in control_flow.get("requires_previous", [])],
        "forbidden_after": [str(item) for item in control_flow.get("forbidden_after", [])],
    }


def project_expressions(items: Any) -> List[str]:
    """Project structured predicates/effects/constraints to expression strings."""
    projected: List[str] = []
    for item in items or []:
        if isinstance(item, str):
            projected.append(item)
        elif isinstance(item, dict):
            expression = item.get("expression")
            if expression:
                projected.append(str(expression))
    return projected


def normalize_predicate(predicate: str) -> str:
    normalized = " ".join(str(predicate).strip().lower().split())
    return normalized.replace("==", "=")


def project_predicate_providers(actions: Any) -> Dict[str, List[Dict[str, str]]]:
    providers: Dict[str, List[Dict[str, str]]] = {}
    for action in actions or []:
        if not isinstance(action, dict):
            continue
        runtime = action.get("runtime") or {}
        provider_id = str(runtime.get("tool_name") or action.get("name") or action.get("id") or "")
        if not provider_id:
            continue
        runtime_role = str(runtime.get("execution_role") or "tool")
        executable = runtime.get("enabled") is not False and runtime.get("tau2_compatible") is not False
        for effect in project_expressions(action.get("effects", [])):
            for predicate in provided_predicates(effect):
                key = normalize_predicate(predicate)
                provider = {
                    "action_id": provider_id,
                    "runtime_role": runtime_role,
                    "executable": "true" if executable else "false",
                }
                if provider not in providers.setdefault(key, []):
                    providers[key].append(provider)
    return providers


def provided_predicates(effect: str) -> List[str]:
    text = str(effect).strip()
    normalized = normalize_predicate(text)
    predicates = [text]
    if normalized == "order cached in state":
        predicates.extend(["order observed", "order.status known"])
    elif normalized == "user cached in state":
        predicates.extend(["user observed"])
    elif normalized == "product cached in state":
        predicates.extend(["product observed", "product.variants known"])
    elif normalized == "item cached in state":
        predicates.extend(["item observed"])
    elif normalized.startswith("user_authenticated = true"):
        predicates.extend(["user_authenticated == true"])
    elif normalized.startswith("user_confirmed = true"):
        predicates.extend(["user_confirmed == true"])
    return predicates
