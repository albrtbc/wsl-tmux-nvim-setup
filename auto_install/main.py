import os
import curses
import json
import subprocess
import shutil

REPO_URL = "https://github.com/albrtbc/wsl-tmux-nvim-setup.git"
REPO_DIR = "/tmp/wsl-tmux-nvim-setup"

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

    selected_components = [(i, c) for i, c in enumerate(components) if selected[i]]
    if not selected_components:
        stdscr.addstr(len(components) + 2, 0, "No components selected. Press any key to exit.")
        stdscr.getch()
        return

    # Exit curses so script output is visible in terminal
    curses.endwin()

    # Clone repo once for all components
    print("\nCloning configuration repository...")
    try:
        clone_repo()
    except subprocess.CalledProcessError as e:
        print(f"Failed to clone repository: {e}")
        return

    # Run selected components and track results
    results = {}
    try:
        for i, component in selected_components:
            print(f"\n{'='*60}")
            print(f"  Installing: {component['name']}")
            print(f"{'='*60}")
            success = run_script(component['script'])
            results[component['name']] = success
    finally:
        cleanup_repo()

    # Print summary
    print(f"\n{'='*60}")
    print("  INSTALLATION SUMMARY")
    print(f"{'='*60}")
    for name, success in results.items():
        symbol = "+" if success else "X"
        status = "OK" if success else "FAILED"
        print(f"  [{symbol}] {name}: {status}")

    failed = [n for n, s in results.items() if not s]
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
