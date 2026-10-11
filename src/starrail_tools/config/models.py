from pathlib import Path
from typing import Literal
import yaml
from pydantic import BaseModel, Field

class GameConfig(BaseModel):
    path: str = Field(default="", description="游戏启动路径")
    channel: Literal["cn", "bilibili", "global"] = Field(default="cn", description="游戏渠道")
    launch_timeout: int = Field(default=60, description="最长启动等待时间(秒)")

class AccountConfig(BaseModel):
    auto_login: bool = Field(default=False, description="是否自动填写账号密码")
    username: str = Field(default="", description="账号")
    password: str = Field(default="", description="密码")

class StaminaConfig(BaseModel):
    reserve_stamina: int = Field(default=0, description="保留体力阈值")
    target_dungeon: str = Field(default="侵蚀隧洞", description="目标副本名称")
    max_runs: int = Field(default=6, description="最大连刷次数")
    use_immersion_device: bool = Field(default=True, description="是否使用沉浸器")

class SystemConfig(BaseModel):
    post_action: Literal["keep_running", "close_game", "sleep", "shutdown"] = Field(
        default="keep_running", description="任务完成后的系统行为"
    )
    log_level: str = Field(default="INFO", description="日志等级")

class AppConfig(BaseModel):
    game: GameConfig = Field(default_factory=GameConfig)
    account: AccountConfig = Field(default_factory=AccountConfig)
    stamina: StaminaConfig = Field(default_factory=StaminaConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)

    @classmethod
    def load(cls, path: str | Path = "config.yaml") -> "AppConfig":
        config_path = Path(path)
        if not config_path.exists():
            default_config = cls()
            default_config.save(config_path)
            return default_config
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.model_validate(data)

    def save(self, path: str | Path = "config.yaml"):
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.model_dump(), f, allow_unicode=True, sort_keys=False)
