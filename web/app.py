import gradio as gr

from jobfit import db
from jobfit.cv import read_cv

db.init_db()

THEME = gr.themes.Soft(
    primary_hue="emerald",
    secondary_hue="sky",
    neutral_hue="slate",
)


def save_profile(cv_file: str, preferences: str) -> str:
    if not cv_file:
        return "Upload a CV PDF first."
    if not preferences.strip():
        return "Enter job preferences first."

    cv_text, _logs = read_cv(cv_file)
    with open(cv_file, "rb") as f:
        cv_pdf = f.read()

    db.save_profile(
        cv_filename=cv_file.split("/")[-1],
        cv_pdf=cv_pdf,
        cv_text=cv_text,
        preferences=preferences,
    )
    return "Saved. The next scheduled run will use this CV and these preferences."


def load_profile_status() -> str:
    profile = db.get_profile()
    if profile is None or not (profile["cv_text"] or "").strip():
        return "No profile saved yet."
    return f"Current profile: {profile['cv_filename']} (last updated {profile['updated_at']})"


def render_run(run_row) -> str:
    if run_row is None:
        return "No successful runs yet."
    if run_row["status"] != "success":
        return f"Run {run_row['id']} ({run_row['started_at']}) did not succeed: {run_row['error_message']}"
    return run_row["report_markdown"] or "(empty report)"


def get_latest_report() -> str:
    return render_run(db.get_latest_run())


def list_run_choices() -> list[tuple[str, int]]:
    runs = db.list_runs()
    return [(f"#{r['id']} - {r['started_at']} ({r['status']})", r["id"]) for r in runs]


def get_report_for_run(run_id: int | None) -> str:
    if run_id is None:
        return "Select a run above."
    return render_run(db.get_run(run_id))


with gr.Blocks(title="JobFit AI") as demo:
    gr.Markdown(
        """
# JobFit AI

Manage your CV and job preferences, and browse daily job-fit reports.
The job search itself runs automatically once a day; this app only stores your
profile and displays results.
"""
    )

    with gr.Tab("Profile"):
        profile_status = gr.Markdown(load_profile_status())
        with gr.Row():
            cv_input = gr.File(label="CV PDF", file_types=[".pdf"], type="filepath")
            preferences_input = gr.Textbox(
                label="Job preferences",
                lines=8,
                placeholder="Describe role type, industry, remote/location preferences, seniority, and topics.",
            )
        save_button = gr.Button("Save Profile", variant="primary")
        save_status = gr.Markdown()

        save_button.click(
            fn=save_profile,
            inputs=[cv_input, preferences_input],
            outputs=save_status,
        ).then(
            fn=load_profile_status,
            outputs=profile_status,
        )

    with gr.Tab("Latest Report"):
        refresh_latest_button = gr.Button("Refresh")
        latest_report = gr.Markdown(get_latest_report())
        refresh_latest_button.click(fn=get_latest_report, outputs=latest_report)

    with gr.Tab("History"):
        refresh_history_button = gr.Button("Refresh run list")
        run_selector = gr.Dropdown(label="Run", choices=list_run_choices(), type="value")
        history_report = gr.Markdown()

        refresh_history_button.click(fn=list_run_choices, outputs=run_selector)
        run_selector.change(fn=get_report_for_run, inputs=run_selector, outputs=history_report)


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, theme=THEME)
