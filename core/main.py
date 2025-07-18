import requests
import json
import os
from dotenv import load_dotenv

from tools.workflow_agent import run_workflow_planner

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.live import Live
from rich.spinner import Spinner
from rich.align import Align
import threading
import time
import sqlite3 as sql
from datetime import datetime, timezone
import uuid

# Load environment variables
load_dotenv()
console = Console()

# === SQLite Setup ===
connection = sql.connect("chat_history.db")
cursor = connection.cursor()

# Create table if it doesn't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    role TEXT,
    message TEXT,
    session_id TEXT
)
''')
connection.commit()

# Generate unique session ID
session_id = str(uuid.uuid4())

# Save message to DB
def save_to_db(role, message):
    timestamp = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        "INSERT INTO chats (timestamp, role, message, session_id) VALUES (?, ?, ?, ?)",
        (timestamp, role, message, session_id)
    )
    connection.commit()

# === Models ===
models = {
    1: os.getenv("MODEL_1"),
    2: os.getenv("MODEL_2"),
    3: os.getenv("MODEL_3")
}

# === Welcome UI ===
console.rule("[bold blue]🧠 AI Terminal Agent")
console.print("[bold cyan]Welcome to your private terminal agent![/bold cyan]\n")

console.print("[bold yellow]Select a model to use:[/bold yellow]")
console.print("1. Mistral")
console.print("2. Mistral Uncensored")
console.print("3. Kimi K2")
model_choice = IntPrompt.ask("\n[green]Enter model number (1-3)[/green]", choices=["1", "2", "3"])
model = models[int(model_choice)]

# === System Prompt & Temperature ===
default_language = "answer me in only english language do not use any other language in output"
system_base = "you are a powerful assistant which helps me in coding"
system_prompt = f"{system_base}. {default_language}"

temperature = float(Prompt.ask("\n[bold magenta]Enter temperature[/bold magenta] (or leave blank)", default="1"))

# Chat history for reference
chat_history = [{"role": "system", "content": system_prompt}]

console.rule(f"[bold green]Model selected: {model}[/bold green]")

# Spinner animation
def show_spinner(stop_flag):
    spinner = Spinner("dots", text="Thinking... ⏳\n\n\n", style="bold yellow")
    with Live(Align.center(spinner), refresh_per_second=20):
        while not stop_flag["stop"]:
            time.sleep(0.05)

# === Main Loop ===
while True:

    try:
        user_input = Prompt.ask("\n[bold green]You[/bold green]")
        # === Workflow Design Agent Trigger ===
        if user_input.lower().startswith("workflow:"):
            task = user_input.replace("workflow:", "").strip()
            console.print("[bold cyan]🛠 Designing Workflow...[/bold cyan]")

            # Show spinner while thinking
            stop_flag = {"stop": False}
            spinner_thread = threading.Thread(target=show_spinner, args=(stop_flag,))
            spinner_thread.start()

            start_time = time.time()
            try:
                content = run_workflow_planner(task)
            except Exception as e:
                content = f"[Error running workflow agent] {e}"
            finally:
                stop_flag["stop"] = True
                spinner_thread.join()

            end_time = time.time()
            duration_ms = int((end_time - start_time) * 1000)

            # Save and show
            console.print(Panel.fit(content, title="📊 Workflow Planner", border_style="magenta"))
            save_to_db("assistant", content)
            console.print(f"[bold blue]⏱ Total response time: {duration_ms} ms[/bold blue]")
            continue

        if user_input.lower() in ["exit", "quit"]:
            console.print("[bold red]Goodbye![/bold red] 👋")
            break

        # Save user input to memory + DB
        chat_history.append({"role": "user", "content": user_input})
        save_to_db("user", user_input)

        # Spinner start
        stop_flag = {"stop": False}
        spinner_thread = threading.Thread(target=show_spinner, args=(stop_flag,))
        start_time = time.time()
        spinner_thread.start()

        # API Request
        response = requests.post(
            url=os.getenv("URL"),
            headers={
                "Authorization": os.getenv("API_KEY"),
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": model,
                "temperature": temperature,
                "messages": chat_history
            })
        )

        # Stop spinner
        stop_flag["stop"] = True
        spinner_thread.join()

        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)

        # Show result
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']

            chat_history.append({"role": "assistant", "content": content})
            save_to_db("assistant", content)

            console.print(Panel.fit(content, title="🤖 Assistant", border_style="cyan"))
        else:
            console.print(f"[red]Error: {response.status_code}[/red]")
            console.print(response.text)

        console.print(f"[bold blue]⏱ Total response time: {duration_ms} ms[/bold blue]")

    except KeyboardInterrupt:
        console.print("\n[bold red]Session ended.[/bold red]")
        break

# Close DB connection when done
connection.close()
