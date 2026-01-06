"""
Formatting classes for log output.

This module provides advanced formatting capabilities including:
- Token-based format string parsing
- Nested field access (e.g., level.name, extra.user_id)
- Format specifications (alignment, width, precision)
- Color tag parsing and colorization
"""

import contextlib
import linecache
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from .utils import BG_COLORS, COLORS, TimeUtils

if TYPE_CHECKING:
    from .record import LogRecord


class Token:
    """Represents a token in a format string."""

    def __init__(
        self,
        token_type: str,
        value: str,
        field_name: Optional[str] = None,
        format_spec: Optional[str] = None,
        color_tag: Optional[str] = None,
    ):
        """Initialize a token."""
        self.type = token_type
        self.value = value
        self.field_name = field_name
        self.format_spec = format_spec
        self.color_tag = color_tag

    def __repr__(self) -> str:
        """Return string representation."""
        if self.type == "literal":
            return f"Token(literal, {self.value!r})"
        else:
            return f"Token(field, {self.field_name!r}, spec={self.format_spec!r})"


class Colorizer:
    """Handle ANSI color code application and stripping."""

    def __init__(self) -> None:
        """Initialize the colorizer with color mappings."""
        self.colors: Dict[str, str] = {**COLORS, **BG_COLORS}
        self.level_colors: Dict[str, str] = {
            "TRACE": "dim+cyan",
            "DEBUG": "cyan",
            "INFO": "white",
            "SUCCESS": "bold+green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold+red",
        }

    def colorize(self, text: str, color: str) -> str:
        r"""Apply color to text."""
        if not color or not text:
            return text

        color_parts = color.split("+")

        codes = []
        for part in color_parts:
            part = part.strip()
            if part in self.colors:
                codes.append(self.colors[part])

        if not codes:
            return text

        return "".join(codes) + text + self.colors["reset"]

    def get_level_color(self, level_name: str) -> str:
        """Get the default color for a log level."""
        return self.level_colors.get(level_name.upper(), "white")

    def colorize_level(self, text: str, level_name: str) -> str:
        """Colorize text using the level's default color."""
        color = self.get_level_color(level_name)
        return self.colorize(text, color)

    def strip_colors(self, text: str) -> str:
        """Remove ANSI color codes from text."""
        ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")
        return ansi_pattern.sub("", text)

    def should_colorize(self) -> bool:
        """Check if colorization should be enabled."""
        return not os.environ.get("NO_COLOR")

    def apply_color_tag(
        self, text: str, tag: str, level_name: Optional[str] = None
    ) -> str:
        """Apply color based on a tag name."""
        if tag == "level" and level_name:
            return self.colorize_level(text, level_name)
        else:
            return self.colorize(text, tag)


class ExceptionFormatter:
    """Format exceptions with beautiful output and optional diagnosis."""

    def __init__(
        self,
        colorize: bool = False,
        backtrace: bool = True,
        diagnose: bool = False,
        max_context_lines: int = 5,
        max_value_length: int = 100,
    ):
        """Initialize exception formatter."""
        self.colorize = colorize
        self.backtrace = backtrace
        self.diagnose = diagnose
        self.max_context_lines = max_context_lines
        self.max_value_length = max_value_length

        self._colors = {
            "red": "\033[91m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "magenta": "\033[95m",
            "cyan": "\033[96m",
            "white": "\033[97m",
            "bold": "\033[1m",
            "dim": "\033[2m",
            "reset": "\033[0m",
        }

    def _color(self, text: str, color: str) -> str:
        """Apply color to text if colorization is enabled."""
        if not self.colorize:
            return text

        color_code = self._colors.get(color, "")
        reset = self._colors.get("reset", "")
        return f"{color_code}{text}{reset}"

    def format_exception(
        self,
        exc_info: Optional[
            Union[tuple[type, BaseException, Any], BaseException]
        ] = None,
    ) -> str:
        """Format an exception with full details."""
        exc_type: Optional[type]
        exc_value: Optional[BaseException]
        exc_tb: Optional[Any]

        if exc_info is None:
            exc_info_tuple = sys.exc_info()
            if exc_info_tuple[0] is None:
                return ""
            exc_type, exc_value, exc_tb = exc_info_tuple
        elif isinstance(exc_info, BaseException):
            exc_type = type(exc_info)
            exc_value = exc_info
            exc_tb = getattr(exc_info, "__traceback__", None)
        elif isinstance(exc_info, tuple) and len(exc_info) == 3:
            exc_type, exc_value, exc_tb = exc_info
            if exc_type is None or exc_value is None:
                return ""
        else:
            return "Invalid exception info"

        if exc_type is None or exc_value is None:
            return ""

        lines = []

        lines.append(self._color("-" * 70, "dim"))

        exc_name = exc_type.__name__
        exc_msg = str(exc_value) if exc_value else ""

        header = f"{exc_name}"
        if exc_msg:
            header += f": {exc_msg}"

        lines.append(self._color(header, "red") + self._color(" [Exception]", "dim"))

        if not self.backtrace:
            lines.append(self._color("-" * 70, "dim"))
            return "\n".join(lines)

        if exc_tb:
            lines.append("")
            lines.append(self._color("Traceback (most recent call last):", "bold"))

            tb_lines = self._format_traceback(exc_tb)
            lines.extend(tb_lines)

        lines.append(self._color("-" * 70, "dim"))

        return "\n".join(lines)

    def _format_traceback(self, tb: Any) -> List[str]:
        """Format the traceback with context and optional diagnosis."""
        lines = []

        frames = self._extract_frames(tb)

        for frame_info in frames:
            filename = frame_info["filename"]
            lineno = frame_info["lineno"]
            func_name = frame_info["function"]
            code_line = frame_info["code"]
            frame = frame_info["frame"]

            file_display = self._shorten_path(filename)
            location = (
                f"  {self._color('File ', 'dim')}"
                f"{self._color(file_display, 'cyan')},"
                f" {self._color('line ', 'dim')}"
                f"{self._color(str(lineno), 'yellow')},"
                f" {self._color('in ', 'dim')}"
                f"{self._color(func_name, 'magenta')}"
            )
            lines.append(location)

            if code_line:
                context_lines = self._get_context_lines(filename, lineno)
                if context_lines:
                    for ctx_lineno, ctx_line, is_error in context_lines:
                        line_num = f"{ctx_lineno:4d} "

                        if is_error:
                            formatted = f"    {self._color('>', 'red')} {self._color(line_num, 'red')}{self._color(ctx_line, 'bold')}"
                        else:
                            formatted = (
                                f"      {self._color(line_num, 'dim')}{ctx_line}"
                            )

                        lines.append(formatted)
                else:
                    lines.append(
                        f"    {self._color(code_line, 'white')}"
                        if code_line
                        else f"    {self._color('<source not available>', 'dim')}"
                    )

            if self.diagnose and frame:
                var_lines = self._format_frame_variables(frame)
                if var_lines:
                    lines.append(self._color("    Variables:", "yellow"))
                    lines.extend(var_lines)

            lines.append("")

        return lines

    def _extract_frames(self, tb: Any) -> List[Dict[str, Any]]:
        """Extract frame information from traceback."""
        frames = []

        while tb is not None:
            frame = tb.tb_frame
            lineno = tb.tb_lineno

            code = frame.f_code
            filename = code.co_filename
            func_name = code.co_name

            code_line = linecache.getline(filename, lineno).strip()

            frames.append(
                {
                    "filename": filename,
                    "lineno": lineno,
                    "function": func_name,
                    "code": code_line,
                    "frame": frame,
                }
            )

            tb = tb.tb_next

        return frames

    def _get_context_lines(
        self, filename: str, lineno: int
    ) -> List[tuple[int, str, bool]]:
        """Get context lines around the error line."""
        try:
            start = max(1, lineno - self.max_context_lines // 2)
            end = lineno + self.max_context_lines // 2 + 1

            try:
                linecache.checkcache(filename)
                file_lines = linecache.getlines(filename)
            except (OSError, ValueError):
                return []

            lines = []
            for i in range(start, end):
                if 1 <= i <= len(file_lines):
                    line = file_lines[i - 1]
                    line = line.rstrip("\n\r")
                    is_error = i == lineno
                    lines.append((i, line, is_error))

            return lines
        except Exception:
            return []

    def _format_frame_variables(self, frame: Any) -> List[str]:
        """Format local variables from a frame."""
        lines = []

        try:
            try:
                local_vars = getattr(frame, "f_locals", {})
            except (AttributeError, ValueError):
                local_vars = {}

            filtered_vars = {
                k: v
                for k, v in local_vars.items()
                if not k.startswith("__") and not callable(v)
            }

            if not filtered_vars:
                return []

            for var_name, var_value in sorted(filtered_vars.items()):
                value_str = self._format_value(var_value)
                var_line = f"      {self._color(var_name, 'green')} = {value_str}"
                lines.append(var_line)

        except Exception:
            pass

        return lines

    def _format_value(self, value: Any) -> str:
        """Format a variable value for display."""
        try:
            val_repr = repr(value)
            if len(val_repr) > self.max_value_length:
                val_repr = val_repr[: self.max_value_length] + "..."
            return self._color(val_repr, "magenta")
        except (AttributeError, ValueError, TypeError):
            return self._color("<unrepresentable>", "dim")

    def _shorten_path(self, path: str) -> str:
        """Shorten file path for display."""
        try:
            path_obj = Path(path)
            parts = path_obj.parts

            if "site-packages" in parts:
                idx = parts.index("site-packages")
                return str(Path(*parts[idx:]))

            try:
                rel_path = path_obj.relative_to(Path.cwd())
                return str(rel_path)
            except (ValueError, AttributeError):
                pass

            home = Path.home()
            with contextlib.suppress(ValueError, AttributeError):
                if path_obj.is_relative_to(home):
                    return "~/" + str(path_obj.relative_to(home))

            if len(parts) > 3:
                return ".../" + "/".join(parts[-3:])

            return str(path_obj)
        except (AttributeError, ValueError, TypeError):
            return path

    def format_exception_only(self, exc_type: type, exc_value: BaseException) -> str:
        """Format just the exception type and message, no traceback."""
        exc_name = exc_type.__name__
        exc_msg = str(exc_value) if exc_value else ""

        if exc_msg:
            return self._color(f"{exc_name}: {exc_msg}", "red")
        else:
            return self._color(exc_name, "red")

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"ExceptionFormatter("
            f"colorize={self.colorize}, "
            f"backtrace={self.backtrace}, "
            f"diagnose={self.diagnose})"
        )


class Formatter:
    """Format log records into strings."""

    def __init__(
        self,
        format_string: Optional[str] = None,
        colorize: bool = False,
        backtrace: bool = True,
        diagnose: bool = False,
    ):
        """Initialize formatter."""
        self.format_string = format_string or self._default_format()
        self.colorize = colorize
        self.backtrace = backtrace
        self.diagnose = diagnose
        self.tokens: List[Token] = []
        self.colorizer = Colorizer()
        self.exception_formatter = ExceptionFormatter(
            colorize=colorize, backtrace=backtrace, diagnose=diagnose
        )
        self._parse_format_string()

    def _default_format(self) -> str:
        """Return default format string."""
        return "{time} | {level: <8} | {name}:{function}:{line} - {message}"

    def _parse_format_string(self) -> None:
        """Parse format string into tokens."""
        self.tokens = []
        i = 0
        current_color = None

        while i < len(self.format_string):
            new_i = self._handle_escaped_braces(i)
            if new_i != i:
                i = new_i
                continue

            new_i, current_color = self._handle_color_tags(i, current_color)
            if new_i != i:
                i = new_i
                continue

            new_i = self._handle_field_tokens(i, current_color)
            if new_i != i:
                i = new_i
                continue

            i = self._handle_literals(i)

    def _handle_escaped_braces(self, i: int) -> int:
        """Handle {{ and }} escape sequences."""
        if i + 1 < len(self.format_string):
            char = self.format_string[i]
            next_char = self.format_string[i + 1]
            if (char == "{" and next_char == "{") or (char == "}" and next_char == "}"):
                self.tokens.append(Token("literal", char))
                return i + 2
        return i

    def _handle_color_tags(
        self, i: int, current_color: Optional[str]
    ) -> tuple[int, Optional[str]]:
        """Handle <...> color tags."""
        if self.format_string[i] == "<":
            end = self.format_string.find(">", i)
            if end != -1:
                tag = self.format_string[i : end + 1]
                if tag.startswith("</"):
                    current_color = None
                    self.tokens.append(Token("color_end", ""))
                else:
                    color_name = tag[1:-1]
                    current_color = color_name
                    self.tokens.append(Token("color_start", color_name))
                return end + 1, current_color
        return i, current_color

    def _handle_field_tokens(self, i: int, current_color: Optional[str]) -> int:
        """Handle {...} field tokens."""
        if self.format_string[i] == "{":
            end = self.format_string.find("}", i)
            if end != -1:
                field_content = self.format_string[i + 1 : end]
                if ":" in field_content:
                    field_name, format_spec = field_content.split(":", 1)
                else:
                    field_name = field_content
                    format_spec = None

                self.tokens.append(
                    Token(
                        "field",
                        self.format_string[i : end + 1],
                        field_name=field_name,
                        format_spec=format_spec,
                        color_tag=current_color,
                    )
                )
                return end + 1
        return i

    def _handle_literals(self, i: int) -> int:
        """Handle literal text strings."""
        literal_start = i
        while i < len(self.format_string) and self.format_string[i] not in "{}<":
            i += 1

        if i > literal_start:
            self.tokens.append(Token("literal", self.format_string[literal_start:i]))
        else:
            self.tokens.append(Token("literal", self.format_string[i]))
            i += 1
        return i

    def format(self, record: "LogRecord") -> str:
        """Format a log record using the parsed tokens."""
        try:
            result: List[str] = []
            color_stack: List[str] = []

            for token in self.tokens:
                self._process_token(token, record, result, color_stack)

            formatted_text = "".join(result)

            if self.colorize:
                formatted_text = self._apply_colors(formatted_text, record)

            if record.exception:
                exc_tuple = (
                    record.exception.type,
                    record.exception.value,
                    record.exception.traceback,
                )
                exception_text = self.exception_formatter.format_exception(exc_tuple)
                if exception_text:
                    formatted_text += "\n" + exception_text

            return formatted_text

        except (AttributeError, ValueError, TypeError) as e:
            return f"[{record.level.name}] {record.message} [FORMAT ERROR: {e}]"

    def _process_token(
        self,
        token: Token,
        record: "LogRecord",
        result: List[str],
        color_stack: List[str],
    ) -> None:
        """Process a single token during formatting."""
        if token.type == "literal":
            result.append(token.value)
        elif token.type == "field":
            if token.field_name is None:
                result.append("<missing>")
            else:
                value = self.get_field_value(record, token.field_name)
                formatted = self._apply_format_spec(
                    value, token.format_spec, token.field_name
                )
                result.append(formatted)
        elif token.type == "color_start":
            if self.colorize:
                color_tag = token.value
                color_stack.append(color_tag)
                result.append("\x00COLOR_START:" + color_tag + "\x00")
        elif token.type == "color_end" and self.colorize and color_stack:
            color_stack.pop()
            result.append("\x00COLOR_END\x00")

    def _apply_colors(self, text: str, record: "LogRecord") -> str:
        """Apply color tags to formatted text."""
        result = []
        i = 0
        color_stack = []

        while i < len(text):
            if text[i : i + 1] == "\x00":
                end = text.find("\x00", i + 1)
                if end != -1:
                    marker = text[i + 1 : end]

                    if marker.startswith("COLOR_START:"):
                        color_tag = marker[12:]
                        color_stack.append(color_tag)
                        i = end + 1
                        continue

                    elif marker == "COLOR_END":
                        if color_stack:
                            color_stack.pop()
                        i = end + 1
                        continue

            char_start = i
            while i < len(text) and text[i : i + 1] != "\x00":
                i += 1

            segment = text[char_start:i]

            if segment and color_stack:
                color_tag = color_stack[-1]
                if color_tag == "level":
                    segment = self.colorizer.colorize_level(segment, record.level.name)
                else:
                    segment = self.colorizer.colorize(segment, color_tag)

            result.append(segment)

        return "".join(result)

    def get_field_value(self, record: "LogRecord", field_name: str) -> Any:
        """Extract field value from record with nested access support."""
        try:
            parts = field_name.split(".")
            obj = record

            for i, part in enumerate(parts):
                if part == "extra" and i < len(parts) - 1:
                    next_part = parts[i + 1]
                    if isinstance(obj.extra, dict) and next_part in obj.extra:
                        return obj.extra[next_part]
                    else:
                        return "<missing>"

                if hasattr(obj, part):
                    obj = getattr(obj, part)
                elif isinstance(obj, dict) and part in obj:
                    obj = obj[part]
                else:
                    return f"<missing:{field_name}>"

            return obj

        except (AttributeError, ValueError, KeyError):
            return f"<error:{field_name}>"

    def _apply_format_spec(
        self, value: Any, format_spec: Optional[str], field_name: str
    ) -> str:
        """Apply format specification to a value."""
        if not format_spec:
            return str(value)

        try:
            if self._is_datetime_custom_format(value, format_spec, field_name):
                return self._format_datetime(value, format_spec)

            return self._try_format(value, format_spec)

        except (ValueError, TypeError, AttributeError, OverflowError):
            return self._format_fallback(value, format_spec)

    def _is_datetime_custom_format(
        self, value: Any, format_spec: str, field_name: str
    ) -> bool:
        """Check if we should use custom datetime formatting."""
        return (isinstance(value, datetime) or field_name == "time") and any(
            token in format_spec
            for token in ["YYYY", "MM", "DD", "HH", "mm", "ss", "SSS"]
        )

    def _try_format(self, value: Any, format_spec: str) -> str:
        """Try standard formatting, falling back to string formatting."""
        try:
            return format(value, format_spec)
        except (ValueError, TypeError):
            return self._format_fallback(value, format_spec)

    def _format_fallback(self, value: Any, format_spec: str) -> str:
        """Format the string representation of the value."""
        try:
            return format(str(value), format_spec)
        except (ValueError, TypeError):
            return str(value)

    def _format_datetime(self, dt: datetime, fmt: str) -> str:
        """Format datetime with custom tokens (Loguru-style)."""
        try:
            return TimeUtils.format_time(dt, fmt)
        except (ValueError, TypeError, AttributeError, OverflowError):
            return dt.strftime("%Y-%m-%d %H:%M:%S")

    def strip_colors(self, text: str) -> str:
        """Remove color tags from text."""
        result = re.sub(r"<[a-zA-Z_]+>", "", text)
        result = re.sub(r"</[a-zA-Z_]+>", "", result)
        return result
