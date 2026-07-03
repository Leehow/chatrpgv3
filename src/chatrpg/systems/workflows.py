from __future__ import annotations

from chatrpg.ir.workflow import WorkflowPhaseSpec, WorkflowSpec, WorkflowTransitionSpec


def workflow_for_system(system_id: str) -> WorkflowSpec | None:
    workflows = {
        "coc7e": build_coc7e_workflow(),
        "triangle_agency": build_triangle_agency_workflow(),
        "cyberpunk_red": build_cyberpunk_red_workflow(),
    }
    return workflows.get(system_id)


def build_coc7e_workflow() -> WorkflowSpec:
    return WorkflowSpec(
        id="coc7e.default_workflow",
        system_id="coc7e",
        label="Call of Cthulhu 7e default play workflow",
        initial_phase_id="coc7e.character_creation",
        phases=[
            WorkflowPhaseSpec(
                id="coc7e.character_creation",
                label="Investigator Creation",
                kind="character_creation",
                description="Create investigators, calculate derived resources, choose occupation and skills, then commit CharacterCreated events.",
                allows_adventure=False,
            ),
            WorkflowPhaseSpec(
                id="coc7e.investigation",
                label="Investigation Play",
                kind="free_play",
                description="Run scenes, clues, skill checks, sanity checks, combat, chase, recovery, and development through runtime procedures.",
                allows_adventure=True,
            ),
            WorkflowPhaseSpec(
                id="coc7e.development",
                label="Investigator Development",
                kind="advancement",
                description="Resolve experience checks, learning, recovery, and between-case changes.",
                allows_adventure=False,
            ),
        ],
        transitions=[
            WorkflowTransitionSpec(
                id="coc7e.character_creation_to_investigation",
                from_phase_id="coc7e.character_creation",
                to_phase_id="coc7e.investigation",
                guard="party_exists",
                automatic=True,
                description="Once at least one investigator exists, the session may enter the adventure investigation loop.",
            )
        ],
    )


def build_triangle_agency_workflow() -> WorkflowSpec:
    return WorkflowSpec(
        id="triangle_agency.default_workflow",
        system_id="triangle_agency",
        label="Triangle Agency default workday workflow",
        initial_phase_id="triangle.agent_creation",
        phases=[
            WorkflowPhaseSpec(
                id="triangle.agent_creation",
                label="Agent ARC Setup",
                kind="character_creation",
                description="Build each Agent's ARC and starting employment profile before mission play.",
                allows_adventure=False,
            ),
            WorkflowPhaseSpec(
                id="triangle.morning_briefing",
                label="Morning Briefing",
                kind="briefing",
                description="Report to work, receive mission briefing, objectives, equipment context, and Agency framing.",
                allows_adventure=True,
            ),
            WorkflowPhaseSpec(
                id="triangle.field_work",
                label="Field Work",
                kind="free_play",
                description="Investigate the anomaly, manage chaos, conflict, harm, and field objectives.",
                allows_adventure=True,
            ),
            WorkflowPhaseSpec(
                id="triangle.mission_report",
                label="Mission Report",
                kind="debrief",
                description="Resolve mission report, checklist, outcomes, and employment consequences.",
                allows_adventure=False,
            ),
        ],
        transitions=[
            WorkflowTransitionSpec(
                id="triangle.agent_creation_to_morning_briefing",
                from_phase_id="triangle.agent_creation",
                to_phase_id="triangle.morning_briefing",
                guard="party_exists",
                automatic=True,
                description="After Agents exist, begin the workday briefing phase.",
            ),
            WorkflowTransitionSpec(
                id="triangle.morning_briefing_to_field_work",
                from_phase_id="triangle.morning_briefing",
                to_phase_id="triangle.field_work",
                guard="manual",
                automatic=False,
                description="The GM or runtime advances after briefing objectives are accepted.",
            ),
            WorkflowTransitionSpec(
                id="triangle.field_work_to_mission_report",
                from_phase_id="triangle.field_work",
                to_phase_id="triangle.mission_report",
                guard="manual",
                automatic=False,
                description="The runtime advances after anomaly outcome is resolved.",
            ),
        ],
    )


def build_cyberpunk_red_workflow() -> WorkflowSpec:
    return WorkflowSpec(
        id="cyberpunk_red.default_workflow",
        system_id="cyberpunk_red",
        label="Cyberpunk RED default gig workflow",
        initial_phase_id="red.character_creation",
        phases=[
            WorkflowPhaseSpec(
                id="red.character_creation",
                label="Edgerunner Creation",
                kind="character_creation",
                description="Choose role, method, stats, skills, outfit, lifepath, gear, and cyberware before the gig.",
                allows_adventure=False,
            ),
            WorkflowPhaseSpec(
                id="red.gig_play",
                label="Gig Play",
                kind="free_play",
                description="Run scenes, skill checks, combat time, netrunning, wound states, recovery, and payment through runtime procedures.",
                allows_adventure=True,
            ),
            WorkflowPhaseSpec(
                id="red.downtime",
                label="Downtime",
                kind="downtime",
                description="Handle healing, therapy, hustle, shopping, repairs, lifestyle, and reputation updates.",
                allows_adventure=False,
            ),
        ],
        transitions=[
            WorkflowTransitionSpec(
                id="red.character_creation_to_gig_play",
                from_phase_id="red.character_creation",
                to_phase_id="red.gig_play",
                guard="party_exists",
                automatic=True,
                description="Once at least one edgerunner exists, begin the gig play loop.",
            )
        ],
    )
