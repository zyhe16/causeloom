"""Docker environment with portable phase-specific network isolation."""

from __future__ import annotations

import asyncio
import json
import subprocess
from typing import override

from harbor.environments.capabilities import EnvironmentCapabilities
from harbor.environments.docker.docker import DockerEnvironment
from harbor.models.task.config import NetworkMode, NetworkPolicy


class OfflineDockerEnvironment(DockerEnvironment):
    """Disconnect the task's public network only while the agent is running."""

    def __init__(self, *args, **kwargs) -> None:
        self._public_network_name: str | None = None
        super().__init__(*args, **kwargs)

    @property
    @override
    def capabilities(self) -> EnvironmentCapabilities:
        return EnvironmentCapabilities(
            disable_internet=True,
            dynamic_network_policy=True,
            windows=False,
            mounted=True,
            docker_compose=True,
        )

    async def _main_container_id(self) -> str:
        result = await self._run_docker_compose_command(["ps", "-q", "main"])
        container_id = (result.stdout or "").strip()
        if not container_id:
            raise RuntimeError("Could not resolve the Harbor main container")
        return container_id

    @staticmethod
    def _inspect_networks(container_id: str) -> dict[str, object]:
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                "{{json .NetworkSettings.Networks}}",
                container_id,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        if not isinstance(data, dict):
            raise RuntimeError("Docker returned invalid network metadata")
        return data

    async def _docker_network(self, action: str, network: str, container_id: str) -> None:
        result = await asyncio.to_thread(
            subprocess.run,
            ["docker", "network", action, network, container_id],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"docker network {action} failed: {result.stdout} {result.stderr}"
            )

    @override
    async def _apply_network_policy(self, network_policy: NetworkPolicy) -> None:
        if network_policy.network_mode == NetworkMode.ALLOWLIST:
            raise ValueError("This environment supports fixed relay isolation, not allowlists")

        container_id = await self._main_container_id()
        networks = await asyncio.to_thread(self._inspect_networks, container_id)
        internal_names = [name for name in networks if name.endswith("_agent-internal")]
        if len(internal_names) != 1:
            raise RuntimeError(
                f"Expected exactly one internal agent network, found {sorted(networks)}"
            )

        public_names = [name for name in networks if name.endswith("_default")]
        if public_names:
            if len(public_names) != 1:
                raise RuntimeError(f"Ambiguous public networks: {public_names}")
            self._public_network_name = public_names[0]

        if network_policy.network_mode == NetworkMode.NO_NETWORK:
            if self._public_network_name in networks:
                await self._docker_network(
                    "disconnect", self._public_network_name, container_id
                )
        elif network_policy.network_mode == NetworkMode.PUBLIC:
            if not self._public_network_name:
                raise RuntimeError("Public Docker network name was not recorded")
            if self._public_network_name not in networks:
                await self._docker_network("connect", self._public_network_name, container_id)
        else:
            raise ValueError(f"Unsupported network mode: {network_policy.network_mode}")

        final_networks = await asyncio.to_thread(self._inspect_networks, container_id)
        has_public = self._public_network_name in final_networks
        should_have_public = network_policy.network_mode == NetworkMode.PUBLIC
        if has_public != should_have_public:
            raise RuntimeError(
                f"Network transition verification failed for {network_policy.network_mode}"
            )
