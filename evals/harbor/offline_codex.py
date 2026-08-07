"""Codex Harbor agent with an uploaded binary and inherited model config."""

from __future__ import annotations

import hashlib
import shlex
from pathlib import Path
from typing import override

from harbor.agents.installed.base import CliFlag, with_prompt_template
from harbor.agents.installed.codex import Codex
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.trial.paths import EnvironmentPaths


class OfflineConfiguredCodex(Codex):
    """Run a pinned uploaded Codex binary without model/effort CLI overrides."""

    CLI_FLAGS = [
        CliFlag(
            "web_search",
            cli="-c",
            type="enum",
            choices=["disabled", "cached", "live"],
            default="disabled",
            format="-c web_search={value}",
        )
    ]

    def __init__(
        self,
        *args,
        codex_binary_path: str,
        codex_binary_sha256: str,
        codex_config_path: str,
        **kwargs,
    ) -> None:
        self._binary_path = Path(codex_binary_path).resolve()
        self._config_path = Path(codex_config_path).resolve()
        if not self._binary_path.is_file():
            raise ValueError(f"Codex Linux binary not found: {self._binary_path}")
        if not self._config_path.is_file():
            raise ValueError(f"Codex config not found: {self._config_path}")
        actual_hash = hashlib.sha256(self._binary_path.read_bytes()).hexdigest()
        if actual_hash.lower() != codex_binary_sha256.lower():
            raise ValueError(
                f"Codex binary SHA-256 mismatch: {actual_hash} != {codex_binary_sha256}"
            )
        super().__init__(*args, **kwargs)

    @override
    async def install(self, environment: BaseEnvironment) -> None:
        remote_binary = "/tmp/codex-upload"
        await environment.upload_file(self._binary_path, remote_binary)
        await self.exec_as_root(
            environment,
            command=(
                f"install -m 0755 {shlex.quote(remote_binary)} /usr/local/bin/codex && "
                f"rm -f {shlex.quote(remote_binary)} && codex --version"
            ),
        )
        if self._version:
            result = await environment.exec(command="codex --version")
            installed = self.parse_version(result.stdout or "")
            if result.return_code != 0 or installed != self._version:
                raise RuntimeError(
                    f"Uploaded Codex version {installed!r} does not match {self._version!r}"
                )

    @override
    @with_prompt_template
    async def run(
        self, instruction: str, environment: BaseEnvironment, context: AgentContext
    ) -> None:
        escaped_instruction = shlex.quote(instruction)
        cli_flags = self.build_cli_flags()
        cli_flags_arg = (cli_flags + " ") if cli_flags else ""
        auth_json_path = self._resolve_auth_json_path()
        remote_codex_home = self._REMOTE_CODEX_HOME.as_posix()
        remote_secrets_dir = self._REMOTE_CODEX_SECRETS_DIR.as_posix()
        remote_auth_path = (self._REMOTE_CODEX_SECRETS_DIR / "auth.json").as_posix()
        remote_config_path = (self._REMOTE_CODEX_HOME / "config.toml").as_posix()
        agent_sessions_dir = (EnvironmentPaths.agent_dir / "sessions").as_posix()
        env: dict[str, str] = {"CODEX_HOME": remote_codex_home}

        await self.exec_as_agent(
            environment,
            command=(
                f'mkdir -p "$CODEX_HOME" {shlex.quote(remote_secrets_dir)} '
                f"{shlex.quote(EnvironmentPaths.agent_dir.as_posix())}"
            ),
            env=env,
        )
        await environment.upload_file(self._config_path, remote_config_path)
        if environment.default_user is not None:
            await self.exec_as_root(
                environment,
                command=f"chown {environment.default_user} {remote_config_path}",
            )

        if auth_json_path:
            await environment.upload_file(auth_json_path, remote_auth_path)
            if environment.default_user is not None:
                await self.exec_as_root(
                    environment,
                    command=f"chown {environment.default_user} {remote_auth_path}",
                )
            setup_command = (
                f'ln -sf {shlex.quote(remote_auth_path)} "$CODEX_HOME/auth.json"\n'
            )
        else:
            env["OPENAI_API_KEY"] = self._get_env("OPENAI_API_KEY") or ""
            setup_command = (
                f"cat >{shlex.quote(remote_auth_path)} <<EOF\n"
                '{\n  "OPENAI_API_KEY": "${OPENAI_API_KEY}"\n}\nEOF\n'
                f"ln -sf {shlex.quote(remote_auth_path)} "
                '"$CODEX_HOME/auth.json"\n'
            )

        if openai_base_url := self._get_env("OPENAI_BASE_URL"):
            env["OPENAI_BASE_URL"] = openai_base_url
            setup_command += (
                '\ncat >>"$CODEX_HOME/config.toml" <<TOML\n'
                'openai_base_url = "${OPENAI_BASE_URL}"\n'
                "TOML\n"
            )

        if self._resume:
            setup_command += (
                f"\nif [ ! -d {shlex.quote(agent_sessions_dir)} ]; then\n"
                '  echo "Cannot resume Codex: no previous session logs found" >&2\n'
                "  exit 1\n"
                "fi\n"
                'rm -rf "$CODEX_HOME/sessions"\n'
                f"cp -R {shlex.quote(agent_sessions_dir)} "
                '"$CODEX_HOME/sessions"\n'
            )
        await self.exec_as_agent(environment, command=setup_command, env=env)

        try:
            await self.exec_as_agent(
                environment,
                command=(
                    f"codex exec {'resume --last ' if self._resume else ''}"
                    "--dangerously-bypass-approvals-and-sandbox "
                    "--skip-git-repo-check "
                    "--json "
                    "--enable unified_exec "
                    f"{cli_flags_arg}"
                    "-- "
                    f"{escaped_instruction} "
                    f"2>&1 </dev/null | tee {EnvironmentPaths.agent_dir / self._OUTPUT_FILENAME}"
                ),
                env=env,
            )
        finally:
            try:
                await self.exec_as_agent(
                    environment,
                    command=(
                        f"mkdir -p {EnvironmentPaths.agent_dir.as_posix()}\n"
                        'if [ -d "$CODEX_HOME/sessions" ]; then\n'
                        f"  rm -rf {(EnvironmentPaths.agent_dir / 'sessions').as_posix()}\n"
                        f'  cp -R "$CODEX_HOME/sessions" '
                        f"{(EnvironmentPaths.agent_dir / 'sessions').as_posix()}\n"
                        "fi"
                    ),
                    env=env,
                )
            except Exception:
                pass
            try:
                await self.exec_as_agent(
                    environment,
                    command=f'rm -rf {shlex.quote(remote_secrets_dir)} "$CODEX_HOME"',
                    env=env,
                )
            except Exception:
                pass
