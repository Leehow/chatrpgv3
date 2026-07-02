from chatrpg.ir.source import SourceBlock
from chatrpg.parsers.adventure_compiler import AdventureCompiler
from chatrpg.parsers.ruleset_compiler import RulesetCompiler
from chatrpg.parsers.structured import StructuredExtractionRequest, StructuredExtractionResult


class FakeAdventureExtractor:
    async def extract(
        self,
        request: StructuredExtractionRequest,
        *,
        trace_id: str,
    ) -> StructuredExtractionResult:
        return StructuredExtractionResult(
            task=request.task,
            payload={"units": [], "revelations": [], "clues": []},
        )


class FakeRulesetExtractor:
    async def extract(
        self,
        request: StructuredExtractionRequest,
        *,
        trace_id: str,
    ) -> StructuredExtractionResult:
        return StructuredExtractionResult(
            task=request.task,
            payload={"rule_atoms": [], "procedures": [], "tables": []},
        )


def test_structured_adventure_compiler_returns_ir() -> None:
    async def run_case() -> None:
        block = SourceBlock(
            id="b1",
            document_id="d1",
            page_number=1,
            block_index=0,
            block_kind="text",
            text="source",
            visibility="system",
            sha256="x",
        )
        adventure = await AdventureCompiler(FakeAdventureExtractor()).compile(
            adventure_id="adv",
            system_id="coc7e",
            title="Case",
            blocks=[block],
            trace_id="trc",
        )
        assert adventure.adventure_id == "adv"
        assert len(adventure.units) == 0

    import asyncio

    asyncio.run(run_case())


def test_structured_ruleset_compiler_returns_ir() -> None:
    async def run_case() -> None:
        block = SourceBlock(
            id="b1",
            document_id="d1",
            page_number=1,
            block_index=0,
            block_kind="text",
            text="source",
            visibility="system",
            sha256="x",
        )
        ruleset = await RulesetCompiler(FakeRulesetExtractor()).compile(
            system_id="demo",
            edition="1",
            blocks=[block],
            trace_id="trc",
        )
        assert ruleset.system_id == "demo"
        assert len(ruleset.procedures) == 0

    import asyncio

    asyncio.run(run_case())
