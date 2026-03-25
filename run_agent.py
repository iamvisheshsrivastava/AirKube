import os
import asyncio
from ml.env import load_env

load_env()

from langchain_core.messages import HumanMessage, SystemMessage
from agent.graph import app
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

SYSTEM_PROMPT = """You are the AirKube Supervisor Agent. 
Your goal is to manage the ML Lifecycle and Knowledge Graph for the AirKube platform.

You have access to the following tools:
1. `trigger_ml_pipeline`: Use this to start training or deployment workflows.
2. `trigger_news_data_pipeline`: Use this to start the news ingestion workflow.
3. `query_knowledge_graph`: Use this to find information about datasets, models, and past runs.
4. `check_system_health`: Use this to verify if the infra (K8s, API) is healthy.

Always be concise. If you need to plan complex steps, outline them first.
If you are answering a user question, use the Knowledge Graph to ground your answer.
"""


def _print_stream_event(event):
    kind = event["event"]

    if kind == "on_chat_model_stream":
        content = event["data"]["chunk"].content
        if content:
            console.print(content, end="", style="cyan")
    elif kind == "on_tool_start":
        console.print(f"\n[bold magenta]Using Tool: {event['name']}[/bold magenta]")
    elif kind == "on_tool_end":
        console.print(f"[dim]Tool Output: {event['data'].get('output')}[/dim]\n")


async def _run_turn(chat_history):
    console.print("[dim]Agent is thinking...[/dim]")

    async for event in app.astream_events({"messages": chat_history}, version="v1"):
        _print_stream_event(event)

    final_state = await app.ainvoke({"messages": chat_history})
    return final_state["messages"]

async def main():
    console.print(Panel.fit("[bold blue]AirKube Agentic CLI[/bold blue]\n[green]Powered by LangGraph & Gemini[/green]"))
    
    if not os.getenv("GEMINI_API_KEY"):
        console.print("[bold red]WARNING: GEMINI_API_KEY not found in environment.[/bold red]")
        console.print("Please set it via `set GEMINI_API_KEY=...` or `.env` file.")
        # We don't exit, just let it fail naturally if they try to use it, or they might set it now.
    
    chat_history = [SystemMessage(content=SYSTEM_PROMPT)]
    
    while True:
        try:
            user_input = console.input("[bold yellow]User > [/bold yellow]")
            if user_input.lower() in ["exit", "quit", "q"]:
                break
            
            chat_history.append(HumanMessage(content=user_input))

            chat_history = await _run_turn(chat_history)
            
            # Print final response if not streamed (or just a separator)
            console.print("\n" + "-"*30 + "\n")
            
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    asyncio.run(main())
