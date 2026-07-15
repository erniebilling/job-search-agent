from agents import Agent, AsyncOpenAI, ModelSettings, OpenAIChatCompletionsModel, set_tracing_disabled

from jobfit.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from jobfit.prompts import AGENT_INSTRUCTIONS
from jobfit.tools import read_job_page, search_jobs

set_tracing_disabled(True)


def build_agent() -> Agent:
    ollama_client = AsyncOpenAI(api_key="ollama", base_url=OLLAMA_BASE_URL)
    ollama_model = OpenAIChatCompletionsModel(model=OLLAMA_MODEL, openai_client=ollama_client)
    return Agent(
        name="JobFit AI",
        model=ollama_model,
        model_settings=ModelSettings(
            tool_choice="auto",
            parallel_tool_calls=True,
        ),
        tools=[search_jobs, read_job_page],
        instructions=AGENT_INSTRUCTIONS,
    )
