import os
from openai import OpenAI


class LLMClient:
    """OpenAI API client for script generation."""

    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv('LLM_MODEL', 'gpt-4o')
        self.max_tokens = int(os.getenv('LLM_MAX_TOKENS', '4000'))
        self.temperature = float(os.getenv('LLM_TEMPERATURE', '0.7'))

    def generate_script(self, system_prompt, user_prompt):
        """Generate podcast script using OpenAI API."""
        print(f"Generating script with {self.model}...")
        print(f"  Max tokens: {self.max_tokens}, Temperature: {self.temperature}")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )

            script = response.choices[0].message.content
            usage = response.usage

            # Calculate cost (approximate for gpt-4o)
            cost_input = usage.prompt_tokens * 0.0000025  # $2.50 per 1M tokens
            cost_output = usage.completion_tokens * 0.00001  # $10.00 per 1M tokens
            total_cost = cost_input + cost_output

            metadata = {
                'model': self.model,
                'tokens': {
                    'input': usage.prompt_tokens,
                    'output': usage.completion_tokens,
                    'total': usage.total_tokens
                },
                'cost_usd': round(total_cost, 4),
                'finish_reason': response.choices[0].finish_reason
            }

            print(f"✓ Script generated: {usage.completion_tokens} tokens, ${total_cost:.4f}")

            return script, metadata

        except Exception as e:
            print(f"ERROR: OpenAI API failed: {e}")
            raise


    def validate_script(self, script, target_duration_minutes=12):
        """Validate script length and quality."""
        # Rough estimate: 150 words per minute for Polish speech
        words = len(script.split())
        estimated_minutes = words / 150

        print(f"Script validation:")
        print(f"  Words: {words}")
        print(f"  Estimated duration: {estimated_minutes:.1f} minutes")
        print(f"  Target duration: {target_duration_minutes} minutes")

        if estimated_minutes < target_duration_minutes * 0.7:
            print("  WARNING: Script may be too short")
            return False
        elif estimated_minutes > target_duration_minutes * 1.5:
            print("  WARNING: Script may be too long")
            return False

        print("  ✓ Script length is acceptable")
        return True
