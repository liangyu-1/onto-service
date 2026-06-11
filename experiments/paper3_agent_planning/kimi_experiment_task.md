# Experiment Task for Kimi CLI

You are running an experiment for a research paper on LLM agent planning.

## Your Task

Run the Python script `run_experiments.py` with the following parameters:
- Model: kimi-latest (via Kimi API)
- Number of tasks: 10 (or all 40 if time permits)
- Output directory: results_kimi

## Steps

1. First, check if the experiment environment is set up:
   ```bash
   cd /Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning
   source ../../onto-service-python/.venv/bin/activate
   python3 -c "import sys; sys.path.insert(0, 'src'); from llm_client import OpenAIClient; print('OK')"
   ```

2. Modify `src/llm_client.py` to use Kimi API:
   - base_url: https://api.kimi.com/coding/v1
   - api_key: read from `KIMI_API_KEY`
   - model: kimi-latest

3. Run the experiment:
   ```bash
   export KIMI_API_KEY="your-kimi-api-key"
   PYTHONPATH=src:$PYTHONPATH python3 run_experiments.py \
     --model "kimi-latest" \
     --base-url "https://api.kimi.com/coding/v1" \
     --api-key "$KIMI_API_KEY" \
     --num-tasks 10 \
     --output-dir results_kimi
   ```

4. After completion, report:
   - Success rate for Schema-Only
   - Success rate for Ours
   - Total violations and invalid actions for each
   - Any errors encountered

## Important Notes

- The experiment may take 30-60 minutes depending on API speed
- Each task involves multiple LLM calls (planning + repair)
- Results are saved to `results_kimi/` directory
- If the API returns 403 errors, report them immediately
