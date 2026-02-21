import os
import sys
import curses
import json
import subprocess
import shutil

REPO_URL = "https://github.com/albrtbc/wsl-tmux-nvim-setup.git"
REPO_DIR = "/tmp/wsl-tmux-nvim-setup"
FORCE_INSTALL = '--force' in sys.argv

def load_components():
    dir_path = os.path.expanduser('~/.config/auto_install/')
    json_path = os.path.join(dir_path, 'components.json')

    with open(json_path, 'r') as file:
        data = json.load(file)
    return data['components']

def clone_repo():
    if os.path.exists(REPO_DIR):
        shutil.rmtree(REPO_DIR)
    subprocess.run(['git', 'clone', REPO_URL, REPO_DIR], check=True)

def cleanup_repo():
    if os.path.exists(REPO_DIR):
        shutil.rmtree(REPO_DIR)

def configure_terminal():
    subprocess.run('stty onlcr', shell=True, check=True)

def is_installed(check_command):
    """Return True if check_command exits 0 (component already installed)."""
    if not check_command:
        return False
    try:
        subprocess.run(check_command, shell=True, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def resolve_dependencies(components, selected):
    """Auto-include dependencies for all selected components.
    Returns (new_selected, auto_added_names)."""
    name_to_idx = {c['name']: i for i, c in enumerate(components)}
    resolved = set(i for i, s in enumerate(selected) if s)

    changed = True
    while changed:
        changed = False
        for i in list(resolved):
            for dep_name in components[i].get('depends_on', []):
                dep_idx = name_to_idx.get(dep_name)
                if dep_idx is not None and dep_idx not in resolved:
                    resolved.add(dep_idx)
                    changed = True

    new_selected = [i in resolved for i in range(len(components))]
    auto_added = [components[i]['name'] for i in sorted(resolved) if not selected[i]]
    return new_selected, auto_added

def topological_sort(components, selected):
    """Return indices of selected components in dependency-first order."""
    name_to_idx = {c['name']: i for i, c in enumerate(components)}
    selected_set = set(i for i, s in enumerate(selected) if s)
    visited = set()
    order = []

    def visit(idx):
        if idx in visited or idx not in selected_set:
            return
        visited.add(idx)
        for dep_name in components[idx].get('depends_on', []):
            dep_idx = name_to_idx.get(dep_name)
            if dep_idx is not None:
                visit(dep_idx)
        order.append(idx)

    for i in range(len(components)):
        if i in selected_set:
            visit(i)

    return order

def run_script(script):
    dir_path = os.path.expanduser('~/.config/auto_install/')
    script_path = os.path.join(dir_path, 'components', script)

    env = os.environ.copy()
    env['REPO_DIR'] = REPO_DIR

    try:
        configure_terminal()
        subprocess.run(['bash', script_path], check=True, env=env)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\nError executing {script_path}: {e}")
        return False
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        return False

def custom_installation(stdscr, components):
    selected = [False] * len(components)
    current = 0
    max_y, max_x = stdscr.getmaxyx()
    if len(components) + 3 > max_y:
        raise RuntimeError("The terminal window is too small to display all components.")

    while True:
        stdscr.clear()
        for i, component in enumerate(components):
            mode = curses.A_NORMAL
            if i == current:
                mode = curses.A_REVERSE
            prefix = '[X] ' if selected[i] else '[ ] '
            stdscr.addstr(i, 0, prefix + component['name'], mode)
        stdscr.addstr(len(components) + 1, 0, "Press 'A' to select/deselect all, 'Enter' to confirm.")
        key = stdscr.getch()
        if key == curses.KEY_UP and current > 0:
            current -= 1
        elif key == curses.KEY_DOWN and current < len(components) - 1:
            current += 1
        elif key == ord(' '):
            selected[current] = not selected[current]
        elif key == ord('a') or key == ord('A'):
            selected = [not all(selected)] * len(components)
        elif key == ord('\n'):
            break
    return selected

def main(stdscr):
    curses.curs_set(0)
    components = load_components()
    selected = custom_installation(stdscr, components)

    if not any(selected):
        stdscr.addstr(len(components) + 2, 0, "No components selected. Press any key to exit.")
        stdscr.getch()
        return

    # Resolve dependencies and sort in dependency-first order
    selected, auto_added = resolve_dependencies(components, selected)
    install_order = topological_sort(components, selected)

    # Exit curses so script output is visible in terminal
    curses.endwin()

    if auto_added:
        print(f"\nAuto-included dependencies: {', '.join(auto_added)}")

    # Clone repo once for all components
    print("\nCloning configuration repository...")
    try:
        clone_repo()
    except subprocess.CalledProcessError as e:
        print(f"Failed to clone repository: {e}")
        return

    # Run selected components in dependency order and track results
    results = {}
    try:
        for i in install_order:
            component = components[i]
            name = component['name']
            check_cmd = component.get('check_command', '')

            # Skip if already installed (unless --force)
            if check_cmd and not FORCE_INSTALL and is_installed(check_cmd):
                print(f"\n[SKIP] {name} is already installed (use --force to reinstall)")
                results[name] = 'skipped'
                continue

            print(f"\n{'='*60}")
            print(f"  Installing: {name}")
            print(f"{'='*60}")
            success = run_script(component['script'])
            results[name] = 'ok' if success else 'failed'
    finally:
        cleanup_repo()

    # Print summary
    print(f"\n{'='*60}")
    print("  INSTALLATION SUMMARY")
    print(f"{'='*60}")
    for name, status in results.items():
        if status == 'ok':
            print(f"  [+] {name}: OK")
        elif status == 'skipped':
            print(f"  [-] {name}: SKIPPED (already installed)")
        else:
            print(f"  [X] {name}: FAILED")

    failed = [n for n, s in results.items() if s == 'failed']
    if failed:
        print(f"\n  {len(failed)} component(s) failed. Re-run to retry.")
    else:
        print("\n  All components installed successfully!")

    input("\nPress Enter to exit.")

try:
    curses.wrapper(main)
except KeyboardInterrupt:
    print("\nInterrupted by user (Ctrl+C). Exiting...")
except RuntimeError as e:
    print(e)
