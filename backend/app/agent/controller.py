from typing import Any, Callable, Dict, List, Optional, Union

from backend.app.agent.hypotheses import Hypothesis
from backend.app.agent.planner import AgentAction, Planner
from backend.app.agent.state import InvestigationState, InvestigationStatus
from backend.app.agent.stopping import DEFAULT_MAX_ITERATIONS, evaluate_stopping_policy
from backend.tools.registry import ToolResult


ToolExecutorCallable = Callable[[Union[AgentAction, Dict[str, Any]]], ToolResult]
EvidenceEvaluatorCallable = Callable[[ToolResult, List[Hypothesis]], None]


def adapt_tool_executor(executor_obj: Any) -> ToolExecutorCallable:
    """
    Adapter that wraps a tool executor object (such as backend.tools.executor.ToolExecutor
    or a custom function) into a standardized callable that accepts an AgentAction or dict
    and returns a Person 3 ToolResult.
    """
    if hasattr(executor_obj, "execute"):
        def _adapted_executor(action: Union[AgentAction, Dict[str, Any]]) -> ToolResult:
            action_dict = action.model_dump() if isinstance(action, AgentAction) else action
            return executor_obj.execute(action_dict)
        return _adapted_executor
    elif callable(executor_obj):
        return executor_obj
    else:
        raise ValueError("executor_obj must be a callable or an object with an execute() method")


class InvestigationController:
    def __init__(self, planner: Optional[Planner] = None):
        self.planner = planner or Planner()

    def run_iteration(
        self,
        state: InvestigationState,
        hypotheses: List[Hypothesis],
        available_tools: List[Dict[str, Any]],
        executor: Union[ToolExecutorCallable, Any],
        evidence_evaluator: Optional[EvidenceEvaluatorCallable] = None,
    ) -> InvestigationState:
        missing_evidence = list(state.missing_evidence)

        candidates, selected_action = self.planner.plan(
            state=state,
            hypotheses=hypotheses,
            missing_evidence=missing_evidence,
            available_tools=available_tools,
        )

        state.candidate_actions = [c.model_dump() for c in candidates]

        if not selected_action:
            state.status = InvestigationStatus.INSUFFICIENT_EVIDENCE
            return state

        action_dict = selected_action.model_dump()
        state.selected_action = action_dict
        state.action_reason = selected_action.reason
        state.status = InvestigationStatus.RUNNING

        adapted_executor = adapt_tool_executor(executor)
        tool_result: ToolResult = adapted_executor(selected_action)

        if evidence_evaluator is not None:
            evidence_evaluator(tool_result, hypotheses)

        evidence_ids = getattr(tool_result, "evidence_ids", [])
        observations = getattr(tool_result, "observations", [])
        status = getattr(tool_result, "status", "unknown")

        for ev_id in evidence_ids:
            if ev_id not in state.evidence_ids:
                state.evidence_ids.append(ev_id)

        for obs in observations:
            if obs not in state.observations:
                state.observations.append(obs)

        # Remove addressed missing evidence items that match this action
        addressed_me = selected_action.missing_evidence_addressed
        if addressed_me:
            state.missing_evidence = [
                me for me in state.missing_evidence if me not in addressed_me
            ]

        state.actions_taken.append(action_dict)
        state.iteration += 1

        audit_event = {
            "iteration": state.iteration,
            "action": action_dict,
            "tool_result_status": status,
            "evidence_count": len(evidence_ids),
            "observation_count": len(observations),
        }
        state.audit_events.append(audit_event)

        return state

    def run_investigation(
        self,
        state: InvestigationState,
        hypotheses: List[Hypothesis],
        available_tools: List[Dict[str, Any]],
        executor: Union[ToolExecutorCallable, Any],
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        evidence_evaluator: Optional[EvidenceEvaluatorCallable] = None,
    ) -> InvestigationState:
        """
        Executes a multi-step investigation loop:
        1. Plan from current state.
        2. Execute selected action through executor.
        3. Call optional evidence_evaluator with ToolResult and hypotheses.
        4. Add ToolResult evidence_ids and observations to state.
        5. Record action and audit event.
        6. Update state for next step.
        7. Re-plan from updated state.
        8. Continue until stopping policy says stop or max_iterations reached.
        """
        state.status = InvestigationStatus.RUNNING

        while True:
            stopping = evaluate_stopping_policy(state, max_iterations=max_iterations)
            if stopping.should_stop:
                if state.status == InvestigationStatus.RUNNING:
                    state.status = InvestigationStatus.COMPLETED
                break

            prev_iteration = state.iteration
            state = self.run_iteration(
                state=state,
                hypotheses=hypotheses,
                available_tools=available_tools,
                executor=executor,
                evidence_evaluator=evidence_evaluator,
            )

            # If iteration count did not advance or state halted, break loop
            if state.iteration == prev_iteration or state.status == InvestigationStatus.INSUFFICIENT_EVIDENCE:
                break

        return state
