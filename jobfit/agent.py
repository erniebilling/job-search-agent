from agents import Agent, AsyncOpenAI, ModelSettings, OpenAIChatCompletionsModel, set_tracing_disabled

from jobfit.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from jobfit.context import JobFitRunContext
from jobfit.prompts import AGENT_INSTRUCTIONS
from jobfit.tools import read_job_page, search_jobs

set_tracing_disabled(True)


def build_agent() -> Agent[JobFitRunContext]:
    ollama_client = AsyncOpenAI(api_key="ollama", base_url=OLLAMA_BASE_URL)
    ollama_model = OpenAIChatCompletionsModel(model=OLLAMA_MODEL, openai_client=ollama_client)
    return Agent(
        name="JobFit AI",
        model=ollama_model,
        model_settings=ModelSettings(
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
        ),
        tools=[search_jobs, read_job_page],
        instructions=AGENT_INSTRUCTIONS,
    )
