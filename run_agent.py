import os
import asyncio
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
2. `query_knowledge_graph`: Use this to find information about datasets, models, and past runs.
3. `check_system_health`: Use this to verify if the infra (K8s, API) is healthy.

Always be concise. If you need to plan complex steps, outline them first.
If you are answering a user question, use the Knowledge Graph to ground your answer.
"""

async def main():
    console.print(Panel.fit("[bold blue]AirKube Agentic CLI[/bold blue]\n[green]Powered by LangGraph & OpenAI[/green]"))
    
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[bold red]WARNING: OPENAI_API_KEY not found in environment.[/bold red]")
        console.print("Please set it via `set OPENAI_API_KEY=sk-...` or `.env` file.")
        # We don't exit, just let it fail naturally if they try to use it, or they might set it now.
    
    chat_history = [SystemMessage(content=SYSTEM_PROMPT)]
    
    while True:
        try:
            user_input = console.input("[bold yellow]User > [/bold yellow]")
            if user_input.lower() in ["exit", "quit", "q"]:
                break
            
            chat_history.append(HumanMessage(content=user_input))
            
            console.print("[dim]Agent is thinking...[/dim]")
            
            # Streaming the graph execution
            async for event in app.astream_events({"messages": chat_history}, version="v1"):
                kind = event["event"]
                
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        console.print(content, end="", style="cyan")
                        
                elif kind == "on_tool_start":
                    console.print(f"\n[bold magenta]Using Tool: {event['name']}[/bold magenta]")
                    
                elif kind == "on_tool_end":
                    console.print(f"[dim]Tool Output: {event['data'].get('output')}[/dim]\n")

            # Update history with the final state (simplified for this loop)
            # In a real app, we'd sync the state object properly.
            # Here we just rely on the graph returning the final response in the stream
            # but for the loop context, we should really update `chat_history`.
            
            # Since `app.invoke` returns the final state, let's use that for history management
            # instead of complex stream parsing for history history updates.
            final_state = await app.ainvoke({"messages": chat_history})
            chat_history = final_state["messages"]
            
            # Print final response if not streamed (or just a separator)
            console.print("\n" + "-"*30 + "\n")
            
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    asyncio.run(main())
