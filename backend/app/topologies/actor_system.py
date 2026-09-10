"""
Actor Topology System: Independent Actors with Dedicated Mailboxes and Message Passing.

Architecture:
┌──────────────────────────────────────────────┐
│ Actor System (Ray / Akka / Asyncio)          │
├──────────────────────────────────────────────┤
│                                              │
│  SupervisorActor                             │
│    ↓                                         │
│  [Mailbox: requests]                         │
│    ↓                                         │
│  Receives: TaskRequest                       │
│  Processes: Decision logic                   │
│  Sends: RouteMessage to SpecialistActors     │
│                                              │
│  SpecialistActors (N parallel)               │
│    ↓                                         │
│  [Mailbox: work requests]                    │
│    ↓                                         │
│  Receives: RouteMessage(task_id, data)       │
│  Processes: LLM call                         │
│  Sends: ResultMessage to Supervisor/Validator│
│                                              │
│  ValidatorActor                              │
│    ↓                                         │
│  [Mailbox: results]                          │
│    ↓                                         │
│  Receives: ResultMessage(output)             │
│  Processes: Validation logic                 │
│  Sends: FinalResult                          │
│                                              │
└──────────────────────────────────────────────┘
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Check for Ray availability
try:
    import ray
    HAS_RAY = True
except ImportError:
    ray = None
    HAS_RAY = False


# ==============================================================================
# 1. Immutable Message Hierarchy
# ==============================================================================

@dataclass(frozen=True)
class Message:
    """
    Immutable message passed between actors via Mailboxes.
    Adheres strictly to the Actor Model principle of zero shared mutable state.
    """
    sender_id: str
    receiver_id: str
    content: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "content": dict(self.content),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class TaskRequest(Message):
    """Initial client task request delivered to the Supervisor's mailbox."""
    def __init__(self, task_id: str, task_input: str, sender_id: str = "client", receiver_id: str = "supervisor", **metadata: Any):
        content = {"task_id": task_id, "data": task_input, "task_input": task_input, **metadata}
        super().__init__(sender_id=sender_id, receiver_id=receiver_id, content=content, timestamp=time.time())

    @property
    def task_id(self) -> str:
        return self.content.get("task_id", "")

    @property
    def task_input(self) -> str:
        return self.content.get("data", self.content.get("task_input", ""))


@dataclass(frozen=True)
class RouteMessage(Message):
    """Routing message dispatched by Supervisor to a SpecialistActor."""
    def __init__(self, task_id: str, specialist_type: str, data: str, sender_id: str = "supervisor", **kwargs: Any):
        receiver_id = f"specialist_{specialist_type}"
        content = {"task_id": task_id, "specialist_type": specialist_type, "data": data, **kwargs}
        super().__init__(sender_id=sender_id, receiver_id=receiver_id, content=content, timestamp=time.time())

    @property
    def task_id(self) -> str:
        return self.content.get("task_id", "")

    @property
    def specialist_type(self) -> str:
        return self.content.get("specialist_type", "")

    @property
    def data(self) -> str:
        return self.content.get("data", "")


@dataclass(frozen=True)
class ResultMessage(Message):
    """Work result produced by a SpecialistActor and sent to Supervisor or Validator."""
    def __init__(self, task_id: str, specialist_type: str, output: str, receiver_id: str = "supervisor", sender_id: Optional[str] = None, **kwargs: Any):
        s_id = sender_id or f"specialist_{specialist_type}"
        content = {"task_id": task_id, "specialist_type": specialist_type, "output": output, **kwargs}
        super().__init__(sender_id=s_id, receiver_id=receiver_id, content=content, timestamp=time.time())

    @property
    def task_id(self) -> str:
        return self.content.get("task_id", "")

    @property
    def specialist_type(self) -> str:
        return self.content.get("specialist_type", "")

    @property
    def output(self) -> str:
        return self.content.get("output", "")


@dataclass(frozen=True)
class FinalResult(Message):
    """Validated final result issued by ValidatorActor."""
    def __init__(self, task_id: str, output: str, is_valid: bool, reason: str = "", receiver_id: str = "supervisor", sender_id: str = "validator", **kwargs: Any):
        content = {
            "task_id": task_id,
            "output": output,
            "is_valid": is_valid,
            "reason": reason,
            **kwargs
        }
        super().__init__(sender_id=sender_id, receiver_id=receiver_id, content=content, timestamp=time.time())

    @property
    def task_id(self) -> str:
        return self.content.get("task_id", "")

    @property
    def output(self) -> str:
        return self.content.get("output", "")

    @property
    def is_valid(self) -> bool:
        return bool(self.content.get("is_valid", False))

    @property
    def reason(self) -> str:
        return self.content.get("reason", "")


# ==============================================================================
# 2. LLM Client Abstraction & Factory
# ==============================================================================

class BaseLLMClient:
    """Base interface for LLM client supporting synchronous and asynchronous calls."""

    def call(self, system: str, user: str) -> str:
        raise NotImplementedError

    async def call_async(self, system: str, user: str) -> str:
        return await asyncio.to_thread(self.call, system, user)


class LiveBackendLLMClient(BaseLLMClient):
    """
    LLM Client connected to AgentMesh's LLMService for live OpenAI, Gemini, Claude, or Ollama completions.
    Strictly invokes live LLM endpoints; raises an explicit RuntimeError if unreachable or misconfigured.
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def call(self, system: str, user: str) -> str:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In an existing event loop, create task or run in executor
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(asyncio.run, self.call_async(system, user))
                    return future.result()
            return loop.run_until_complete(self.call_async(system, user))
        except Exception as err:
            raise RuntimeError(f"Actor LLM call failed for model '{self.model}': {err}") from err

    async def call_async(self, system: str, user: str) -> str:
        from app.services.llm_service import llm_service
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
        try:
            response = await llm_service.call_llm(messages=messages, max_tokens=600)
            if response and response.strip():
                return response.strip()
            raise RuntimeError(f"Received empty response from LLM model '{self.model}'")
        except Exception as err:
            logger.error(f"Live LLM call error in Actor system: {err}")
            raise RuntimeError(f"Actor system LLM invocation error for '{self.model}': {err}") from err


def get_llm_client(model: str = "gpt-4o", use_mock: Optional[bool] = None) -> BaseLLMClient:
    """
    Factory creating an LLM client configured for the given model.
    Strict mode: Always returns LiveBackendLLMClient.
    """
    return LiveBackendLLMClient(model=model)


# ==============================================================================
# 3. Mailbox Implementation (Actor Mailbox)
# ==============================================================================

class Mailbox:
    """
    Asynchronous FIFO message queue representing an Actor's mailbox.
    Stores unhandled messages, provides inspection metrics, and isolates actor execution.
    """

    def __init__(self, owner_id: str, capacity: int = 1000):
        self.owner_id = owner_id
        self.capacity = capacity
        self._queue: asyncio.Queue[Message] = asyncio.Queue(maxsize=capacity)
        self._history: List[Message] = []
        self._total_received = 0
        self._total_processed = 0

    @property
    def size(self) -> int:
        return self._queue.qsize()

    def is_empty(self) -> bool:
        return self._queue.empty()

    async def put(self, message: Message) -> None:
        """Enqueues an incoming message into the mailbox."""
        await self._queue.put(message)
        self._total_received += 1
        self._history.append(message)

    def put_nowait(self, message: Message) -> None:
        """Non-blocking enqueue for fire-and-forget message delivery."""
        self._queue.put_nowait(message)
        self._total_received += 1
        self._history.append(message)

    async def get(self) -> Message:
        """Dequeues the next pending message from the mailbox."""
        msg = await self._queue.get()
        self._total_processed += 1
        return msg

    def get_history(self) -> List[Message]:
        return list(self._history)

    def stats(self) -> Dict[str, Any]:
        return {
            "owner_id": self.owner_id,
            "current_size": self.size,
            "total_received": self._total_received,
            "total_processed": self._total_processed,
        }


# ==============================================================================
# 4. Ray Remote Proxy (Transparent Ray Compatibility)
# ==============================================================================

class _RemoteMethodWrapper:
    """Wraps an actor method to provide .remote(*args, **kwargs) semantics."""

    def __init__(self, actor_instance: Any, method_name: str):
        self.actor_instance = actor_instance
        self.method_name = method_name
        self.method = getattr(actor_instance, method_name)

    def remote(self, *args: Any, **kwargs: Any) -> Any:
        """
        Invokes the target method.
        If the method is a coroutine function, returns the coroutine for `await`.
        If synchronous, returns an awaitable coroutine.
        """
        if inspect.iscoroutinefunction(self.method):
            return self.method(*args, **kwargs)
        else:
            async def _run():
                return self.method(*args, **kwargs)
            return _run()


class RayProxyActor:
    """
    Transparent proxy enabling `.remote(...)` syntax when Ray is not initialized or in local mode.
    Allows exact Ray syntax (`actor = SupervisorActor.remote(...)`, `await actor.process_task.remote(...)`).
    """

    def __init__(self, actor_instance: Any):
        self._instance = actor_instance

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._instance, name)
        if callable(attr):
            return _RemoteMethodWrapper(self._instance, name)
        return attr


def actor_remote(cls: type) -> type:
    """
    Class decorator adding a `.remote(*args, **kwargs)` factory method.
    If Ray is imported and ray.is_initialized() is True, it registers with real Ray.
    Otherwise, returns RayProxyActor wrapping the native actor instance.
    """
    original_init = cls.__init__

    @classmethod
    def remote_factory(class_ref: type, *args: Any, **kwargs: Any) -> Any:
        if HAS_RAY and ray is not None and ray.is_initialized():
            ray_cls = ray.remote(class_ref)
            return ray_cls.remote(*args, **kwargs)
        else:
            instance = class_ref(*args, **kwargs)
            return RayProxyActor(instance)

    cls.remote = remote_factory
    return cls


# ==============================================================================
# 5. Actor Base Class & Lifecycle (Akka / Ray Pattern)
# ==============================================================================

class Actor(ABC):
    """
    Abstract Base Class for an Actor.
    Encapsulates state, behavior, and dedicated Mailbox.
    Communication occurs exclusively via immutable message passing.
    Provides:
    - receive(message): abstract message processing method
    - tell(message): non-blocking asynchronous fire-and-forget message dispatch
    - ask(message, timeout): request-reply pattern awaiting response
    """

    def __init__(self, actor_id: str):
        self.actor_id = actor_id
        self.mailbox = Mailbox(owner_id=actor_id)
        self.system: Optional[Any] = None

    @abstractmethod
    def receive(self, message: Message) -> Optional[Message]:
        """Handles an incoming message and optionally returns a response."""
        pass

    async def receive_async(self, message: Message) -> Optional[Message]:
        """Asynchronous handler variant; defaults to calling receive."""
        return self.receive(message)

    async def tell(self, message: Message) -> None:
        """Non-blocking asynchronous fire-and-forget message send."""
        if self.system:
            await self.system.tell(message)
        else:
            await self.mailbox.put(message)

    async def ask(self, message: Message, timeout: float = 5.0) -> Message:
        """Request-reply pattern: sends a message and awaits reply with timeout."""
        if self.system:
            return await self.system.ask(message, timeout=timeout)
        raise RuntimeError(f"Actor '{self.actor_id}' must be registered within an ActorSystem to use 'ask'.")


# ==============================================================================
# 6. Core Independent Actors
# ==============================================================================

@actor_remote
class SupervisorActor(Actor):
    """
    Supervisor as an independent Actor.
    Owns [Mailbox: requests].
    Receives: TaskRequest / prompt.
    Processes: Decision logic to determine appropriate specialist.
    Sends: RouteMessage to SpecialistActors.
    """

    def __init__(self, model: str = "gpt-4o"):
        super().__init__(actor_id="supervisor")
        self.model = model
        self.llm_client = get_llm_client(model)
        self.state: Dict[str, Any] = {}
        self.processed_tasks: List[str] = []

    def receive(self, message: Message) -> Optional[Message]:
        """Processes incoming TaskRequest or work message and routes to specialist."""
        task_id = message.content.get("task_id", f"task_{int(time.time()*1000)}")
        task_input = message.content.get("data", message.content.get("task_input", ""))
        return self.process_task(task_id, task_input)

    def process_task(self, task_id: str, task_input: str) -> RouteMessage:
        """
        Receive task, make routing decision via LLM, and generate RouteMessage for specialist.
        Synchronous / Ray-remote compatible.
        """
        decision = self.llm_client.call(
            system="Route this task. Return one word specialist category (coding, reasoning, math, critic, fact_checker).",
            user=task_input
        )
        clean_decision = re.sub(r"[^a-zA-Z0-9_]", "", decision.strip().lower().split()[0]) if decision else "reasoning"
        if clean_decision not in ["coding", "reasoning", "math", "critic", "fact_checker"]:
            clean_decision = "coding" if "code" in task_input.lower() else "reasoning"

        message = Message(
            sender_id="supervisor",
            receiver_id=f"specialist_{clean_decision}",
            content={
                "task_id": task_id,
                "data": task_input,
                "decision": clean_decision
            },
            timestamp=time.time()
        )

        self.state[task_id] = {
            "routed_to": clean_decision,
            "timestamp": time.time(),
            "status": "routed"
        }
        self.processed_tasks.append(task_id)
        self.mailbox.put_nowait(message)
        return message

    async def process_task_async(self, task_id: str, task_input: str) -> Message:
        """Asynchronous processing variant."""
        decision = await self.llm_client.call_async(
            system="Route this task. Return one word specialist category (coding, reasoning, math, critic, fact_checker).",
            user=task_input
        )
        clean_decision = re.sub(r"[^a-zA-Z0-9_]", "", decision.strip().lower().split()[0]) if decision else "reasoning"
        if clean_decision not in ["coding", "reasoning", "math", "critic", "fact_checker"]:
            clean_decision = "coding" if "code" in task_input.lower() else "reasoning"

        message = Message(
            sender_id="supervisor",
            receiver_id=f"specialist_{clean_decision}",
            content={"task_id": task_id, "data": task_input, "decision": clean_decision},
            timestamp=time.time()
        )
        self.state[task_id] = {"routed_to": clean_decision, "timestamp": time.time(), "status": "routed"}
        await self.mailbox.put(message)
        return message

    def validate_result(self, result: str) -> bool:
        """Validate specialist result via LLM."""
        validation = self.llm_client.call(
            system="Validate this output. Does it logically solve the request? Reply with 'yes' or 'no' followed by reasons.",
            user=result
        )
        return "yes" in validation.lower()

    async def validate_result_async(self, result: str) -> bool:
        """Asynchronous validation variant."""
        validation = await self.llm_client.call_async(
            system="Validate this output. Does it logically solve the request? Reply with 'yes' or 'no' followed by reasons.",
            user=result
        )
        return "yes" in validation.lower()


@actor_remote
class SpecialistActor(Actor):
    """
    Specialist as an independent Actor (N parallel instances).
    Owns [Mailbox: work requests].
    Receives: RouteMessage(task_id, data).
    Processes: Domain-specific LLM completion.
    Sends: ResultMessage to Supervisor / Validator.
    """

    def __init__(self, specialist_type: str, model: str = "gpt-4o"):
        super().__init__(actor_id=f"specialist_{specialist_type}")
        self.type = specialist_type
        self.model = model
        self.llm_client = get_llm_client(model)
        self.completed_jobs: int = 0

    def receive(self, message: Message) -> Optional[Message]:
        """Processes incoming RouteMessage and returns ResultMessage."""
        return self.process_work(message)

    def process_work(self, message: Message) -> ResultMessage:
        """Receive work message, process via LLM call, and return ResultMessage."""
        task_data = message.content
        user_input = task_data.get("data", task_data.get("task_input", ""))
        task_id = task_data.get("task_id", f"task_{int(time.time())}")

        self.mailbox.put_nowait(message)

        output = self.llm_client.call(
            system=f"You are a {self.type} specialist. Provide an in-depth, rigorous, and logically sound response.",
            user=user_input
        )

        response = ResultMessage(
            task_id=task_id,
            specialist_type=self.type,
            output=output,
            sender_id=self.actor_id,
            receiver_id="supervisor"
        )

        self.completed_jobs += 1
        return response

    async def process_work_async(self, message: Message) -> ResultMessage:
        """Asynchronous work processing variant."""
        task_data = message.content
        user_input = task_data.get("data", task_data.get("task_input", ""))
        task_id = task_data.get("task_id", f"task_{int(time.time())}")

        await self.mailbox.put(message)

        output = await self.llm_client.call_async(
            system=f"You are a {self.type} specialist. Provide an in-depth, rigorous, and logically sound response.",
            user=user_input
        )

        response = ResultMessage(
            task_id=task_id,
            specialist_type=self.type,
            output=output,
            sender_id=self.actor_id,
            receiver_id="supervisor"
        )
        self.completed_jobs += 1
        return response


@actor_remote
class ValidatorActor(Actor):
    """
    Validator as an independent Actor.
    Owns [Mailbox: results].
    Receives: ResultMessage(output).
    Processes: Multi-criteria verification logic.
    Sends: FinalResult.
    """

    def __init__(self, model: str = "gpt-4o", criteria: Optional[str] = None):
        super().__init__(actor_id="validator")
        self.model = model
        self.criteria = criteria or "Correctness, constraint adherence, completeness, and logical consistency."
        self.llm_client = get_llm_client(model)
        self.validation_history: List[FinalResult] = []

    def receive(self, message: Message) -> Optional[Message]:
        """Processes incoming ResultMessage and returns FinalResult."""
        return self.validate_output(message)

    def validate_output(self, message: Message) -> FinalResult:
        """
        Receives ResultMessage from specialist or supervisor, evaluates correctness,
        and returns immutable FinalResult.
        """
        self.mailbox.put_nowait(message)

        task_data = message.content
        task_id = task_data.get("task_id", "unknown")
        output = task_data.get("output", "")

        verification = self.llm_client.call(
            system=(
                f"You are the Solution Validator. Evaluate whether the proposed output satisfies "
                f"the criteria: '{self.criteria}'. Reply with 'YES' or 'NO' followed by a concise diagnostic justification."
            ),
            user=output
        )

        is_valid = "yes" in verification.lower()
        final_result = FinalResult(
            task_id=task_id,
            output=output,
            is_valid=is_valid,
            reason=verification.strip(),
            sender_id=self.actor_id,
            receiver_id=message.sender_id
        )

        self.validation_history.append(final_result)
        return final_result

    async def validate_output_async(self, message: Message) -> FinalResult:
        """Asynchronous validation variant."""
        await self.mailbox.put(message)

        task_data = message.content
        task_id = task_data.get("task_id", "unknown")
        output = task_data.get("output", "")

        verification = await self.llm_client.call_async(
            system=(
                f"You are the Solution Validator. Evaluate whether the proposed output satisfies "
                f"the criteria: '{self.criteria}'. Reply with 'YES' or 'NO' followed by a concise diagnostic justification."
            ),
            user=output
        )

        is_valid = "yes" in verification.lower()
        final_result = FinalResult(
            task_id=task_id,
            output=output,
            is_valid=is_valid,
            reason=verification.strip(),
            sender_id=self.actor_id,
            receiver_id=message.sender_id
        )
        self.validation_history.append(final_result)
        return final_result


# ==============================================================================
# 6. Actor System Coordinator (In-Process Mailbox Dispatcher)
# ==============================================================================

class ActorSystem:
    """
    Actor System Runtime (Akka & Ray Actor Model pattern).
    Manages actor registrations, mailboxes, non-blocking message dispatching (tell),
    request-reply semantics (ask), and error supervision without shared mutable state.
    """

    def __init__(self, name: str = "AgentMeshActorSystem"):
        self.name = name
        self.actors: Dict[str, Any] = {}
        self.mailboxes: Dict[str, Mailbox] = {}
        self.message_trace: List[Message] = []
        self._supervision_log: List[Dict[str, Any]] = []
        self._running = False

    def register_actor(self, actor_id: str, actor_instance: Any) -> None:
        """Registers an actor and assigns/attaches its mailbox and system reference."""
        self.actors[actor_id] = actor_instance
        if hasattr(actor_instance, "system"):
            actor_instance.system = self
        if hasattr(actor_instance, "mailbox"):
            self.mailboxes[actor_id] = actor_instance.mailbox
        else:
            mailbox = Mailbox(owner_id=actor_id)
            self.mailboxes[actor_id] = mailbox
            setattr(actor_instance, "mailbox", mailbox)

    def get_mailbox(self, actor_id: str) -> Optional[Mailbox]:
        return self.mailboxes.get(actor_id)

    async def tell(self, message: Message) -> None:
        """
        Non-blocking message dispatch to receiver mailbox (fire-and-forget).
        """
        self.message_trace.append(message)
        receiver_id = message.receiver_id
        mailbox = self.mailboxes.get(receiver_id)
        if mailbox:
            await mailbox.put(message)
        else:
            logger.warning(f"Dead letter: actor '{receiver_id}' not registered in ActorSystem '{self.name}'.")

    async def send_message(self, message: Message) -> None:
        """Alias for tell(message) ensuring full backward compatibility."""
        await self.tell(message)

    async def ask(self, message: Message, timeout: float = 5.0) -> Message:
        """
        Request-Reply pattern: sends message to target actor and awaits response with timeout.
        """
        self.message_trace.append(message)
        receiver_id = message.receiver_id
        target = self.actors.get(receiver_id)
        if not target:
            raise KeyError(f"Target actor '{receiver_id}' not found in ActorSystem '{self.name}'.")

        try:
            if hasattr(target, "receive_async") and inspect.iscoroutinefunction(target.receive_async):
                response = await asyncio.wait_for(target.receive_async(message), timeout=timeout)
            elif hasattr(target, "receive"):
                response = target.receive(message)
            else:
                raise NotImplementedError(f"Actor '{receiver_id}' does not implement receive().")

            if response:
                self.message_trace.append(response)
                return response
            raise ValueError(f"Actor '{receiver_id}' did not return a response for ask().")
        except Exception as exc:
            strategy = self.supervise(receiver_id, exc)
            logger.error(f"Supervision handling for '{receiver_id}': error={exc}, action={strategy}")
            raise

    def supervise(self, actor_id: str, error: Exception) -> str:
        """
        Error supervision strategy (Akka Supervisor pattern).
        Evaluates failure and determines recovery action: 'resume', 'restart', or 'escalate'.
        """
        record = {
            "actor_id": actor_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": time.time()
        }
        self._supervision_log.append(record)

        if isinstance(error, (TimeoutError, asyncio.TimeoutError)):
            return "resume"
        elif isinstance(error, (ValueError, TypeError)):
            return "restart"
        return "escalate"

    def get_supervision_log(self) -> List[Dict[str, Any]]:
        return list(self._supervision_log)

    def get_trace(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self.message_trace]


# ==============================================================================
# 7. Distributed Topology Runner
# ==============================================================================

def ray_init() -> None:
    """Initializes Ray if available; gracefully logs if in local proxy mode."""
    if HAS_RAY and ray is not None:
        if not ray.is_initialized():
            ray.init(ignore_reinit_error=True)
            logger.info("Ray distributed cluster initialized.")
    else:
        logger.info("Ray not installed; running in local Actor Mode.")


def ray_shutdown() -> None:
    """Shuts down Ray if active."""
    if HAS_RAY and ray is not None and ray.is_initialized():
        ray.shutdown()
        logger.info("Ray distributed cluster shutdown.")


async def run_distributed_topology(
    task_id: str = "fizzbuzz",
    task_input: str = "Solve FizzBuzz in Python up to N=15 with detailed comments.",
    model: str = "gpt-4o"
) -> Dict[str, Any]:
    """
    Run star topology as distributed actors matching the user specification.

    Execution Flow:
    1. Phase 1: Supervisor routes the task to appropriate specialist
    2. Phase 2: Specialist processes work in parallel
    3. Phase 3: Supervisor / Validator validates the output
    """
    ray_init()

    try:
        # Create actors
        supervisor = SupervisorActor.remote(model=model)
        coding_specialist = SpecialistActor.remote("coding", model)
        reasoning_specialist = SpecialistActor.remote("reasoning", model)
        validator = ValidatorActor.remote(model=model)

        # Phase 1: Supervisor routes
        route_message = await supervisor.process_task.remote(task_id, task_input)

        # Determine which specialist to invoke based on routing decision
        specialist_target = route_message.receiver_id
        if "coding" in specialist_target:
            active_specialist = coding_specialist
        else:
            active_specialist = reasoning_specialist

        # Phase 2: Specialist processes (parallel capable)
        result_message = await active_specialist.process_work.remote(route_message)

        # Phase 3: Supervisor validates (or ValidatorActor validates)
        is_valid = await supervisor.validate_result.remote(
            result_message.content["output"]
        )

        # Additional Phase 3b: Dedicated ValidatorActor assessment
        final_result = await validator.validate_output.remote(result_message)

        return {
            "task_id": task_id,
            "task_input": task_input,
            "route_message": route_message,
            "result_message": result_message,
            "is_valid": is_valid,
            "final_result": final_result,
            "output": result_message.content["output"]
        }
    finally:
        ray_shutdown()
