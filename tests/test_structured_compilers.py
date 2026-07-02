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


class FakeBrokenAdventureExtractor:
    async def extract(
        self,
        request: StructuredExtractionRequest,
        *,
        trace_id: str,
    ) -> StructuredExtractionResult:
        return StructuredExtractionResult(
            task=request.task,
            payload={
                "units": [],
                "revelations": [],
                "clues": [
                    {
                        "id": "c1",
                        "revelation_id": "missing",
                        "carrier_type": "object",
                        "unit_id": "missing_unit",
                        "acquisition": "automatic",
                    }
                ],
            },
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
        block = _block()
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


def test_structured_adventure_compiler_returns_validation_issues() -> None:
    async def run_case() -> None:
        result = await AdventureCompiler(FakeBrokenAdventureExtractor()).compile_validated(
            adventure_id="adv",
            system_id="coc7e",
            title="Case",
            blocks=[_block()],
            trace_id="trc",
        )
        assert {issue.code for issue in result.issues} == {"missing_clue_unit", "missing_clue_revelation"}

    import asyncio

    asyncio.run(run_case())


def test_structured_ruleset_compiler_returns_ir() -> None:
    async def run_case() -> None:
        block = _block()
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


def _block() -> SourceBlock:
    return SourceBlock(
        id="b1",
        document_id="d1",
        page_number=1,
        block_index=0,
        block_kind="text",
        text="source",
        visibility="system",
        sha256="x",
    )
