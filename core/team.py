from core.agent_registry import build_agent
from rich.console import Console

console = Console()

def run_team_workflow(task: str, config, on_switch=None):
    """
    Run a task through a multi-agent team sequentially:
    1. Planner
    2. Writer
    3. Code Reviewer
    """
    # 1. Planner
    if on_switch:
        on_switch("Planner", "Breaking down the task into an implementation plan.")
    planner = build_agent("planner", config)
    console.print("[blue]>> Planner is analyzing...[/blue]")
    plan = planner.run(task)
    
    # 2. Writer
    if on_switch:
        on_switch("Writer", "Writing code based on the plan.")
    writer = build_agent("writer", config)
    writer_task = f"Implement the following plan:\n\n{plan}"
    console.print("[blue]>> Writer is implementing...[/blue]")
    impl = writer.run(writer_task)
    
    # 3. Code Reviewer
    if on_switch:
        on_switch("Reviewer", "Reviewing the implementation for errors.")
    reviewer = build_agent("code_reviewer", config)
    reviewer_task = f"Review the recent implementation for this task: {task}\n\n{impl}"
    console.print("[blue]>> Reviewer is checking...[/blue]")
    review = reviewer.run(reviewer_task)
    
    return review
