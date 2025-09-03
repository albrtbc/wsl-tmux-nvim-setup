#!/usr/bin/env python3
"""
Enhanced Logging and Error Handling System for WSM CLI

Provides comprehensive logging, error recovery, and user guidance.
"""

import os
import sys
import logging
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.prompt import Confirm
    from rich.traceback import install as install_rich_traceback
except ImportError as e:
    print(f"Error: Required packages not found: {e}", file=sys.stderr)
    sys.exit(1)


class LogLevel(Enum):
    """Log levels with severity"""
    DEBUG = (logging.DEBUG, "dim")
    INFO = (logging.INFO, "blue")
    SUCCESS = (25, "green")  # Custom level between INFO and WARNING
    WARNING = (logging.WARNING, "yellow")
    ERROR = (logging.ERROR, "red")
    CRITICAL = (logging.CRITICAL, "bold red")


class ErrorCategory(Enum):
    """Error categories for better handling"""
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    PERMISSIONS = "permissions"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    USER_INPUT = "user_input"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for errors"""
    category: ErrorCategory
    message: str
    details: Optional[str] = None
    suggestions: List[str] = None
    recovery_actions: List[Callable] = None
    user_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []
        if self.recovery_actions is None:
            self.recovery_actions = []
        if self.user_data is None:
            self.user_data = {}


@dataclass
class LogEntry:
    """Log entry with enhanced metadata"""
    timestamp: datetime
    level: LogLevel
    message: str
    component: Optional[str] = None
    operation: Optional[str] = None
    error_context: Optional[ErrorContext] = None
    extra_data: Optional[Dict[str, Any]] = None


class EnhancedLogger:
    """Enhanced logging system with error handling and recovery"""
    
    def __init__(self, name: str = "wsm", log_dir: Optional[Path] = None, console: Optional[Console] = None):
        self.name = name
        self.console = console or Console()
        self.log_entries: List[LogEntry] = []
        
        # Setup log directory
        if log_dir is None:
            log_dir = Path.home() / ".local" / "share" / "wsl-tmux-nvim-setup" / "logs"
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        # Install rich traceback handling
        install_rich_traceback(show_locals=True, suppress=[click])
        
        # Error recovery registry
        self.error_handlers: Dict[ErrorCategory, List[Callable]] = {}
        self._register_default_handlers()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        # Add custom SUCCESS level
        logging.addLevelName(25, "SUCCESS")
        
        # Create logger
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # File handler for detailed logs
        log_file = self.log_dir / f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Rich handler for console output
        rich_handler = RichHandler(
            console=self.console,
            show_time=False,
            show_path=False,
            rich_tracebacks=True
        )
        rich_handler.setLevel(logging.INFO)
        self.logger.addHandler(rich_handler)
        
        self.log_file_path = log_file
    
    def _register_default_handlers(self):
        """Register default error handlers"""
        
        # Network error handlers
        self.register_error_handler(ErrorCategory.NETWORK, self._handle_network_error)
        
        # Filesystem error handlers  
        self.register_error_handler(ErrorCategory.FILESYSTEM, self._handle_filesystem_error)
        
        # Permission error handlers
        self.register_error_handler(ErrorCategory.PERMISSIONS, self._handle_permission_error)
        
        # Configuration error handlers
        self.register_error_handler(ErrorCategory.CONFIGURATION, self._handle_config_error)
        
        # Dependency error handlers
        self.register_error_handler(ErrorCategory.DEPENDENCY, self._handle_dependency_error)
    
    def register_error_handler(self, category: ErrorCategory, handler: Callable):
        """Register an error handler for a specific category"""
        if category not in self.error_handlers:
            self.error_handlers[category] = []
        self.error_handlers[category].append(handler)
    
    def log(self, level: LogLevel, message: str, component: Optional[str] = None, 
            operation: Optional[str] = None, error_context: Optional[ErrorContext] = None,
            extra_data: Optional[Dict[str, Any]] = None):
        """Log a message with enhanced metadata"""
        
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            component=component,
            operation=operation,
            error_context=error_context,
            extra_data=extra_data
        )
        
        self.log_entries.append(entry)
        
        # Log to standard logger
        log_level = level.value[0]
        formatted_message = message
        
        if component:
            formatted_message = f"[{component}] {formatted_message}"
        if operation:
            formatted_message = f"({operation}) {formatted_message}"
        
        self.logger.log(log_level, formatted_message)
        
        # Handle errors
        if level in [LogLevel.ERROR, LogLevel.CRITICAL] and error_context:
            self._handle_error(error_context)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.log(LogLevel.INFO, message, **kwargs)
    
    def success(self, message: str, **kwargs):
        """Log success message"""
        self.log(LogLevel.SUCCESS, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, error_context: Optional[ErrorContext] = None, **kwargs):
        """Log error message"""
        self.log(LogLevel.ERROR, message, error_context=error_context, **kwargs)
    
    def critical(self, message: str, error_context: Optional[ErrorContext] = None, **kwargs):
        """Log critical message"""
        self.log(LogLevel.CRITICAL, message, error_context=error_context, **kwargs)
    
    def _handle_error(self, error_context: ErrorContext):
        """Handle an error with recovery suggestions"""
        
        # Display error information
        self._display_error_panel(error_context)
        
        # Try registered error handlers
        handlers = self.error_handlers.get(error_context.category, [])
        
        for handler in handlers:
            try:
                if handler(error_context):
                    self.success("Error resolved automatically")
                    return True
            except Exception as e:
                self.debug(f"Error handler failed: {e}")
        
        # Show recovery options to user
        if error_context.suggestions or error_context.recovery_actions:
            return self._interactive_error_recovery(error_context)
        
        return False
    
    def _display_error_panel(self, error_context: ErrorContext):
        """Display error information in a rich panel"""
        
        error_text = Text()
        error_text.append(f"Error Category: ", style="bold")
        error_text.append(f"{error_context.category.value.title()}\n", style="red")
        error_text.append(f"Message: ", style="bold") 
        error_text.append(f"{error_context.message}\n")
        
        if error_context.details:
            error_text.append(f"Details: ", style="bold")
            error_text.append(f"{error_context.details}\n", style="dim")
        
        if error_context.suggestions:
            error_text.append("\nSuggestions:\n", style="bold blue")
            for i, suggestion in enumerate(error_context.suggestions, 1):
                error_text.append(f"{i}. {suggestion}\n", style="blue")
        
        panel = Panel(
            error_text,
            title="🚨 Error Occurred",
            border_style="red"
        )
        
        self.console.print(panel)
    
    def _interactive_error_recovery(self, error_context: ErrorContext) -> bool:
        """Provide interactive error recovery options"""
        
        if not error_context.recovery_actions:
            return False
        
        self.console.print("\n[bold]Recovery Options:[/bold]")
        
        options = []
        for i, action in enumerate(error_context.recovery_actions, 1):
            action_name = getattr(action, '__name__', f'action_{i}').replace('_', ' ').title()
            options.append(action_name)
            self.console.print(f"{i}. {action_name}")
        
        options.append("Skip and continue")
        options.append("Abort operation")
        
        self.console.print(f"{len(options)-1}. Skip and continue")
        self.console.print(f"{len(options)}. Abort operation")
        
        try:
            choice = int(input("\nSelect option (number): ")) - 1
            
            if 0 <= choice < len(error_context.recovery_actions):
                # Execute recovery action
                try:
                    if error_context.recovery_actions[choice]():
                        self.success("Recovery action completed successfully")
                        return True
                    else:
                        self.warning("Recovery action failed")
                        return False
                except Exception as e:
                    self.error(f"Recovery action error: {e}")
                    return False
            
            elif choice == len(options) - 2:  # Skip
                self.warning("Error skipped, continuing...")
                return True
            
            elif choice == len(options) - 1:  # Abort
                self.info("Operation aborted by user")
                sys.exit(1)
            
            else:
                self.warning("Invalid choice, skipping error...")
                return False
                
        except (ValueError, KeyboardInterrupt):
            self.warning("Invalid input, skipping error...")
            return False
    
    def _handle_network_error(self, error_context: ErrorContext) -> bool:
        """Handle network-related errors"""
        import requests
        
        # Test internet connectivity
        try:
            requests.get("https://httpbin.org/status/200", timeout=5)
            self.info("Internet connectivity confirmed")
            return False  # Error not resolved, need to handle differently
        except requests.RequestException:
            error_context.suggestions.extend([
                "Check your internet connection",
                "Try again in a few minutes",
                "Use a different network if available",
                "Check if a VPN is interfering"
            ])
            return False
    
    def _handle_filesystem_error(self, error_context: ErrorContext) -> bool:
        """Handle filesystem-related errors"""
        # Check disk space
        import shutil
        
        try:
            total, used, free = shutil.disk_usage(Path.home())
            free_gb = free // (1024**3)
            
            if free_gb < 1:  # Less than 1GB free
                error_context.suggestions.extend([
                    f"Only {free_gb}GB disk space available",
                    "Free up disk space and try again",
                    "Choose a different installation location"
                ])
            
            return False
        except Exception:
            return False
    
    def _handle_permission_error(self, error_context: ErrorContext) -> bool:
        """Handle permission-related errors"""
        error_context.suggestions.extend([
            "Check file/directory permissions",
            "Try running with appropriate privileges",
            "Choose a location where you have write access",
            "Contact your system administrator"
        ])
        return False
    
    def _handle_config_error(self, error_context: ErrorContext) -> bool:
        """Handle configuration-related errors"""
        error_context.suggestions.extend([
            "Check configuration file syntax",
            "Reset configuration to defaults",
            "Remove corrupted configuration files",
            "Refer to documentation for correct format"
        ])
        return False
    
    def _handle_dependency_error(self, error_context: ErrorContext) -> bool:
        """Handle dependency-related errors"""
        error_context.suggestions.extend([
            "Install missing system dependencies",
            "Update package manager cache",
            "Check system requirements",
            "Use package manager to install prerequisites"
        ])
        return False
    
    def get_log_summary(self) -> Dict[str, Any]:
        """Get summary of logged events"""
        summary = {
            'total_entries': len(self.log_entries),
            'by_level': {},
            'by_component': {},
            'errors': [],
            'warnings': [],
            'log_file': str(self.log_file_path)
        }
        
        for entry in self.log_entries:
            # Count by level
            level_name = entry.level.name
            summary['by_level'][level_name] = summary['by_level'].get(level_name, 0) + 1
            
            # Count by component
            component = entry.component or 'unknown'
            summary['by_component'][component] = summary['by_component'].get(component, 0) + 1
            
            # Collect errors and warnings
            if entry.level == LogLevel.ERROR:
                summary['errors'].append({
                    'timestamp': entry.timestamp.isoformat(),
                    'message': entry.message,
                    'component': entry.component
                })
            elif entry.level == LogLevel.WARNING:
                summary['warnings'].append({
                    'timestamp': entry.timestamp.isoformat(),
                    'message': entry.message,
                    'component': entry.component
                })
        
        return summary
    
    def display_log_summary(self):
        """Display log summary in a rich table"""
        summary = self.get_log_summary()
        
        # Create summary table
        table = Table(title="Log Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Entries", str(summary['total_entries']))
        table.add_row("Log File", str(summary['log_file']))
        
        # Level breakdown
        for level, count in summary['by_level'].items():
            table.add_row(f"{level} Messages", str(count))
        
        self.console.print(table)
        
        # Show errors if any
        if summary['errors']:
            self.console.print(f"\n[red]Errors ({len(summary['errors'])}):[/red]")
            for error in summary['errors'][-5:]:  # Show last 5 errors
                self.console.print(f"• [{error['timestamp']}] {error['message']}")
    
    def cleanup(self):
        """Cleanup logging resources"""
        # Close file handlers
        for handler in self.logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                self.logger.removeHandler(handler)


# Global logger instance
_global_logger: Optional[EnhancedLogger] = None


def get_logger(name: str = "wsm") -> EnhancedLogger:
    """Get global logger instance"""
    global _global_logger
    
    if _global_logger is None:
        _global_logger = EnhancedLogger(name)
    
    return _global_logger


def create_error_context(category: ErrorCategory, message: str, **kwargs) -> ErrorContext:
    """Factory function to create error context"""
    return ErrorContext(category=category, message=message, **kwargs)


if __name__ == "__main__":
    # Test the enhanced logging system
    logger = get_logger("test")
    
    # Test different log levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.success("Success message")
    logger.warning("Warning message")
    
    # Test error with context
    error_context = create_error_context(
        category=ErrorCategory.NETWORK,
        message="Failed to download file",
        details="Connection timeout after 30 seconds",
        suggestions=["Check internet connection", "Try again later"]
    )
    
    logger.error("Network error occurred", error_context=error_context)
    
    # Display summary
    logger.display_log_summary()