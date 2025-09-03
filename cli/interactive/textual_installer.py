#!/usr/bin/env python3
"""
Textual-based Advanced Installation Interface

Provides a modern TUI experience for WSL-Tmux-Nvim-Setup installation.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
    from textual.screen import Screen
    from textual.widgets import (
        Button,
        Checkbox,
        Footer,
        Header,
        Input,
        Label,
        ListItem,
        ListView,
        ProgressBar,
        SelectionList,
    )
except ImportError as e:
    print(f"Error: Textual not available: {e}", file=sys.stderr)
    # Fall back to rich-only implementation
    textual_available = False
else:
    textual_available = True


if textual_available:

    class ComponentSelectionScreen(Screen):
        """Component selection screen"""

        BINDINGS = [
            ("escape", "back", "Back"),
            ("ctrl+c", "quit", "Quit"),
        ]

        def __init__(self, components: Dict[str, Any]):
            super().__init__()
            self.components = components
            self.selected = set()

        def compose(self) -> ComposeResult:
            """Create the component selection interface"""

            with Container():
                yield Header()

                with Vertical():
                    yield Label("Select Components to Install", classes="title")

                    # Create selection list
                    options = []
                    for name, comp in self.components.items():
                        size_info = (
                            f" (~{comp.get('size_mb', 5):.0f}MB)" if comp.get("size_mb") else ""
                        )
                        display_text = f"{comp['name']}{size_info}"
                        comp.get("description", "No description available")

                        # Mark required components
                        if comp.get("required", False) or name == "dependencies":
                            display_text += " [REQUIRED]"
                            self.selected.add(name)

                        options.append((display_text, name, comp.get("required", False)))

                    selection_list = SelectionList(*options)
                    selection_list.select_all()  # Start with all selected
                    yield selection_list

                    with Horizontal():
                        yield Button("Select All", id="select_all")
                        yield Button("Select None", id="select_none")
                        yield Button("Continue", id="continue", variant="primary")
                        yield Button("Back", id="back")

                yield Footer()

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """Handle button presses"""
            button_id = event.button.id
            selection_list = self.query_one(SelectionList)

            if button_id == "select_all":
                selection_list.select_all()
            elif button_id == "select_none":
                selection_list.deselect_all()
                # Keep required components selected
                for i, (_, name, required) in enumerate(selection_list._options):
                    if required or name == "dependencies":
                        selection_list.select(i)
            elif button_id == "continue":
                self.selected = set(selection_list.selected)
                self.dismiss(self.selected)
            elif button_id == "back":
                self.dismiss(None)

    class ConfigurationScreen(Screen):
        """Configuration options screen"""

        BINDINGS = [
            ("escape", "back", "Back"),
            ("ctrl+c", "quit", "Quit"),
        ]

        def __init__(self):
            super().__init__()
            self.config = {}

        def compose(self) -> ComposeResult:
            """Create configuration interface"""

            with Container():
                yield Header()

                with ScrollableContainer():
                    yield Label("Configuration Options", classes="title")

                    with Vertical():
                        # Installation path
                        yield Label("Installation Path:")
                        default_path = str(Path.home() / ".local" / "share" / "wsl-tmux-nvim-setup")
                        yield Input(
                            value=default_path,
                            placeholder="Installation directory",
                            id="install_path",
                        )

                        # Backup options
                        yield Label("Backup Settings:")
                        yield Checkbox("Enable automatic backups", value=True, id="backup_enabled")
                        yield Checkbox("Auto-update checking", value=False, id="auto_update")

                        # Network options
                        yield Label("Network Settings:")
                        yield Checkbox("Parallel downloads", value=True, id="parallel_downloads")
                        yield Checkbox("Verify checksums", value=True, id="verify_checksums")

                        # GitHub token (optional)
                        yield Label("GitHub Token (optional, for higher API limits):")
                        yield Input(placeholder="ghp_...", password=True, id="github_token")

                        # Action buttons
                        with Horizontal():
                            yield Button("Continue", id="continue", variant="primary")
                            yield Button("Back", id="back")

                yield Footer()

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """Handle button presses"""
            if event.button.id == "continue":
                self.config = {
                    "installation_path": self.query_one("#install_path", Input).value,
                    "backup_enabled": self.query_one("#backup_enabled", Checkbox).value,
                    "auto_update": self.query_one("#auto_update", Checkbox).value,
                    "parallel_downloads": self.query_one("#parallel_downloads", Checkbox).value,
                    "verify_checksums": self.query_one("#verify_checksums", Checkbox).value,
                    "github_token": self.query_one("#github_token", Input).value or None,
                }
                self.dismiss(self.config)
            elif event.button.id == "back":
                self.dismiss(None)

    class InstallationProgressScreen(Screen):
        """Installation progress screen"""

        def __init__(self, components: List[str], config: Dict[str, Any]):
            super().__init__()
            self.components = components
            self.config = config
            self.current_step = 0
            self.total_steps = len(components) + 2  # +2 for download and setup

        def compose(self) -> ComposeResult:
            """Create installation progress interface"""

            with Container():
                yield Header()

                with Vertical():
                    yield Label("Installing WSL Development Environment", classes="title")

                    # Overall progress
                    yield Label("Overall Progress:", id="overall_label")
                    yield ProgressBar(total=self.total_steps, id="overall_progress")

                    # Current step
                    yield Label("Current Step:", id="step_label")
                    yield ProgressBar(total=100, id="step_progress")

                    # Status log
                    yield Label("Installation Log:")
                    with ScrollableContainer(id="log_container"):
                        yield ListView(id="log_list")

                    # Control buttons
                    with Horizontal():
                        yield Button("Cancel", id="cancel", variant="error")
                        yield Button("Hide Details", id="toggle_details")

                yield Footer()

        def on_mount(self) -> None:
            """Start installation process"""
            self.run_worker(self.install_components)

        async def install_components(self) -> None:
            """Install selected components"""
            log_list = self.query_one("#log_list", ListView)
            overall_progress = self.query_one("#overall_progress", ProgressBar)
            step_progress = self.query_one("#step_progress", ProgressBar)
            step_label = self.query_one("#step_label", Label)

            try:
                # Step 1: Download assets
                step_label.update("Downloading installation files...")
                await log_list.append(ListItem(Label("Starting download...")))

                # Simulate download progress
                for i in range(0, 101, 10):
                    step_progress.update(progress=i)
                    await asyncio.sleep(0.1)

                self.current_step += 1
                overall_progress.update(progress=self.current_step)
                await log_list.append(ListItem(Label("✓ Download completed")))

                # Step 2: Install components
                for i, component in enumerate(self.components):
                    step_label.update(f"Installing {component}...")
                    await log_list.append(ListItem(Label(f"Installing {component}...")))

                    # Simulate component installation
                    for progress in range(0, 101, 20):
                        step_progress.update(progress=progress)
                        await asyncio.sleep(0.2)

                    self.current_step += 1
                    overall_progress.update(progress=self.current_step)
                    await log_list.append(ListItem(Label(f"✓ {component} installed successfully")))

                # Final step: Configuration
                step_label.update("Finalizing configuration...")
                await log_list.append(ListItem(Label("Configuring environment...")))

                for i in range(0, 101, 25):
                    step_progress.update(progress=i)
                    await asyncio.sleep(0.1)

                await log_list.append(ListItem(Label("✓ Installation completed successfully!")))
                step_label.update("Installation Complete")

                # Update buttons
                cancel_btn = self.query_one("#cancel", Button)
                cancel_btn.label = "Finish"
                cancel_btn.variant = "success"

            except Exception as e:
                await log_list.append(
                    ListItem(Label(f"✗ Installation failed: {e}", classes="error"))
                )
                step_label.update("Installation Failed")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """Handle button presses"""
            if event.button.id == "cancel":
                if event.button.label == "Finish":
                    self.dismiss(True)
                else:
                    self.dismiss(False)
            elif event.button.id == "toggle_details":
                log_container = self.query_one("#log_container")
                if log_container.styles.display == "none":
                    log_container.styles.display = "block"
                    event.button.label = "Hide Details"
                else:
                    log_container.styles.display = "none"
                    event.button.label = "Show Details"

    class WSMInstallerApp(App):
        """Main Textual application for WSM installation"""

        CSS_PATH = None  # We'll define styles inline

        BINDINGS = [
            ("d", "toggle_dark", "Toggle dark mode"),
            ("q", "quit", "Quit"),
        ]

        def __init__(self, components: Dict[str, Any]):
            super().__init__()
            self.components = components
            self.selected_components = set()
            self.config = {}

        def compose(self) -> ComposeResult:
            """Create the main interface"""

            with Container():
                yield Header()

                with Vertical():
                    yield Label("WSL-Tmux-Nvim-Setup Installer", classes="title")

                    with Container(id="welcome_screen"):
                        yield Label(
                            "Welcome to the interactive installer!\n\n"
                            "This tool will help you install and configure a modern "
                            "WSL development environment with:\n"
                            "• Terminal multiplexer (Tmux)\n"
                            "• Modern text editor (Neovim)\n"
                            "• File manager (Yazi)\n"
                            "• Git interface (Lazygit)\n"
                            "• Enhanced shell environment\n"
                            "• Developer fonts and themes\n\n"
                            "Click 'Start Installation' to begin."
                        )

                        with Horizontal():
                            yield Button("Start Installation", id="start", variant="primary")
                            yield Button("Exit", id="exit")

                yield Footer()

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """Handle button presses"""
            if event.button.id == "start":
                self.start_installation()
            elif event.button.id == "exit":
                self.exit()

        async def start_installation(self) -> None:
            """Start the installation process"""

            # Step 1: Component selection
            selection_screen = ComponentSelectionScreen(self.components)
            selected = await self.push_screen_wait(selection_screen)

            if selected is None:
                return  # User cancelled

            self.selected_components = selected

            # Step 2: Configuration
            config_screen = ConfigurationScreen()
            config = await self.push_screen_wait(config_screen)

            if config is None:
                return  # User cancelled

            self.config = config

            # Step 3: Installation
            progress_screen = InstallationProgressScreen(
                list(self.selected_components), self.config
            )
            success = await self.push_screen_wait(progress_screen)

            if success:
                self.notify("Installation completed successfully!", severity="information")
            else:
                self.notify("Installation cancelled or failed", severity="warning")

            # Return to main screen or exit
            self.exit()

        def action_toggle_dark(self) -> None:
            """Toggle dark mode"""
            self.dark = not self.dark

    class TextualInstaller:
        """Textual-based installer interface"""

        def __init__(self, components: Dict[str, Any]):
            if not textual_available:
                raise RuntimeError("Textual UI not available")

            self.components = components
            self.app = None

        def run(self) -> Optional[Dict[str, Any]]:
            """Run the textual installer"""
            try:
                self.app = WSMInstallerApp(self.components)
                self.app.run()

                # Return installation results
                if hasattr(self.app, "selected_components") and self.app.selected_components:
                    return {
                        "components": list(self.app.selected_components),
                        "config": self.app.config,
                    }

            except Exception as e:
                print(f"Textual UI error: {e}")
                return None

            return None

else:
    # Fallback when textual is not available
    class TextualInstaller:
        def __init__(self, components: Dict[str, Any]):
            raise RuntimeError("Textual UI not available. Install with: pip install textual")

        def run(self) -> Optional[Dict[str, Any]]:
            return None


def create_textual_installer(components: Dict[str, Any]) -> TextualInstaller:
    """Factory function to create textual installer"""
    return TextualInstaller(components)


if __name__ == "__main__":
    # Test the textual installer
    sample_components = {
        "dependencies": {
            "name": "Dependencies",
            "description": "Essential system dependencies and build tools",
            "required": True,
            "size_mb": 50.0,
        },
        "tmux": {
            "name": "Tmux",
            "description": "Terminal multiplexer for persistent sessions",
            "required": False,
            "size_mb": 3.0,
        },
        "neovim": {
            "name": "Neovim",
            "description": "Modern Vim-based text editor with LSP support",
            "required": False,
            "size_mb": 15.0,
        },
    }

    if textual_available:
        installer = create_textual_installer(sample_components)
        result = installer.run()
        print(f"Installation result: {result}")
    else:
        print("Textual not available for testing")
