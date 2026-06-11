"""Simulator for airline domain tool execution."""
from __future__ import annotations

import copy
import random
import string
from typing import Any, Dict, List, Optional

from state_manager import DialogueState


class AirlineSimulator:
    """Simulates airline tool execution on a copy of the database."""

    CURRENT_TIME = "2024-05-15T15:00:00"

    def __init__(self, db: Dict[str, Any]):
        self.db = copy.deepcopy(db)
        self.users = self.db["users"]
        self.flights = self.db["flights"]
        self.reservations = self.db["reservations"]
        self._res_counter = len(self.reservations)

    def execute(self, action_name: str, arguments: Dict[str, Any], state: DialogueState) -> Any:
        """Execute an action and return the result."""
        method = getattr(self, action_name, None)
        if method is None:
            raise ValueError(f"Unknown action: {action_name}")
        return method(arguments, state)

    # --- Query actions (read-only) ---

    def get_user_details(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        user_id = arguments["user_id"]
        user = self.users.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")
        state.cached_users[user_id] = copy.deepcopy(user)
        return copy.deepcopy(user)

    def get_reservation_details(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        reservation_id = arguments["reservation_id"]
        reservation = self.reservations.get(reservation_id)
        if reservation is None:
            raise ValueError(f"Reservation {reservation_id} not found")
        state.cached_reservations[reservation_id] = copy.deepcopy(reservation)
        return copy.deepcopy(reservation)

    def search_direct_flight(self, arguments: Dict[str, Any], state: DialogueState) -> List[Dict[str, Any]]:
        origin = arguments["origin"]
        destination = arguments["destination"]
        date = arguments["date"]

        results = []
        for flight_number, flight in self.flights.items():
            if flight["origin"] != origin or flight["destination"] != destination:
                continue
            date_info = flight.get("dates", {}).get(date)
            if date_info is None:
                continue

            result = {
                "flight_number": flight_number,
                "origin": origin,
                "destination": destination,
                "scheduled_departure_time_est": flight.get("scheduled_departure_time_est"),
                "scheduled_arrival_time_est": flight.get("scheduled_arrival_time_est"),
                "date": date,
                "status": date_info.get("status"),
            }
            if date_info.get("status") == "available":
                result["available_seats"] = date_info.get("available_seats", {})
                result["prices"] = date_info.get("prices", {})

            results.append(result)

        state.cached_flights[f"{origin}_{destination}_{date}"] = copy.deepcopy(results)
        return results

    # --- Update actions (mutate DB) ---

    def book_reservation(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        user_id = arguments["user_id"]
        origin = arguments["origin"]
        destination = arguments["destination"]
        flight_type = arguments["flight_type"]
        cabin = arguments["cabin"]
        flights = arguments["flights"]
        passengers = arguments["passengers"]
        payment_methods = arguments["payment_methods"]
        total_baggages = arguments["total_baggages"]
        nonfree_baggages = arguments["nonfree_baggages"]
        insurance = arguments["insurance"]

        # Validate user
        user = self.users.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        # Validate passengers count
        if len(passengers) > 5:
            raise ValueError("Maximum 5 passengers allowed")

        # Validate cabin
        if cabin not in ("basic_economy", "economy", "business"):
            raise ValueError(f"Invalid cabin: {cabin}")

        # Validate flights and decrement seats
        total_price = 0
        for seg in flights:
            fn = seg["flight_number"]
            date = seg["date"]
            flight = self.flights.get(fn)
            if flight is None:
                raise ValueError(f"Flight {fn} not found")
            date_info = flight.get("dates", {}).get(date)
            if date_info is None:
                raise ValueError(f"Flight {fn} not available on {date}")
            if date_info.get("status") != "available":
                raise ValueError(f"Flight {fn} on {date} is not available (status: {date_info.get('status')})")

            available = date_info.get("available_seats", {}).get(cabin, 0)
            if available < len(passengers):
                raise ValueError(f"Not enough {cabin} seats on {fn} for {len(passengers)} passengers")

            price = date_info.get("prices", {}).get(cabin, 0)
            total_price += price * len(passengers)

            # Decrement seats
            date_info["available_seats"][cabin] = available - len(passengers)

        # Calculate baggage fees
        baggage_fee = nonfree_baggages * 50
        total_price += baggage_fee

        # Insurance fee
        if insurance == "yes":
            total_price += 30 * len(passengers)

        # Validate payment methods
        self._validate_payment_methods(user, payment_methods, total_price)

        # Deduct payments
        self._deduct_payments(user, payment_methods)

        # Generate reservation ID
        reservation_id = self._generate_reservation_id()

        # Build reservation
        reservation = {
            "reservation_id": reservation_id,
            "user_id": user_id,
            "origin": origin,
            "destination": destination,
            "flight_type": flight_type,
            "cabin": cabin,
            "flights": copy.deepcopy(flights),
            "passengers": copy.deepcopy(passengers),
            "payment_history": copy.deepcopy(payment_methods),
            "created_at": self.CURRENT_TIME,
            "total_baggages": total_baggages,
            "nonfree_baggages": nonfree_baggages,
            "insurance": insurance,
        }

        self.reservations[reservation_id] = reservation

        # Update user's reservations list
        if "reservations" not in user:
            user["reservations"] = []
        user["reservations"].append(reservation_id)

        state.cached_reservations[reservation_id] = copy.deepcopy(reservation)
        return copy.deepcopy(reservation)

    def update_reservation_flights(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        reservation_id = arguments["reservation_id"]
        new_cabin = arguments["cabin"]
        new_flights = arguments["flights"]
        payment_id = arguments["payment_id"]

        reservation = self.reservations.get(reservation_id)
        if reservation is None:
            raise ValueError(f"Reservation {reservation_id} not found")

        old_cabin = reservation["cabin"]
        old_flights = reservation["flights"]
        passengers = reservation["passengers"]
        num_passengers = len(passengers)

        # Validate new cabin
        if new_cabin not in ("basic_economy", "economy", "business"):
            raise ValueError(f"Invalid cabin: {new_cabin}")

        # Release old seats
        for seg in old_flights:
            fn = seg["flight_number"]
            date = seg["date"]
            flight = self.flights.get(fn)
            if flight:
                date_info = flight.get("dates", {}).get(date)
                if date_info and "available_seats" in date_info:
                    date_info["available_seats"][old_cabin] = date_info["available_seats"].get(old_cabin, 0) + num_passengers

        # Validate and occupy new seats
        total_new_price = 0
        for seg in new_flights:
            fn = seg["flight_number"]
            date = seg["date"]
            flight = self.flights.get(fn)
            if flight is None:
                # Rollback
                self._rollback_seats(old_flights, old_cabin, num_passengers)
                raise ValueError(f"Flight {fn} not found")
            date_info = flight.get("dates", {}).get(date)
            if date_info is None or date_info.get("status") != "available":
                self._rollback_seats(old_flights, old_cabin, num_passengers)
                raise ValueError(f"Flight {fn} on {date} is not available")
            available = date_info.get("available_seats", {}).get(new_cabin, 0)
            if available < num_passengers:
                self._rollback_seats(old_flights, old_cabin, num_passengers)
                raise ValueError(f"Not enough {new_cabin} seats on {fn}")
            date_info["available_seats"][new_cabin] = available - num_passengers
            total_new_price += date_info.get("prices", {}).get(new_cabin, 0) * num_passengers

        # Calculate old price (for kept segments, use original price from reservation)
        total_old_price = 0
        for seg in old_flights:
            # Use stored price if available, otherwise look up current price
            total_old_price += seg.get("price", 0)

        price_diff = total_new_price - total_old_price

        # Validate payment method if needed
        user = self.users.get(reservation["user_id"])
        if price_diff > 0:
            self._validate_single_payment(user, payment_id, price_diff)
            self._deduct_single_payment(user, payment_id, price_diff)
        elif price_diff < 0:
            # Refund - simplified: just record
            reservation.setdefault("refund_history", []).append({
                "payment_id": payment_id,
                "amount": abs(price_diff),
            })

        # Update reservation flights with new prices
        updated_flights = []
        for seg in new_flights:
            fn = seg["flight_number"]
            date = seg["date"]
            flight = self.flights.get(fn)
            price = flight["dates"][date]["prices"].get(new_cabin, 0)
            updated_flights.append({
                "origin": flight["origin"],
                "destination": flight["destination"],
                "flight_number": fn,
                "date": date,
                "price": price,
            })

        reservation["cabin"] = new_cabin
        reservation["flights"] = updated_flights
        reservation["payment_history"].append({
            "payment_id": payment_id,
            "amount": price_diff if price_diff > 0 else 0,
        })

        state.cached_reservations[reservation_id] = copy.deepcopy(reservation)
        return copy.deepcopy(reservation)

    def update_reservation_baggages(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        reservation_id = arguments["reservation_id"]
        total_baggages = arguments["total_baggages"]
        nonfree_baggages = arguments["nonfree_baggages"]
        payment_id = arguments["payment_id"]

        reservation = self.reservations.get(reservation_id)
        if reservation is None:
            raise ValueError(f"Reservation {reservation_id} not found")

        old_total = reservation["total_baggages"]
        if total_baggages < old_total:
            raise ValueError("Cannot remove checked bags")

        extra_bags = total_baggages - old_total
        if extra_bags > 0:
            # Fee is based on nonfree_baggages increase, not total bag increase
            old_nonfree = reservation.get("nonfree_baggages", 0)
            extra_nonfree = nonfree_baggages - old_nonfree
            if extra_nonfree > 0:
                fee = extra_nonfree * 50
                user = self.users.get(reservation["user_id"])
                self._validate_single_payment(user, payment_id, fee)
                self._deduct_single_payment(user, payment_id, fee)
                reservation["payment_history"].append({
                    "payment_id": payment_id,
                    "amount": fee,
                })

        reservation["total_baggages"] = total_baggages
        reservation["nonfree_baggages"] = nonfree_baggages

        state.cached_reservations[reservation_id] = copy.deepcopy(reservation)
        return copy.deepcopy(reservation)

    def update_reservation_passengers(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        reservation_id = arguments["reservation_id"]
        passengers = arguments["passengers"]

        reservation = self.reservations.get(reservation_id)
        if reservation is None:
            raise ValueError(f"Reservation {reservation_id} not found")

        if len(passengers) != len(reservation["passengers"]):
            raise ValueError("Cannot change the number of passengers")

        reservation["passengers"] = copy.deepcopy(passengers)

        state.cached_reservations[reservation_id] = copy.deepcopy(reservation)
        return copy.deepcopy(reservation)

    def cancel_reservation(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        reservation_id = arguments["reservation_id"]

        reservation = self.reservations.get(reservation_id)
        if reservation is None:
            raise ValueError(f"Reservation {reservation_id} not found")

        # Release seats
        cabin = reservation["cabin"]
        num_passengers = len(reservation["passengers"])
        for seg in reservation["flights"]:
            fn = seg["flight_number"]
            date = seg["date"]
            flight = self.flights.get(fn)
            if flight:
                date_info = flight.get("dates", {}).get(date)
                if date_info and "available_seats" in date_info:
                    date_info["available_seats"][cabin] = date_info["available_seats"].get(cabin, 0) + num_passengers

        reservation["status"] = "cancelled"

        state.cached_reservations[reservation_id] = copy.deepcopy(reservation)
        return copy.deepcopy(reservation)

    def transfer_to_human_agents(self, arguments: Dict[str, Any], state: DialogueState) -> str:
        state.transfer_to_human = True
        return "Transferred to human agent."

    def finish_task(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        return {"finished": True}

    def calculate(self, arguments: Dict[str, Any], state: DialogueState) -> str:
        expression = arguments.get("expression", "")
        return f"Calculated: {expression}"

    def ask_for_confirmation(self, arguments: Dict[str, Any], state: DialogueState) -> Dict[str, Any]:
        state.user_confirmed = True
        return {"confirmed": True}

    # --- Helpers ---

    def _generate_reservation_id(self) -> str:
        """Generate a new unique reservation ID."""
        self._res_counter += 1
        # Use random 6-char alphanumeric, retry on collision
        for _ in range(100):
            rid = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if rid not in self.reservations:
                return rid
        raise RuntimeError("Failed to generate unique reservation ID")

    def _validate_payment_methods(self, user: Dict[str, Any], payment_methods: List[Dict[str, Any]], total_price: int) -> None:
        """Check that payment methods are valid and sum to at least total_price."""
        if not payment_methods:
            raise ValueError("At least one payment method required")

        user_methods = user.get("payment_methods", {})
        total_paid = 0

        cc_count = 0
        cert_count = 0
        gc_count = 0

        for pm in payment_methods:
            pid = pm["payment_id"]
            amount = pm.get("amount", 0)

            if pid not in user_methods:
                raise ValueError(f"Payment method {pid} not in user profile")

            method = user_methods[pid]
            source = method.get("source", "")

            if source == "credit_card":
                cc_count += 1
            elif source == "certificate":
                cert_count += 1
                # Certificate remainder is wasted, but amount used can't exceed certificate value
                cert_amount = method.get("amount", 0)
                if amount > cert_amount:
                    raise ValueError(f"Certificate {pid} only has ${cert_amount}")
            elif source == "gift_card":
                gc_count += 1
                gc_amount = method.get("amount", 0)
                if amount > gc_amount:
                    raise ValueError(f"Gift card {pid} only has ${gc_amount}")
            else:
                raise ValueError(f"Unknown payment source: {source}")

            total_paid += amount

        if cc_count > 1:
            raise ValueError("At most one credit card allowed")
        if cert_count > 1:
            raise ValueError("At most one travel certificate allowed")
        if gc_count > 3:
            raise ValueError("At most three gift cards allowed")

        if total_paid < total_price:
            raise ValueError(f"Payment total ${total_paid} is less than price ${total_price}")

    def _deduct_payments(self, user: Dict[str, Any], payment_methods: List[Dict[str, Any]]) -> None:
        """Deduct payment amounts from user's payment methods."""
        user_methods = user.get("payment_methods", {})
        for pm in payment_methods:
            pid = pm["payment_id"]
            amount = pm.get("amount", 0)
            method = user_methods.get(pid)
            if method and method.get("source") in ("certificate", "gift_card"):
                method["amount"] = method.get("amount", 0) - amount

    def _validate_single_payment(self, user: Dict[str, Any], payment_id: str, amount: float) -> None:
        """Validate a single payment method has sufficient funds."""
        user_methods = user.get("payment_methods", {})
        if payment_id not in user_methods:
            raise ValueError(f"Payment method {payment_id} not in user profile")
        method = user_methods[payment_id]
        if method.get("source") in ("certificate", "gift_card"):
            if method.get("amount", 0) < amount:
                raise ValueError(f"Payment method {payment_id} has insufficient funds")

    def _deduct_single_payment(self, user: Dict[str, Any], payment_id: str, amount: float) -> None:
        """Deduct from a single payment method."""
        user_methods = user.get("payment_methods", {})
        method = user_methods.get(payment_id)
        if method and method.get("source") in ("certificate", "gift_card"):
            method["amount"] = method.get("amount", 0) - amount

    def _rollback_seats(self, flights: List[Dict[str, Any]], cabin: str, count: int) -> None:
        """Rollback seat decrement on failure."""
        for seg in flights:
            fn = seg["flight_number"]
            date = seg["date"]
            flight = self.flights.get(fn)
            if flight:
                date_info = flight.get("dates", {}).get(date)
                if date_info and "available_seats" in date_info:
                    date_info["available_seats"][cabin] = date_info["available_seats"].get(cabin, 0) + count
