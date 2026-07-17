from agents import (
    Agent,
    AsyncOpenAI,
    ModelSettings,
    OpenAIChatCompletionsModel,
    RunContextWrapper,
    handoff,
    set_tracing_disabled,
)

from jobfit.config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_REPORT_MODEL, OLLAMA_TIMEOUT_SECONDS
from jobfit.context import JobFitRunContext
from jobfit.prompts import REPORT_AGENT_INSTRUCTIONS, SEARCH_AGENT_INSTRUCTIONS
from jobfit.tools import read_job_page, search_jobs

set_tracing_disabled(True)


def _build_model(model_name: str) -> OpenAIChatCompletionsModel:
    ollama_client = AsyncOpenAI(api_key="ollama", base_url=OLLAMA_BASE_URL, timeout=OLLAMA_TIMEOUT_SECONDS)
    return OpenAIChatCompletionsModel(model=model_name, openai_client=ollama_client)


def _model_settings() -> ModelSettings:
    return ModelSettings(
        tool_choice="auto",
        parallel_tool_calls=True,
        # Greedy decoding for more consistent tool choices and report
        # structure run to run. A fixed seed removes the remaining
        # nondeterminism from multi-threaded CPU float reduction order.
        temperature=0,
        # Qwen3.5 is a thinking model: without this it burns its whole
        # completion budget on reasoning_content and can return empty
        # content once a turn's prompt is long enough (confirmed via
        # direct llama-server test, and reproduced in a real run where the
        # final report turn came back empty after all tool calls succeeded).
        extra_body={"chat_template_kwargs": {"enable_thinking": False}, "seed": 42},
    )


def _handoff_to_report_enabled(ctx: RunContextWrapper[JobFitRunContext], agent) -> bool:
    """The handoff becomes available as soon as at least one page has been
    read (so a model that already has good results is not forced to burn its
    whole search/read budget first), and it becomes the only thing left to do
    once search_jobs and read_job_page are both capped, since those tools'
    own is_enabled checks remove them from the toolset at that point."""
    return ctx.context.read_call_count >= 1


def build_agent() -> Agent[JobFitRunContext]:
    """Two agents in a handoff chain instead of one model doing everything.
    search_agent (OLLAMA_MODEL) makes many small turns choosing search
    queries and urls, where a slower but more careful model pays off.
    report_agent (OLLAMA_REPORT_MODEL) makes one large generation over the
    full accumulated context, the single most expensive turn in the run,
    where raw throughput matters more. Defaults to the same model for both
    if OLLAMA_REPORT_MODEL is unset, preserving single-model behavior."""
    report_agent = Agent(
        name="JobFit AI Report Writer",
        model=_build_model(OLLAMA_REPORT_MODEL),
        model_settings=_model_settings(),
        tools=[],
        instructions=REPORT_AGENT_INSTRUCTIONS,
    )
    search_agent = Agent(
        name="JobFit AI Search Agent",
        model=_build_model(OLLAMA_MODEL),
        model_settings=_model_settings(),
        tools=[search_jobs, read_job_page],
        handoffs=[handoff(report_agent, is_enabled=_handoff_to_report_enabled)],
        instructions=SEARCH_AGENT_INSTRUCTIONS,
    )
    return search_agent
