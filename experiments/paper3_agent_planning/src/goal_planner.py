"""Goal-regression planner using ActionBank effects for ontology-grounded planning.

This planner treats ActionBank effects as planning operators: given a goal state
(predicate), it finds the action that produces it, then recursively satisfies
that action's preconditions by finding prerequisite actions.

Unlike the verifier-based approach (which only blocks invalid actions), this
planner proactively generates an action sequence that is admissible by
construction.
"""
from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from action_bank import ActionBank, ActionSchema
from state_manager import DialogueState


# ---------------------------------------------------------------------------
# Effect parsing and simulation
# ---------------------------------------------------------------------------

def apply_effect(effect: str, state: DialogueState, arguments: Dict[str, Any]) -> None:
    """Apply a single ActionBank effect to a simulated DialogueState."""
    eff = effect.strip().lower()

    # Authentication
    if "user_authenticated = true" in eff:
        state.user_authenticated = True
        return

    # Confirmation
    if "user_confirmed = true" in eff:
        state.user_confirmed = True
        return

    # Transfer
    if "transfer_to_human = true" in eff:
        state.transfer_to_human = True
        return

    # User ID binding (simplified: we don't know the real user_id yet)
    if "user_id = found_user_id" in eff:
        # Best-effort: if email is in args, keep a sentinel so later code
        # knows auth has happened.
        state.user_authenticated = True
        return

    # Object caching
    if "order cached in state" in eff:
        oid = arguments.get("order_id")
        if oid:
            state.cached_orders.setdefault(oid, {})
        return
    if "product cached in state" in eff:
        pid = arguments.get("product_id")
        if pid:
            state.cached_products.setdefault(pid, {})
        return
    if "item cached in state" in eff:
        iid = arguments.get("item_id")
        if iid:
            state.cached_products.setdefault(iid, {})  # reuse product cache
        return
    if "user cached in state" in eff:
        uid = arguments.get("user_id")
        if uid:
            state.cached_users.setdefault(uid, {})
        return

    # Order status mutations
    if "order.status = 'cancelled'" in eff:
        oid = arguments.get("order_id")
        if oid and oid in state.cached_orders:
            state.cached_orders[oid]["status"] = "cancelled"
        return
    if "order.status = 'return requested'" in eff:
        oid = arguments.get("order_id")
        if oid and oid in state.cached_orders:
            state.cached_orders[oid]["status"] = "return requested"
        return
    if "order.status = 'exchange requested'" in eff:
        oid = arguments.get("order_id")
        if oid and oid in state.cached_orders:
            state.cached_orders[oid]["status"] = "exchange requested"
        return
    if "order.status = 'pending (items modified)'" in eff:
        oid = arguments.get("order_id")
        if oid and oid in state.cached_orders:
            state.cached_orders[oid]["status"] = "pending"
        return
    if "order.status = 'pending'" in eff:
        oid = arguments.get("order_id")
        if oid and oid in state.cached_orders:
            state.cached_orders[oid]["status"] = "pending"
        return

    # Property updates
    if "order.address = new_address" in eff:
        oid = arguments.get("order_id")
        if oid and oid in state.cached_orders:
            state.cached_orders[oid]["address"] = arguments.get("address", {})
        return
    if "user.address = new_address" in eff:
        uid = arguments.get("user_id") or state.user_id
        if uid:
            state.cached_users.setdefault(uid, {})["address"] = arguments.get("address", {})
        return
    if "order.payment updated" in eff:
        oid = arguments.get("order_id")
        if oid and oid in state.cached_orders:
            state.cached_orders[oid]["payment_method_id"] = arguments.get("payment_method_id")
        return
    if "order.items replaced" in eff:
        oid = arguments.get("order_id")
        if oid and oid in state.cached_orders:
            state.cached_orders[oid]["items_replaced"] = True
        return

    # Refund trigger
    if "trigger refund" in eff:
        return  # no state change needed for planning

    # Task completed
    if "task completed" in eff:
        return


def precondition_satisfied(precond: str, state: DialogueState, db: Dict[str, Any], arguments: Dict[str, Any]) -> bool:
    """Check whether a precondition holds in the current (possibly simulated) state."""
    p = precond.strip()

    # user_authenticated
    if "user_authenticated == true" in p:
        return state.user_authenticated

    # user_confirmed (used in constraints but treated similarly)
    if "user_confirmed == true" in p:
        return state.user_confirmed

    # order.status == 'pending'
    if "order.status == 'pending'" in p:
        oid = arguments.get("order_id")
        if oid:
            order = state.cached_orders.get(oid) or db.get("orders", {}).get(oid)
            if order:
                return str(order.get("status", "")).lower() == "pending"
        return False

    # order.status == 'delivered'
    if "order.status == 'delivered'" in p:
        oid = arguments.get("order_id")
        if oid:
            order = state.cached_orders.get(oid) or db.get("orders", {}).get(oid)
            if order:
                return str(order.get("status", "")).lower() == "delivered"
        return False

    # reason in [...]
    if " in [" in p:
        parts = p.split(" in ")
        param_name = parts[0].strip()
        allowed = _parse_list(parts[1])
        actual = arguments.get(param_name, "")
        return actual in allowed

    # len(item_ids) == len(new_item_ids)
    if "len(item_ids) == len(new_item_ids)" in p:
        item_ids = arguments.get("item_ids")
        new_item_ids = arguments.get("new_item_ids")
        return (
            isinstance(item_ids, list)
            and isinstance(new_item_ids, list)
            and len(item_ids) == len(new_item_ids)
        )

    # Unknown preconditions default to False (must be resolved)
    return False


def _parse_list(text: str) -> List[str]:
    """Parse ['a', 'b'] into list."""
    if "[" not in text or "]" not in text:
        return []
    body = text.split("[", 1)[1].split("]", 1)[0]
    return [x.strip().strip("'\"").strip() for x in body.split(",") if x.strip()]


# ---------------------------------------------------------------------------
# Goal inference
# ---------------------------------------------------------------------------

def infer_goal_effects(task_info: str) -> List[str]:
    """Infer desired end-state effects from natural-language task description."""
    text = task_info.lower()
    goals: List[str] = []

    # Transfer / escalation
    if "transfer" in text or "human agent" in text or "speak to a person" in text:
        goals.append("transfer_to_human = true")
        return goals  # transfer is terminal

    # Order status changes
    if "cancel" in text:
        goals.append("order.status = 'cancelled'")
    if "return" in text and "exchange" not in text:
        goals.append("order.status = 'return requested'")
    if "exchange" in text:
        goals.append("order.status = 'exchange requested'")

    # Property changes
    if "address" in text or "shipping" in text:
        # Distinguish user profile address vs order address
        if "profile" in text or "my address" in text or "user address" in text:
            goals.append("user.address = new_address")
        else:
            goals.append("order.address = new_address")

    if "payment" in text or "card" in text:
        goals.append("order.payment updated")

    if any(w in text for w in ["change item", "replace item", "modify item", "different size", "different color", "different variant", "bigger", "smaller"]):
        if "exchange" not in text:
            goals.append("order.items replaced")

    # Information-only tasks (no state change goal)
    # These will result in an empty goal list → planner returns empty plan
    return goals


# ---------------------------------------------------------------------------
# Argument extraction from task text and DB
# ---------------------------------------------------------------------------

def extract_arguments(
    action: ActionSchema,
    task_info: str,
    state: DialogueState,
    db: Dict[str, Any],
) -> Dict[str, Any]:
    """Extract concrete arguments for an action from task text + DB."""
    args: Dict[str, Any] = {}
    text = task_info

    # Email
    if "email" in action.parameters:
        m = re.search(r"[\w.+-]+@[\w.-]+\.\w+", text)
        if m:
            args["email"] = m.group(0)

    # Order ID
    if "order_id" in action.parameters:
        ms = re.findall(r"#?W\d{7,10}\b", text, re.IGNORECASE)
        if ms:
            oid = ms[0] if ms[0].startswith("#") else f"#{ms[0]}"
            # Validate against DB
            if oid in db.get("orders", {}):
                args["order_id"] = oid
            elif oid[1:] in db.get("orders", {}):
                args["order_id"] = oid[1:]
            else:
                args["order_id"] = oid

    # Name + zip for authentication
    if "first_name" in action.parameters or "last_name" in action.parameters:
        matched = _match_user_by_task_text(text, db)
        if matched:
            name = matched.get("name", {})
            addr = matched.get("address", {})
            args["first_name"] = name.get("first_name", "")
            args["last_name"] = name.get("last_name", "")
            args["zip"] = addr.get("zip", "")

    # User ID
    if "user_id" in action.parameters:
        if state.user_id and state.user_id in db.get("users", {}):
            args["user_id"] = state.user_id

    # Reason for cancel
    if "reason" in action.parameters:
        if "mistake" in text.lower():
            args["reason"] = "ordered by mistake"
        else:
            args["reason"] = "no longer needed"

    # Payment method ID
    if "payment_method_id" in action.parameters:
        order_id = args.get("order_id")
        pm = _resolve_payment_method(order_id, state, db)
        if pm:
            args["payment_method_id"] = pm

    # Item IDs (prefer items explicitly mentioned in task text)
    if "item_ids" in action.parameters:
        order_id = args.get("order_id")
        if order_id:
            order = state.cached_orders.get(order_id) or db.get("orders", {}).get(order_id)
            if order:
                text = task_info.lower()
                mentioned = []
                for item in order.get("items", []):
                    product_id = item.get("product_id")
                    product = db.get("products", {}).get(product_id)
                    name = str(product.get("name", "")).lower() if product else ""
                    if name and name in text:
                        mentioned.append(item.get("item_id"))
                # Fallback to all items if none are explicitly mentioned
                args["item_ids"] = mentioned if mentioned else [
                    item.get("item_id")
                    for item in order.get("items", [])
                    if item.get("item_id")
                ]

    # New item IDs (for exchange / modify)
    if "new_item_ids" in action.parameters:
        # Do NOT auto-fill from task text (requires semantic matching).
        # Leave empty so downstream grounder/LLM can fill it.
        args["new_item_ids"] = []

    # Address
    if "address" in action.parameters:
        # Try user profile address first
        uid = args.get("user_id") or state.user_id
        if uid and uid in db.get("users", {}):
            user_addr = db["users"][uid].get("address")
            if isinstance(user_addr, dict):
                args["address"] = copy.deepcopy(user_addr)
        # Or from known orders
        if "address" not in args:
            for oid, order in db.get("orders", {}).items():
                if oid in text:
                    oaddr = order.get("address")
                    if isinstance(oaddr, dict):
                        args["address"] = copy.deepcopy(oaddr)
                        break

    # Confirmation description
    if "action_description" in action.parameters:
        target = action.action_id.replace("_", " ")
        oid = args.get("order_id", "")
        args["action_description"] = f"{target} for order {oid}".strip()

    # Summary for transfer
    if "summary" in action.parameters:
        args["summary"] = "Customer request requires human agent assistance."

    # new_item_ids for exchange / modify items (best-effort variant matching)
    if "new_item_ids" in action.parameters:
        order_id = args.get("order_id")
        item_ids = args.get("item_ids", [])
        if order_id and item_ids:
            new_ids = _match_replacement_variants(task_info, order_id, db, item_ids)
            if new_ids:
                args["new_item_ids"] = new_ids

    return args


def _match_replacement_variants(
    task_info: str, order_id: str, db: Dict[str, Any], target_item_ids: List[str]
) -> List[str]:
    """Best-effort matching of replacement variants for exchange/modify items.

    Only processes items listed in ``target_item_ids`` and returns a
    ``new_item_ids`` list aligned one-to-one with ``target_item_ids``.
    """
    text = task_info.lower()
    order = db.get("orders", {}).get(order_id)
    if not order:
        return []

    # Build a lookup from item_id → item record
    item_by_id = {str(item.get("item_id", "")): item for item in order.get("items", [])}
    matched: List[str] = []

    for item_id in target_item_ids:
        item = item_by_id.get(str(item_id))
        if not item:
            matched.append(str(item_id))
            continue

        product_id = item.get("product_id")
        product = db.get("products", {}).get(product_id)
        if not product:
            matched.append(str(item_id))
            continue

        name = str(product.get("name", "")).lower()
        # Only auto-match items explicitly mentioned in the task text
        if name and name not in text:
            matched.append(str(item_id))
            continue

        old_item_id = str(item.get("item_id", ""))
        old_options = item.get("options", {})
        old_price = item.get("price")

        best_variant: Optional[str] = None
        best_score = -1

        for variant_id, variant in product.get("variants", {}).items():
            if str(variant_id) == old_item_id or not variant.get("available", False):
                continue

            score = _variant_match_score(
                text, old_options, variant.get("options", {}), old_price, variant.get("price")
            )
            if score > best_score:
                best_score = score
                best_variant = str(variant_id)

        if best_variant:
            matched.append(best_variant)
        else:
            matched.append(old_item_id)

    return matched


def _variant_match_score(
    text: str,
    old_options: Dict[str, Any],
    new_options: Dict[str, Any],
    old_price: Any,
    new_price: Any,
) -> int:
    """Score a candidate replacement variant against task requirements."""
    score = 0

    # Keyword matching from task text (with synonyms and negative-context guard)
    for value in new_options.values():
        vtext = str(value).lower()
        if not vtext:
            continue

        # Direct keyword match
        if vtext in text:
            # Guard against negative context (e.g., "instead of Apple HomeKit")
            if _is_negated(text, vtext):
                score -= 4
            else:
                score += 2

        # Synonym matches
        for syn in _synonyms(vtext):
            if syn in text and syn != vtext:
                if _is_negated(text, syn):
                    score -= 4
                else:
                    score += 2

    # Price constraints
    if "same or lower" in text or "same price or lower" in text or "lower price" in text:
        try:
            if float(new_price) <= float(old_price):
                score += 2
            else:
                score -= 3
        except (TypeError, ValueError):
            pass

    # Size changes (bigger / smaller)
    size_keywords = {
        "bigger": ("size", 1), "larger": ("size", 1),
        "smaller": ("size", -1), "mini": ("size", -1),
    }
    for keyword, (opt_key, direction) in size_keywords.items():
        if keyword in text:
            old_val = str(old_options.get(opt_key, "")).lower()
            new_val = str(new_options.get(opt_key, "")).lower()
            # Simple lexical comparison for sizes like "small" < "medium" < "large"
            size_order = ["mini", "small", "medium", "large", "xl", "extra large", "full size", "compact"]
            old_idx = next((i for i, s in enumerate(size_order) if s in old_val), -1)
            new_idx = next((i for i, s in enumerate(size_order) if s in new_val), -1)
            if old_idx >= 0 and new_idx >= 0:
                if (new_idx - old_idx) * direction > 0:
                    score += 4
                elif (new_idx - old_idx) * direction < 0:
                    score -= 2

    # Water resistance constraint
    water = str(new_options.get("water resistance", "")).lower()
    if "without water resistance" in text or "no water resistance" in text:
        if water in {"not resistant", "no", "none"}:
            score += 3
        elif water:
            score -= 2

    # Keep same options
    for key, value in old_options.items():
        val_text = str(value).lower()
        if ("same" in text or "keep" in text) and val_text and new_options.get(key) == value:
            score += 1

    # Cheapest preference
    if "cheapest" in text:
        score += 1

    return score


def _synonyms(value: str) -> List[str]:
    """Return known synonyms for common product-option values."""
    mapping = {
        "google assistant": ["google home"],
        "google home": ["google assistant"],
        "amazon alexa": ["alexa"],
        "alexa": ["amazon alexa"],
        "apple homekit": ["homekit"],
        "homekit": ["apple homekit"],
    }
    return mapping.get(value, [])


def _is_negated(text: str, value: str) -> bool:
    """Heuristic: is ``value`` preceded by a negation phrase in ``text``?"""
    # Simple pattern: "instead of X", "not X", "rather than X"
    neg_patterns = [
        rf"instead of\s+{re.escape(value)}",
        rf"not\s+{re.escape(value)}",
        rf"rather than\s+{re.escape(value)}",
        rf"replace\s+{re.escape(value)}",
    ]
    return any(re.search(p, text) for p in neg_patterns)


def _match_user_by_task_text(text: str, db: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find a user record whose name appears in the task text."""
    text_lower = text.lower()
    zips = set(re.findall(r"\b\d{5}\b", text))
    for uid, user in db.get("users", {}).items():
        name = user.get("name", {})
        full = f"{name.get('first_name', '')} {name.get('last_name', '')}".lower().strip()
        if full and len(full) > 3 and full in text_lower:
            user_zip = str(user.get("address", {}).get("zip", ""))
            if not zips or user_zip in zips:
                return user
    return None


def _resolve_payment_method(order_id: Optional[str], state: DialogueState, db: Dict[str, Any]) -> Optional[str]:
    """Resolve a single payment_method_id for an order or user."""
    if order_id:
        order = state.cached_orders.get(order_id) or db.get("orders", {}).get(order_id)
        if order:
            methods = [
                p.get("payment_method_id")
                for p in order.get("payment_history", [])
                if p.get("payment_method_id")
            ]
            unique = list(dict.fromkeys(methods))
            if len(unique) == 1:
                return unique[0]
    if state.user_id and state.user_id in db.get("users", {}):
        user_methods = list(db["users"][state.user_id].get("payment_methods", {}).keys())
        if len(user_methods) == 1:
            return user_methods[0]
    return None


# ---------------------------------------------------------------------------
# Goal-regression planner
# ---------------------------------------------------------------------------

class GoalRegressionPlanner:
    """Generate action plans by regressing goal effects through ActionBank."""

    def __init__(self, action_bank: ActionBank):
        self.action_bank = action_bank

    def generate_plan(
        self,
        task_info: str,
        state: DialogueState,
        db: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate a full action plan for the task.

        Returns a list of action dicts, each with at least:
            {"action": str, "arguments": dict, "_from_goal_planner": True}
        """
        goals = infer_goal_effects(task_info)
        if not goals:
            # Informational / ambiguous task → no deterministic plan
            return []

        plan: List[Dict[str, Any]] = []
        sim_state = state.clone()

        for goal in goals:
            sub_plan = self._regress_goal(goal, sim_state, db, task_info)
            plan.extend(sub_plan)

        # Terminal action
        if plan and plan[-1]["action"] not in {"finish_task", "transfer_to_human_agents"}:
            plan.append({"action": "finish_task", "arguments": {}, "_from_goal_planner": True})

        return plan

    def _regress_goal(
        self,
        goal_effect: str,
        state: DialogueState,
        db: Dict[str, Any],
        task_info: str,
    ) -> List[Dict[str, Any]]:
        """Backward-chain from a goal effect to a sequence of actions."""
        target = self._find_action_by_effect(goal_effect)
        if target is None:
            return []

        args = extract_arguments(target, task_info, state, db)
        plan: List[Dict[str, Any]] = []
        sim = state.clone()

        # --- Prerequisite 1: authentication ---
        needs_auth = (
            "user_authenticated == true" in target.preconditions
            or "user_authenticated == true" in target.constraints
        )
        if needs_auth and not sim.user_authenticated:
            # Prefer email auth if email is present; otherwise use name+zip.
            auth_action = self.action_bank.get("find_user_id_by_email")
            auth_args = extract_arguments(auth_action, task_info, sim, db) if auth_action else {}
            if not auth_args.get("email"):
                auth_action = self.action_bank.get("find_user_id_by_name_zip")
                auth_args = extract_arguments(auth_action, task_info, sim, db) if auth_action else {}
            if auth_action and auth_args:
                plan.append({
                    "action": auth_action.action_id,
                    "arguments": auth_args,
                    "_from_goal_planner": True,
                    "_prerequisite_for": target.action_id,
                })
                for eff in auth_action.effects:
                    apply_effect(eff, sim, auth_args)

        # --- Prerequisite 2: user details (for payment/address context) ---
        if needs_auth and target.action_id not in {
            "find_user_id_by_email",
            "find_user_id_by_name_zip",
            "get_user_details",
        }:
            uid = args.get("user_id") or sim.user_id
            if uid and uid not in sim.cached_users:
                plan.append({
                    "action": "get_user_details",
                    "arguments": {"user_id": uid},
                    "_from_goal_planner": True,
                    "_prerequisite_for": target.action_id,
                })
                apply_effect("user cached in state", sim, {"user_id": uid})

        # --- Prerequisite 3: order details (if status precondition) ---
        needs_order_status = any("order.status ==" in p for p in target.preconditions)
        if needs_order_status:
            oid = args.get("order_id")
            if oid and oid not in sim.cached_orders:
                plan.append({
                    "action": "get_order_details",
                    "arguments": {"order_id": oid},
                    "_from_goal_planner": True,
                    "_prerequisite_for": target.action_id,
                })
                apply_effect("order cached in state", sim, {"order_id": oid})

        # --- Prerequisite 4: product details (for exchange / modify items) ---
        if target.action_id in {"exchange_delivered_order_items", "modify_pending_order_items"}:
            oid = args.get("order_id")
            if oid:
                order = db.get("orders", {}).get(oid) or sim.cached_orders.get(oid)
                if order:
                    # Only fetch product details for items that will be exchanged
                    item_id_set = set(str(i) for i in args.get("item_ids", []))
                    for item in order.get("items", []):
                        if str(item.get("item_id", "")) not in item_id_set:
                            continue
                        pid = item.get("product_id")
                        if pid and pid not in sim.cached_products:
                            plan.append({
                                "action": "get_product_details",
                                "arguments": {"product_id": pid},
                                "_from_goal_planner": True,
                                "_prerequisite_for": target.action_id,
                            })
                            apply_effect("product cached in state", sim, {"product_id": pid})

        # --- Prerequisite 5: user confirmation ---
        needs_confirm = "user_confirmed == true" in target.constraints
        if needs_confirm and not sim.user_confirmed:
            plan.append({
                "action": "ask_for_confirmation",
                "arguments": {
                    "action_description": f"{target.action_id} for order {args.get('order_id', 'this request')}"
                },
                "_from_goal_planner": True,
                "_prerequisite_for": target.action_id,
            })
            apply_effect("user_confirmed = true", sim, {})

        # --- Target action ---
        plan.append({
            "action": target.action_id,
            "arguments": args,
            "_from_goal_planner": True,
            "_goal_effect": goal_effect,
        })
        for eff in target.effects:
            apply_effect(eff, sim, args)

        return plan

    def _find_action_by_effect(self, goal_effect: str) -> Optional[ActionSchema]:
        """Find the action whose effect most closely matches the goal."""
        goal_lower = goal_effect.lower().strip()
        candidates: List[Tuple[int, ActionSchema]] = []

        for schema in self.action_bank.schemas.values():
            for eff in schema.effects:
                eff_lower = eff.lower().strip()
                score = 0

                # Exact match
                if goal_lower == eff_lower:
                    score = 100
                # Substring match
                elif goal_lower in eff_lower or eff_lower in goal_lower:
                    score = 50
                # Semantic match for order.status
                elif "order.status" in goal_lower and "order.status" in eff_lower:
                    score = 40
                # Semantic match for address
                elif "address" in goal_lower and "address" in eff_lower:
                    score = 40
                # Semantic match for payment
                elif "payment" in goal_lower and "payment" in eff_lower:
                    score = 40
                # Semantic match for items
                elif "items" in goal_lower and "items" in eff_lower:
                    score = 40
                # Transfer
                elif "transfer_to_human" in goal_lower and "transfer_to_human" in eff_lower:
                    score = 100

                if score > 0:
                    candidates.append((score, schema))
                    break  # one effect match is enough per schema

        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def format_plan_for_prompt(self, plan: List[Dict[str, Any]]) -> str:
        """Render a plan as readable text for LLM prompting."""
        if not plan:
            return "No ontology-derived plan available for this task."
        lines = ["Ontology-derived execution plan (generated by goal-regression over ActionBank effects):"]
        for i, step in enumerate(plan, 1):
            action = step["action"]
            args = step.get("arguments", {})
            arg_str = ", ".join(f'{k}="{v}"' for k, v in args.items() if v not in (None, [], {}))
            prereq = " [prerequisite]" if step.get("_prerequisite_for") else ""
            lines.append(f"  {i}. {action}({arg_str}){prereq}")
        return "\n".join(lines)
