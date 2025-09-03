#!/usr/bin/env python3
"""
Interactive Installation Wizard for WSL-Tmux-Nvim-Setup CLI

Provides both rich-based and curses-based interactive installation interfaces.
"""

import os
import sys
import json
import curses
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import click
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.layout import Layout
    from rich.align import Align
    from rich.text import Text
    from rich.columns import Columns
except ImportError as e:
    print(f"Error: Required packages not found: {e}", file=sys.stderr)
    sys.exit(1)


class UIMode(Enum):
    """UI interaction modes"""
    RICH = "rich"
    CURSES = "curses"
    AUTO = "auto"


@dataclass
class Component:
    """Component information"""
    name: str
    script: str
    description: str = ""
    category: str = "core"
    size_mb: Optional[float] = None
    dependencies: List[str] = None
    optional: bool = False
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class InstallationSettings:
    """Installation configuration settings"""
    components: List[str]
    installation_path: str
    backup_enabled: bool = True
    auto_update: bool = False
    github_token: Optional[str] = None
    network_timeout: int = 30
    max_retries: int = 3
    parallel_downloads: bool = True
    verify_checksums: bool = True


class InteractiveWizard:
    """Main interactive installation wizard"""
    
    def __init__(self, config_manager, console: Optional[Console] = None):
        self.config_manager = config_manager
        self.console = console or Console()
        self.components = {}
        self.installation_settings = None
        
        # Load component information
        self._load_components()
    
    def _load_components(self):
        """Load component information from various sources"""
        # Load from auto_install components.json
        auto_install_path = Path.home() / ".config" / "auto_install" / "components.json"
        if auto_install_path.exists():
            with open(auto_install_path, 'r') as f:
                data = json.load(f)
                for comp in data.get('components', []):
                    self.components[comp['name'].lower()] = Component(
                        name=comp['name'],
                        script=comp['script'],
                        description=self._get_component_description(comp['name']),
                        category=self._get_component_category(comp['name']),
                        size_mb=self._estimate_component_size(comp['name']),
                        optional=comp['name'].lower() not in ['dependencies']
                    )
        
        # Add additional component metadata
        self._enhance_component_info()
    
    def _get_component_description(self, name: str) -> str:
        """Get description for component"""
        descriptions = {
            'Dependencies': 'Essential system dependencies and build tools',
            'Lazygit': 'Terminal-based Git interface with intuitive UI',
            'Yazi': 'Blazing fast terminal file manager written in Rust',
            'NERDFonts': 'Iconic font aggregator and patches for developers',
            'Synth Shell': 'Enhanced shell prompt with Git integration',
            'Tmux': 'Terminal multiplexer for persistent sessions',
            'Neovim': 'Modern Vim-based text editor with LSP support',
            'Kitty': 'GPU-based terminal emulator with advanced features',
            'Git': 'Distributed version control system configuration'
        }
        return descriptions.get(name, f"{name} component")
    
    def _get_component_category(self, name: str) -> str:
        """Get category for component"""
        categories = {
            'Dependencies': 'system',
            'Git': 'tools',
            'Lazygit': 'tools',
            'Yazi': 'tools',
            'NERDFonts': 'ui',
            'Synth Shell': 'ui',
            'Tmux': 'core',
            'Neovim': 'core',
            'Kitty': 'terminal'
        }
        return categories.get(name, 'other')
    
    def _estimate_component_size(self, name: str) -> float:
        """Estimate component size in MB"""
        sizes = {
            'Dependencies': 50.0,
            'Lazygit': 10.0,
            'Yazi': 5.0,
            'NERDFonts': 200.0,
            'Synth Shell': 1.0,
            'Tmux': 3.0,
            'Neovim': 15.0,
            'Kitty': 25.0,
            'Git': 2.0
        }
        return sizes.get(name, 5.0)
    
    def _enhance_component_info(self):
        """Add dependency information and other metadata"""
        if 'dependencies' in self.components:
            # All components depend on Dependencies
            for comp_name, comp in self.components.items():
                if comp_name != 'dependencies':
                    comp.dependencies.append('dependencies')
        
        # Add specific dependencies
        if 'neovim' in self.components:
            self.components['neovim'].dependencies.extend(['nerdfonts'])
        
        if 'tmux' in self.components:
            self.components['tmux'].dependencies.extend(['git'])
    
    def detect_ui_mode(self) -> UIMode:
        """Detect best UI mode for current environment"""
        # Check if we're in a proper terminal
        if not sys.stdout.isatty():
            return UIMode.RICH
        
        # Check terminal capabilities
        try:
            # Try to get terminal size
            rows, cols = os.get_terminal_size()
            if rows < 20 or cols < 80:
                return UIMode.RICH  # Terminal too small for curses
        except OSError:
            return UIMode.RICH
        
        # Check if curses is available and functional
        try:
            curses.setupterm()
            if curses.tigetnum('colors') < 8:
                return UIMode.RICH  # Limited color support
        except:
            return UIMode.RICH
        
        # Check environment variables
        term = os.environ.get('TERM', '').lower()
        if any(t in term for t in ['screen', 'tmux', 'xterm']):
            return UIMode.CURSES
        
        return UIMode.RICH  # Default to rich UI
    
    def run_wizard(self, ui_mode: UIMode = UIMode.AUTO) -> Optional[InstallationSettings]:
        """Run the interactive installation wizard"""
        if ui_mode == UIMode.AUTO:
            ui_mode = self.detect_ui_mode()
        
        self.console.print("\n[bold blue]🧙‍♂️ WSL-Tmux-Nvim-Setup Installation Wizard[/bold blue]\n")
        
        try:
            if ui_mode == UIMode.CURSES:
                return self._run_curses_wizard()
            else:
                return self._run_rich_wizard()
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Installation wizard cancelled[/yellow]")
            return None
        except Exception as e:
            self.console.print(f"\n[red]Wizard error: {e}[/red]")
            return None
    
    def _run_rich_wizard(self) -> Optional[InstallationSettings]:
        """Run rich-based interactive wizard"""
        
        # Welcome screen
        self._show_welcome_screen()
        
        # Step 1: Component selection
        selected_components = self._rich_select_components()
        if not selected_components:
            return None
        
        # Step 2: Installation path
        install_path = self._rich_get_installation_path()
        if not install_path:
            return None
        
        # Step 3: Configuration options
        config_options = self._rich_get_configuration()
        
        # Step 4: Review and confirm
        settings = InstallationSettings(
            components=selected_components,
            installation_path=install_path,
            **config_options
        )
        
        if self._rich_review_settings(settings):
            return settings
        
        return None
    
    def _run_curses_wizard(self) -> Optional[InstallationSettings]:
        """Run curses-based interactive wizard"""
        try:
            return curses.wrapper(self._curses_main)
        except Exception as e:
            self.console.print(f"[red]Curses interface error: {e}[/red]")
            # Fallback to rich UI
            return self._run_rich_wizard()
    
    def _curses_main(self, stdscr) -> Optional[InstallationSettings]:
        """Main curses interface"""
        curses.curs_set(0)  # Hide cursor
        
        # Initialize colors
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
        
        # Component selection
        selected = self._curses_select_components(stdscr)
        if not selected:
            return None
        
        # Get basic configuration (simplified for curses)
        install_path = str(Path.home() / ".local" / "share" / "wsl-tmux-nvim-setup")
        
        return InstallationSettings(
            components=selected,
            installation_path=install_path,
            backup_enabled=True,
            auto_update=False,
            parallel_downloads=True,
            verify_checksums=True
        )
    
    def _curses_select_components(self, stdscr) -> List[str]:
        """Curses-based component selection (enhanced version of auto_install)"""
        components = list(self.components.values())
        selected = [False] * len(components)
        current = 0
        
        # Pre-select essential components
        for i, comp in enumerate(components):
            if comp.name.lower() == 'dependencies':
                selected[i] = True
        
        max_y, max_x = stdscr.getmaxyx()
        if len(components) + 10 > max_y:
            raise RuntimeError("Terminal window is too small to display all components")
        
        while True:
            stdscr.clear()
            
            # Title
            title = "WSL-Tmux-Nvim-Setup Component Selection"
            stdscr.addstr(0, (max_x - len(title)) // 2, title, 
                         curses.color_pair(1) | curses.A_BOLD)
            
            # Instructions
            stdscr.addstr(2, 2, "Use ↑/↓ to navigate, SPACE to select, A to toggle all, ENTER to continue")
            
            # Component list
            for i, component in enumerate(components):
                y = i + 4
                if y >= max_y - 4:
                    break
                
                mode = curses.A_NORMAL
                if i == current:
                    mode = curses.A_REVERSE
                
                # Selection indicator
                prefix = '[X] ' if selected[i] else '[ ] '
                
                # Component name and description
                text = f"{prefix}{component.name}"
                if len(text) + 3 < max_x:
                    text += f" - {component.description[:max_x - len(text) - 3]}"
                
                # Color coding
                color_pair = curses.color_pair(2) if selected[i] else curses.color_pair(0)
                if component.name.lower() == 'dependencies':
                    color_pair = curses.color_pair(3)  # Yellow for required
                
                try:
                    stdscr.addstr(y, 2, text[:max_x-4], mode | color_pair)
                except curses.error:
                    pass
            
            # Summary
            selected_count = sum(selected)
            total_size = sum(comp.size_mb for i, comp in enumerate(components) if selected[i])
            summary = f"Selected: {selected_count}/{len(components)} components (~{total_size:.0f}MB)"
            try:
                stdscr.addstr(max_y - 3, 2, summary, curses.color_pair(2))
            except curses.error:
                pass
            
            # Help
            help_text = "Press 'A' to select/deselect all, 'Enter' to continue, 'Q' to quit"
            try:
                stdscr.addstr(max_y - 2, 2, help_text[:max_x-4])
            except curses.error:
                pass
            
            stdscr.refresh()
            
            # Handle input
            key = stdscr.getch()
            
            if key == curses.KEY_UP and current > 0:
                current -= 1
            elif key == curses.KEY_DOWN and current < len(components) - 1:
                current += 1
            elif key == ord(' '):
                # Don't allow deselecting dependencies
                if components[current].name.lower() != 'dependencies':
                    selected[current] = not selected[current]
            elif key in (ord('a'), ord('A')):
                # Toggle all (except dependencies)
                all_selected = all(selected[i] for i, comp in enumerate(components) 
                                 if comp.name.lower() != 'dependencies')
                for i, comp in enumerate(components):
                    if comp.name.lower() != 'dependencies':
                        selected[i] = not all_selected
            elif key == ord('\n') or key == ord('\r'):
                break
            elif key in (ord('q'), ord('Q')):
                return []
        
        # Return selected component names
        return [comp.name.lower() for i, comp in enumerate(components) if selected[i]]
    
    def _show_welcome_screen(self):
        """Show welcome screen with system information"""
        # System detection
        system_info = self._detect_system_info()
        
        # Create welcome panel
        welcome_text = Text()
        welcome_text.append("Welcome to the WSL Development Environment Setup!\n\n", style="bold")
        welcome_text.append("This wizard will guide you through installing and configuring:\n")
        welcome_text.append("• Terminal multiplexer (Tmux)\n")
        welcome_text.append("• Modern text editor (Neovim)\n")
        welcome_text.append("• File manager (Yazi)\n")
        welcome_text.append("• Git interface (Lazygit)\n")
        welcome_text.append("• Enhanced shell environment\n")
        welcome_text.append("• Developer fonts and terminal themes\n\n")
        
        if system_info:
            welcome_text.append("System Information:\n", style="bold blue")
            for key, value in system_info.items():
                welcome_text.append(f"• {key}: {value}\n")
        
        panel = Panel(
            welcome_text,
            title="🚀 Installation Wizard",
            border_style="blue"
        )
        
        self.console.print(panel)
        self.console.print()
        
        if not Confirm.ask("Would you like to continue with the installation?", default=True):
            raise KeyboardInterrupt()
    
    def _detect_system_info(self) -> Dict[str, str]:
        """Detect system information"""
        info = {}
        
        # WSL detection
        try:
            with open('/proc/version', 'r') as f:
                version_info = f.read()
                if 'microsoft' in version_info.lower() or 'wsl' in version_info.lower():
                    if 'WSL2' in version_info:
                        info['Environment'] = 'WSL2'
                    else:
                        info['Environment'] = 'WSL1'
                else:
                    info['Environment'] = 'Native Linux'
        except:
            info['Environment'] = 'Unknown'
        
        # Shell detection
        shell = os.environ.get('SHELL', 'unknown')
        info['Shell'] = Path(shell).name if shell != 'unknown' else 'unknown'
        
        # Terminal detection
        term = os.environ.get('TERM', 'unknown')
        info['Terminal'] = term
        
        # Space available
        try:
            import shutil
            total, used, free = shutil.disk_usage(Path.home())
            info['Available Space'] = f"{free // (1024**3):.1f} GB"
        except:
            info['Available Space'] = 'Unknown'
        
        return info
    
    def _rich_select_components(self) -> List[str]:
        """Rich-based component selection"""
        
        self.console.print("[bold]📦 Component Selection[/bold]\n")
        
        # Group components by category
        categories = {}
        for comp in self.components.values():
            if comp.category not in categories:
                categories[comp.category] = []
            categories[comp.category].append(comp)
        
        selected_components = []
        
        # Show components by category
        for category, comps in categories.items():
            category_title = category.title().replace('_', ' ')
            self.console.print(f"\n[bold blue]{category_title} Components:[/bold blue]")
            
            # Create table for category
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Component", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Size", style="yellow")
            table.add_column("Required", style="green")
            
            for comp in comps:
                required = "Yes" if not comp.optional else "No"
                size_str = f"{comp.size_mb:.0f}MB" if comp.size_mb else "Unknown"
                
                table.add_row(
                    comp.name,
                    comp.description[:50] + "..." if len(comp.description) > 50 else comp.description,
                    size_str,
                    required
                )
            
            self.console.print(table)
            
            # Component selection for this category
            for comp in comps:
                if comp.name.lower() == 'dependencies':
                    # Dependencies are always selected
                    selected_components.append(comp.name.lower())
                    self.console.print(f"✓ [green]{comp.name}[/green] (required)")
                else:
                    default = comp.category in ['core', 'tools']
                    if Confirm.ask(f"Install {comp.name}?", default=default):
                        selected_components.append(comp.name.lower())
        
        # Show selection summary
        if selected_components:
            total_size = sum(self.components[name].size_mb or 0 for name in selected_components)
            self.console.print(f"\n[bold green]Selected {len(selected_components)} components (~{total_size:.0f}MB)[/bold green]")
            
            selected_names = [self.components[name].name for name in selected_components]
            columns = Columns(selected_names, equal=True, expand=True)
            self.console.print(Panel(columns, title="Selected Components"))
        
        return selected_components
    
    def _rich_get_installation_path(self) -> Optional[str]:
        """Get installation path from user"""
        self.console.print("\n[bold]📁 Installation Location[/bold]\n")
        
        default_path = str(Path.home() / ".local" / "share" / "wsl-tmux-nvim-setup")
        
        self.console.print(f"Default installation path: [cyan]{default_path}[/cyan]")
        self.console.print("This path will contain all installed components and configurations.\n")
        
        path = Prompt.ask(
            "Installation path",
            default=default_path,
            show_default=True
        )
        
        # Expand and validate path
        expanded_path = Path(path).expanduser().resolve()
        
        # Check if path exists and has contents
        if expanded_path.exists() and any(expanded_path.iterdir()):
            if not Confirm.ask(f"Directory {expanded_path} exists and is not empty. Continue?"):
                return None
        
        # Check if parent directory is writable
        parent = expanded_path.parent
        if not os.access(parent, os.W_OK):
            self.console.print(f"[red]Error: Cannot write to {parent}[/red]")
            return None
        
        return str(expanded_path)
    
    def _rich_get_configuration(self) -> Dict[str, Any]:
        """Get configuration options from user"""
        self.console.print("\n[bold]⚙️ Configuration Options[/bold]\n")
        
        config = {}
        
        # Backup settings
        config['backup_enabled'] = Confirm.ask(
            "Enable automatic backups before updates?",
            default=True
        )
        
        # Auto-update settings
        config['auto_update'] = Confirm.ask(
            "Enable automatic update checking?",
            default=False
        )
        
        # GitHub token (optional)
        self.console.print("\n[dim]GitHub token is optional but recommended for higher API rate limits[/dim]")
        token = Prompt.ask(
            "GitHub personal access token (optional)",
            default="",
            show_default=False,
            password=True
        )
        config['github_token'] = token if token else None
        
        # Network settings
        config['network_timeout'] = 30
        config['max_retries'] = 3
        config['parallel_downloads'] = Confirm.ask(
            "Enable parallel downloads for faster installation?",
            default=True
        )
        config['verify_checksums'] = Confirm.ask(
            "Verify file checksums for security?",
            default=True
        )
        
        return config
    
    def _rich_review_settings(self, settings: InstallationSettings) -> bool:
        """Review installation settings with user"""
        self.console.print("\n[bold]📋 Installation Summary[/bold]\n")
        
        # Create summary table
        table = Table(show_header=False, box=None, padding=(0, 2))
        
        # Components
        component_names = [self.components[name].name for name in settings.components]
        total_size = sum(self.components[name].size_mb or 0 for name in settings.components)
        
        table.add_row("Components:", f"{len(settings.components)} selected (~{total_size:.0f}MB)")
        table.add_row("", ", ".join(component_names[:3]) + 
                     (f" and {len(component_names)-3} more" if len(component_names) > 3 else ""))
        
        # Settings
        table.add_row("Installation Path:", settings.installation_path)
        table.add_row("Backup Enabled:", "Yes" if settings.backup_enabled else "No")
        table.add_row("Auto Updates:", "Yes" if settings.auto_update else "No")
        table.add_row("Parallel Downloads:", "Yes" if settings.parallel_downloads else "No")
        table.add_row("Verify Checksums:", "Yes" if settings.verify_checksums else "No")
        
        if settings.github_token:
            table.add_row("GitHub Token:", "Configured")
        
        panel = Panel(table, title="Installation Configuration", border_style="green")
        self.console.print(panel)
        
        return Confirm.ask("\nProceed with installation?", default=True)


def create_wizard(config_manager, console: Optional[Console] = None) -> InteractiveWizard:
    """Factory function to create installation wizard"""
    return InteractiveWizard(config_manager, console)


if __name__ == "__main__":
    # Test the wizard
    console = Console()
    
    class MockConfigManager:
        pass
    
    wizard = InteractiveWizard(MockConfigManager(), console)
    settings = wizard.run_wizard()
    
    if settings:
        console.print(f"[green]Would install: {settings.components}[/green]")
    else:
        console.print("[yellow]Installation cancelled[/yellow]")