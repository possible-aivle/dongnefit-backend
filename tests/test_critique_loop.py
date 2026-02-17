
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from app.core.agent.sub_agents.content_generator import ContentGenerator
from app.core.agent.models import PolicyIssue, NewsArticle

class TestCritiqueLoop(unittest.TestCase):
    def setUp(self):
        # Prevent actual API calls
        with patch('app.config.settings') as mock_settings:
            mock_settings.openai_api_key = "dummy"
            self.generator = ContentGenerator(llm_provider="openai")

        # Mock LLM
        self.generator.llm = AsyncMock()
        self.generator.llm.ainvoke = AsyncMock()

    def test_critique_flow(self):
        async def run_test():
             # Mock _generate_outline to return a string immediately
            with patch.object(self.generator, '_generate_outline', return_value="Mock Outline") as mock_outline:

                # Mock LLM responses sequence:
                # 1. Draft generation
                # 2. Critique generation
                # 3. Revision generation

                mock_response_draft = MagicMock()
                mock_response_draft.content = "Draft Content"

                mock_response_critique = MagicMock()
                mock_response_critique.content = "Critique: Needs more keywords"

                mock_response_final = MagicMock()
                mock_response_final.content = "Final Revised Content"

                self.generator.llm.ainvoke.side_effect = [
                    mock_response_draft,
                    mock_response_critique,
                    mock_response_final
                ]

                # Dummy Data
                # Need to construct PolicyIssue carefully as it is a Pydantic model
                issue = PolicyIssue(
                    category="traffic",
                    title="Issue 1",
                    sentiment="positive",
                    importance=8,
                    summary="Summary",
                    sources=[]
                )

                # Execute
                final_content = await self.generator._generate_blog_content(
                    region="Gangnam",
                    all_issues=[issue],
                    positive_issues=[issue],
                    negative_issues=[],
                    user_query="Analyze this",
                    needs_classification=True, # Test classification path
                    region_data={"description": "Desc", "target_audience": "Audience", "focus_points": []}
                )

                # Assertions
                # We expect final content to be the revised one
                self.assertEqual(final_content, "Final Revised Content")

                # Verify call count: 1 (draft) + 1 (critique) + 1 (revision) = 3
                # Plus maybe title generation? _generate_blog_content returns content string, title is separate method.
                # Let's check _generate_blog_content code. It returns string.
                # So expect 3 calls.
                self.assertEqual(self.generator.llm.ainvoke.call_count, 3)

                calls = self.generator.llm.ainvoke.call_args_list

                # 1. Draft
                # Check that outline is in the prompt
                draft_prompt = calls[0][0][0][1].content # HumanMessage
                self.assertIn("Mock Outline", self.generator._generate_outline.return_value)

                # 2. Critique
                critique_prompt = calls[1][0][0][1].content
                self.assertIn("Draft Content", critique_prompt) # Draft should be in prompt
                self.assertIn("비평", critique_prompt) # "Critique" instructions

                # 3. Revision
                revision_prompt = calls[2][0][0][1].content
                self.assertIn("Critique: Needs more keywords", revision_prompt) # Critique should be in prompt
                self.assertIn("Draft Content", revision_prompt) # Original draft should be in prompt

        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_test())
        loop.close()

if __name__ == '__main__':
    unittest.main()
