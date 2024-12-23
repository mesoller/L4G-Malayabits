import os
import json
import glob
import click

from src.console import console
from rich.markdown import Markdown
from rich.style import Style


def handle_queue(path, meta, parser, sys_args, paths, allowed_extensions=None):
    queue = []

    log_file = os.path.join(base_dir, "tmp", f"{meta['queue']}_queue.log")
    allowed_extensions = ['.mkv', '.mp4', '.ts']

    if path.endswith('.txt') and meta.get('unit3d'):
        console.print(f"[bold yellow]Detected a text file for queue input: {path}[/bold yellow]")
        if os.path.exists(path):
            safe_file_locations = extract_safe_file_locations(path)
            if safe_file_locations:
                console.print(f"[cyan]Extracted {len(safe_file_locations)} safe file locations from the text file.[/cyan]")
                queue = safe_file_locations
                meta['queue'] = "unit3d"

                # Save the queue to the log file
                try:
                    with open(log_file, 'w') as f:
                        json.dump(queue, f, indent=4)
                    console.print(f"[bold green]Queue log file saved successfully: {log_file}[/bold green]")
                except IOError as e:
                    console.print(f"[bold red]Failed to save the queue log file: {e}[/bold red]")
                    exit(1)
            else:
                console.print("[bold red]No safe file locations found in the text file. Exiting.[/bold red]")
                exit(1)
        else:
            console.print(f"[bold red]Text file not found: {path}. Exiting.[/bold red]")
            exit(1)

    elif path.endswith('.log') and meta['debug']:
        console.print(f"[bold yellow]Processing debugging queue:[/bold yellow] [bold green{path}[/bold green]")
        if os.path.exists(path):
            log_file = path
            with open(path, 'r') as f:
                queue = json.load(f)
                meta['queue'] = "debugging"

        else:
            console.print(f"[bold red]Log file not found: {path}. Exiting.[/bold red]")
            exit(1)

    elif meta.get('queue'):
        meta, help, before_args = parser.parse(tuple(' '.join(sys.argv[1:]).split(' ')), meta)
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                existing_queue = json.load(f)
            console.print(f"[bold yellow]Found an existing queue log file:[/bold yellow] [green]{log_file}[/green]")
            console.print(f"[cyan]The queue log contains {len(existing_queue)} items.[/cyan]")
            console.print("[cyan]Do you want to edit, discard, or keep the existing queue?[/cyan]")
            edit_choice = input("Enter 'e' to edit, 'd' to discard, or press Enter to keep it as is: ").strip().lower()

            if edit_choice == 'e':
                edited_content = click.edit(json.dumps(existing_queue, indent=4))
                if edited_content:
                    try:
                        queue = json.loads(edited_content.strip())
                        console.print("[bold green]Successfully updated the queue from the editor.")
                        with open(log_file, 'w') as f:
                            json.dump(queue, f, indent=4)
                    except json.JSONDecodeError as e:
                        console.print(f"[bold red]Failed to parse the edited content: {e}. Using the original queue.")
                        queue = existing_queue
                else:
                    console.print("[bold red]No changes were made. Using the original queue.")
                    queue = existing_queue
            elif edit_choice == 'd':
                console.print("[bold yellow]Discarding the existing queue log. Creating a new queue.")
                queue = []
            else:
                console.print("[bold green]Keeping the existing queue as is.")
                queue = existing_queue
        else:
            if os.path.exists(path):
                queue = gather_files_recursive(path, allowed_extensions=allowed_extensions)
            else:
                queue = resolve_queue_with_glob_or_split(path, paths, allowed_extensions=allowed_extensions)

            console.print(f"[cyan]A new queue log file will be created:[/cyan] [green]{log_file}[/green]")
            console.print(f"[cyan]The new queue will contain {len(queue)} items.[/cyan]")
            console.print("[cyan]Do you want to edit the initial queue before saving?[/cyan]")
            edit_choice = input("Enter 'e' to edit, or press Enter to save as is: ").strip().lower()

            if edit_choice == 'e':
                edited_content = click.edit(json.dumps(queue, indent=4))
                if edited_content:
                    try:
                        queue = json.loads(edited_content.strip())
                        console.print("[bold green]Successfully updated the queue from the editor.")
                    except json.JSONDecodeError as e:
                        console.print(f"[bold red]Failed to parse the edited content: {e}. Using the original queue.")
                else:
                    console.print("[bold red]No changes were made. Using the original queue.")

            # Save the queue to the log file
            with open(log_file, 'w') as f:
                json.dump(queue, f, indent=4)
            console.print(f"[bold green]Queue log file created: {log_file}[/bold green]")

    elif os.path.exists(path):
        meta, help, before_args = parser.parse(tuple(' '.join(sys.argv[1:]).split(' ')), meta)
        queue = [path]

    else:
        # Search glob if dirname exists
        if os.path.exists(os.path.dirname(path)) and len(paths) <= 1:
            escaped_path = path.replace('[', '[[]')
            globs = glob.glob(escaped_path)
            queue = globs
            if len(queue) != 0:
                md_text = "\n - ".join(queue)
                console.print("\n[bold green]Queuing these files:[/bold green]", end='')
                console.print(Markdown(f"- {md_text.rstrip()}\n\n", style=Style(color='cyan')))
                console.print("\n\n")
            else:
                console.print(f"[red]Path: [bold red]{path}[/bold red] does not exist")

        elif os.path.exists(os.path.dirname(path)) and len(paths) != 1:
            queue = paths
            md_text = "\n - ".join(queue)
            console.print("\n[bold green]Queuing these files:[/bold green]", end='')
            console.print(Markdown(f"- {md_text.rstrip()}\n\n", style=Style(color='cyan')))
            console.print("\n\n")
        elif not os.path.exists(os.path.dirname(path)):
            split_path = path.split()
            p1 = split_path[0]
            for i, each in enumerate(split_path):
                try:
                    if os.path.exists(p1) and not os.path.exists(f"{p1} {split_path[i + 1]}"):
                        queue.append(p1)
                        p1 = split_path[i + 1]
                    else:
                        p1 += f" {split_path[i + 1]}"
                except IndexError:
                    if os.path.exists(p1):
                        queue.append(p1)
                    else:
                        console.print(f"[red]Path: [bold red]{p1}[/bold red] does not exist")
            if len(queue) >= 1:
                md_text = "\n - ".join(queue)
                console.print("\n[bold green]Queuing these files:[/bold green]", end='')
                console.print(Markdown(f"- {md_text.rstrip()}\n\n", style=Style(color='cyan')))
                console.print("\n\n")

        else:
            # Add Search Here
            console.print("[red]There was an issue with your input. If you think this was not an issue, please make a report that includes the full command used.")
            exit()