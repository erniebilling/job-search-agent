import logging

from agents import RunConfig, Runner

from jobfit.agent import build_agent
from jobfit.config import MAX_AGENT_TURNS
from jobfit.context import JobFitRunContext
from jobfit.prompts import RUN_PROMPT_TEMPLATE

log = logging.getLogger(__name__)

_FORCE_REPORT_MESSAGE = (
    "You did not write the report. Instead you wrote text that looks like a tool call, "
    "but no tools are available anymore. Do not call or describe any tool. Using only the "
    "search results and pages already in this conversation, write the final report now in "
    "the exact Markdown structure from your instructions, starting with '# JobFit AI Report'."
)


def extract_report(text: str) -> str:
    """Strip any narration a local model prepends before the report heading."""
    marker = "# JobFit AI Report"
    index = text.find(marker)
    if index == -1:
        log.warning(
            "Report marker %r not found in final_output (%d chars); returning unstripped text",
            marker,
            len(text),
        )
    return text[index:] if index != -1 else text


def _looks_like_hallucinated_tool_call(text: str) -> bool:
    """Detect a model writing tool-call syntax as plain text instead of using a
    real tool call or writing the report. Observed twice: once as a single
    <tool_call> block, once as five stacked <tool_call> blocks requesting
    read_job_page after it had already been capped and removed from the
    model's toolset."""
    return "# JobFit AI Report" not in text and "<tool_call>" in text


async def run_jobfit_once(cv_text: str, preferences: str) -> tuple[str, set[str]]:
    """Run the JobFit AI agent once and return the final report markdown plus the
    set of URLs it actually observed via search_jobs/read_job_page, so the report
    can be checked against ground truth instead of trusting the model's output."""
    prompt = RUN_PROMPT_TEMPLATE.format(cv_text=cv_text, preferences=preferences)
    log.info("Running agent, prompt length=%d chars, max_turns=%d", len(prompt), MAX_AGENT_TURNS)
    run_context = JobFitRunContext()
    agent = build_agent()
    run_config = RunConfig(workflow_name="JobFit AI Ollama Search", tracing_disabled=True)
    result = await Runner.run(
        agent,
        prompt,
        context=run_context,
        max_turns=MAX_AGENT_TURNS,
        run_config=run_config,
    )

    if _looks_like_hallucinated_tool_call(result.final_output):
        log.warning(
            "final_output looks like a hallucinated tool call instead of a report "
            "(%d chars); forcing one more turn with an explicit instruction",
            len(result.final_output),
        )
        follow_up_input = result.to_input_list() + [{"role": "user", "content": _FORCE_REPORT_MESSAGE}]
        result = await Runner.run(
            result.last_agent,
            follow_up_input,
            context=run_context,
            max_turns=3,
            run_config=run_config,
        )
        log.info("Forced report retry finished, final_output length=%d chars", len(result.final_output))

    num_items = len(getattr(result, "new_items", []) or [])
    log.info("Agent finished, generated %d run items, final_output length=%d chars", num_items, len(result.final_output))
    log.info(
        "Agent observed %d distinct URLs during the run, called search_jobs %d times",
        len(run_context.seen_urls),
        run_context.search_call_count,
    )
    return extract_report(result.final_output), run_context.seen_urls
