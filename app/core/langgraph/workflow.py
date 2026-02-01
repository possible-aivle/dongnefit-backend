"""LangGraph workflow for real estate content generation."""

from typing import TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.config import settings


class ContentState(TypedDict):
    """State for content generation workflow."""

    location: str
    content_type: str
    keywords: list[str]
    additional_context: str | None
    scraped_data: dict | None
    research: str | None
    outline: str | None
    draft: str | None
    final_content: str | None
    title: str | None
    summary: str | None


class ContentGenerationWorkflow:
    """LangGraph workflow for generating real estate content."""

    def __init__(self, provider: str = "openai"):
        """Initialize workflow with LLM provider."""
        if provider == "anthropic" and settings.anthropic_api_key:
            self.llm = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                api_key=settings.anthropic_api_key,
            )
        else:
            self.llm = ChatOpenAI(
                model="gpt-4o",
                api_key=settings.openai_api_key,
            )

        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        workflow = StateGraph(ContentState)

        # Add nodes
        workflow.add_node("research", self._research_node)
        workflow.add_node("outline", self._outline_node)
        workflow.add_node("draft", self._draft_node)
        workflow.add_node("finalize", self._finalize_node)

        # Add edges
        workflow.set_entry_point("research")
        workflow.add_edge("research", "outline")
        workflow.add_edge("outline", "draft")
        workflow.add_edge("draft", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def _research_node(self, state: ContentState) -> ContentState:
        """Research node: Gather and analyze information."""
        system_prompt = """You are a real estate content researcher.
        Analyze the provided location and context to gather relevant information
        for creating engaging real estate content in Korean."""

        user_prompt = f"""
        Location: {state['location']}
        Content Type: {state['content_type']}
        Keywords: {', '.join(state['keywords'])}
        Additional Context: {state.get('additional_context', 'None')}
        Scraped Data: {state.get('scraped_data', 'None')}

        Research and provide key insights about this location for real estate content.
        Focus on: amenities, transportation, lifestyle, property market trends.
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        state["research"] = response.content
        return state

    async def _outline_node(self, state: ContentState) -> ContentState:
        """Outline node: Create content structure."""
        system_prompt = """You are a content strategist for real estate marketing.
        Create a detailed outline for engaging Korean real estate content."""

        user_prompt = f"""
        Based on this research:
        {state['research']}

        Create a detailed outline for a {state['content_type']} about {state['location']}.
        The outline should be in markdown format and include:
        - Engaging title
        - Key sections
        - Main points for each section
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        state["outline"] = response.content
        return state

    async def _draft_node(self, state: ContentState) -> ContentState:
        """Draft node: Write initial content."""
        system_prompt = """You are a professional real estate content writer.
        Write engaging, informative content in Korean for real estate marketing.
        Use markdown formatting for structure."""

        user_prompt = f"""
        Write a complete draft based on this outline:
        {state['outline']}

        Requirements:
        - Write in Korean
        - Use markdown formatting
        - Be engaging and informative
        - Include relevant details about {state['location']}
        - Focus on keywords: {', '.join(state['keywords'])}
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        state["draft"] = response.content
        return state

    async def _finalize_node(self, state: ContentState) -> ContentState:
        """Finalize node: Polish and finalize content."""
        system_prompt = """You are a content editor specializing in real estate.
        Polish the draft to create engaging, professional Korean content.
        Also generate a compelling title and summary."""

        user_prompt = f"""
        Polish this draft into final content:
        {state['draft']}

        Provide:
        1. A compelling title (제목)
        2. The finalized content in markdown
        3. A brief summary (2-3 sentences)

        Format your response as:
        TITLE: [title]
        SUMMARY: [summary]
        CONTENT:
        [full content]
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        content = response.content

        # Parse response
        lines = content.split("\n")
        title = ""
        summary = ""
        final_content = ""

        in_content = False
        for line in lines:
            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
            elif line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
            elif line.startswith("CONTENT:"):
                in_content = True
            elif in_content:
                final_content += line + "\n"

        state["title"] = title or f"{state['location']} 부동산 가이드"
        state["summary"] = summary or "부동산 정보를 담은 콘텐츠입니다."
        state["final_content"] = final_content.strip() or state["draft"]

        return state

    async def run(self, state: ContentState) -> ContentState:
        """Run the content generation workflow."""
        result = await self.graph.ainvoke(state)
        return result
