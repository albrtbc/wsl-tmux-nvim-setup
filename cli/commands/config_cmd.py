#!/usr/bin/env python3
"""
Config Command for WSL-Tmux-Nvim-Setup CLI

Manages configuration settings and preferences.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import click
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    import yaml
    import json
except ImportError as e:
    print(f"Error: Required packages not found: {e}", file=sys.stderr)
    sys.exit(1)

# Add parent directories to path for imports
CLI_DIR = Path(__file__).parent.parent
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

from config import ConfigManager, UserConfig


class ConfigCommand:
    """Manages configuration commands"""
    
    def __init__(self, config_manager: ConfigManager, console: Console):
        self.config_manager = config_manager
        self.console = console
        
        # Configuration field information for validation and help
        self.config_fields = {
            'auto_update': {
                'type': bool,
                'description': 'Enable automatic updates',
                'values': ['true', 'false']
            },
            'update_frequency': {
                'type': str,
                'description': 'Update check frequency',
                'values': ['daily', 'weekly', 'monthly', 'never']
            },
            'backup_retention': {
                'type': int,
                'description': 'Number of backups to retain',
                'values': 'positive integer'
            },
            'installation_path': {
                'type': str,
                'description': 'Installation directory path',
                'values': 'valid directory path'
            },
            'preferred_components': {
                'type': list,
                'description': 'Preferred components to install',
                'values': 'comma-separated list'
            },
            'github_token': {
                'type': str,
                'description': 'GitHub token for higher API limits',
                'values': 'GitHub personal access token',
                'sensitive': True
            },
            'network_timeout': {
                'type': int,
                'description': 'Network timeout in seconds',
                'values': 'positive integer'
            },
            'max_retries': {
                'type': int,
                'description': 'Maximum retry attempts',
                'values': 'positive integer'
            },
            'show_progress': {
                'type': bool,
                'description': 'Show progress bars',
                'values': ['true', 'false']
            },
            'verbose': {
                'type': bool,
                'description': 'Enable verbose output',
                'values': ['true', 'false']
            },
            'color_output': {
                'type': bool,
                'description': 'Enable colored output',
                'values': ['true', 'false']
            },
            'verify_checksums': {
                'type': bool,
                'description': 'Verify downloaded file checksums',
                'values': ['true', 'false']
            },
            'parallel_downloads': {
                'type': bool,
                'description': 'Enable parallel downloads',
                'values': ['true', 'false']
            },
            'max_concurrent_downloads': {
                'type': int,
                'description': 'Maximum concurrent downloads',
                'values': 'positive integer (1-10)'
            }
        }
    
    def show_config(self, format: str = 'table') -> None:
        """Display current configuration"""
        config = self.config_manager.config
        
        if format == 'table':
            self.console.print("[bold blue]⚙️ Current Configuration[/bold blue]\n")
            
            table = Table()
            table.add_column("Setting", style="cyan", min_width=20)
            table.add_column("Value", style="white")
            table.add_column("Description", style="dim")
            
            config_dict = config.dict()
            
            for key, value in config_dict.items():
                field_info = self.config_fields.get(key, {})
                description = field_info.get('description', 'No description available')
                
                # Handle sensitive fields
                if field_info.get('sensitive') and value:
                    display_value = "***hidden***"
                else:
                    display_value = str(value)
                
                # Color-code values
                if isinstance(value, bool):
                    display_value = f"[green]{display_value}[/green]" if value else f"[red]{display_value}[/red]"
                elif isinstance(value, list):
                    if value:
                        display_value = f"[yellow]{', '.join(map(str, value))}[/yellow]"
                    else:
                        display_value = "[dim]empty[/dim]"
                
                table.add_row(key, display_value, description)
            
            self.console.print(table)
            
        elif format == 'yaml':
            config_dict = config.dict()
            # Hide sensitive values
            for key, field_info in self.config_fields.items():
                if field_info.get('sensitive') and config_dict.get(key):
                    config_dict[key] = "***hidden***"
            
            yaml_output = yaml.dump(config_dict, default_flow_style=False, indent=2)
            self.console.print("[bold]Configuration (YAML):[/bold]")
            self.console.print(f"[dim]{yaml_output}[/dim]")
            
        elif format == 'json':
            config_dict = config.dict()
            # Hide sensitive values
            for key, field_info in self.config_fields.items():
                if field_info.get('sensitive') and config_dict.get(key):
                    config_dict[key] = "***hidden***"
            
            json_output = json.dumps(config_dict, indent=2)
            self.console.print("[bold]Configuration (JSON):[/bold]")
            self.console.print(f"[dim]{json_output}[/dim]")
    
    def set_config_value(self, key: str, value: str) -> None:
        """Set a configuration value"""
        if key not in self.config_fields:
            available_keys = ', '.join(self.config_fields.keys())
            raise click.ClickException(f"Unknown configuration key: {key}\nAvailable keys: {available_keys}")
        
        field_info = self.config_fields[key]
        field_type = field_info['type']
        
        # Convert value to appropriate type
        try:
            if field_type == bool:
                if value.lower() in ['true', '1', 'yes', 'on']:
                    converted_value = True
                elif value.lower() in ['false', '0', 'no', 'off']:
                    converted_value = False
                else:
                    raise ValueError(f"Invalid boolean value: {value}")
                    
            elif field_type == int:
                converted_value = int(value)
                
                # Validate ranges for specific fields
                if key in ['backup_retention'] and converted_value < 0:
                    raise ValueError("backup_retention must be non-negative")
                elif key in ['network_timeout', 'max_retries'] and converted_value <= 0:
                    raise ValueError(f"{key} must be positive")
                elif key == 'max_concurrent_downloads' and not (1 <= converted_value <= 10):
                    raise ValueError("max_concurrent_downloads must be between 1 and 10")
                    
            elif field_type == str:
                converted_value = value
                
                # Validate specific string fields
                if key == 'update_frequency' and converted_value not in ['daily', 'weekly', 'monthly', 'never']:
                    raise ValueError("update_frequency must be one of: daily, weekly, monthly, never")
                    
            elif field_type == list:
                # Handle list values (comma-separated)
                if value.strip():
                    converted_value = [item.strip() for item in value.split(',')]
                else:
                    converted_value = []
                    
            else:
                converted_value = value
            
            # Update configuration
            self.config_manager.update_config(**{key: converted_value})
            
            # Show confirmation
            display_value = converted_value
            if field_info.get('sensitive') and converted_value:
                display_value = "***hidden***"
            
            self.console.print(f"[green]✓ Set {key} = {display_value}[/green]")
            
        except ValueError as e:
            raise click.ClickException(f"Invalid value for {key}: {e}")
        except Exception as e:
            raise click.ClickException(f"Failed to set {key}: {e}")
    
    def get_config_value(self, key: str) -> None:
        """Get a specific configuration value"""
        if key not in self.config_fields:
            available_keys = ', '.join(self.config_fields.keys())
            raise click.ClickException(f"Unknown configuration key: {key}\nAvailable keys: {available_keys}")
        
        config = self.config_manager.config
        value = getattr(config, key)
        
        field_info = self.config_fields[key]
        description = field_info.get('description', 'No description available')
        
        # Handle sensitive fields
        if field_info.get('sensitive') and value:
            display_value = "***hidden***"
        else:
            display_value = str(value)
        
        self.console.print(f"[bold]{key}[/bold]: [green]{display_value}[/green]")
        self.console.print(f"[dim]{description}[/dim]")
    
    def interactive_config(self) -> None:
        """Interactive configuration setup"""
        self.console.print("[bold blue]🔧 Interactive Configuration Setup[/bold blue]\n")
        
        current_config = self.config_manager.config.dict()
        changes = {}
        
        # Group settings by category
        categories = {
            'Update Settings': [
                'auto_update', 'update_frequency', 'backup_retention'
            ],
            'Installation Settings': [
                'installation_path', 'preferred_components'
            ],
            'Network Settings': [
                'github_token', 'network_timeout', 'max_retries'
            ],
            'UI Preferences': [
                'show_progress', 'verbose', 'color_output'
            ],
            'Advanced Settings': [
                'verify_checksums', 'parallel_downloads', 'max_concurrent_downloads'
            ]
        }
        
        for category, settings in categories.items():
            self.console.print(f"\n[bold]{category}[/bold]")
            
            if not Confirm.ask(f"Configure {category.lower()}?", default=False):
                continue
            
            for setting in settings:
                if setting not in self.config_fields:
                    continue
                
                field_info = self.config_fields[setting]
                current_value = current_config[setting]
                description = field_info.get('description', '')
                
                self.console.print(f"\n[cyan]{setting}[/cyan] - {description}")
                self.console.print(f"Current value: [yellow]{current_value}[/yellow]")
                
                if isinstance(field_info.get('values'), list):
                    self.console.print(f"Valid values: {', '.join(field_info['values'])}")
                elif isinstance(field_info.get('values'), str):
                    self.console.print(f"Expected: {field_info['values']}")
                
                # Get new value
                if field_info['type'] == bool:
                    new_value = Confirm.ask("Enable this setting?", default=current_value)
                    if new_value != current_value:
                        changes[setting] = new_value
                else:
                    prompt_text = f"New value (press Enter to keep current)"
                    if field_info.get('sensitive'):
                        new_value = Prompt.ask(prompt_text, password=True, default="")
                    else:
                        new_value = Prompt.ask(prompt_text, default="")
                    
                    if new_value and new_value != str(current_value):
                        try:
                            if field_info['type'] == int:
                                changes[setting] = int(new_value)
                            elif field_info['type'] == list:
                                changes[setting] = [item.strip() for item in new_value.split(',')]
                            else:
                                changes[setting] = new_value
                        except ValueError as e:
                            self.console.print(f"[red]Invalid value: {e}[/red]")
        
        # Apply changes
        if changes:
            self.console.print(f"\n[bold]Summary of changes:[/bold]")
            for key, value in changes.items():
                display_value = value if not self.config_fields[key].get('sensitive') else "***hidden***"
                self.console.print(f"  {key}: [yellow]{display_value}[/yellow]")
            
            if Confirm.ask("\nApply these changes?", default=True):
                try:
                    self.config_manager.update_config(**changes)
                    self.console.print(f"[green]✓ Configuration updated successfully[/green]")
                except Exception as e:
                    self.console.print(f"[red]Failed to update configuration: {e}[/red]")
            else:
                self.console.print("Configuration changes cancelled")
        else:
            self.console.print("[dim]No changes made[/dim]")
    
    def reset_config(self) -> None:
        """Reset configuration to defaults"""
        if Confirm.ask("Reset all configuration to defaults? This cannot be undone.", default=False):
            try:
                self.config_manager.reset_config()
                self.console.print("[green]✓ Configuration reset to defaults[/green]")
            except Exception as e:
                self.console.print(f"[red]Failed to reset configuration: {e}[/red]")
        else:
            self.console.print("Reset cancelled")
    
    def export_config(self, output_file: Path, format: str = 'yaml') -> None:
        """Export configuration to file"""
        try:
            if format == 'yaml':
                output_file = output_file.with_suffix('.yml')
            elif format == 'json':
                output_file = output_file.with_suffix('.json')
            
            self.config_manager.export_config(output_file)
            self.console.print(f"[green]✓ Configuration exported to {output_file}[/green]")
            
        except Exception as e:
            self.console.print(f"[red]Failed to export configuration: {e}[/red]")
    
    def import_config(self, input_file: Path) -> None:
        """Import configuration from file"""
        if not input_file.exists():
            raise click.ClickException(f"File not found: {input_file}")
        
        try:
            self.console.print(f"[blue]Importing configuration from {input_file}...[/blue]")
            self.config_manager.import_config(input_file)
            self.console.print("[green]✓ Configuration imported successfully[/green]")
            
        except Exception as e:
            raise click.ClickException(f"Failed to import configuration: {e}")
    
    def show_help(self) -> None:
        """Show configuration help"""
        self.console.print("[bold blue]⚙️ Configuration Help[/bold blue]\n")
        
        for category, settings in [
            ('Update Settings', ['auto_update', 'update_frequency', 'backup_retention']),
            ('Installation Settings', ['installation_path', 'preferred_components']),
            ('Network Settings', ['github_token', 'network_timeout', 'max_retries']),
            ('UI Preferences', ['show_progress', 'verbose', 'color_output']),
            ('Advanced Settings', ['verify_checksums', 'parallel_downloads', 'max_concurrent_downloads'])
        ]:
            self.console.print(f"[bold]{category}[/bold]")
            
            for setting in settings:
                if setting not in self.config_fields:
                    continue
                
                field_info = self.config_fields[setting]
                description = field_info.get('description', 'No description')
                
                values_info = ""
                if isinstance(field_info.get('values'), list):
                    values_info = f" (values: {', '.join(field_info['values'])})"
                elif isinstance(field_info.get('values'), str):
                    values_info = f" ({field_info['values']})"
                
                self.console.print(f"  [cyan]{setting}[/cyan]: {description}{values_info}")
            
            self.console.print()


@click.group(invoke_without_command=True)
@click.pass_context
def config(ctx):
    """
    Manage WSM configuration settings
    
    \b
    Examples:
        wsm config                  # Show current configuration
        wsm config set auto_update true    # Set a configuration value
        wsm config get auto_update          # Get a configuration value
        wsm config interactive              # Interactive configuration
        wsm config reset                    # Reset to defaults
        wsm config export config.yml       # Export configuration
        wsm config import config.yml       # Import configuration
    
    Configuration manages various aspects of WSM behavior including
    update settings, network preferences, and UI options.
    """
    if ctx.invoked_subcommand is None:
        # Show current configuration if no subcommand
        ctx.invoke(show)


@config.command()
@click.option('--format', '-f', type=click.Choice(['table', 'yaml', 'json']),
              default='table', help='Output format')
@click.pass_obj
def show(ctx_obj, format):
    """Show current configuration"""
    config_cmd = ConfigCommand(ctx_obj.config_manager, ctx_obj.console)
    config_cmd.show_config(format=format)


@config.command()
@click.argument('key')
@click.argument('value')
@click.pass_obj
def set(ctx_obj, key, value):
    """Set a configuration value"""
    config_cmd = ConfigCommand(ctx_obj.config_manager, ctx_obj.console)
    config_cmd.set_config_value(key, value)


@config.command()
@click.argument('key')
@click.pass_obj
def get(ctx_obj, key):
    """Get a configuration value"""
    config_cmd = ConfigCommand(ctx_obj.config_manager, ctx_obj.console)
    config_cmd.get_config_value(key)


@config.command()
@click.pass_obj
def interactive(ctx_obj):
    """Interactive configuration setup"""
    config_cmd = ConfigCommand(ctx_obj.config_manager, ctx_obj.console)
    config_cmd.interactive_config()


@config.command()
@click.pass_obj
def reset(ctx_obj):
    """Reset configuration to defaults"""
    config_cmd = ConfigCommand(ctx_obj.config_manager, ctx_obj.console)
    config_cmd.reset_config()


@config.command()
@click.argument('output_file', type=click.Path())
@click.option('--format', '-f', type=click.Choice(['yaml', 'json']),
              default='yaml', help='Export format')
@click.pass_obj
def export(ctx_obj, output_file, format):
    """Export configuration to file"""
    config_cmd = ConfigCommand(ctx_obj.config_manager, ctx_obj.console)
    config_cmd.export_config(Path(output_file), format=format)


@config.command(name='import')
@click.argument('input_file', type=click.Path(exists=True))
@click.pass_obj
def import_config(ctx_obj, input_file):
    """Import configuration from file"""
    config_cmd = ConfigCommand(ctx_obj.config_manager, ctx_obj.console)
    config_cmd.import_config(Path(input_file))


@config.command()
@click.pass_obj
def help(ctx_obj):
    """Show detailed configuration help"""
    config_cmd = ConfigCommand(ctx_obj.config_manager, ctx_obj.console)
    config_cmd.show_help()


if __name__ == '__main__':
    config()