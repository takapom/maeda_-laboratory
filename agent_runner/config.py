"""Configuration loaded from environment variables."""

from __future__ import annotations

import getpass
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # LLM
    openai_api_key: str = ""
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    temperature: float = 0.2
    prompt_template_version: str = "v1"
    patch_file: str = ""
    patch_tool_name: str = "claude_code"
    patch_skill_name: str = ""
    operator_name: str = field(default_factory=getpass.getuser)

    # CoppeliaSim
    coppeliasim_host: str = "127.0.0.1"
    coppeliasim_port: int = 23000

    # Repo
    repo_url: str = ""
    base_ref: str = ""

    # Evaluation
    scene_id: str = "default"
    seed_list: list[int] = field(default_factory=lambda: [42])
    episodes: int = 1
    connect_timeout_sec: int = 30
    sim_time_limit_sec: int = 60
    run_timeout_sec: int = 300
    buffer_sec: int = 60

    # Paths
    artifacts_root: str = "/artifacts"
    workspace_root: str = "/workspace"

    @classmethod
    def from_env(cls) -> Config:
        seed_str = os.environ.get("SEED_LIST", "42")
        seeds = [int(s.strip()) for s in seed_str.split(",") if s.strip()]
        episodes = int(os.environ.get("EPISODES", "1"))
        sim_time_limit = int(os.environ.get("SIM_TIME_LIMIT_SEC", "60"))
        connect_timeout = int(os.environ.get("CONNECT_TIMEOUT_SEC", "30"))
        buffer = int(os.environ.get("BUFFER_SEC", "60"))

        return cls(
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            llm_provider=os.environ.get("LLM_PROVIDER", "openai"),
            llm_model=os.environ.get("LLM_MODEL", "gpt-4o"),
            temperature=float(os.environ.get("TEMPERATURE", "0.2")),
            prompt_template_version=os.environ.get("PROMPT_TEMPLATE_VERSION", "v1"),
            patch_file=os.environ.get("PATCH_FILE", ""),
            patch_tool_name=os.environ.get("PATCH_TOOL_NAME", "claude_code"),
            patch_skill_name=os.environ.get("PATCH_SKILL_NAME", ""),
            operator_name=os.environ.get("OPERATOR_NAME", getpass.getuser()),
            coppeliasim_host=os.environ.get("COPPELIASIM_HOST", "127.0.0.1"),
            coppeliasim_port=int(os.environ.get("COPPELIASIM_PORT", "23000")),
            repo_url=os.environ.get("REPO_URL", ""),
            base_ref=os.environ.get("BASE_REF", ""),
            scene_id=os.environ.get("SCENE_ID", "default"),
            seed_list=seeds,
            episodes=episodes,
            connect_timeout_sec=connect_timeout,
            sim_time_limit_sec=sim_time_limit,
            run_timeout_sec=connect_timeout + 2 * episodes * sim_time_limit + buffer,
            buffer_sec=buffer,
            artifacts_root=os.environ.get("ARTIFACTS_ROOT", "/artifacts"),
            workspace_root=os.environ.get("WORKSPACE_ROOT", "/workspace"),
        )
