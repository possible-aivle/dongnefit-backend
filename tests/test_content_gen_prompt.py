import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.agent.sub_agents.content_generator import ContentGenerator
from app.core.agent.models import RegionalAnalysisContent

class TestContentGeneratorPrompt(unittest.IsolatedAsyncioTestCase):
    @patch('app.core.agent.sub_agents.content_generator.ChatOpenAI')
    @patch('app.core.agent.sub_agents.content_generator.OpenAI')
    async def test_gangnam_prompt_injection(self, mock_openai, mock_chat):
        # Setup Mock LLM
        mock_llm_instance = AsyncMock()
        # Mock ainvoke response structure
        mock_response = MagicMock()
        mock_response.content = "Mocked Blog Content"
        mock_llm_instance.ainvoke.return_value = mock_response
        # Mock bind for temperature settings
        mock_llm_instance.bind.return_value = mock_llm_instance

        mock_chat.return_value = mock_llm_instance

        # Initialize
        generator = ContentGenerator()
        # Ensure image generation is off
        generator.ENABLE_IMAGE_GENERATION = False

        # Test Case 1: Gangnam-gu (Strong Signal)
        region = "강남구"
        print(f"\nTesting Region: {region}")

        # Run generation
        await generator.generate_content(
            region=region,
            policy_issues=[],
            user_query="재건축 전망",
            num_images=0
        )

        # Verification
        # Get all calls to ainvoke
        calls = mock_llm_instance.ainvoke.call_args_list
        found_prompt = False

        for call in calls:
            args, _ = call
            messages = args[0] # messages list
            # Check system message (usually first message)
            if hasattr(messages[0], 'content'):
                sys_msg = messages[0].content
                # Look for the injected context marker
                if "[지역 전문 정보]" in sys_msg:
                    found_prompt = True
                    print("\n[Confirmed] Region Context Injected:")
                    print("-" * 20)
                    print(sys_msg)
                    print("-" * 20)

                    # Assertions for specific data from region_prompts.py
                    self.assertIn("대치동 학원가", sys_msg, "Failed to find '대치동 학원가' in prompt")
                    self.assertIn("전문직 실거주자", sys_msg, "Failed to find '전문직 실거주자' in prompt")
                    break

        if not found_prompt:
            self.fail("Could not find '[지역 전문 정보]' context in any LLM call.")

if __name__ == "__main__":
    unittest.main()
