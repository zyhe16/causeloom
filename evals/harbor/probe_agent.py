"""Harbor agent used only for agent-phase isolation preflights."""

from __future__ import annotations

import json
from typing import override

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


class IsolationProbeAgent(BaseAgent):
    """Prove hidden artifacts are absent and outbound egress is blocked."""

    @staticmethod
    @override
    def name() -> str:
        return "research-isolation-probe"

    @override
    def version(self) -> str:
        return "1.0.0"

    @override
    async def setup(self, environment: BaseEnvironment) -> None:
        return

    @override
    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        del instruction
        checks = {
            "tests_hidden": "test ! -e /tests",
            "solution_hidden": "test ! -e /solution",
            "public_ipv4_blocked": (
                "! timeout 5 bash -c 'echo >/dev/tcp/1.1.1.1/80' 2>/dev/null"
            ),
            "public_dns_blocked": (
                "! timeout 5 bash -c 'echo >/dev/tcp/example.com/80' 2>/dev/null"
            ),
            "model_endpoint_reachable": (
                "timeout 5 bash -c 'echo >/dev/tcp/model-relay/10101' "
                "2>/dev/null"
            ),
        }
        results: dict[str, bool] = {}
        for name, command in checks.items():
            result = await environment.exec(command=command)
            results[name] = result.return_code == 0

        payload = json.dumps(results, sort_keys=True)
        escaped = payload.replace("'", "'\\''")
        await environment.exec(
            command=f"printf '%s\\n' '{escaped}' > /logs/agent/isolation-probe.json"
        )
        if not all(results.values()):
            failed = ", ".join(name for name, passed in results.items() if not passed)
            raise RuntimeError(f"Isolation preflight failed: {failed}")
