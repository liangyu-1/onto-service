"""Constraint verifier for airline domain action execution."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from action_bank import ActionBank, ActionSchema
from state_manager import DialogueState


class VerificationResult:
    def __init__(self, passed: bool, violations: List[str] = None):
        self.passed = passed
        self.violations = violations or []

    def __bool__(self):
        return self.passed


class AirlineConstraintVerifier:
    """Verifies if an airline action can be executed given current state."""

    def __init__(self, action_bank: ActionBank):
        self.action_bank = action_bank

    def verify(self, action_name: str, arguments: Dict[str, Any], state: DialogueState, db: Dict[str, Any]) -> VerificationResult:
        """Check all preconditions and constraints for an action."""
        schema = self.action_bank.get(action_name)
        if schema is None:
            return VerificationResult(False, [f"Unknown action: {action_name}"])

        violations = []

        # Check required parameters declared by the action ontology.
        for param_name in schema.parameters:
            if param_name not in arguments or arguments.get(param_name) in (None, "", []):
                violations.append(f"ARGUMENT: Missing required parameter '{param_name}'")

        # Check for duplicate actions (same action with same args already succeeded)
        dup = self._check_duplicate(action_name, arguments, state)
        if dup:
            violations.append(f"DUPLICATE: {dup}")

        # Check preconditions
        for precond in schema.preconditions:
            ok, msg = self._check_precondition(precond, action_name, arguments, state, db)
            if not ok:
                violations.append(f"PRECONDITION: {msg}")

        # Check constraints
        for constraint in schema.constraints:
            ok, msg = self._check_constraint(constraint, action_name, arguments, state, db)
            if not ok:
                violations.append(f"CONSTRAINT: {msg}")

        return VerificationResult(len(violations) == 0, violations)

    def _check_duplicate(self, action_name: str, arguments: Dict[str, Any], state: DialogueState) -> str:
        """Check if this exact action was already executed successfully."""
        for h in state.history:
            if h.get('action') != action_name:
                continue
            prev_args = h.get('arguments', {})
            if prev_args == arguments:
                result = h.get('result', {})
                if self._is_successful_result(result):
                    return f"Action {action_name} with same arguments already executed successfully. Use the result from history instead."
        return ""

    def _is_successful_result(self, result: Any) -> bool:
        if isinstance(result, dict):
            return 'error' not in result and 'verifier_rejected' not in result
        return result is not None

    def _check_precondition(self, precond: str, action_name: str, arguments: Dict[str, Any], state: DialogueState, db: Dict[str, Any]) -> Tuple[bool, str]:
        """Evaluate a precondition string."""
        precond = precond.strip()

        # Handle: user_authenticated == true
        if "user_authenticated" in precond:
            if not state.user_authenticated:
                return False, "User not authenticated"
            return True, ""

        # Handle: user_confirmed == true
        if "user_confirmed" in precond:
            if not state.user_confirmed:
                return False, "User did not confirm action"
            return True, ""

        # Handle: reservation.cabin != 'basic_economy' or cabin_change_only == true
        if "reservation.cabin" in precond and "basic_economy" in precond:
            reservation_id = arguments.get("reservation_id")
            reservation = self._get_reservation(reservation_id, state, db)
            if reservation is None:
                return False, f"Reservation {reservation_id} not found"
            if reservation.get("cabin") == "basic_economy":
                # Check if only cabin is changing (flights unchanged)
                new_flights = arguments.get("flights", [])
                old_flights = reservation.get("flights", [])
                if self._flights_unchanged(new_flights, old_flights):
                    return True, ""
                return False, "Basic economy flights cannot be modified"
            return True, ""

        # Handle: len(passengers) <= 5
        if precond == "len(passengers) <= 5":
            passengers = arguments.get("passengers")
            if not isinstance(passengers, list):
                return False, "passengers must be a list"
            if len(passengers) > 5:
                return False, f"Too many passengers: {len(passengers)} (max 5)"
            return True, ""

        # Handle: cabin in ['basic_economy', 'economy', 'business']
        if precond.startswith("cabin in"):
            cabin = arguments.get("cabin", "")
            allowed = ["basic_economy", "economy", "business"]
            if cabin not in allowed:
                return False, f"Invalid cabin: '{cabin}'"
            return True, ""

        # Handle: reservation.can_cancel == true
        if "can_cancel" in precond:
            reservation_id = arguments.get("reservation_id")
            reservation = self._get_reservation(reservation_id, state, db)
            if reservation is None:
                return False, f"Reservation {reservation_id} not found"
            if not self._can_cancel_reservation(reservation, db):
                return False, "Reservation cannot be cancelled (not within 24h, not business, no insurance, not airline-cancelled)"
            return True, ""

        # Handle: no_portion_flown == true
        if "no_portion_flown" in precond:
            reservation_id = arguments.get("reservation_id")
            reservation = self._get_reservation(reservation_id, state, db)
            if reservation is None:
                return False, f"Reservation {reservation_id} not found"
            if self._has_flown_segment(reservation, db):
                return False, "Some flight segments have already been flown"
            return True, ""

        # Handle: total_baggages >= current_total_baggages
        if "total_baggages >= current_total_baggages" in precond:
            reservation_id = arguments.get("reservation_id")
            new_total = arguments.get("total_baggages")
            reservation = self._get_reservation(reservation_id, state, db)
            if reservation is None:
                return False, f"Reservation {reservation_id} not found"
            old_total = reservation.get("total_baggages", 0)
            if new_total < old_total:
                return False, f"Cannot reduce baggage from {old_total} to {new_total}"
            return True, ""

        # Handle: len(passengers) == current_passenger_count
        if "len(passengers) == current_passenger_count" in precond:
            reservation_id = arguments.get("reservation_id")
            passengers = arguments.get("passengers")
            reservation = self._get_reservation(reservation_id, state, db)
            if reservation is None:
                return False, f"Reservation {reservation_id} not found"
            old_count = len(reservation.get("passengers", []))
            if not isinstance(passengers, list) or len(passengers) != old_count:
                return False, f"Passenger count must remain {old_count}"
            return True, ""

        # Default: pass (unknown preconditions are warnings)
        return True, ""

    def _check_constraint(self, constraint: str, action_name: str, arguments: Dict[str, Any], state: DialogueState, db: Dict[str, Any]) -> Tuple[bool, str]:
        """Evaluate a policy constraint."""
        constraint = constraint.strip()

        if "user_authenticated" in constraint:
            if not state.user_authenticated:
                return False, "User not authenticated"
            return True, ""

        if "user_confirmed" in constraint:
            if not state.user_confirmed:
                return False, "User did not confirm action"
            return True, ""

        if "referential_integrity" in constraint:
            return self._check_referential_integrity(action_name, arguments, state, db)

        # Default: pass
        return True, ""

    def _flights_unchanged(self, new_flights: List[Dict[str, Any]], old_flights: List[Dict[str, Any]]) -> bool:
        """Check if flight segments are identical (same flight_number and date)."""
        if len(new_flights) != len(old_flights):
            return False
        for nf, of in zip(new_flights, old_flights):
            if nf.get("flight_number") != of.get("flight_number"):
                return False
            if nf.get("date") != of.get("date"):
                return False
        return True

    def _get_reservation(self, reservation_id: Optional[str], state: DialogueState, db: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get reservation from cache or DB."""
        if reservation_id is None:
            return None
        if reservation_id in state.cached_reservations:
            return state.cached_reservations[reservation_id]
        return db.get("reservations", {}).get(reservation_id)

    def _can_cancel_reservation(self, reservation: Dict[str, Any], db: Dict[str, Any]) -> bool:
        """Check if a reservation can be cancelled per policy."""
        # Already cancelled
        if reservation.get("status") == "cancelled":
            return False

        # Business class
        if reservation.get("cabin") == "business":
            return True

        # Has insurance
        if reservation.get("insurance") == "yes":
            return True

        # Within 24h of booking (current time is 2024-05-15T15:00:00)
        from datetime import datetime, timedelta
        current_time = datetime(2024, 5, 15, 15, 0, 0)
        created_at = reservation.get("created_at", "")
        if created_at:
            try:
                created_dt = datetime.fromisoformat(created_at)
                if current_time - created_dt <= timedelta(hours=24):
                    return True
            except ValueError:
                pass

        # Check if any flight was airline-cancelled
        flights = db.get("flights", {})
        for seg in reservation.get("flights", []):
            fn = seg.get("flight_number")
            date = seg.get("date")
            flight = flights.get(fn)
            if flight:
                date_info = flight.get("dates", {}).get(date)
                if date_info and date_info.get("status") == "cancelled":
                    return True

        return False

    def _has_flown_segment(self, reservation: Dict[str, Any], db: Dict[str, Any]) -> bool:
        """Check if any segment of the reservation has already been flown."""
        flights = db.get("flights", {})
        for seg in reservation.get("flights", []):
            fn = seg.get("flight_number")
            date = seg.get("date")
            flight = flights.get(fn)
            if flight:
                date_info = flight.get("dates", {}).get(date)
                if date_info:
                    status = date_info.get("status", "")
                    if status in ("landed", "flying"):
                        return True
        return False

    def _check_referential_integrity(self, action_name: str, arguments: Dict[str, Any], state: DialogueState, db: Dict[str, Any]) -> Tuple[bool, str]:
        """Check referential integrity for airline actions."""
        user_id = arguments.get("user_id")
        reservation_id = arguments.get("reservation_id")

        # Check user exists
        if user_id:
            users = db.get("users", {})
            if user_id not in users and user_id not in state.cached_users:
                return False, f"User {user_id} not found"

        # Check reservation exists
        if reservation_id:
            reservations = db.get("reservations", {})
            if reservation_id not in reservations and reservation_id not in state.cached_reservations:
                return False, f"Reservation {reservation_id} not found"

        # Check payment method exists for user
        payment_id = arguments.get("payment_id")
        if payment_id and user_id:
            user = users.get(user_id) or state.cached_users.get(user_id)
            if user:
                user_methods = user.get("payment_methods", {})
                if payment_id not in user_methods:
                    return False, f"Payment method {payment_id} not in user profile"

        # Check payment methods list for book_reservation
        payment_methods = arguments.get("payment_methods")
        if payment_methods and user_id:
            user = users.get(user_id) or state.cached_users.get(user_id)
            if user:
                user_methods = user.get("payment_methods", {})
                for pm in payment_methods:
                    pid = pm.get("payment_id")
                    if pid and pid not in user_methods:
                        return False, f"Payment method {pid} not in user profile"

        # Check flights exist for book/update
        flights = arguments.get("flights")
        if flights:
            db_flights = db.get("flights", {})
            for seg in flights:
                fn = seg.get("flight_number")
                date = seg.get("date")
                if fn not in db_flights:
                    return False, f"Flight {fn} not found"
                flight = db_flights[fn]
                if date not in flight.get("dates", {}):
                    return False, f"Flight {fn} not available on {date}"

        return True, ""
