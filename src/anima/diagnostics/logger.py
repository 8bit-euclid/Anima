from loguru import logger as _loguru_logger


class Logger:
    """
    A facade for logging operations that currently wraps the Loguru library.

    This class provides a consistent logging interface while abstracting away
    the underlying logging implementation. It supports all standard logging
    levels and preserves Loguru's advanced features like structured logging,
    context binding, and flexible configuration.

    The facade maintains minimal overhead by directly delegating calls to
    the underlying Loguru logger instance.

    Example:
        Basic usage:
        >>> logger = Logger()
        >>> logger.info("Application started")
        >>> logger.error("Error occurred: {error}", error="connection failed")

        With context binding:
        >>> request_logger = logger.bind(request_id="123", user_id="456")
        >>> request_logger.info("Processing user request")

        Custom configuration:
        >>> logger.configure(handlers=[{"sink": sys.stdout, "level": "DEBUG"}])
    """

    def __init__(self) -> None:
        self._logger = _loguru_logger

    def debug(self, message: str, *args, **kwargs) -> None:
        """
        Log a message with DEBUG level.

        Args:
            message: The log message string
            *args: Positional arguments for message formatting
            **kwargs: Keyword arguments for message formatting and context
        """
        self._logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """
        Log a message with INFO level.

        Args:
            message: The log message string
            *args: Positional arguments for message formatting
            **kwargs: Keyword arguments for message formatting and context
        """
        self._logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """
        Log a message with WARNING level.

        Args:
            message: The log message string
            *args: Positional arguments for message formatting
            **kwargs: Keyword arguments for message formatting and context
        """
        self._logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        """
        Log a message with ERROR level.

        Args:
            message: The log message string
            *args: Positional arguments for message formatting
            **kwargs: Keyword arguments for message formatting and context
        """
        self._logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        """
        Log a message with CRITICAL level.

        Args:
            message: The log message string
            *args: Positional arguments for message formatting
            **kwargs: Keyword arguments for message formatting and context
        """
        self._logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs) -> None:
        """
        Log a message with ERROR level and include exception traceback.

        This method should be called from an exception handler to log the
        current exception along with its traceback information.

        Args:
            message: The log message string
            *args: Positional arguments for message formatting
            **kwargs: Keyword arguments for message formatting and context

        Example:
            >>> try:
            ...     risky_operation()
            ... except Exception as e:
            ...     logger.exception("Operation failed: {operation}", operation="data_sync")
        """
        self._logger.exception(message, *args, **kwargs)

    def log(self, level: str | int, message: str, *args, **kwargs) -> None:
        """
        Log a message with the specified level.

        Args:
            level: The logging level (e.g., "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
                  Can be a string or integer
            message: The log message string, can contain formatting placeholders
            *args: Positional arguments for message formatting
            **kwargs: Keyword arguments for message formatting and context

        Example:
            >>> logger.log("WARNING", "Custom warning message")
            >>> logger.log(20, "Info level message using numeric level")
        """
        self._logger.log(level, message, *args, **kwargs)

    def bind(self, **kwargs) -> 'Logger':
        """
        Return a new logger with bound context variables.

        Creates a new Logger instance with additional context that will be
        included in all subsequent log messages from that logger instance.

        Args:
            **kwargs: Key-value pairs to bind as context

        Returns:
            Logger: A new Logger instance with the bound context

        Example:
            >>> request_logger = logger.bind(request_id="req-123", user_id="user-456")
            >>> request_logger.info("Processing request")  # Will include request_id and user_id

            >>> db_logger = logger.bind(component="database", table="users")
            >>> db_logger.error("Query failed")  # Will include component and table context
        """
        bound_logger = Logger()
        bound_logger._logger = self._logger.bind(**kwargs)
        return bound_logger

    def configure(self, **kwargs) -> None:
        """
        Configure the underlying logger.

        Allows full configuration of the Loguru logger including handlers,
        formatters, filters, and other settings. Accepts all configuration
        options supported by Loguru's configure method.

        Args:
            **kwargs: Configuration parameters for Loguru logger
                     Common options include:
                     - handlers: List of handler configurations
                     - levels: Custom level definitions
                     - extra: Additional context variables
                     - patcher: Function to patch log records
                     - activation: Activation rules

        Example:
            >>> logger.configure(
            ...     handlers=[
            ...         {"sink": sys.stdout, "level": "INFO"},
            ...         {"sink": "file.log", "level": "DEBUG", "rotation": "1 MB"}
            ...     ]
            ... )
        """
        self._logger.configure(**kwargs)

    def add(self, sink, **kwargs) -> int:
        """
        Add a sink (output destination) to the logger.

        Args:
            sink: The sink to add (file path, file object, callable, etc.)
            **kwargs: Additional configuration for the sink
                     Common options include:
                     - level: Minimum level for this sink
                     - format: Log format string
                     - filter: Filter function or dictionary
                     - colorize: Whether to colorize output
                     - serialize: Whether to serialize as JSON
                     - backtrace: Whether to include backtrace
                     - diagnose: Whether to include variable values
                     - enqueue: Whether to enqueue messages
                     - rotation: File rotation policy
                     - retention: File retention policy
                     - compression: Compression format

        Returns:
            int: Handler ID that can be used to remove the sink later

        Example:
            >>> handler_id = logger.add("app.log", level="INFO", rotation="10 MB")
            >>> logger.add(sys.stderr, level="ERROR", colorize=True)
            >>> logger.add(lambda msg: print(f"Custom: {msg}"), level="DEBUG")
        """
        return self._logger.add(sink, **kwargs)

    def remove(self, handler_id: int | None = None) -> None:
        """
        Remove a handler from the logger.

        Args:
            handler_id: The ID of the handler to remove. If None, removes
                       the default handler. Use the ID returned by add() method.

        Example:
            >>> handler_id = logger.add("temp.log")
            >>> logger.remove(handler_id)  # Remove specific handler
            >>> logger.remove()  # Remove default handler
        """
        self._logger.remove(handler_id)

    def level(self, name: str, **kwargs) -> None:
        """
        Create or update a logging level.

        Args:
            name: Name of the level
            **kwargs: Level configuration (no, color, icon)

        Example:
            >>> logger.level("TRACE", no=5, color="<cyan>", icon="🔍")
        """
        self._logger.level(name, **kwargs)

    def disable(self, name: str) -> None:
        """
        Disable logging for a specific module or logger name.

        Args:
            name: Name of the module or logger to disable

        Example:
            >>> logger.disable("third_party_module")
        """
        self._logger.disable(name)

    def enable(self, name: str) -> None:
        """
        Enable logging for a specific module or logger name.

        Args:
            name: Name of the module or logger to enable

        Example:
            >>> logger.enable("third_party_module")
        """
        self._logger.enable(name)


# Create a singleton instance for convenient access
logger = Logger()
