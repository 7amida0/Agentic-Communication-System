import random
from autogen_core import (MessageContext, RoutedAgent, message_handler,)
from messages.order_message import OrderMessage

class OrderAgent(RoutedAgent):

    def __init__(self) -> None:
        super().__init__(
            description=("Generates and validates production orders."))
        self.order_counter = 0

    def generate_order(self) -> OrderMessage:
        self.order_counter += 1
        order_id = (f"ORD-{self.order_counter:03d}")
        required_capability = random.choice(
            ["milling","drilling","cutting","turning","grinding",])

        deadline_minutes = random.choice([60,75,90,120,150,180,])

        quality_requirement = random.choice(["standard","high","critical",])

        priority = random.choice(
            ["urgent","critical","high","medium", "low"])

        return OrderMessage(
            order_id=order_id,
            priority=priority,
            required_capability=(
                required_capability
            ),
            deadline_minutes=deadline_minutes,
            quality_requirement=(
                quality_requirement
            ),
        )

    @message_handler
    async def handle_order_creation(
        self,
        message: OrderMessage,
        ctx: MessageContext,
    ) -> OrderMessage:

        print(
            f"Order Agent received order "
            f"{message.order_id}"
        )

        validated_order = OrderMessage(
            order_id=message.order_id,
            priority=message.priority,
            required_capability=(
                message.required_capability
            ),
            deadline_minutes=(
                message.deadline_minutes
            ),
            quality_requirement=(
                message.quality_requirement
            ),
        )

        print(
            f"Order Agent validated "
            f"{validated_order.order_id}"
        )

        return validated_order
