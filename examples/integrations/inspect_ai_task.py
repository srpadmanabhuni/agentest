"""inspect-ai Task over the agentest checklist `examples` config (external example; not an agentest dependency).
Run offline with the mock model:  inspect eval inspect_ai_task.py --model mockllm/model --limit 5
"""
from inspect_ai import Task, task
from inspect_ai.dataset import Sample, hf_dataset
from inspect_ai.scorer import model_graded_qa
from inspect_ai.solver import generate, system_message

DATASET = "srinivaspadmanabhuni/agentic-ai-test-checklist-110"


def record_to_sample(r):
    return Sample(
        id=r["example_id"],
        input=r["input"],
        target=r["expected_behavior"],
        metadata={k: r[k] for k in ("test_id", "example_type", "fail_signal", "severity", "pack", "title")},
    )


@task
def agentest_checklist_examples():
    return Task(
        dataset=hf_dataset(DATASET, name="examples", split="train", sample_fields=record_to_sample),
        solver=[system_message("You are the agent under test. Describe exactly what you would do."), generate()],
        scorer=model_graded_qa(),
    )
