#!/usr/bin/env python3
"""
Auto Install Integration Bridge

Provides seamless integration between the WSM CLI and the existing auto_install system.
"""

import os
import sys
import json
import subprocess
import curses
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.panel import Panel
    from rich.table import Table
    import click
except ImportError as e:
    print(f"Error: Required packages not found: {e}", file=sys.stderr)
    sys.exit(1)


class InstallationMode(Enum):
    """Installation execution modes"""
    INTEGRATED = "integrated"  # Full WSM integration
    HYBRID = "hybrid"          # WSM with auto_install scripts
    LEGACY = "legacy"          # Pure auto_install mode
    CUSTOM = "custom"          # Custom component selection


@dataclass
class ComponentScript:
    """Component installation script information"""
    name: str
    script_path: Path
    description: str = ""
    dependencies: List[str] = None
    estimated_time: int = 60  # seconds
    size_mb: float = 0.0
    optional: bool = True
    category: str = "tools"
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class AutoInstallBridge:
    """Bridge between WSM CLI and auto_install system"""
    
    def __init__(self, config_manager, console: Optional[Console] = None):
        self.config_manager = config_manager
        self.console = console or Console()
        
        # Detect auto_install system
        self.auto_install_dir = self._detect_auto_install_directory()
        self.components_config = self._load_components_config()
        self.component_scripts = self._discover_component_scripts()
        
        # Installation tracking
        self.installation_log = []
        self.failed_components = []
        self.successful_components = []
    
    def _detect_auto_install_directory(self) -> Optional[Path]:
        """Detect auto_install directory"""
        possible_locations = [
            Path.home() / ".config" / "auto_install",
            Path(__file__).parent.parent.parent / "auto_install",
            Path.cwd() / "auto_install"
        ]
        
        for location in possible_locations:
            if location.exists() and (location / "components.json").exists():
                self.console.print(f"[dim]Found auto_install at: {location}[/dim]")
                return location
        
        return None
    
    def _load_components_config(self) -> Dict[str, Any]:
        """Load components configuration"""
        if not self.auto_install_dir:
            return {"components": []}
        
        components_file = self.auto_install_dir / "components.json"
        try:
            with open(components_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not load components config: {e}[/yellow]")
            return {"components": []}
    
    def _discover_component_scripts(self) -> Dict[str, ComponentScript]:
        """Discover available component scripts"""
        scripts = {}
        
        if not self.auto_install_dir:
            return scripts
        
        components_dir = self.auto_install_dir / "components"
        if not components_dir.exists():
            return scripts
        
        # Load from components.json
        for component_data in self.components_config.get("components", []):
            name = component_data["name"].lower()
            script_name = component_data["script"]
            script_path = components_dir / script_name
            
            if script_path.exists():
                scripts[name] = ComponentScript(
                    name=component_data["name"],
                    script_path=script_path,
                    description=self._get_component_description(component_data["name"]),
                    estimated_time=self._estimate_installation_time(name),
                    size_mb=self._estimate_component_size(name),
                    optional=name != "dependencies",
                    category=self._categorize_component(name)
                )
        
        return scripts
    
    def _get_component_description(self, name: str) -> str:
        """Get detailed description for component"""
        descriptions = {
            "Dependencies": "Essential system dependencies including build tools, Python, Node.js, and core utilities",
            "Lazygit": "Terminal-based Git interface with intuitive branching, staging, and commit management",
            "Yazi": "Blazing fast terminal file manager with vim-like keybindings and preview capabilities",
            "NERDFonts": "Comprehensive collection of developer fonts with icons and ligatures for better coding experience",
            "Synth Shell": "Enhanced bash/zsh prompt with Git status, virtual environment, and system information",
            "Tmux": "Terminal multiplexer enabling persistent sessions, window management, and remote development",
            "Neovim": "Modern, extensible text editor with Language Server Protocol support and advanced plugins",
            "Kitty": "GPU-accelerated terminal emulator with advanced features like image display and multiplexing",
            "Git": "Distributed version control system with optimized configuration for development workflows"
        }
        return descriptions.get(name, f"Install and configure {name} for development environment")
    
    def _estimate_installation_time(self, component: str) -> int:
        """Estimate installation time in seconds"""
        times = {
            "dependencies": 300,  # 5 minutes
            "lazygit": 60,       # 1 minute
            "yazi": 120,         # 2 minutes
            "nerdfonts": 180,    # 3 minutes
            "synth shell": 30,   # 30 seconds
            "tmux": 60,          # 1 minute
            "neovim": 240,       # 4 minutes
            "kitty": 120,        # 2 minutes
            "git": 30            # 30 seconds
        }
        return times.get(component, 90)
    
    def _estimate_component_size(self, component: str) -> float:
        """Estimate component size in MB"""
        sizes = {
            "dependencies": 150.0,
            "lazygit": 15.0,
            "yazi": 8.0,
            "nerdfonts": 200.0,
            "synth shell": 2.0,
            "tmux": 5.0,
            "neovim": 25.0,
            "kitty": 30.0,
            "git": 3.0
        }
        return sizes.get(component, 10.0)
    
    def _categorize_component(self, component: str) -> str:
        """Categorize component for organization"""
        categories = {
            "dependencies": "system",
            "git": "tools",
            "lazygit": "tools", 
            "yazi": "tools",
            "nerdfonts": "ui",
            "synth shell": "ui",
            "tmux": "core",
            "neovim": "core",
            "kitty": "terminal"
        }
        return categories.get(component, "other")
    
    def get_available_components(self) -> Dict[str, ComponentScript]:
        """Get available components for installation"""
        return self.component_scripts.copy()
    
    def is_component_installed(self, component_name: str) -> bool:
        """Check if component is already installed"""
        # Use multiple detection methods
        
        # Check through configuration manager
        try:
            status = self.config_manager.status
            if status.installed_components and component_name.lower() in [c.lower() for c in status.installed_components]:
                return True
        except:
            pass
        
        # Check for component-specific indicators
        return self._check_component_specific_installation(component_name.lower())
    
    def _check_component_specific_installation(self, component: str) -> bool:
        """Check component-specific installation indicators"""
        checks = {
            "tmux": lambda: self._command_exists("tmux"),
            "neovim": lambda: self._command_exists("nvim"),
            "lazygit": lambda: self._command_exists("lazygit"),
            "yazi": lambda: self._command_exists("yazi"),
            "kitty": lambda: self._command_exists("kitty"),
            "git": lambda: self._command_exists("git"),
            "nerdfonts": lambda: (Path.home() / ".local" / "share" / "fonts").exists(),
            "synth shell": lambda: (Path.home() / ".config" / "synth-shell").exists()
        }
        
        check_func = checks.get(component)
        if check_func:
            try:
                return check_func()
            except:
                return False
        
        return False
    
    def _command_exists(self, command: str) -> bool:
        """Check if command exists in PATH"""
        try:
            result = subprocess.run(
                ["which", command],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def run_curses_selector(self) -> Optional[List[str]]:
        """Run the legacy curses-based component selector"""
        if not self.auto_install_dir:
            self.console.print("[red]Auto install directory not found[/red]")
            return None
        
        # Import and use the original auto_install main function
        try:
            sys.path.insert(0, str(self.auto_install_dir))
            
            # Create a modified version that returns selections instead of installing
            def custom_main(stdscr):
                curses.curs_set(0)
                components = list(self.component_scripts.values())
                selected = self._curses_select_components(stdscr, components)
                return [comp.name.lower() for i, comp in enumerate(components) if selected[i]]
            
            selected_components = curses.wrapper(custom_main)
            return selected_components
            
        except Exception as e:
            self.console.print(f"[red]Curses selector error: {e}[/red]")
            return None
        finally:
            if str(self.auto_install_dir) in sys.path:
                sys.path.remove(str(self.auto_install_dir))
    
    def _curses_select_components(self, stdscr, components: List[ComponentScript]) -> List[bool]:
        """Enhanced curses component selection"""
        selected = [False] * len(components)
        current = 0
        
        # Auto-select dependencies
        for i, comp in enumerate(components):
            if comp.name.lower() == "dependencies":
                selected[i] = True
        
        max_y, max_x = stdscr.getmaxyx()
        
        # Initialize colors if available
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)   # Header
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Selected
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Required
            curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Category
            curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)    # Warning
        
        while True:
            stdscr.clear()
            
            # Header
            header = "WSL Development Environment - Component Selection"
            try:
                stdscr.addstr(0, (max_x - len(header)) // 2, header, 
                             curses.color_pair(1) | curses.A_BOLD)
            except:
                pass
            
            # Instructions
            instructions = [
                "Use ↑/↓ to navigate, SPACE to select, ENTER to continue",
                "A: Toggle all, I: Show info, Q: Quit"
            ]
            
            for i, instruction in enumerate(instructions):
                try:
                    stdscr.addstr(2 + i, 2, instruction)
                except:
                    pass
            
            # Component list
            start_y = 5
            for i, comp in enumerate(components):
                y = start_y + i
                if y >= max_y - 4:
                    break
                
                # Selection indicator
                indicator = '[X]' if selected[i] else '[ ]'
                
                # Component info
                status_info = ""
                if self.is_component_installed(comp.name):
                    status_info = " (installed)"
                
                # Build display line
                line = f"{indicator} {comp.name}"
                if comp.category != "other":
                    line += f" [{comp.category}]"
                line += status_info
                
                # Truncate if too long
                if len(line) > max_x - 4:
                    line = line[:max_x - 7] + "..."
                
                # Display with appropriate colors
                mode = curses.A_NORMAL
                if i == current:
                    mode = curses.A_REVERSE
                
                color_pair = 0
                if selected[i]:
                    color_pair = 2  # Green for selected
                elif comp.name.lower() == "dependencies":
                    color_pair = 3  # Yellow for required
                
                try:
                    stdscr.addstr(y, 2, line, mode | curses.color_pair(color_pair))
                except:
                    pass
            
            # Summary
            selected_count = sum(selected)
            total_size = sum(comp.size_mb for i, comp in enumerate(components) if selected[i])
            total_time = sum(comp.estimated_time for i, comp in enumerate(components) if selected[i])
            
            summary_lines = [
                f"Selected: {selected_count}/{len(components)} components",
                f"Est. size: ~{total_size:.0f}MB, Est. time: ~{total_time//60}min {total_time%60}s"
            ]
            
            for i, line in enumerate(summary_lines):
                try:
                    stdscr.addstr(max_y - 4 + i, 2, line, curses.color_pair(4))
                except:
                    pass
            
            # Current component details (if space allows)
            if max_y > 25 and current < len(components):
                comp = components[current]
                details = f"Description: {comp.description[:max_x-15]}"
                try:
                    stdscr.addstr(max_y - 2, 2, details[:max_x-4])
                except:
                    pass
            
            stdscr.refresh()
            
            # Handle input
            try:
                key = stdscr.getch()
            except:
                key = ord('q')
            
            if key == curses.KEY_UP and current > 0:
                current -= 1
            elif key == curses.KEY_DOWN and current < len(components) - 1:
                current += 1
            elif key == ord(' '):
                if components[current].name.lower() != "dependencies":
                    selected[current] = not selected[current]
            elif key in [ord('a'), ord('A')]:
                all_optional_selected = all(
                    selected[i] for i, comp in enumerate(components) 
                    if comp.name.lower() != "dependencies"
                )
                for i, comp in enumerate(components):
                    if comp.name.lower() != "dependencies":
                        selected[i] = not all_optional_selected
            elif key in [ord('i'), ord('I')]:
                # Show component info (basic implementation)
                if current < len(components):
                    comp = components[current]
                    info_text = f"{comp.name}: {comp.description}"
                    try:
                        stdscr.addstr(max_y - 1, 2, info_text[:max_x-4], curses.A_BOLD)
                        stdscr.getch()  # Wait for key press
                    except:
                        pass
            elif key in [ord('\n'), ord('\r'), 10]:
                break
            elif key in [ord('q'), ord('Q'), 27]:  # Q or ESC
                return [False] * len(components)
        
        return selected
    
    def install_components(self, component_names: List[str], 
                          mode: InstallationMode = InstallationMode.HYBRID,
                          show_progress: bool = True) -> bool:
        """Install selected components using appropriate method"""
        
        if not component_names:
            self.console.print("[yellow]No components selected for installation[/yellow]")
            return True
        
        self.console.print(f"[blue]Installing {len(component_names)} components using {mode.value} mode[/blue]")
        
        # Validate components
        valid_components = []
        for name in component_names:
            name_lower = name.lower()
            if name_lower in self.component_scripts:
                valid_components.append(name_lower)
            else:
                self.console.print(f"[yellow]Warning: Unknown component '{name}' skipped[/yellow]")
        
        if not valid_components:
            self.console.print("[red]No valid components to install[/red]")
            return False
        
        # Sort components by dependencies (dependencies first)
        def sort_key(comp_name):
            comp = self.component_scripts[comp_name]
            if comp.name.lower() == "dependencies":
                return 0
            elif comp.category == "system":
                return 1
            elif comp.category == "core":
                return 2
            else:
                return 3
        
        valid_components.sort(key=sort_key)
        
        # Install components
        if show_progress:
            total_time = sum(self.component_scripts[name].estimated_time for name in valid_components)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console
            ) as progress:
                
                main_task = progress.add_task("Installing components...", total=len(valid_components))
                
                for i, component_name in enumerate(valid_components):
                    component = self.component_scripts[component_name]
                    
                    progress.update(main_task, description=f"Installing {component.name}...")
                    
                    success = self._install_single_component(component, mode)
                    
                    if success:
                        self.successful_components.append(component_name)
                        progress.console.print(f"[green]✓ {component.name} installed successfully[/green]")
                    else:
                        self.failed_components.append(component_name)
                        progress.console.print(f"[red]✗ {component.name} installation failed[/red]")
                    
                    progress.advance(main_task)
        else:
            # Install without progress display
            for component_name in valid_components:
                component = self.component_scripts[component_name]
                self.console.print(f"Installing {component.name}...")
                
                success = self._install_single_component(component, mode)
                
                if success:
                    self.successful_components.append(component_name)
                    self.console.print(f"[green]✓ {component.name} completed[/green]")
                else:
                    self.failed_components.append(component_name)
                    self.console.print(f"[red]✗ {component.name} failed[/red]")
        
        # Summary
        self._display_installation_summary()
        
        return len(self.failed_components) == 0
    
    def _install_single_component(self, component: ComponentScript, 
                                 mode: InstallationMode) -> bool:
        """Install a single component"""
        
        try:
            if mode in [InstallationMode.HYBRID, InstallationMode.LEGACY]:
                # Use original auto_install script
                return self._run_component_script(component)
            
            elif mode == InstallationMode.INTEGRATED:
                # Use WSM-integrated installation
                return self._run_integrated_installation(component)
            
            else:
                self.console.print(f"[red]Unknown installation mode: {mode}[/red]")
                return False
                
        except Exception as e:
            self.console.print(f"[red]Component installation error: {e}[/red]")
            self.installation_log.append(f"ERROR: {component.name} - {e}")
            return False
    
    def _run_component_script(self, component: ComponentScript) -> bool:
        """Run original component installation script"""
        script_path = component.script_path
        
        if not script_path.exists():
            self.console.print(f"[red]Script not found: {script_path}[/red]")
            return False
        
        # Set up environment
        env = os.environ.copy()
        env['WSM_COMPONENT'] = component.name
        env['WSM_AUTOMATED'] = '1'
        
        try:
            # Make script executable
            script_path.chmod(0o755)
            
            # Run script
            result = subprocess.run(
                [str(script_path)],
                cwd=component.script_path.parent,
                env=env,
                capture_output=True,
                text=True,
                timeout=component.estimated_time * 2  # Allow double the estimated time
            )
            
            # Log output
            self.installation_log.append(f"Component: {component.name}")
            self.installation_log.append(f"Script: {script_path}")
            self.installation_log.append(f"Exit code: {result.returncode}")
            
            if result.stdout:
                self.installation_log.append(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                self.installation_log.append(f"STDERR:\n{result.stderr}")
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            self.console.print(f"[red]Installation timeout for {component.name}[/red]")
            self.installation_log.append(f"TIMEOUT: {component.name}")
            return False
        
        except Exception as e:
            self.console.print(f"[red]Script execution error: {e}[/red]")
            self.installation_log.append(f"SCRIPT ERROR: {component.name} - {e}")
            return False
    
    def _run_integrated_installation(self, component: ComponentScript) -> bool:
        """Run integrated WSM installation for component"""
        # This would implement native WSM installation logic
        # For now, fall back to script execution
        self.console.print(f"[dim]Using script fallback for {component.name}[/dim]")
        return self._run_component_script(component)
    
    def _display_installation_summary(self):
        """Display installation summary"""
        
        # Create summary table
        table = Table(title="Installation Summary")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Category", style="dim")
        
        all_components = self.successful_components + self.failed_components
        
        for comp_name in all_components:
            if comp_name in self.component_scripts:
                comp = self.component_scripts[comp_name]
                status = "✓ Success" if comp_name in self.successful_components else "✗ Failed"
                status_style = "green" if comp_name in self.successful_components else "red"
                
                table.add_row(
                    comp.name,
                    f"[{status_style}]{status}[/{status_style}]",
                    comp.category
                )
        
        self.console.print(table)
        
        # Overall summary
        total = len(all_components)
        successful = len(self.successful_components)
        failed = len(self.failed_components)
        
        if failed == 0:
            self.console.print(f"[green]🎉 All {successful} components installed successfully![/green]")
        else:
            self.console.print(f"[yellow]⚠ {successful}/{total} components succeeded, {failed} failed[/yellow]")
            
            if self.failed_components:
                self.console.print("[red]Failed components:[/red]")
                for comp_name in self.failed_components:
                    if comp_name in self.component_scripts:
                        comp = self.component_scripts[comp_name]
                        self.console.print(f"  • {comp.name}")
    
    def get_installation_log(self) -> List[str]:
        """Get detailed installation log"""
        return self.installation_log.copy()
    
    def save_installation_log(self, log_file: Optional[Path] = None):
        """Save installation log to file"""
        if log_file is None:
            log_dir = Path.home() / ".local" / "share" / "wsl-tmux-nvim-setup" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"auto_install_{int(time.time())}.log"
        
        try:
            with open(log_file, 'w') as f:
                f.write("WSL-Tmux-Nvim-Setup Auto Install Log\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Timestamp: {time.ctime()}\n")
                f.write(f"Successful components: {', '.join(self.successful_components)}\n")
                f.write(f"Failed components: {', '.join(self.failed_components)}\n\n")
                
                for line in self.installation_log:
                    f.write(line + "\n")
            
            self.console.print(f"[dim]Installation log saved to: {log_file}[/dim]")
            
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not save log: {e}[/yellow]")


def create_auto_install_bridge(config_manager, console: Optional[Console] = None) -> AutoInstallBridge:
    """Factory function to create auto install bridge"""
    return AutoInstallBridge(config_manager, console)


if __name__ == "__main__":
    # Test the auto install bridge
    console = Console()
    
    class MockConfigManager:
        class MockStatus:
            installed_components = []
        status = MockStatus()
    
    bridge = create_auto_install_bridge(MockConfigManager(), console)
    
    # Show available components
    components = bridge.get_available_components()
    console.print(f"Found {len(components)} components:")
    
    for name, comp in components.items():
        status = "installed" if bridge.is_component_installed(name) else "available"
        console.print(f"  • {comp.name} [{comp.category}] - {status}")