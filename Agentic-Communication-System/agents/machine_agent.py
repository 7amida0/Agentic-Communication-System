import time

from dataclasses import dataclass

from autogen_core import (
    MessageContext,
    RoutedAgent,
    message_handler,
)

from messages.machine_status_request import MachineStatusRequest
from messages.machine_status_response import MachineStatusResponse
from messages.order_message import OrderMessage


@dataclass
class QueuedOrder:
    order: OrderMessage
    processing_time_mins: int
    arrival_sequence: int


class MachineAgent(RoutedAgent):

    def __init__(
        self,
        machine_id: str,
        status: str,
        capability: str,
        estimated_processing_time_mins: int,
        maintenance_condition: float,
        active_warnings: list[str],
    ) -> None:

        super().__init__(
            description=f"Machine Agent {machine_id}"
        )

        self.machine_id = machine_id
        self.capability = capability
        self.maintenance_condition = maintenance_condition
        self.active_warnings = active_warnings

        self.current_order: QueuedOrder | None = None
        self.queue: list[QueuedOrder] = []

        self.next_sequence_number = 0

        self.current_order_started_at: float | None = None
        self.current_order_remaining_mins = 0

        self.default_processing_time_mins = (
            estimated_processing_time_mins
        )

        self.maintenance_override = (
            status.lower() == "maintenance"
        )

        self._update_status()

    def _update_status(self) -> None:

        if self.maintenance_override:
            self.status = "maintenance"

        elif self.current_order is not None:
            self.status = "busy"

        elif self.queue:
            self.status = "busy"

        else:
            self.status = "available"

    def _update_current_order_progress(self) -> None:

        if self.current_order is None:
            self._start_next_order()
            return

        if self.current_order_started_at is None:
            self.current_order_started_at = time.monotonic()
            return

        elapsed_seconds = (
            time.monotonic()
            - self.current_order_started_at
        )

        elapsed_minutes = int(
            elapsed_seconds // 60
        )

        if elapsed_minutes <= 0:
            return

        self.current_order_remaining_mins = max(
            0,
            self.current_order_remaining_mins
            - elapsed_minutes,
        )

        self.current_order_started_at = (
            time.monotonic()
        )

        if self.current_order_remaining_mins <= 0:

            completed_order = (
                self.current_order.order
            )

            print(
                f"[MACHINE COMPLETE] "
                f"{self.machine_id} completed "
                f"{completed_order.order_id}"
            )

            self.current_order = None
            self.current_order_started_at = None
            self.current_order_remaining_mins = 0

            self._start_next_order()

    @staticmethod
    def _priority_value(priority: str) -> int:

        return {
            "critical": 0,
            "urgent": 1,
            "high": 2,
            "medium": 3,
            "low": 4,
        }.get(
            priority.lower(),
            5,
        )

    def _sort_queue(self) -> None:

        self.queue.sort(
            key=lambda item: (
                self._priority_value(
                    item.order.priority
                ),
                item.order.deadline_minutes,
                item.arrival_sequence,
            )
        )

    def _start_next_order(self) -> None:

        if (
            self.maintenance_override
            or self.current_order is not None
            or not self.queue
        ):
            self._update_status()
            return

        next_order = self.queue.pop(0)

        self.current_order = next_order

        self.current_order_remaining_mins = (
            next_order.processing_time_mins
        )

        self.current_order_started_at = (
            time.monotonic()
        )

        print(
            f"[MACHINE START] "
            f"{self.machine_id} started "
            f"{next_order.order.order_id}"
        )

        print(
            f"  Capability: {self.capability}"
        )

        print(
            f"  Processing time: "
            f"{next_order.processing_time_mins} min"
        )

        print(
            f"  Deadline: "
            f"{next_order.order.deadline_minutes} min"
        )

        self._update_status()

    def _workload_before_new_order(self) -> int:

        self._update_current_order_progress()

        workload = 0

        if self.current_order is not None:
            workload += (
                self.current_order_remaining_mins
            )

        workload += sum(
            item.processing_time_mins
            for item in self.queue
        )

        return workload

    @message_handler
    async def handle_status_request(
        self,
        message: MachineStatusRequest,
        ctx: MessageContext,
    ) -> MachineStatusResponse:

        self._update_current_order_progress()

        workload = (
            self._workload_before_new_order()
        )

        completion = (
            workload
            + self.default_processing_time_mins
        )

        self._update_status()

        current = (
            self.current_order.order.order_id
            if self.current_order
            else "None"
        )

        print()
        print(
            f"{self.machine_id} status request "
            f"for order {message.order_id}"
        )

        print(
            f"  Status: {self.status}"
        )

        print(
            f"  Capability: {self.capability}"
        )

        print(
            f"  Current: {current}"
        )

        if self.current_order:
            print(
                f"  Remaining: "
                f"{self.current_order_remaining_mins} min"
            )

        print(
            f"  Queue: "
            f"{[item.order.order_id for item in self.queue]}"
        )

        print(
            f"  Queue length: "
            f"{len(self.queue)}"
        )

        print(
            f"  Available in: {workload} min"
        )

        print(
            f"  New order completion: "
            f"{completion} min"
        )

        return MachineStatusResponse(
            machine_id=self.machine_id,
            status=self.status,
            capability=self.capability,
            queue_length=len(self.queue),
            estimated_processing_time_mins=(
                self.default_processing_time_mins
            ),
            estimated_available_in_mins=workload,
            estimated_completion_in_mins=completion,
            queue_order_ids=[
                item.order.order_id
                for item in self.queue
            ],
            maintenance_condition=(
                self.maintenance_condition
            ),
            active_warnings=self.active_warnings,
        )

    @message_handler
    async def handle_order(
        self,
        message: OrderMessage,
        ctx: MessageContext,
    ) -> MachineStatusResponse:

        print()
        print(
            f"{self.machine_id} received order "
            f"{message.order_id}"
        )

        if self.maintenance_override:

            print(
                f"{self.machine_id} is under maintenance. "
                f"Order not accepted."
            )

            return await self._build_status_response(
                message.order_id
            )

        self._update_current_order_progress()

        self.next_sequence_number += 1

        queued_order = QueuedOrder(
            order=message,
            processing_time_mins=(
                self.default_processing_time_mins
            ),
            arrival_sequence=(
                self.next_sequence_number
            ),
        )

        self.queue.append(queued_order)

        self._sort_queue()

        if self.current_order is None:
            self._start_next_order()

        self._update_status()

        print(
            f"{self.machine_id} queue is now: "
            f"{[item.order.order_id for item in self.queue]}"
        )

        return await self._build_status_response(
            message.order_id
        )

    async def _build_status_response(
        self,
        order_id: str,
    ) -> MachineStatusResponse:

        self._update_current_order_progress()

        workload = (
            self._workload_before_new_order()
        )

        completion = (
            workload
            + self.default_processing_time_mins
        )

        self._update_status()

        return MachineStatusResponse(
            machine_id=self.machine_id,
            status=self.status,
            capability=self.capability,
            queue_length=len(self.queue),
            estimated_processing_time_mins=(
                self.default_processing_time_mins
            ),
            estimated_available_in_mins=workload,
            estimated_completion_in_mins=completion,
            queue_order_ids=[
                item.order.order_id
                for item in self.queue
            ],
            maintenance_condition=(
                self.maintenance_condition
            ),
            active_warnings=self.active_warnings,
        )
