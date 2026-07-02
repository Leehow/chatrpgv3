from __future__ import annotations

from chatrpg.ir.ruleset import ProcedureSpec, ResourceChangeSpec, RollSpec, RulesetIR


def build_coc7e_native_ruleset() -> RulesetIR:
    return RulesetIR(
        system_id="coc7e",
        edition="7e",
        character_schema={
            "resources": ["hp", "mp", "sanity", "luck"],
            "traits": ["str", "con", "siz", "dex", "app", "int", "pow", "edu"],
            "skills": "percentile",
        },
        resolution_kernels=[
            {"id": "coc7e.percentile_roll_under", "dice": "d100"},
            {"id": "coc7e.bonus_penalty_dice", "dice": "d100_with_tens_selection"},
        ],
        procedures=[
            ProcedureSpec(
                id="coc7e.skill_roll",
                system_id="coc7e",
                name="Skill Roll",
                inputs=["actor_id", "target", "bonus_dice", "penalty_dice"],
                rolls=[RollSpec(id="roll", kernel_id="coc7e.percentile_roll_under")],
                events=["SkillRollResolved"],
            ),
            ProcedureSpec(
                id="coc7e.pushed_roll",
                system_id="coc7e",
                name="Pushed Roll",
                inputs=["actor_id", "target", "stakes"],
                rolls=[RollSpec(id="roll", kernel_id="coc7e.percentile_roll_under")],
                events=["PushedRollResolved"],
            ),
            ProcedureSpec(
                id="coc7e.luck_spend",
                system_id="coc7e",
                name="Luck Spend",
                inputs=["actor_id", "roll", "current_luck"],
                resource_changes=[ResourceChangeSpec(resource_id="luck", expression="-luck_spent", timing="commit")],
                events=["LuckSpent"],
            ),
            ProcedureSpec(
                id="coc7e.sanity_roll",
                system_id="coc7e",
                name="Sanity Roll",
                inputs=["actor_id", "success_loss", "failure_loss"],
                rolls=[RollSpec(id="sanity_roll", kernel_id="coc7e.percentile_roll_under")],
                resource_changes=[ResourceChangeSpec(resource_id="sanity", expression="-sanity_lost", timing="commit")],
                events=["SanityRollResolved", "CharacterResourceChanged"],
            ),
            ProcedureSpec(
                id="coc7e.opposed_roll",
                system_id="coc7e",
                name="Opposed Roll",
                inputs=["attacker_id", "defender_id", "attacker_target", "defender_target"],
                rolls=[RollSpec(id="attacker_roll", kernel_id="coc7e.percentile_roll_under"), RollSpec(id="defender_roll", kernel_id="coc7e.percentile_roll_under")],
                events=["OpposedRollResolved"],
            ),
        ],
    )
