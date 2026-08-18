FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY prompts/ prompts/
COPY data/ data/
COPY run_eval.py compare_runs.py generate_report.py send_alert.py validate_dataset.py ./

# Written to at runtime -- not baked into the image, so a container run
# produces its own history rather than inheriting one from the build.
RUN mkdir -p runs reports

# Required: GROQ_API_KEY (classifier + judge model calls)
# Optional: SLACK_WEBHOOK_URL (skips the alert step if unset)
# Optional: EVAL_WARNING_THRESHOLD, EVAL_CRITICAL_THRESHOLD (default 0.03 / 0.08)
ENV EVAL_WARNING_THRESHOLD=0.03
ENV EVAL_CRITICAL_THRESHOLD=0.08

ENTRYPOINT ["python"]
CMD ["run_eval.py"]
