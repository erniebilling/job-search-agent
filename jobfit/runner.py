from agents import RunConfig, Runner

from jobfit.agent import build_agent
from jobfit.config import MAX_AGENT_TURNS
from jobfit.prompts import RUN_PROMPT_TEMPLATE


def extract_report(text: str) -> str:
    """Strip any narration a local model prepends before the report heading."""
    marker = "# JobFit AI Report"
    index = text.find(marker)
    return text[index:] if index != -1 else text


async def run_jobfit_once(cv_text: str, preferences: str) -> str:
    """Run the JobFit AI agent once and return the final report markdown."""
    prompt = RUN_PROMPT_TEMPLATE.format(cv_text=cv_text, preferences=preferences)
    result = await Runner.run(
        build_agent(),
        prompt,
        max_turns=MAX_AGENT_TURNS,
        run_config=RunConfig(workflow_name="JobFit AI Ollama Search", tracing_disabled=True),
    )
    return extract_report(result.final_output)
