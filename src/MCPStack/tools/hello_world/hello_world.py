from collections.abc import Callable

from MCPStack.core.tool.base import BaseTool


class HelloWorld(BaseTool):
    """Minimal example tool that exposes greetings in several languages.

    !!! note ""

        Serves as an example scaffold for real tools.
    """

    def __init__(self, allowed_languages: list[str] | None = None) -> None:
        super().__init__()
        self.required_env_vars = {
            "MCP_HELLO_PREFIX": "",
        }
        self.allowed_languages = {lang.lower() for lang in (allowed_languages or [])}
        self.prefix = ""

    def _initialize(self) -> None:
        pass

    def actions(self) -> list[Callable]:
        """actions function."""
        actions = [
            self.say_hello_world_in_french,
            self.say_hello_world_in_italian,
            self.say_hello_world_in_german,
            self.say_hello_world_in_chinese,
        ]
        if self.allowed_languages:
            actions = [
                a
                for a in actions
                if a.__name__.rsplit("_", 1)[-1].replace("_", "")
                in {"french", "italian", "german", "chinese"}
                and any(lang in a.__name__ for lang in self.allowed_languages)
            ]
        return actions

    def _with_prefix(self, s: str) -> str:
        import os

        pref = os.getenv("MCP_HELLO_PREFIX", "")
        return f"{pref} {s}" if pref else s

    def say_hello_world_in_french(self) -> str:
        """Return 'Hello world' in french.

        Returns:
          str: The translated greeting.
        """
        return self._with_prefix("Bonjour le monde")

    def say_hello_world_in_italian(self) -> str:
        """Return 'Hello world' in italian.

        Returns:
          str: The translated greeting.
        """
        return self._with_prefix("Ciao mondo")

    def say_hello_world_in_german(self) -> str:
        """Return 'Hello world' in german.

        Returns:
          str: The translated greeting.
        """
        return self._with_prefix("Hallo Welt")

    def say_hello_world_in_chinese(self) -> str:
        """Return 'Hello world' in chinese.

        Returns:
          str: The translated greeting.
        """
        return self._with_prefix("你好，世界")

    def to_dict(self) -> dict[str, object]:
        """to_dict function."""
        return {"allowed_languages": list(self.allowed_languages)}

    @classmethod
    def from_dict(cls, params: dict[str, object]):
        """from_dict function."""
        langs = params.get("allowed_languages") or []
        if isinstance(langs, list):
            langs = [str(x) for x in langs]
        else:
            langs = [str(langs)]
        return cls(allowed_languages=langs)  # type: ignore[arg-type]
