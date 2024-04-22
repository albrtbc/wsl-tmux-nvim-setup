import os
import curses
import json
import subprocess

def load_components():
    dir_path = os.path.expanduser('~/.config/auto_install/')
    json_path = os.path.join(dir_path, 'components.json')
    
    with open(json_path, 'r') as file:
        data = json.load(file)
    return data['components']

def configure_terminal():
    subprocess.run('stty onlcr', shell=True, check=True)

def run_script(script):
    dir_path = os.path.expanduser('~/.config/auto_install/')
    script_path = os.path.join(dir_path, 'components', script)

    try:
        configure_terminal()
        subprocess.run(['bash', script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing {script_path}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def custom_installation(stdscr, components):
    selected = [False] * len(components)
    current = 0
    max_y, max_x = stdscr.getmaxyx()
    if len(components) + 3 > max_y:  # +3 for the additional lines
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
            selected = [not all(selected)] * len(components)  # Toggle all components
        elif key == ord('\n'):
            break
    return selected

def main(stdscr):
    curses.curs_set(0)
    components = load_components()
    selected = custom_installation(stdscr, components)
    for i, component in enumerate(components):
        if selected[i]:
            run_script(component['script'])

    stdscr.addstr(len(components) + 2, 0, "Installation completed. Press any key to exit.")
    stdscr.getch()

try:
    curses.wrapper(main)
except KeyboardInterrupt:
    print("Interrupted by user (Ctrl+C). Exiting...")
except RuntimeError as e:
    print(e)
