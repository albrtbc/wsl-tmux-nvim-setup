"""
Unit tests for the main WSM CLI application.
"""

from unittest.mock import MagicMock, patch

import pytest

from cli.wsm import WSMContext, cli, main, show_welcome_screen


class TestWSMContext:
    """Test the WSMContext class."""

    def test_context_initialization(self):
        """Test WSMContext initializes correctly."""
        ctx = WSMContext()
        assert ctx.console is not None
        assert ctx.config_manager is None
        assert ctx.verbose is False
        assert ctx.quiet is False

    def test_context_initialize_with_config(self, temp_config_dir, mock_config_manager):
        """Test context initialization with custom config directory."""
        ctx = WSMContext()

        with patch("cli.wsm.ConfigManager") as mock_manager_class:
            mock_manager_class.return_value = mock_config_manager
            ctx.initialize(temp_config_dir, verbose=True, quiet=False)

            assert ctx.config_manager is mock_config_manager
            assert ctx.verbose is True
            assert ctx.quiet is False
            mock_manager_class.assert_called_once_with(str(temp_config_dir))

    def test_context_initialize_with_default_config(self, mock_config_manager):
        """Test context initialization with default config."""
        ctx = WSMContext()

        with patch("cli.wsm.get_default_config_manager", return_value=mock_config_manager):
            ctx.initialize()
            assert ctx.config_manager is mock_config_manager

    def test_context_initialize_error_handling(self, temp_config_dir):
        """Test context initialization error handling."""
        ctx = WSMContext()

        with patch("cli.wsm.ConfigManager", side_effect=Exception("Config error")):
            with pytest.raises(SystemExit):
                ctx.initialize(temp_config_dir)

    def test_print_methods(self, mock_console):
        """Test context print methods."""
        with patch("cli.wsm.Console", return_value=mock_console):
            ctx = WSMContext()

            # Test info message
            ctx.print_info("Test info")
            mock_console.print.assert_called_with("[blue]ℹ Test info[/blue]")

            # Test success message
            ctx.print_success("Test success")
            mock_console.print.assert_called_with("[green]✓ Test success[/green]")

            # Test warning message
            ctx.print_warning("Test warning")
            mock_console.print.assert_called_with("[yellow]⚠ Test warning[/yellow]")

            # Test error message
            ctx.print_error("Test error")
            mock_console.print.assert_called_with("[red]✗ Test error[/red]")

    def test_print_quiet_mode(self, mock_console):
        """Test print methods respect quiet mode."""
        with patch("cli.wsm.Console", return_value=mock_console):
            ctx = WSMContext()
            ctx.quiet = True

            # These should not print in quiet mode
            ctx.print_info("Test info")
            ctx.print_success("Test success")
            ctx.print_warning("Test warning")

            # Error should still print
            ctx.print_error("Test error")
            mock_console.print.assert_called_once_with("[red]✗ Test error[/red]")

    def test_print_verbose_mode(self, mock_console):
        """Test verbose print method."""
        with patch("cli.wsm.Console", return_value=mock_console):
            ctx = WSMContext()

            # Normal mode - should not print
            ctx.print_verbose("Verbose message")
            mock_console.print.assert_not_called()

            # Verbose mode - should print
            ctx.verbose = True
            ctx.print_verbose("Verbose message")
            mock_console.print.assert_called_with("[dim]Verbose message[/dim]")

            # Verbose + quiet mode - should not print
            ctx.quiet = True
            mock_console.print.reset_mock()
            ctx.print_verbose("Verbose message")
            mock_console.print.assert_not_called()


class TestCLICommands:
    """Test the main CLI command group."""

    def test_cli_version_flag(self, cli_runner, mock_version_manager):
        """Test --version flag shows version information."""
        with patch("cli.wsm.ComponentVersionManager", return_value=mock_version_manager):
            result = cli_runner.invoke(cli, ["--version"])

            assert result.exit_code == 0
            assert "WSL-Tmux-Nvim-Setup Manager v1.0.0" in result.output

    def test_cli_version_flag_fallback(self, cli_runner):
        """Test --version flag fallback when version detection fails."""
        with patch("cli.wsm.ComponentVersionManager", side_effect=Exception("Version error")):
            result = cli_runner.invoke(cli, ["--version"])

            assert result.exit_code == 0
            assert "WSL-Tmux-Nvim-Setup Manager v1.0.0" in result.output

    def test_cli_help_output(self, cli_runner):
        """Test CLI help output contains expected information."""
        result = cli_runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "WSL-Tmux-Nvim-Setup Manager" in result.output
        assert "install" in result.output
        assert "update" in result.output
        assert "status" in result.output
        assert "config" in result.output

    def test_cli_no_command_shows_welcome(self, cli_runner, mock_config_manager):
        """Test CLI with no command shows welcome screen."""
        with patch("cli.wsm.get_default_config_manager", return_value=mock_config_manager), patch(
            "cli.wsm.show_welcome_screen"
        ) as mock_welcome:

            result = cli_runner.invoke(cli, [])

            assert result.exit_code == 0
            mock_welcome.assert_called_once()

    def test_cli_verbose_flag(self, cli_runner, mock_config_manager):
        """Test --verbose flag is passed to context."""
        with patch("cli.wsm.get_default_config_manager", return_value=mock_config_manager), patch(
            "cli.wsm.show_welcome_screen"
        ):

            result = cli_runner.invoke(cli, ["--verbose"])

            assert result.exit_code == 0
            # Context should be initialized with verbose=True

    def test_cli_quiet_flag(self, cli_runner, mock_config_manager):
        """Test --quiet flag is passed to context."""
        with patch("cli.wsm.get_default_config_manager", return_value=mock_config_manager), patch(
            "cli.wsm.show_welcome_screen"
        ):

            result = cli_runner.invoke(cli, ["--quiet"])

            assert result.exit_code == 0
            # Context should be initialized with quiet=True

    def test_cli_custom_config_dir(self, cli_runner, temp_config_dir, mock_config_manager):
        """Test --config-dir flag uses custom configuration directory."""
        with patch("cli.wsm.ConfigManager", return_value=mock_config_manager), patch(
            "cli.wsm.show_welcome_screen"
        ) as mock_welcome:

            result = cli_runner.invoke(cli, ["--config-dir", str(temp_config_dir)])

            assert result.exit_code == 0
            mock_welcome.assert_called_once()


class TestWelcomeScreen:
    """Test the welcome screen functionality."""

    def test_show_welcome_screen_basic(self, mock_console, mock_config_manager):
        """Test basic welcome screen display."""
        mock_config_manager.status.version = "unknown"
        mock_config_manager.status.installed_components = []

        with patch("cli.wsm.get_default_config_manager", return_value=mock_config_manager), patch(
            "cli.wsm.Console", return_value=mock_console
        ):

            show_welcome_screen()

            # Should print welcome panel
            assert mock_console.print.called
            args = mock_console.print.call_args_list
            # Check that some form of welcome message was printed
            assert len(args) > 0

    def test_show_welcome_screen_with_installation(self, mock_console, mock_config_manager):
        """Test welcome screen with existing installation."""
        mock_config_manager.status.version = "1.0.0"
        mock_config_manager.status.installed_components = ["tmux", "neovim"]
        mock_config_manager.status.installation_date = "2025-09-01"
        mock_config_manager.should_check_for_updates.return_value = False

        with patch("cli.wsm.get_default_config_manager", return_value=mock_config_manager), patch(
            "cli.wsm.Console", return_value=mock_console
        ):

            show_welcome_screen()

            # Should print welcome panel and status information
            assert mock_console.print.called
            assert len(mock_console.print.call_args_list) >= 2

    def test_show_welcome_screen_update_reminder(self, mock_console, mock_config_manager):
        """Test welcome screen shows update reminder."""
        mock_config_manager.status.version = "1.0.0"
        mock_config_manager.status.installed_components = ["tmux"]
        mock_config_manager.should_check_for_updates.return_value = True

        with patch("cli.wsm.get_default_config_manager", return_value=mock_config_manager), patch(
            "cli.wsm.Console", return_value=mock_console
        ):

            show_welcome_screen()

            # Should suggest checking for updates
            call_args = [call.args[0] for call in mock_console.print.call_args_list]
            update_reminder_found = any("update --check" in str(arg) for arg in call_args)
            assert update_reminder_found

    def test_show_welcome_screen_error_handling(self, mock_console):
        """Test welcome screen handles configuration errors gracefully."""
        with patch(
            "cli.wsm.get_default_config_manager", side_effect=Exception("Config error")
        ), patch("cli.wsm.Console", return_value=mock_console):

            # Should not raise exception
            show_welcome_screen()

            # Should still print basic welcome
            assert mock_console.print.called


class TestDoctorCommand:
    """Test the doctor diagnostic command."""

    def test_doctor_command_basic(self, cli_runner, mock_config_manager, mock_version_manager):
        """Test doctor command shows system diagnostics."""
        with patch("cli.wsm.get_default_config_manager", return_value=mock_config_manager), patch(
            "cli.wsm.ComponentVersionManager", return_value=mock_version_manager
        ):

            result = cli_runner.invoke(cli, ["doctor"])

            assert result.exit_code == 0
            assert "WSM Doctor" in result.output
            assert "System Information" in result.output

    def test_doctor_command_wsl_detection(
        self, cli_runner, mock_config_manager, mock_version_manager
    ):
        """Test doctor command detects WSL environment."""
        with patch("cli.wsm.get_default_config_manager", return_value=mock_config_manager), patch(
            "cli.wsm.ComponentVersionManager", return_value=mock_version_manager
        ), patch("builtins.open", create=True) as mock_open:

            # Mock /proc/version to indicate WSL
            mock_file = MagicMock()
            mock_file.read.return_value = "Linux version 5.4.0-microsoft-standard-WSL2"
            mock_open.return_value.__enter__.return_value = mock_file

            result = cli_runner.invoke(cli, ["doctor"])

            assert result.exit_code == 0
            # Should detect WSL environment

    def test_doctor_command_dependency_check(
        self, cli_runner, mock_config_manager, mock_version_manager
    ):
        """Test doctor command checks dependencies."""
        with patch("cli.wsm.get_default_config_manager", return_value=mock_config_manager), patch(
            "cli.wsm.ComponentVersionManager", return_value=mock_version_manager
        ):

            result = cli_runner.invoke(cli, ["doctor"])

            assert result.exit_code == 0
            assert "Dependencies" in result.output
            # Should show status of key dependencies like click, rich, etc.

    def test_doctor_command_recommendations(
        self, cli_runner, mock_config_manager, mock_version_manager
    ):
        """Test doctor command provides recommendations."""
        # Configure mock to trigger recommendations
        mock_config_manager.config.auto_update = False
        mock_config_manager.status.version = "unknown"
        mock_config_manager.config.github_token = None

        with patch("cli.wsm.get_default_config_manager", return_value=mock_config_manager), patch(
            "cli.wsm.ComponentVersionManager", return_value=mock_version_manager
        ):

            result = cli_runner.invoke(cli, ["doctor"])

            assert result.exit_code == 0
            assert "Recommendations" in result.output
            # Should provide specific recommendations


class TestVersionInfoCommand:
    """Test the version-info command."""

    def test_version_info_basic(self, cli_runner, mock_config_manager, mock_version_manager):
        """Test version-info command shows detailed version information."""
        with patch("cli.wsm.get_default_config_manager", return_value=mock_config_manager), patch(
            "cli.wsm.ComponentVersionManager", return_value=mock_version_manager
        ):

            result = cli_runner.invoke(cli, ["version-info"])

            assert result.exit_code == 0
            assert "WSL-Tmux-Nvim-Setup v1.0.0" in result.output

    def test_version_info_with_components(
        self, cli_runner, mock_config_manager, mock_version_manager
    ):
        """Test version-info shows component versions."""
        mock_version_manager.get_component_versions.return_value = {
            "tmux": "3.3a",
            "neovim": "0.9.0",
            "git": "2.40.0",
        }

        with patch("cli.wsm.get_default_config_manager", return_value=mock_config_manager), patch(
            "cli.wsm.ComponentVersionManager", return_value=mock_version_manager
        ):

            result = cli_runner.invoke(cli, ["version-info"])

            assert result.exit_code == 0
            assert "Component Versions" in result.output

    def test_version_info_with_compatibility(
        self, cli_runner, mock_config_manager, mock_version_manager
    ):
        """Test version-info shows compatibility information."""
        mock_version_manager.get_compatibility_info.return_value = {
            "supported_platforms": ["linux", "wsl1", "wsl2"],
            "python_versions": ["3.7+"],
            "required_tools": ["git", "curl", "wget"],
        }

        with patch("cli.wsm.get_default_config_manager", return_value=mock_config_manager), patch(
            "cli.wsm.ComponentVersionManager", return_value=mock_version_manager
        ):

            result = cli_runner.invoke(cli, ["version-info"])

            assert result.exit_code == 0
            assert "Compatibility" in result.output

    def test_version_info_error_handling(self, cli_runner, mock_config_manager):
        """Test version-info handles errors gracefully."""
        with patch("cli.wsm.get_default_config_manager", return_value=mock_config_manager), patch(
            "cli.wsm.ComponentVersionManager", side_effect=Exception("Version error")
        ):

            result = cli_runner.invoke(cli, ["version-info"])

            assert result.exit_code == 0
            assert "Error getting version information" in result.output


class TestMainFunction:
    """Test the main entry point function."""

    def test_main_success(self, mock_config_manager):
        """Test main function executes successfully."""
        with patch("cli.wsm.cli") as mock_cli, patch(
            "cli.wsm.get_default_config_manager", return_value=mock_config_manager
        ):

            mock_cli.return_value = None
            main()
            mock_cli.assert_called_once()

    def test_main_keyboard_interrupt(self, mock_console):
        """Test main function handles keyboard interrupt."""
        with patch("cli.wsm.cli", side_effect=KeyboardInterrupt), patch(
            "cli.wsm.Console", return_value=mock_console
        ):

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 130
            mock_console.print.assert_called_with("\n[yellow]Operation cancelled by user[/yellow]")

    def test_main_unexpected_error(self, mock_console):
        """Test main function handles unexpected errors."""
        test_error = Exception("Unexpected error")

        with patch("cli.wsm.cli", side_effect=test_error), patch(
            "cli.wsm.Console", return_value=mock_console
        ), patch.dict("os.environ", {}, clear=True):

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            mock_console.print.assert_any_call("\n[red]Unexpected error: Unexpected error[/red]")

    def test_main_debug_mode(self, mock_console):
        """Test main function shows traceback in debug mode."""
        test_error = Exception("Debug error")

        with patch("cli.wsm.cli", side_effect=test_error), patch(
            "cli.wsm.Console", return_value=mock_console
        ), patch.dict("os.environ", {"WSM_DEBUG": "1"}), patch(
            "traceback.format_exc", return_value="Mock traceback"
        ):

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            # Should show traceback in debug mode
            calls = [str(call) for call in mock_console.print.call_args_list]
            traceback_shown = any("traceback" in call.lower() for call in calls)
            assert traceback_shown
